import { FindingStatus, OverrideAction, Severity } from '../enums';

/**
 * User Override for a finding - tracks user decisions and adjustments
 */
export interface UserOverride {
  id: string;
  finding_id: string;
  contract_id: string; // Partition key
  action: OverrideAction;
  user_email: string;
  timestamp: string; // ISO 8601 datetime string
  previous_value?: string | Severity;
  new_value?: string | Severity;
  notes?: string;
  reason?: string;
}

/**
 * Finding with user overrides applied
 */
export interface FindingWithOverrides {
  id: string;
  contract_id: string;
  finding_id: string;

  // Original finding data
  original_severity: Severity;
  original_risk_type: string;

  // Current state (with overrides applied)
  current_severity: Severity;
  status: FindingStatus;
  user_notes?: string;

  // Override history
  overrides: UserOverride[];
  last_modified_by?: string;
  last_modified_at?: string;
}

/**
 * Summary of user overrides for a contract
 */
export interface OverrideSummary {
  contract_id: string;
  total_overrides: number;
  by_action: Record<OverrideAction, number>;
  accepted_count: number;
  rejected_count: number;
  false_positive_count: number;
  severity_changes: number;
}
