import { Contract } from '../models/contract';
import { Clause } from '../models/clause';
import { LeakageFinding } from '../models/finding';
import { AnalysisSession } from '../models/session';

/**
 * API Response Types for Contract Leakage Engine
 */

// Generic API Error Response
export interface ApiErrorResponse {
  error: string;
  details?: string;
  status_code: number;
}

// POST /api/upload_contract
export interface UploadContractResponse {
  message: string;
  contract_id: string;
  contract_name: string;
  file_path: string;
  status: string;
}

// POST /api/analyze_contract
export interface AnalyzeContractResponse {
  message: string;
  contract_id: string;
  session_id: string;
  total_clauses_extracted: number;
  total_findings: number;
  findings_by_severity: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  processing_time_seconds: number;
}

// GET /api/get_contract/:contract_id
export interface GetContractResponse {
  contract: Contract;
}

// GET /api/get_clauses/:contract_id
export interface GetClausesResponse {
  contract_id: string;
  clauses: Clause[];
  total_count: number;
  limit?: number;
  offset?: number;
}

// GET /api/get_findings/:contract_id
export interface GetFindingsResponse {
  contract_id: string;
  findings: LeakageFinding[];
  total_count: number;
  summary: {
    total_findings: number;
    by_severity: {
      CRITICAL: number;
      HIGH: number;
      MEDIUM: number;
      LOW: number;
    };
    by_category: Record<string, number>;
    total_estimated_impact?: {
      amount: number;
      currency: string;
    };
  };
  limit?: number;
  offset?: number;
}

// GET /api/export_report/:contract_id
// Response is binary (PDF or Excel file) with headers:
// - Content-Type: application/pdf or application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
// - Content-Disposition: attachment; filename="..."
export interface ExportReportResponse {
  // This is a binary response, not JSON
  // Frontend will handle as Blob
}

// Additional helper types for common patterns
export interface PaginatedResponse<T> {
  data: T[];
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface SuccessResponse {
  message: string;
  success: boolean;
}
