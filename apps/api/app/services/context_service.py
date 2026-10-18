import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, List, Set

from app.domain.context import (
    AssembledContextPackage,
    ContextAssembleRequest,
    RankedEpisode,
    RelevanceTrace,
)
from app.domain.enums import FactStatus, ProcedureStatus
from app.domain.memory import EntityRecord, FactRecord, ProcedureRecord
from app.domain.tenant import TenantScope
from app.extraction.canonicalizer import canonicalize_entity, extract_keywords
from app.repositories.context_repository import get_context_repository
from app.repositories.coordination_repository import get_coordination_repository
from app.repositories.memory_repository import get_memory_repository


class ContextService:
    """
    Unified 4-Part Context Assembly and Hybrid Graph + Lexical Ranking Service
    (FR-004, FR-006, FR-007, FR-008, FR-011, NFR-001, NFR-008).
    """

    def assemble_context(
        self, scope: TenantScope, req: ContextAssembleRequest
    ) -> AssembledContextPackage:
        start_perf = time.perf_counter()
        mem_repo = get_memory_repository()
        ctx_repo = get_context_repository()
        coord_repo = get_coordination_repository()

        query_terms = extract_keywords(req.query)
        query_lower = req.query.lower()

        # 1. Match Semantic Entities via canonical key, name, aliases, or query tokens
        all_entities = mem_repo.list_entities(scope, limit=300)
        matched_entities: List[EntityRecord] = []
        matched_entity_ids: Set[str] = set()

        # Also check if any token canonicalizes to a known entity
        query_canonical_keys = {canonicalize_entity(tok)[0] for tok in query_terms}

        for ent in all_entities:
            alias_match = any(alias.lower() in query_lower for alias in ent.aliases)
            name_match = ent.canonical_name.lower() in query_lower
            key_match = ent.canonical_key in query_canonical_keys
            token_overlap = any(
                tok in ent.canonical_name.lower() or any(tok in al.lower() for al in ent.aliases)
                for tok in query_terms
            )
            if name_match or alias_match or key_match or token_overlap:
                matched_entities.append(ent)
                matched_entity_ids.add(ent.id)

        # 2. Traverse FalkorDB (Episode)-[:MENTIONS]->(Entity) for graph-boosted episodes
        graph_episode_entities: Dict[str, List[str]] = ctx_repo.find_episodes_mentioning_entities(
            scope, list(matched_entity_ids)
        )

        # 3. Score and Rank Candidate Episodes (FR-007: Relevance primary, importance_score tiebreaker)
        candidate_episodes = mem_repo.list_episodes(
            scope,
            session_id=req.session_id,
            include_archived=False,
            limit=300,
        )

        ranked_candidates: List[RankedEpisode] = []
        for ep in candidate_episodes:
            content_lower = ep.content.lower()
            matched_toks = [t for t in query_terms if t in content_lower]

            if not query_terms:
                lexical_score = 1.0 if query_lower in content_lower else 0.0
            else:
                lexical_score = len(matched_toks) / float(len(query_terms))

            linked_entity_names = graph_episode_entities.get(ep.id, [])
            graph_boost = min(0.45, 0.25 * len(linked_entity_names)) if linked_entity_names else 0.0

            # Primary relevance combines lexical match + FalkorDB graph-traversal boost
            primary_relevance = round(lexical_score + graph_boost, 4)

            if primary_relevance > 0.0:
                explanation_parts = []
                if matched_toks:
                    explanation_parts.append(f"matched query terms {matched_toks}")
                if linked_entity_names:
                    explanation_parts.append(f"graph-linked to entities {linked_entity_names}")
                explanation_parts.append(f"importance tiebreaker={ep.importance_score:.2f}")

                trace = RelevanceTrace(
                    matched_terms=matched_toks,
                    lexical_score=round(lexical_score, 4),
                    graph_boost=round(graph_boost, 4),
                    importance_score=ep.importance_score,
                    recency_score=0.0,
                    final_score=primary_relevance,
                    explanation="; ".join(explanation_parts),
                )
                ranked_candidates.append(
                    RankedEpisode(
                        episode=ep,
                        relevance_score=primary_relevance,
                        trace=trace,
                    )
                )

        # Sort by (primary_relevance DESC, importance_score DESC, timestamp DESC) per FR-007
        ranked_candidates.sort(
            key=lambda item: (
                round(item.relevance_score, 4),
                round(item.episode.importance_score, 4),
                item.episode.timestamp.timestamp(),
            ),
            reverse=True,
        )
        top_episodes = ranked_candidates[: req.max_episodes]
        top_episode_ids = [item.episode.id for item in top_episodes]

        # 4. Assemble Connected Facts with Provenance (FR-006, FR-008)
        facts: List[FactRecord] = ctx_repo.find_connected_facts(
            scope=scope,
            entity_ids=list(matched_entity_ids),
            episode_ids=top_episode_ids,
            include_superseded=req.include_superseded_facts,
            limit=req.max_facts,
        )
        # Fallback lexical check over facts if graph traversal returned fewer than max_facts
        if len(facts) < req.max_facts and query_terms:
            seen_fact_ids = {f.id for f in facts}
            all_facts = mem_repo.list_facts(
                scope, include_superseded=req.include_superseded_facts, limit=200
            )
            for f in all_facts:
                if f.id in seen_fact_ids:
                    continue
                fact_blob = f"{f.subject_name} {f.predicate} {f.object_value}".lower()
                if any(t in fact_blob for t in query_terms):
                    facts.append(f)
                    seen_fact_ids.add(f.id)
                    if len(facts) >= req.max_facts:
                        break

        if not req.include_superseded_facts:
            facts = [f for f in facts if f.status == FactStatus.CURRENT]

        # Ensure any entity referenced by returned facts is also included in entities list
        fact_subject_ids = {f.subject_entity_id for f in facts}
        for ent in all_entities:
            if ent.id in fact_subject_ids and ent.id not in matched_entity_ids:
                matched_entities.append(ent)
                matched_entity_ids.add(ent.id)

        # 5. Match Applicable Procedures by Trigger & Name (FR-004, FR-006, BR-003)
        all_procedures = mem_repo.list_procedures(scope, limit=100)
        scored_procedures: List[tuple[int, int, ProcedureRecord]] = []
        for proc in all_procedures:
            if not req.include_proposed_procedures and proc.status != ProcedureStatus.CONFIRMED:
                continue
            proc_blob = f"{proc.name} {proc.trigger_text} {' '.join(proc.trigger_keywords)}".lower()
            overlap_count = sum(1 for t in query_terms if t in proc_blob)
            direct_substring = (
                proc.trigger_text.lower() in query_lower or proc.name.lower() in query_lower
            )
            if overlap_count > 0 or direct_substring:
                confirmed_rank = 1 if proc.status == ProcedureStatus.CONFIRMED else 0
                scored_procedures.append(
                    (confirmed_rank, overlap_count + (3 if direct_substring else 0), proc)
                )

        scored_procedures.sort(key=lambda x: (x[0], x[1], x[2].evidence_count), reverse=True)
        applicable_procedures = [item[2] for item in scored_procedures[: req.max_procedures]]

        # 6. Fetch Pending Handoffs for the Requesting Agent (FR-006, FR-011)
        pending_handoffs = coord_repo.list_pending_handoffs_for_agent(
            scope=scope,
            target_agent_id=req.agent_id,
            limit=20,
        )

        duration_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)
        return AssembledContextPackage(
            tenant_id=scope.tenant_id,
            query=req.query,
            requesting_agent_id=req.agent_id,
            assembled_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            episodes=top_episodes,
            entities=matched_entities[:25],
            facts=facts[: req.max_facts],
            procedures=applicable_procedures,
            pending_handoffs=pending_handoffs,
        )


@lru_cache()
def get_context_service() -> ContextService:
    return ContextService()
