/**
 * Enums matching Python Pydantic models
 */

export enum ContractStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  ANALYZED = "analyzed",
  ERROR = "error"
}

export enum ClauseType {
  PRICING = "pricing",
  PAYMENT_TERMS = "payment_terms",
  RENEWAL = "renewal",
  TERMINATION = "termination",
  LIABILITY = "liability",
  INDEMNIFICATION = "indemnification",
  WARRANTY = "warranty",
  SLA = "sla",
  PENALTY = "penalty",
  DISCOUNT = "discount",
  VOLUME_COMMITMENT = "volume_commitment",
  PRICE_ADJUSTMENT = "price_adjustment",
  OTHER = "other"
}

export enum Severity {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL"
}

export enum LeakageCategory {
  PRICING = "pricing",
  PAYMENT = "payment",
  RENEWAL = "renewal",
  TERMINATION = "termination",
  LIABILITY = "liability",
  COMPLIANCE = "compliance",
  SLA = "sla",
  DISCOUNTS = "discounts",
  VOLUME = "volume",
  OTHER = "other"
}

export enum DetectionMethod {
  RULE = "RULE",
  AI = "AI",
  HYBRID = "HYBRID"
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
