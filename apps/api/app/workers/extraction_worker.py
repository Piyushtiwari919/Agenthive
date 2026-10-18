import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import get_settings
from app.domain.enums import ExtractionStatus
from app.domain.tenant import TenantScope
from app.extraction.base import ExtractionPayload, ExtractorProvider
from app.extraction.canonicalizer import canonicalize_entity, extract_keywords, normalize_predicate
from app.extraction.deterministic_extractor import DeterministicExtractor
from app.extraction.gemini_extractor import GeminiExtractor
from app.extraction.ollama_extractor import OllamaExtractor
from app.repositories.control_repository import get_control_repository
from app.repositories.memory_repository import get_memory_repository

logger = logging.getLogger(__name__)


class ExtractionOrchestrator:
    """
    Executes semantic & procedural extraction for an episode and persists results to FalkorDB.
    Implements NFR-004 & C-03: if the configured provider is unavailable or simulated outage is active,
    the episode remains safely persisted and extraction is marked DEFERRED for later enrichment.
    """

    def __init__(self) -> None:
        self._deterministic = DeterministicExtractor()
        self._gemini = GeminiExtractor()
        self._ollama = OllamaExtractor()
        self._simulate_outage_override: Optional[bool] = None

    def set_simulate_outage(self, simulate: Optional[bool]) -> None:
        self._simulate_outage_override = simulate

    def is_outage_simulated(self) -> bool:
        if self._simulate_outage_override is not None:
            return self._simulate_outage_override
        return get_settings().extraction_simulate_outage

    def get_active_provider(self) -> ExtractorProvider:
        provider_name = get_settings().extraction_provider
        if provider_name == "gemini":
            return self._gemini
        if provider_name == "ollama":
            return self._ollama
        return self._deterministic

    def process_episode_extraction(
        self,
        scope: TenantScope,
        episode_id: str,
        content: str,
        episode_timestamp: datetime,
        attempt_count: int = 0,
    ) -> ExtractionStatus:
        mem_repo = get_memory_repository()
        provider = self.get_active_provider()

        if self.is_outage_simulated():
            retry_time = datetime.now(timezone.utc) + timedelta(seconds=5)
            mem_repo.update_episode_extraction_status(scope, episode_id, ExtractionStatus.DEFERRED)
            mem_repo.upsert_extraction_job(
                scope=scope,
                episode_id=episode_id,
                status=ExtractionStatus.DEFERRED,
                provider=provider.provider_name,
                attempt_count=attempt_count + 1,
                retry_after=retry_time,
                last_error_category="ProviderOutageSimulated",
            )
            return ExtractionStatus.DEFERRED

        try:
            payload: ExtractionPayload = provider.extract(content)
            self._persist_extraction_payload(scope, episode_id, episode_timestamp, payload)
            mem_repo.update_episode_extraction_status(scope, episode_id, ExtractionStatus.COMPLETED)
            mem_repo.upsert_extraction_job(
                scope=scope,
                episode_id=episode_id,
                status=ExtractionStatus.COMPLETED,
                provider=provider.provider_name,
                attempt_count=attempt_count + 1,
                last_error_category="",
            )
            return ExtractionStatus.COMPLETED
        except Exception as exc:
            logger.warning(
                "Extraction provider failed; marking episode DEFERRED",
                extra={"error_category": exc.__class__.__name__, "operation": "extract_episode"},
            )
            next_attempt = attempt_count + 1
            max_attempts = get_settings().extraction_max_attempts
            status = (
                ExtractionStatus.DEFERRED
                if next_attempt < max_attempts
                else ExtractionStatus.FAILED
            )
            backoff_sec = min(30, 2**next_attempt)
            retry_time = datetime.now(timezone.utc) + timedelta(seconds=backoff_sec)
            mem_repo.update_episode_extraction_status(scope, episode_id, status)
            mem_repo.upsert_extraction_job(
                scope=scope,
                episode_id=episode_id,
                status=status,
                provider=provider.provider_name,
                attempt_count=next_attempt,
                retry_after=retry_time,
                last_error_category=exc.__class__.__name__,
            )
            return status

    def _persist_extraction_payload(
        self,
        scope: TenantScope,
        episode_id: str,
        episode_timestamp: datetime,
        payload: ExtractionPayload,
    ) -> None:
        mem_repo = get_memory_repository()
        entity_name_to_id: dict[str, str] = {}

        for ent_item in payload.entities:
            c_key, c_name, c_type, aliases = canonicalize_entity(
                ent_item.name, ent_item.entity_type, ent_item.aliases
            )
            record = mem_repo.upsert_canonical_entity(
                scope=scope,
                canonical_key=c_key,
                canonical_name=c_name,
                entity_type=c_type,
                aliases=aliases,
                source_episode_id=episode_id,
            )
            entity_name_to_id[c_name.lower()] = record.id
            entity_name_to_id[c_key] = record.id

        for fact_item in payload.facts:
            c_key, c_name, c_type, aliases = canonicalize_entity(
                fact_item.subject_name, fact_item.subject_type
            )
            subj_id = entity_name_to_id.get(c_key)
            if not subj_id:
                subj_ent = mem_repo.upsert_canonical_entity(
                    scope=scope,
                    canonical_key=c_key,
                    canonical_name=c_name,
                    entity_type=c_type,
                    aliases=aliases,
                    source_episode_id=episode_id,
                )
                subj_id = subj_ent.id
                entity_name_to_id[c_key] = subj_id

            obj_ent_id: Optional[str] = None
            if fact_item.object_entity_name:
                ok_key, ok_name, ok_type, ok_aliases = canonicalize_entity(
                    fact_item.object_entity_name, "Component"
                )
                obj_ent_id = entity_name_to_id.get(ok_key)
                if not obj_ent_id:
                    obj_ent = mem_repo.upsert_canonical_entity(
                        scope=scope,
                        canonical_key=ok_key,
                        canonical_name=ok_name,
                        entity_type=ok_type,
                        aliases=ok_aliases,
                        source_episode_id=episode_id,
                    )
                    obj_ent_id = obj_ent.id
                    entity_name_to_id[ok_key] = obj_ent_id

            mem_repo.record_fact_with_conflict_resolution(
                scope=scope,
                subject_entity_id=subj_id,
                subject_name=c_name,
                predicate=normalize_predicate(fact_item.predicate),
                object_value=fact_item.object_value.strip(),
                source_episode_id=episode_id,
                observed_at=episode_timestamp,
                confidence=fact_item.confidence,
                object_entity_id=obj_ent_id,
            )

        for proc_item in payload.procedures:
            keywords = extract_keywords(f"{proc_item.name} {proc_item.trigger_text}")
            mem_repo.upsert_procedure(
                scope=scope,
                name=proc_item.name,
                trigger_text=proc_item.trigger_text,
                trigger_keywords=keywords,
                steps=proc_item.steps,
                source_episode_id=episode_id,
                confirmed_by_user=False,
            )

    def drain_pending_jobs_for_tenant(self, scope: TenantScope, limit: int = 50) -> int:
        mem_repo = get_memory_repository()
        due_jobs = mem_repo.fetch_due_extraction_jobs(scope, limit=limit)
        processed = 0
        for _job_id, ep_id, content, ep_ts_iso, attempt_count in due_jobs:
            status = self.process_episode_extraction(
                scope=scope,
                episode_id=ep_id,
                content=content,
                episode_timestamp=datetime.fromisoformat(ep_ts_iso),
                attempt_count=attempt_count,
            )
            if status == ExtractionStatus.COMPLETED:
                processed += 1
        return processed


extraction_orchestrator = ExtractionOrchestrator()


async def background_extraction_loop(stop_event: asyncio.Event) -> None:
    """
    Background worker coroutine that polls due ExtractionJob nodes across registered tenants.
    """
    settings = get_settings()
    control_repo = get_control_repository()
    while not stop_event.is_set():
        try:
            if not extraction_orchestrator.is_outage_simulated():
                tenants = control_repo.list_tenants()
                for t in tenants:
                    scope = TenantScope(
                        tenant_id=t.tenant_id,
                        graph_name=t.graph_name,
                        display_name=t.display_name,
                        is_demo=t.is_demo,
                    )
                    await asyncio.to_thread(
                        extraction_orchestrator.drain_pending_jobs_for_tenant, scope, 25
                    )
        except Exception as exc:
            logger.debug(
                "Background extraction poll skipped",
                extra={"error_category": exc.__class__.__name__},
            )
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=settings.extraction_poll_interval_seconds
            )
        except asyncio.TimeoutError:
            pass