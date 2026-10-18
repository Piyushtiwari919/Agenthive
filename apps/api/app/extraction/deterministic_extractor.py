import re
from typing import List

from app.extraction.base import (
    ExtractedEntityItem,
    ExtractedFactItem,
    ExtractedProcedureItem,
    ExtractionPayload,
)
from app.extraction.canonicalizer import CANONICAL_SYNONYM_MAP, canonicalize_entity, normalize_predicate

# Regex patterns for structured and natural-language fact & procedure extraction
FACT_KV_PATTERN = re.compile(
    r"(?:FACT|Fact)\s*:\s*([A-Za-z0-9_-]+)\s+([a-zA-Z0-9_]+)\s*=\s*([^.;\n]+)"
)
NATURAL_FACT_PATTERNS = [
    re.compile(
        r"\b([A-Za-z0-9_-]{3,})\s+(?:has|uses|requires|configured with)\s+([a-z_][a-z0-9_ ]{2,30}?)\s+(?:of|set to|equal to|=|is)\s+([A-Za-z0-9_./:-]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b([A-Za-z0-9_-]{3,})\s+(timeout_ms|retry_limit|max_connections|pool_size|rate_limit_rps|port|version|status|protocol|owner|database|cache_ttl_sec|encryption_mode|token_ttl_min)\s+(?:is|set to|=)\s+([A-Za-z0-9_./:-]+)",
        re.IGNORECASE,
    ),
]
PROCEDURE_BLOCK_PATTERN = re.compile(
    r"PROCEDURE:\s*(?P<name>[^\n|]+?)\s*\|\s*TRIGGER:\s*(?P<trigger>[^\n|]+?)\s*\|\s*STEPS:\s*(?P<steps>[^\n]+)",
    re.IGNORECASE,
)


class DeterministicExtractor:
    """
    Default $0 offline deterministic extractor (C-03, C-04).
    Extracts canonical entities, structured & natural facts, and repeatable procedures
    with zero external API keys or network dependencies.
    """

    provider_name: str = "deterministic"

    def extract(self, content: str) -> ExtractionPayload:
        entities_by_key: dict[str, ExtractedEntityItem] = {}
        facts: List[ExtractedFactItem] = []
        procedures: List[ExtractedProcedureItem] = []

        lower_content = content.lower()

        # 1. Match known domain entities & aliases (BR-007)
        for alias_key, (canon_name, canon_type, aliases) in CANONICAL_SYNONYM_MAP.items():
            pattern = r"(?<![a-z0-9])" + re.escape(alias_key) + r"(?![a-z0-9])"
            if re.search(pattern, lower_content):
                key, c_name, c_type, merged_aliases = canonicalize_entity(canon_name, canon_type, aliases)
                entities_by_key[key] = ExtractedEntityItem(
                    name=c_name,
                    entity_type=c_type,
                    aliases=merged_aliases,
                )

        # 2. Match CamelCase or hyphenated service/component names in prose
        for match in re.finditer(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+|[a-z]+-(?:service|gateway|worker|engine|router|api|store|vault|hub|job|filter|portal))\b", content):
            raw_token = match.group(1)
            key, c_name, c_type, merged_aliases = canonicalize_entity(raw_token, "Service")
            if key not in entities_by_key:
                entities_by_key[key] = ExtractedEntityItem(
                    name=c_name,
                    entity_type=c_type,
                    aliases=merged_aliases,
                )

        # 3. Extract explicit "FACT: <Subject> <predicate> = <value>" statements
        for match in FACT_KV_PATTERN.finditer(content):
            raw_subj, raw_pred, raw_val = match.group(1), match.group(2), match.group(3).strip()
            key, c_name, c_type, merged_aliases = canonicalize_entity(raw_subj, "Service")
            if key not in entities_by_key:
                entities_by_key[key] = ExtractedEntityItem(
                    name=c_name, entity_type=c_type, aliases=merged_aliases
                )
            pred = normalize_predicate(raw_pred)
            obj_entity_name = None
            val_key = raw_val.lower()
            if val_key in CANONICAL_SYNONYM_MAP:
                obj_entity_name = CANONICAL_SYNONYM_MAP[val_key][0]
            facts.append(
                ExtractedFactItem(
                    subject_name=c_name,
                    subject_type=c_type,
                    predicate=pred,
                    object_value=raw_val,
                    object_entity_name=obj_entity_name,
                    confidence=0.96,
                )
            )

        # 4. Extract natural-language facts (e.g. "PaymentGateway timeout_ms is 3500ms")
        for pat in NATURAL_FACT_PATTERNS:
            for match in pat.finditer(content):
                raw_subj, raw_pred, raw_val = (
                    match.group(1).strip(),
                    match.group(2).strip(),
                    match.group(3).strip().rstrip(".,;"),
                )
                key, c_name, c_type, merged_aliases = canonicalize_entity(raw_subj, "Service")
                if key not in entities_by_key:
                    entities_by_key[key] = ExtractedEntityItem(
                        name=c_name, entity_type=c_type, aliases=merged_aliases
                    )
                pred = normalize_predicate(raw_pred)
                if not any(
                    f.subject_name == c_name and f.predicate == pred and f.object_value == raw_val
                    for f in facts
                ):
                    facts.append(
                        ExtractedFactItem(
                            subject_name=c_name,
                            subject_type=c_type,
                            predicate=pred,
                            object_value=raw_val,
                            confidence=0.91,
                        )
                    )

        # 5. Extract procedures ("PROCEDURE: <name> | TRIGGER: <trigger> | STEPS: 1. ...; 2. ...")
        for match in PROCEDURE_BLOCK_PATTERN.finditer(content):
            proc_name = match.group("name").strip()
            trigger_text = match.group("trigger").strip()
            raw_steps = match.group("steps").strip()
            steps = [
                re.sub(r"^\d+[\).\s-]+", "", s.strip()).strip()
                for s in re.split(r";|\|\|", raw_steps)
                if s.strip()
            ]
            if proc_name and trigger_text and steps:
                procedures.append(
                    ExtractedProcedureItem(
                        name=proc_name,
                        trigger_text=trigger_text,
                        steps=steps,
                    )
                )

        return ExtractionPayload(
            entities=list(entities_by_key.values()),
            facts=facts,
            procedures=procedures,
        )