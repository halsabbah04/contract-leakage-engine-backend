import { ClauseType } from '../enums';

/**
 * Clause interface matching Python Clause model
 */
export interface Clause {
  id: string;
  contract_id: string; // Partition key
  clause_type: ClauseType;
  section_number?: string;
  original_text: string;
  normalized_summary: string; // Optimized for AI prompts and RAG
  entities: ExtractedEntities;
  risk_signals: string[];
  confidence_score: number; // 0.0 to 1.0
  embedding?: number[]; // 3072-dim vector for RAG (optional, not always sent to frontend)
  created_at: string; // ISO 8601 datetime string
}

export interface ExtractedEntities {
  dates?: string[];
  monetary_values?: MonetaryValue[];
  percentages?: string[];
  parties?: string[];
  obligations?: string[];
  conditions?: string[];
  deadlines?: string[];
}

export interface MonetaryValue {
  amount: number;
  currency: string;
  context?: string;
}
