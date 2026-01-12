import { Severity, LeakageCategory, DetectionMethod } from '../enums';

/**
 * Leakage Finding interface matching Python LeakageFinding model
 */
export interface LeakageFinding {
  id: string;
  contract_id: string; // Partition key
  finding_id: string; // Unique identifier for this finding
  category: LeakageCategory;
  severity: Severity;
  risk_type: string;
  explanation: string;
  recommended_action: string;
  affected_clause_ids: string[];
  confidence_score: number; // 0.0 to 1.0
  detection_method: DetectionMethod;
  rule_id?: string; // If detected by rule
  estimated_financial_impact?: FinancialImpact;
  assumptions?: string[];
  created_at: string; // ISO 8601 datetime string
}

export interface FinancialImpact {
  amount: number;
  currency: string;
  calculation_method?: string;
  notes?: string;
}
