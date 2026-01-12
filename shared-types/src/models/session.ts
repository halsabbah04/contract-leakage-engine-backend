import { SessionStatus } from '../enums';

/**
 * Analysis Session interface matching Python AnalysisSession model
 */
export interface AnalysisSession {
  id: string;
  contract_id: string; // Partition key
  session_id: string; // Unique identifier for this session
  status: SessionStatus;
  start_time: string; // ISO 8601 datetime string
  end_time?: string; // ISO 8601 datetime string
  total_findings: number;
  findings_by_severity: FindingsBySeverity;
  processing_steps: ProcessingStep[];
  error_message?: string;
  created_at: string; // ISO 8601 datetime string
}

export interface FindingsBySeverity {
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
}

export interface ProcessingStep {
  step_name: string;
  status: string;
  start_time: string; // ISO 8601 datetime string
  end_time?: string; // ISO 8601 datetime string
  duration_seconds?: number;
  error_message?: string;
  metadata?: Record<string, any>;
}
