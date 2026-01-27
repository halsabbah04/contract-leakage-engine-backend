/**
 * Finding Override interface matching Python FindingOverride model
 */
export interface FindingOverride {
  finding_id: string;
  action: string; // 'dismissed' | 'accepted' | 'modified' | 'noted'
  reason?: string;
  modified_impact?: number;
  modified_assumptions?: Record<string, any>;
  timestamp: string; // ISO 8601 datetime string
}

/**
 * Export record for tracking export history
 */
export interface ExportRecord {
  format: string;
  uri?: string;
  timestamp: string; // ISO 8601 datetime string
}

/**
 * Analysis Session interface matching Python AnalysisSession model
 *
 * Cosmos DB Container: analysis_sessions
 * Partition Key: contract_id
 */
export interface AnalysisSession {
  id: string;
  type: 'session'; // Literal type matching Python model
  contract_id: string; // Partition key

  // User information
  user_role?: string; // Role of user (contract_manager, finance, etc.)
  user_id?: string; // User identifier (if auth is implemented)

  // Session data
  overrides: FindingOverride[];

  // Custom parameters
  custom_inflation_rate?: number;
  custom_assumptions: Record<string, any>;

  // Session metadata
  created_at: string; // ISO 8601 datetime string
  last_activity_at: string; // ISO 8601 datetime string
  session_duration_seconds?: number;

  // Export history
  exports: ExportRecord[];

  partition_key: string; // Cosmos DB partition key (contract_id)
}

// =============================================================================
// LEGACY INTERFACES - Kept for backwards compatibility
// These were from an older design and may still be used in some parts of the app
// =============================================================================

import { SessionStatus } from '../enums';

/**
 * @deprecated Use AnalysisSession instead - this was from an older design
 */
export interface LegacyAnalysisSession {
  id: string;
  contract_id: string;
  session_id: string;
  status: SessionStatus;
  start_time: string;
  end_time?: string;
  total_findings: number;
  findings_by_severity: FindingsBySeverity;
  processing_steps: ProcessingStep[];
  error_message?: string;
  created_at: string;
}

/**
 * @deprecated Part of legacy session design
 */
export interface FindingsBySeverity {
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
}

/**
 * @deprecated Part of legacy session design
 */
export interface ProcessingStep {
  step_name: string;
  status: string;
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
  error_message?: string;
  metadata?: Record<string, any>;
}
