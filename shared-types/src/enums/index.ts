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
