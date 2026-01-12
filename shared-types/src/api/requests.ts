import { ContractMetadata } from '../models/contract';

/**
 * API Request Types for Contract Leakage Engine
 */

// POST /api/upload_contract
export interface UploadContractRequest {
  contract_name: string;
  uploaded_by: string;
  file: File | Blob; // Frontend will use FormData
  metadata?: ContractMetadata;
}

// POST /api/analyze_contract
export interface AnalyzeContractRequest {
  contract_id: string;
}

// GET /api/get_contract/:contract_id
// No request body - contract_id in path

// GET /api/get_clauses/:contract_id
export interface GetClausesRequest {
  contract_id: string;
  clause_type?: string; // Optional filter by clause type
  limit?: number; // Optional pagination limit
  offset?: number; // Optional pagination offset
}

// GET /api/get_findings/:contract_id
export interface GetFindingsRequest {
  contract_id: string;
  severity?: string; // Optional filter by severity
  category?: string; // Optional filter by category
  limit?: number; // Optional pagination limit
  offset?: number; // Optional pagination offset
}

// GET /api/export_report/:contract_id
export interface ExportReportRequest {
  contract_id: string;
  format?: 'pdf' | 'excel'; // Default: pdf
  include_clauses?: boolean; // Default: false (PDF only)
}
