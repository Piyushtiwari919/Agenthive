import re
from typing import Dict, List, Tuple

# Canonical Entity Synonym Dictionary (Enforces BR-007 single canonical entity resolution)
CANONICAL_SYNONYM_MAP: Dict[str, Tuple[str, str, List[str]]] = {
    "payment-gateway": ("PaymentGateway", "Service", ["payment-gateway", "payment gateway", "pay-gw", "PaymentGateway"]),
    "payment gateway": ("PaymentGateway", "Service", ["payment-gateway", "payment gateway", "pay-gw", "PaymentGateway"]),
    "pay-gw": ("PaymentGateway", "Service", ["payment-gateway", "payment gateway", "pay-gw", "PaymentGateway"]),
    "paymentgateway": ("PaymentGateway", "Service", ["payment-gateway", "payment gateway", "pay-gw", "PaymentGateway"]),
    "auth-service": ("AuthService", "Service", ["auth-service", "AuthService", "authentication service", "auth_svc"]),
    "authservice": ("AuthService", "Service", ["auth-service", "AuthService", "authentication service", "auth_svc"]),
    "authentication service": ("AuthService", "Service", ["auth-service", "AuthService", "authentication service", "auth_svc"]),
    "falkordb": ("FalkorDB", "Database", ["FalkorDB", "falkordb", "FalkorDB Graph"]),
    "ledger-worker": ("LedgerWorker", "Service", ["LedgerWorker", "ledger-worker", "ledger worker"]),
    "ledgerworker": ("LedgerWorker", "Service", ["LedgerWorker", "ledger-worker", "ledger worker"]),
    "order-router": ("OrderRouter", "Service", ["OrderRouter", "order-router", "order router"]),
    "orderrouter": ("OrderRouter", "Service", ["OrderRouter", "order-router", "order router"]),
    "risk-engine": ("RiskEngine", "Service", ["RiskEngine", "risk-engine", "risk engine"]),
    "riskengine": ("RiskEngine", "Service", ["RiskEngine", "risk-engine", "risk engine"]),
    "webhook-dispatcher": ("WebhookDispatcher", "Service", ["WebhookDispatcher", "webhook-dispatcher", "webhook dispatcher"]),
    "webhookdispatcher": ("WebhookDispatcher", "Service", ["WebhookDispatcher", "webhook-dispatcher", "webhook dispatcher"]),
    "invoice-generator": ("InvoiceGenerator", "Service", ["InvoiceGenerator", "invoice-generator"]),
    "invoicegenerator": ("InvoiceGenerator", "Service", ["InvoiceGenerator", "invoice-generator"]),
    "token-vault": ("TokenVault", "SecurityComponent", ["TokenVault", "token-vault", "token vault"]),
    "tokenvault": ("TokenVault", "SecurityComponent", ["TokenVault", "token-vault", "token vault"]),
    "rate-limiter": ("RateLimiter", "Middleware", ["RateLimiter", "rate-limiter", "rate limiter"]),
    "ratelimiter": ("RateLimiter", "Middleware", ["RateLimiter", "rate-limiter", "rate limiter"]),
    "schema-registry": ("SchemaRegistry", "Infrastructure", ["SchemaRegistry", "schema-registry"]),
    "schemaregistry": ("SchemaRegistry", "Infrastructure", ["SchemaRegistry", "schema-registry"]),
    "session-store": ("SessionStore", "Component", ["SessionStore", "session-store"]),
    "sessionstore": ("SessionStore", "Component", ["SessionStore", "session-store"]),
    "audit-trail": ("AuditTrail", "ComplianceComponent", ["AuditTrail", "audit-trail", "audit log"]),
    "audittrail": ("AuditTrail", "ComplianceComponent", ["AuditTrail", "audit-trail", "audit log"]),
    "checkout-api": ("CheckoutAPI", "Service", ["CheckoutAPI", "checkout-api", "checkout service"]),
    "checkoutapi": ("CheckoutAPI", "Service", ["CheckoutAPI", "checkout-api", "checkout service"]),
    "fraud-detector": ("FraudDetector", "Service", ["FraudDetector", "fraud-detector"]),
    "frauddetector": ("FraudDetector", "Service", ["FraudDetector", "fraud-detector"]),
    "settlement-job": ("SettlementJob", "BatchWorker", ["SettlementJob", "settlement-job"]),
    "settlementjob": ("SettlementJob", "BatchWorker", ["SettlementJob", "settlement-job"]),
    "merchant-portal": ("MerchantPortal", "FrontendApp", ["MerchantPortal", "merchant-portal"]),
    "merchantportal": ("MerchantPortal", "FrontendApp", ["MerchantPortal", "merchant-portal"]),
    "notification-hub": ("NotificationHub", "Service", ["NotificationHub", "notification-hub"]),
    "notificationhub": ("NotificationHub", "Service", ["NotificationHub", "notification-hub"]),
    "currency-converter": ("CurrencyConverter", "Service", ["CurrencyConverter", "currency-converter"]),
    "currencyconverter": ("CurrencyConverter", "Service", ["CurrencyConverter", "currency-converter"]),
    "reconciliation-engine": ("ReconciliationEngine", "Service", ["ReconciliationEngine", "reconciliation-engine"]),
    "reconciliationengine": ("ReconciliationEngine", "Service", ["ReconciliationEngine", "reconciliation-engine"]),
    "idempotency-filter": ("IdempotencyFilter", "Middleware", ["IdempotencyFilter", "idempotency-filter"]),
    "idempotencyfilter": ("IdempotencyFilter", "Middleware", ["IdempotencyFilter", "idempotency-filter"]),
    "retry-scheduler": ("RetryScheduler", "Component", ["RetryScheduler", "retry-scheduler"]),
    "retryscheduler": ("RetryScheduler", "Component", ["RetryScheduler", "retry-scheduler"]),
    "circuit-breaker": ("CircuitBreaker", "Pattern", ["CircuitBreaker", "circuit-breaker"]),
    "circuitbreaker": ("CircuitBreaker", "Pattern", ["CircuitBreaker", "circuit-breaker"]),
    "dead-letter-queue": ("DeadLetterQueue", "Infrastructure", ["DeadLetterQueue", "dead-letter-queue", "dlq"]),
    "deadletterqueue": ("DeadLetterQueue", "Infrastructure", ["DeadLetterQueue", "dead-letter-queue", "dlq"]),
    "dlq": ("DeadLetterQueue", "Infrastructure", ["DeadLetterQueue", "dead-letter-queue", "dlq"]),
    "telemetry-collector": ("TelemetryCollector", "Observability", ["TelemetryCollector", "telemetry-collector"]),
    "telemetrycollector": ("TelemetryCollector", "Observability", ["TelemetryCollector", "telemetry-collector"]),
    # Tenant B Security Entities
    "waf-gateway": ("WAFGateway", "SecurityAppliance", ["WAFGateway", "waf-gateway", "WAF"]),
    "wafgateway": ("WAFGateway", "SecurityAppliance", ["WAFGateway", "waf-gateway", "WAF"]),
    "siem-ingestor": ("SIEMIngestor", "SecurityService", ["SIEMIngestor", "siem-ingestor"]),
    "siemingestor": ("SIEMIngestor", "SecurityService", ["SIEMIngestor", "siem-ingestor"]),
    "iam-controller": ("IAMController", "SecurityService", ["IAMController", "iam-controller"]),
    "iamcontroller": ("IAMController", "SecurityService", ["IAMController", "iam-controller"]),
    "cert-manager": ("CertManager", "SecurityInfrastructure", ["CertManager", "cert-manager"]),
    "certmanager": ("CertManager", "SecurityInfrastructure", ["CertManager", "cert-manager"]),
    "kms-rotator": ("KMSRotator", "SecurityService", ["KMSRotator", "kms-rotator"]),
    "kmsrotator": ("KMSRotator", "SecurityService", ["KMSRotator", "kms-rotator"]),
}

STOPWORDS = {
    "the", "and", "for", "with", "when", "from", "into", "that", "this", "are",
    "was", "were", "have", "has", "had", "how", "what", "why", "who", "should",
}


def canonicalize_entity(
    raw_name: str, default_type: str = "Component", extra_aliases: List[str] | None = None
) -> Tuple[str, str, str, List[str]]:
    """
    Returns (canonical_key, canonical_name, entity_type, merged_aliases).
    Guarantees that aliases like 'pay-gw', 'payment-gateway', and 'PaymentGateway'
    all resolve to canonical_key='paymentgateway' and canonical_name='PaymentGateway' (BR-007).
    """
    cleaned = raw_name.strip()
    lookup_key = cleaned.lower()
    aliases = list(extra_aliases or [])
    if cleaned not in aliases:
        aliases.append(cleaned)

    if lookup_key in CANONICAL_SYNONYM_MAP:
        canon_name, canon_type, known_aliases = CANONICAL_SYNONYM_MAP[lookup_key]
        merged = list(dict.fromkeys([*known_aliases, *aliases]))
        key = re.sub(r"[^a-z0-9]", "", canon_name.lower())
        return key, canon_name, canon_type, merged

    alnum_key = re.sub(r"[^a-z0-9]", "", lookup_key)
    if alnum_key in CANONICAL_SYNONYM_MAP:
        canon_name, canon_type, known_aliases = CANONICAL_SYNONYM_MAP[alnum_key]
        merged = list(dict.fromkeys([*known_aliases, *aliases]))
        key = re.sub(r"[^a-z0-9]", "", canon_name.lower())
        return key, canon_name, canon_type, merged

    return alnum_key or "unknown", cleaned, default_type, aliases


def normalize_predicate(predicate: str) -> str:
    clean = re.sub(r"[^a-z0-9_]", "_", predicate.strip().lower())
    return re.sub(r"_+", "_", clean).strip("_") or "related_to"


def extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9_-]{3,}", text.lower())
    seen: List[str] = []
    for tok in tokens:
        if tok not in STOPWORDS and tok not in seen:
            seen.append(tok)
    return seen[:20]