import { ContractStatus } from '../enums';

/**
 * Contract source enum
 */
export type ContractSource = 'upload' | 'manual';

/**
 * Contract document interface matching Python Contract model
 */
export interface Contract {
  id: string;
  type: 'contract';
  contract_id: string; // Partition key
  contract_name: string;
  source: ContractSource;
  file_type?: string;
  language: string;
  counterparty?: string;
  start_date?: string; // ISO 8601 date string
  end_date?: string; // ISO 8601 date string
  contract_value_estimate?: number;
  status: ContractStatus;
  created_at: string; // ISO 8601 datetime string
  updated_at: string; // ISO 8601 datetime string
  upload_date?: string; // ISO 8601 datetime string
  partition_key: string;

  // Storage references
  blob_uri?: string;
  extracted_text_uri?: string;

  // Processing metadata
  clause_ids?: string[];
  error_message?: string;
  processing_duration_seconds?: number;
}

/**
 * Legacy ContractMetadata interface for backwards compatibility
 * @deprecated Use Contract fields directly
 */
export interface ContractMetadata {
  file_type?: string;
  file_size?: number;
  contract_value?: number;
  currency?: string;
  start_date?: string;
  end_date?: string;
  auto_renewal?: boolean;
  counterparty_name?: string;
  custom_fields?: Record<string, unknown>;
}
