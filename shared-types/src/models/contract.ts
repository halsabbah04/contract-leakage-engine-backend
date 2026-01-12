import { ContractStatus } from '../enums';

/**
 * Contract document interface matching Python Contract model
 */
export interface Contract {
  id: string;
  contract_id: string; // Partition key
  contract_name: string;
  uploaded_by: string;
  upload_date: string; // ISO 8601 datetime string
  file_path: string;
  status: ContractStatus;
  metadata: ContractMetadata;
  created_at: string; // ISO 8601 datetime string
  updated_at: string; // ISO 8601 datetime string
}

export interface ContractMetadata {
  file_type?: string;
  file_size?: number;
  contract_value?: number;
  currency?: string;
  start_date?: string; // ISO 8601 date string
  end_date?: string; // ISO 8601 date string
  auto_renewal?: boolean;
  counterparty_name?: string;
  custom_fields?: Record<string, any>;
}
