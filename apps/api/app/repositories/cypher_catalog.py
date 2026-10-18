"""
Complete Parameterized OpenCypher Query Catalog for AgentHive on FalkorDB (C-01, C-06).
All runtime user inputs are bound via $params; zero string concatenation is used.
"""

# ---------------------------------------------------------------------------
# 1. Control Graph Queries (ah_control)
# ---------------------------------------------------------------------------
UPSERT_TENANT = """
MERGE (t:Tenant {tenant_id: $tenant_id})
ON CREATE SET
    t.display_name = $display_name,
    t.description = $description,
    t.graph_name = $graph_name,
    t.is_demo = $is_demo,
    t.created_at = $created_at
ON MATCH SET
    t.display_name = $display_name,
    t.description = $description,
    t.is_demo = $is_demo
RETURN t.tenant_id, t.display_name, t.description, t.graph_name, t.is_demo, t.created_at
"""

GET_TENANT = """
MATCH (t:Tenant {tenant_id: $tenant_id})
RETURN t.tenant_id, t.display_name, t.description, t.graph_name, t.is_demo, t.created_at
LIMIT 1
"""

LIST_TENANTS = """
MATCH (t:Tenant)
RETURN t.tenant_id, t.display_name, t.description, t.graph_name, t.is_demo, t.created_at
ORDER BY t.tenant_id ASC
"""

# ---------------------------------------------------------------------------
# 2. Episodic Memory & Session Queries (FR-001, FR-002, FR-005, BR-008)
# ---------------------------------------------------------------------------
FIND_EPISODE_BY_IDEMPOTENCY = """
MATCH (e:Episode {tenant_id: $tenant_id, idempotency_key: $idempotency_key})
RETURN e.id, e.tenant_id, e.content, e.agent_id, e.agent_name, e.session_id,
       e.timestamp, e.importance_score, e.extraction_status, e.archived,
       e.idempotency_key, e.created_at
LIMIT 1
"""

CREATE_EPISODE_AND_SESSION = """
MERGE (s:Session {id: $session_id, tenant_id: $tenant_id})
ON CREATE SET
    s.title = $session_title,
    s.started_at = $timestamp,
    s.last_activity_at = $timestamp
ON MATCH SET
    s.last_activity_at = CASE WHEN $timestamp > s.last_activity_at THEN $timestamp ELSE s.last_activity_at END
CREATE (e:Episode {
    id: $id,
    tenant_id: $tenant_id,
    content: $content,
    agent_id: $agent_id,
    agent_name: $agent_name,
    session_id: $session_id,
    timestamp: $timestamp,
    importance_score: $importance_score,
    extraction_status: $extraction_status,
    archived: $archived,
    idempotency_key: $idempotency_key,
    created_at: $created_at
})
CREATE (s)-[:HAS_EPISODE]->(e)
WITH e
OPTIONAL MATCH (a:Agent {id: $agent_id, tenant_id: $tenant_id})
FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
    MERGE (a)-[:ACTED_IN]->(e)
)
RETURN e.id, e.tenant_id, e.content, e.agent_id, e.agent_name, e.session_id,
       e.timestamp, e.importance_score, e.extraction_status, e.archived,
       e.idempotency_key, e.created_at
"""

GET_EPISODE_BY_ID = """
MATCH (e:Episode {id: $episode_id, tenant_id: $tenant_id})
RETURN e.id, e.tenant_id, e.content, e.agent_id, e.agent_name, e.session_id,
       e.timestamp, e.importance_score, e.extraction_status, e.archived,
       e.idempotency_key, e.created_at
LIMIT 1
"""

LIST_EPISODES = """
MATCH (e:Episode {tenant_id: $tenant_id})
WHERE ($include_archived = true OR e.archived = false)
  AND ($session_id = '' OR e.session_id = $session_id)
  AND ($agent_id = '' OR e.agent_id = $agent_id)
RETURN e.id, e.tenant_id, e.content, e.agent_id, e.agent_name, e.session_id,
       e.timestamp, e.importance_score, e.extraction_status, e.archived,
       e.idempotency_key, e.created_at
ORDER BY e.timestamp DESC, e.id DESC
LIMIT $limit
"""

GET_SESSION_HISTORY = """
MATCH (s:Session {id: $session_id, tenant_id: $tenant_id})-[:HAS_EPISODE]->(e:Episode {tenant_id: $tenant_id})
WHERE ($start_iso = '' OR e.timestamp >= $start_iso)
  AND ($end_iso = '' OR e.timestamp <= $end_iso)
RETURN e.id, e.tenant_id, e.content, e.agent_id, e.agent_name, e.session_id,
       e.timestamp, e.importance_score, e.extraction_status, e.archived,
       e.idempotency_key, e.created_at
ORDER BY e.timestamp ASC, e.created_at ASC
LIMIT $limit
"""

LIST_SESSIONS = """
MATCH (s:Session {tenant_id: $tenant_id})
OPTIONAL MATCH (s)-[:HAS_EPISODE]->(e:Episode {tenant_id: $tenant_id})
RETURN s.id, s.tenant_id, s.title, s.started_at, s.last_activity_at, count(e) AS ep_count
ORDER BY s.last_activity_at DESC
LIMIT $limit
"""

UPDATE_EPISODE_EXTRACTION_STATUS = """
MATCH (e:Episode {id: $episode_id, tenant_id: $tenant_id})
SET e.extraction_status = $extraction_status
RETURN e.id, e.extraction_status
"""

ARCHIVE_EPISODE = """
MATCH (e:Episode {id: $episode_id, tenant_id: $tenant_id})
SET e.archived = true
RETURN e.id, e.archived
"""

GET_EPISODES_BY_IDS = """
MATCH (e:Episode {tenant_id: $tenant_id})
WHERE e.id IN $episode_ids
RETURN e.id, e.tenant_id, e.content, e.agent_id, e.agent_name, e.session_id,
       e.timestamp, e.importance_score, e.extraction_status, e.archived,
       e.idempotency_key, e.created_at
ORDER BY e.timestamp DESC
"""

# ---------------------------------------------------------------------------
# 3. Durable Extraction Queue Queries (NFR-004)
# ---------------------------------------------------------------------------
UPSERT_EXTRACTION_JOB = """
MERGE (j:ExtractionJob {episode_id: $episode_id, tenant_id: $tenant_id})
ON CREATE SET
    j.id = $job_id,
    j.status = $status,
    j.provider = $provider,
    j.attempt_count = $attempt_count,
    j.retry_after = $retry_after,
    j.last_error_category = $last_error_category,
    j.created_at = $now,
    j.updated_at = $now
ON MATCH SET
    j.status = $status,
    j.provider = $provider,
    j.attempt_count = $attempt_count,
    j.retry_after = $retry_after,
    j.last_error_category = $last_error_category,
    j.updated_at = $now
WITH j
MATCH (e:Episode {id: $episode_id, tenant_id: $tenant_id})
MERGE (e)-[:HAS_EXTRACTION_JOB]->(j)
RETURN j.id, j.episode_id, j.status, j.attempt_count
"""

FETCH_DUE_EXTRACTION_JOBS = """
MATCH (e:Episode {tenant_id: $tenant_id})-[:HAS_EXTRACTION_JOB]->(j:ExtractionJob {tenant_id: $tenant_id})
WHERE j.status IN ['PENDING', 'DEFERRED'] AND j.retry_after <= $now
RETURN j.id, j.episode_id, e.content, e.timestamp, j.attempt_count
ORDER BY j.updated_at ASC
LIMIT $limit
"""

# ---------------------------------------------------------------------------
# 4. Semantic Memory: Canonical Entities & Facts (FR-003, FR-008, BR-002, BR-004, BR-007)
# ---------------------------------------------------------------------------
GET_ENTITY_BY_CANONICAL_KEY = """
MATCH (en:Entity {canonical_key: $canonical_key, tenant_id: $tenant_id})
RETURN en.id, en.tenant_id, en.canonical_key, en.canonical_name, en.entity_type,
       en.aliases_json, en.source_episode_ids_json, en.created_at, en.updated_at
LIMIT 1
"""

GET_ENTITY_BY_ID = """
MATCH (en:Entity {id: $entity_id, tenant_id: $tenant_id})
RETURN en.id, en.tenant_id, en.canonical_key, en.canonical_name, en.entity_type,
       en.aliases_json, en.source_episode_ids_json, en.created_at, en.updated_at
LIMIT 1
"""

UPSERT_CANONICAL_ENTITY = """
MERGE (en:Entity {canonical_key: $canonical_key, tenant_id: $tenant_id})
ON CREATE SET
    en.id = $entity_id,
    en.canonical_name = $canonical_name,
    en.entity_type = $entity_type,
    en.aliases_json = $aliases_json,
    en.source_episode_ids_json = $source_episode_ids_json,
    en.created_at = $now,
    en.updated_at = $now
ON MATCH SET
    en.aliases_json = $aliases_json,
    en.source_episode_ids_json = $source_episode_ids_json,
    en.updated_at = $now
WITH en
MATCH (e:Episode {id: $episode_id, tenant_id: $tenant_id})
MERGE (e)-[:MENTIONS]->(en)
RETURN en.id, en.tenant_id, en.canonical_key, en.canonical_name, en.entity_type,
       en.aliases_json, en.source_episode_ids_json, en.created_at, en.updated_at
"""

LIST_ENTITIES = """
MATCH (en:Entity {tenant_id: $tenant_id})
WHERE ($entity_type = '' OR en.entity_type = $entity_type)
  AND ($search = '' OR toLower(en.canonical_name) CONTAINS toLower($search) OR toLower(en.aliases_json) CONTAINS toLower($search))
RETURN en.id, en.tenant_id, en.canonical_key, en.canonical_name, en.entity_type,
       en.aliases_json, en.source_episode_ids_json, en.created_at, en.updated_at
ORDER BY en.canonical_name ASC
LIMIT $limit
"""

FIND_CURRENT_FACTS_FOR_SUBJECT_PREDICATE = """
MATCH (f:Fact {tenant_id: $tenant_id, subject_entity_id: $subject_entity_id, predicate: $predicate, status: 'CURRENT'})
RETURN f.id, f.tenant_id, f.subject_entity_id, f.subject_name, f.predicate, f.object_value,
       f.object_entity_id, f.status, f.confidence, f.source_episode_id, f.observed_at, f.superseded_by_id
ORDER BY f.observed_at DESC
"""

SUPERSEDE_FACT = """
MATCH (old_f:Fact {id: $old_fact_id, tenant_id: $tenant_id})
MATCH (new_f:Fact {id: $new_fact_id, tenant_id: $tenant_id})
SET old_f.status = 'SUPERSEDED',
    old_f.superseded_by_id = $new_fact_id
MERGE (new_f)-[:SUPERSEDES]->(old_f)
RETURN old_f.id, old_f.status, old_f.superseded_by_id
"""

CREATE_FACT = """
MATCH (sub:Entity {id: $subject_entity_id, tenant_id: $tenant_id})
MATCH (ep:Episode {id: $source_episode_id, tenant_id: $tenant_id})
CREATE (f:Fact {
    id: $fact_id,
    tenant_id: $tenant_id,
    subject_entity_id: $subject_entity_id,
    subject_name: $subject_name,
    predicate: $predicate,
    object_value: $object_value,
    object_entity_id: $object_entity_id,
    status: $status,
    confidence: $confidence,
    source_episode_id: $source_episode_id,
    observed_at: $observed_at,
    superseded_by_id: $superseded_by_id
})
MERGE (sub)-[:SUBJECT_OF]->(f)
MERGE (ep)-[:DERIVED_FACT]->(f)
WITH f
OPTIONAL MATCH (obj:Entity {id: $object_entity_id, tenant_id: $tenant_id})
FOREACH (_ IN CASE WHEN obj IS NOT NULL AND $object_entity_id <> '' THEN [1] ELSE [] END |
    MERGE (f)-[:OBJECT_ENTITY]->(obj)
)
RETURN f.id, f.tenant_id, f.subject_entity_id, f.subject_name, f.predicate, f.object_value,
       f.object_entity_id, f.status, f.confidence, f.source_episode_id, f.observed_at, f.superseded_by_id
"""

LIST_FACTS = """
MATCH (f:Fact {tenant_id: $tenant_id})
WHERE ($subject_entity_id = '' OR f.subject_entity_id = $subject_entity_id)
  AND ($include_superseded = true OR f.status = 'CURRENT')
RETURN f.id, f.tenant_id, f.subject_entity_id, f.subject_name, f.predicate, f.object_value,
       f.object_entity_id, f.status, f.confidence, f.source_episode_id, f.observed_at, f.superseded_by_id
ORDER BY f.observed_at DESC, f.id DESC
LIMIT $limit
"""

GET_FACT_BY_ID = """
MATCH (f:Fact {id: $fact_id, tenant_id: $tenant_id})
RETURN f.id, f.tenant_id, f.subject_entity_id, f.subject_name, f.predicate, f.object_value,
       f.object_entity_id, f.status, f.confidence, f.source_episode_id, f.observed_at, f.superseded_by_id
LIMIT 1
"""

# ---------------------------------------------------------------------------
# 5. Procedural Memory Queries (FR-004, BR-002, BR-003)
# ---------------------------------------------------------------------------
GET_PROCEDURE_BY_NAME = """
MATCH (p:Procedure {name: $name, tenant_id: $tenant_id})
RETURN p.id, p.tenant_id, p.name, p.trigger_text, p.trigger_keywords_json, p.steps_json,
       p.status, p.confirmation_method, p.evidence_count, p.source_episode_ids_json,
       p.active_task_id, p.last_executed_at, p.created_at, p.updated_at
LIMIT 1
"""

GET_PROCEDURE_BY_ID = """
MATCH (p:Procedure {id: $procedure_id, tenant_id: $tenant_id})
RETURN p.id, p.tenant_id, p.name, p.trigger_text, p.trigger_keywords_json, p.steps_json,
       p.status, p.confirmation_method, p.evidence_count, p.source_episode_ids_json,
       p.active_task_id, p.last_executed_at, p.created_at, p.updated_at
LIMIT 1
"""

UPSERT_PROCEDURE = """
MERGE (p:Procedure {name: $name, tenant_id: $tenant_id})
ON CREATE SET
    p.id = $procedure_id,
    p.trigger_text = $trigger_text,
    p.trigger_keywords_json = $trigger_keywords_json,
    p.steps_json = $steps_json,
    p.status = $status,
    p.confirmation_method = $confirmation_method,
    p.evidence_count = $evidence_count,
    p.source_episode_ids_json = $source_episode_ids_json,
    p.active_task_id = $active_task_id,
    p.last_executed_at = $last_executed_at,
    p.created_at = $now,
    p.updated_at = $now
ON MATCH SET
    p.trigger_text = $trigger_text,
    p.trigger_keywords_json = $trigger_keywords_json,
    p.steps_json = $steps_json,
    p.status = $status,
    p.confirmation_method = $confirmation_method,
    p.evidence_count = $evidence_count,
    p.source_episode_ids_json = $source_episode_ids_json,
    p.updated_at = $now
WITH p
MATCH (ep:Episode {id: $source_episode_id, tenant_id: $tenant_id})
MERGE (p)-[:SUPPORTED_BY]->(ep)
RETURN p.id, p.tenant_id, p.name, p.trigger_text, p.trigger_keywords_json, p.steps_json,
       p.status, p.confirmation_method, p.evidence_count, p.source_episode_ids_json,
       p.active_task_id, p.last_executed_at, p.created_at, p.updated_at
"""

CONFIRM_PROCEDURE = """
MATCH (p:Procedure {id: $procedure_id, tenant_id: $tenant_id})
SET p.status = 'CONFIRMED',
    p.confirmation_method = 'USER_CONFIRMED',
    p.updated_at = $now
RETURN p.id, p.tenant_id, p.name, p.trigger_text, p.trigger_keywords_json, p.steps_json,
       p.status, p.confirmation_method, p.evidence_count, p.source_episode_ids_json,
       p.active_task_id, p.last_executed_at, p.created_at, p.updated_at
"""

SET_PROCEDURE_ACTIVE_TASK = """
MATCH (p:Procedure {id: $procedure_id, tenant_id: $tenant_id})
SET p.active_task_id = $active_task_id,
    p.last_executed_at = CASE WHEN $active_task_id <> '' THEN $now ELSE p.last_executed_at END,
    p.updated_at = $now
RETURN p.id, p.tenant_id, p.name, p.trigger_text, p.trigger_keywords_json, p.steps_json,
       p.status, p.confirmation_method, p.evidence_count, p.source_episode_ids_json,
       p.active_task_id, p.last_executed_at, p.created_at, p.updated_at
"""

LIST_PROCEDURES = """
MATCH (p:Procedure {tenant_id: $tenant_id})
WHERE ($status = '' OR p.status = $status)
RETURN p.id, p.tenant_id, p.name, p.trigger_text, p.trigger_keywords_json, p.steps_json,
       p.status, p.confirmation_method, p.evidence_count, p.source_episode_ids_json,
       p.active_task_id, p.last_executed_at, p.created_at, p.updated_at
ORDER BY p.status ASC, p.evidence_count DESC, p.name ASC
LIMIT $limit
"""

# ---------------------------------------------------------------------------
# 6. Context Assembly & Graph Traversal Queries (FR-006, FR-007, FR-008)
# ---------------------------------------------------------------------------
FIND_EPISODES_MENTIONING_ENTITIES = """
MATCH (e:Episode {tenant_id: $tenant_id})-[:MENTIONS]->(en:Entity {tenant_id: $tenant_id})
WHERE e.archived = false AND en.id IN $entity_ids
RETURN DISTINCT e.id, collect(en.canonical_name) AS matched_entities
LIMIT 200
"""

FIND_FACTS_FOR_ENTITIES_OR_EPISODES = """
MATCH (f:Fact {tenant_id: $tenant_id})
WHERE ($include_superseded = true OR f.status = 'CURRENT')
  AND (f.subject_entity_id IN $entity_ids OR f.object_entity_id IN $entity_ids OR f.source_episode_id IN $episode_ids)
RETURN f.id, f.tenant_id, f.subject_entity_id, f.subject_name, f.predicate, f.object_value,
       f.object_entity_id, f.status, f.confidence, f.source_episode_id, f.observed_at, f.superseded_by_id
ORDER BY f.status ASC, f.observed_at DESC
LIMIT $limit
"""

# ---------------------------------------------------------------------------
# 7. Agent Registry, Handoffs & Shared Task State Queries (FR-009..FR-012, BR-006)
# ---------------------------------------------------------------------------
UPSERT_AGENT = """
MERGE (a:Agent {id: $agent_id, tenant_id: $tenant_id})
ON CREATE SET
    a.name = $name,
    a.role = $role,
    a.capabilities_json = $capabilities_json,
    a.status = $status,
    a.created_at = $now
ON MATCH SET
    a.name = $name,
    a.role = $role,
    a.capabilities_json = $capabilities_json,
    a.status = $status
RETURN a.id, a.tenant_id, a.name, a.role, a.capabilities_json, a.status, a.created_at
"""

GET_AGENT_BY_ID = """
MATCH (a:Agent {id: $agent_id, tenant_id: $tenant_id})
RETURN a.id, a.tenant_id, a.name, a.role, a.capabilities_json, a.status, a.created_at
LIMIT 1
"""

LIST_AGENTS = """
MATCH (a:Agent {tenant_id: $tenant_id})
RETURN a.id, a.tenant_id, a.name, a.role, a.capabilities_json, a.status, a.created_at
ORDER BY a.created_at ASC, a.id ASC
LIMIT $limit
"""

CREATE_TASK = """
MATCH (owner:Agent {id: $owner_agent_id, tenant_id: $tenant_id})
CREATE (t:Task {
    id: $task_id,
    tenant_id: $tenant_id,
    title: $title,
    status: $status,
    owner_agent_id: $owner_agent_id,
    session_id: $session_id,
    active_procedure_id: $active_procedure_id,
    result_summary: $result_summary,
    created_at: $now,
    updated_at: $now
})
MERGE (owner)-[:OWNS_TASK]->(t)
WITH t
OPTIONAL MATCH (p:Procedure {id: $active_procedure_id, tenant_id: $tenant_id})
FOREACH (_ IN CASE WHEN p IS NOT NULL AND $active_procedure_id <> '' THEN [1] ELSE [] END |
    MERGE (t)-[:USES_PROCEDURE]->(p)
)
RETURN t.id, t.tenant_id, t.title, t.status, t.owner_agent_id, t.session_id,
       t.active_procedure_id, t.result_summary, t.created_at, t.updated_at
"""

GET_TASK_BY_ID = """
MATCH (t:Task {id: $task_id, tenant_id: $tenant_id})
RETURN t.id, t.tenant_id, t.title, t.status, t.owner_agent_id, t.session_id,
       t.active_procedure_id, t.result_summary, t.created_at, t.updated_at
LIMIT 1
"""

UPDATE_TASK_STATUS = """
MATCH (t:Task {id: $task_id, tenant_id: $tenant_id})
SET t.status = $status,
    t.owner_agent_id = $owner_agent_id,
    t.active_procedure_id = $active_procedure_id,
    t.result_summary = $result_summary,
    t.updated_at = $now
WITH t
OPTIONAL MATCH (p:Procedure {id: $active_procedure_id, tenant_id: $tenant_id})
FOREACH (_ IN CASE WHEN p IS NOT NULL AND $active_procedure_id <> '' THEN [1] ELSE [] END |
    MERGE (t)-[:USES_PROCEDURE]->(p)
)
RETURN t.id, t.tenant_id, t.title, t.status, t.owner_agent_id, t.session_id,
       t.active_procedure_id, t.result_summary, t.created_at, t.updated_at
"""

LIST_TASKS = """
MATCH (t:Task {tenant_id: $tenant_id})
WHERE ($owner_agent_id = '' OR t.owner_agent_id = $owner_agent_id)
  AND ($status = '' OR t.status = $status)
RETURN t.id, t.tenant_id, t.title, t.status, t.owner_agent_id, t.session_id,
       t.active_procedure_id, t.result_summary, t.created_at, t.updated_at
ORDER BY t.updated_at DESC, t.id DESC
LIMIT $limit
"""

CREATE_HANDOFF = """
MATCH (origin:Agent {id: $origin_agent_id, tenant_id: $tenant_id})
MATCH (target:Agent {id: $target_agent_id, tenant_id: $tenant_id})
MATCH (t:Task {id: $task_id, tenant_id: $tenant_id})
CREATE (h:Handoff {
    id: $handoff_id,
    tenant_id: $tenant_id,
    task_id: $task_id,
    task_title: $task_title,
    origin_agent_id: $origin_agent_id,
    target_agent_id: $target_agent_id,
    context_summary: $context_summary,
    state_payload_json: $state_payload_json,
    status: $status,
    session_id: $session_id,
    created_at: $now,
    updated_at: $now
})
MERGE (origin)-[:INITIATED_HANDOFF]->(h)
MERGE (h)-[:TARGET_AGENT]->(target)
MERGE (h)-[:FOR_TASK]->(t)
RETURN h.id, h.tenant_id, h.task_id, h.task_title, h.origin_agent_id, h.target_agent_id,
       h.context_summary, h.state_payload_json, h.status, h.session_id, h.created_at, h.updated_at
"""

GET_HANDOFF_BY_ID = """
MATCH (h:Handoff {id: $handoff_id, tenant_id: $tenant_id})
RETURN h.id, h.tenant_id, h.task_id, h.task_title, h.origin_agent_id, h.target_agent_id,
       h.context_summary, h.state_payload_json, h.status, h.session_id, h.created_at, h.updated_at
LIMIT 1
"""

UPDATE_HANDOFF_STATUS = """
MATCH (h:Handoff {id: $handoff_id, tenant_id: $tenant_id})
SET h.status = $status,
    h.updated_at = $now
RETURN h.id, h.tenant_id, h.task_id, h.task_title, h.origin_agent_id, h.target_agent_id,
       h.context_summary, h.state_payload_json, h.status, h.session_id, h.created_at, h.updated_at
"""

LIST_HANDOFFS = """
MATCH (h:Handoff {tenant_id: $tenant_id})
WHERE ($target_agent_id = '' OR h.target_agent_id = $target_agent_id)
  AND ($origin_agent_id = '' OR h.origin_agent_id = $origin_agent_id)
  AND ($status = '' OR h.status = $status)
RETURN h.id, h.tenant_id, h.task_id, h.task_title, h.origin_agent_id, h.target_agent_id,
       h.context_summary, h.state_payload_json, h.status, h.session_id, h.created_at, h.updated_at
ORDER BY h.created_at DESC, h.id DESC
LIMIT $limit
"""

LIST_PENDING_HANDOFFS_FOR_AGENT = """
MATCH (h:Handoff {tenant_id: $tenant_id})
WHERE h.status IN ['PENDING', 'ACCEPTED', 'IN_PROGRESS']
  AND ($target_agent_id = '' OR h.target_agent_id = $target_agent_id)
RETURN h.id, h.tenant_id, h.task_id, h.task_title, h.origin_agent_id, h.target_agent_id,
       h.context_summary, h.state_payload_json, h.status, h.session_id, h.created_at, h.updated_at
ORDER BY h.created_at ASC
LIMIT $limit
"""

# ---------------------------------------------------------------------------
# 8. Graph Visualization & Live Metrics Queries (FR-015)
# ---------------------------------------------------------------------------
COUNT_BY_LABEL = """
MATCH (n {tenant_id: $tenant_id})
RETURN labels(n)[0] AS label, n.status AS status, count(n) AS cnt
"""

LIST_GRAPH_EDGES = """
MATCH (a {tenant_id: $tenant_id})-[r]->(b {tenant_id: $tenant_id})
WHERE a.id IS NOT NULL AND b.id IS NOT NULL
RETURN a.id, type(r) AS rel_type, b.id
LIMIT $limit
"""
