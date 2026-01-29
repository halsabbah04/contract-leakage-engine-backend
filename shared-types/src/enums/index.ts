/**
 * Enums matching Python Pydantic models
 */

export enum ContractStatus {
  UPLOADED = "uploaded",
  EXTRACTING_TEXT = "extracting_text",
  TEXT_EXTRACTED = "text_extracted",
  EXTRACTING_CLAUSES = "extracting_clauses",
  CLAUSES_EXTRACTED = "clauses_extracted",
  ANALYZING = "analyzing",
  ANALYZED = "analyzed",
  FAILED = "failed"
}

export enum ClauseType {
  PRICING = "pricing",
  PAYMENT = "payment",
  PAYMENT_TERMS = "payment_terms",
  RENEWAL = "renewal",
  AUTO_RENEWAL = "auto_renewal",
  TERMINATION = "termination",
  SERVICE_LEVEL = "service_level",
  LIABILITY = "liability",
  INDEMNIFICATION = "indemnification",
  CONFIDENTIALITY = "confidentiality",
  INTELLECTUAL_PROPERTY = "intellectual_property",
  DISPUTE_RESOLUTION = "dispute_resolution",
  FORCE_MAJEURE = "force_majeure",
  WARRANTY = "warranty",
  DELIVERY = "delivery",
  SLA = "sla",
  PENALTY = "penalty",
  PENALTIES = "penalties",
  DISCOUNT = "discount",
  DISCOUNTS = "discounts",
  VOLUME_COMMITMENT = "volume_commitment",
  PRICE_ADJUSTMENT = "price_adjustment",
  EXCLUSIVITY = "exclusivity",
  OTHER = "other"
}

export enum Severity {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical",
  INFO = "info"
}

export enum LeakageCategory {
  PRICING = "pricing",
  RENEWAL = "renewal",
  TERMINATION = "termination",
  SERVICE_CREDIT = "service_credit",
  VOLUME_DISCOUNT = "volume_discount",
  PENALTY = "penalty",
  AUTO_RENEWAL = "auto_renewal",
  LIABILITY_CAP = "liability_cap",
  PAYMENT_TERMS = "payment_terms",
  DELIVERY = "delivery",
  COMPLIANCE = "compliance",
  OTHER = "other"
}

export enum DetectionMethod {
  RULE = "rule",
  AI = "ai",
  HYBRID = "hybrid"
}

export enum SessionStatus {
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed"
}

export enum FindingStatus {
  PENDING = "pending",
  ACCEPTED = "accepted",
  REJECTED = "rejected",
  FALSE_POSITIVE = "false_positive",
  RESOLVED = "resolved"
}

export enum OverrideAction {
  CHANGE_SEVERITY = "change_severity",
  MARK_FALSE_POSITIVE = "mark_false_positive",
  ADD_NOTE = "add_note",
  ACCEPT = "accept",
  REJECT = "reject",
  RESOLVE = "resolve"
}

// Obligation-related enums
export enum ObligationType {
  PAYMENT = "payment",
  DELIVERY = "delivery",
  NOTICE = "notice",
  REPORTING = "reporting",
  COMPLIANCE = "compliance",
  PERFORMANCE = "performance",
  RENEWAL = "renewal",
  TERMINATION = "termination",
  INSURANCE = "insurance",
  AUDIT = "audit",
  CONFIDENTIALITY = "confidentiality",
  OTHER = "other"
}

export enum ObligationStatus {
  UPCOMING = "upcoming",
  DUE_SOON = "due_soon",
  OVERDUE = "overdue",
  COMPLETED = "completed",
  WAIVED = "waived",
  NOT_APPLICABLE = "not_applicable"
}

export enum ObligationPriority {
  CRITICAL = "critical",
  HIGH = "high",
  MEDIUM = "medium",
  LOW = "low"
}

export enum RecurrencePattern {
  NONE = "none",
  DAILY = "daily",
  WEEKLY = "weekly",
  MONTHLY = "monthly",
  QUARTERLY = "quarterly",
  SEMI_ANNUALLY = "semi_annually",
  ANNUALLY = "annually",
  CUSTOM = "custom"
}

// Agent-related enums
export enum AgentType {
  OBLIGATION = "obligation",
  PARTY_INTELLIGENCE = "party_intelligence",
  BENCHMARK = "benchmark",
  COMPLIANCE = "compliance",
  CONTRACT_COMPARISON = "contract_comparison",
  RISK_FORECAST = "risk_forecast",
  NEGOTIATION = "negotiation"
}

export enum AgentStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  PARTIAL = "partial"
}
