import { ClauseType } from '../enums';

/**
 * Clause interface matching Python Clause model
 */
export interface Clause {
  id: string;
  type?: 'clause';
  contract_id: string; // Partition key
  clause_type: ClauseType | string;
  clause_subtype?: string | null;
  section_number?: string | null;
  page_number?: number | null;
  start_position?: number | null;
  end_position?: number | null;
  original_text: string;
  normalized_summary: string; // Optimized for AI prompts and RAG
  entities: ExtractedEntities;
  risk_signals: string[];
  extraction_confidence?: number | null; // 0.0 to 1.0 (backend name)
  confidence_score?: number | null; // Legacy name for backwards compatibility
  embedding?: number[]; // 3072-dim vector for RAG (optional, not always sent to frontend)
  extracted_at?: string; // ISO 8601 datetime string (backend name)
  created_at?: string; // Legacy name for backwards compatibility
  partition_key?: string;
}

/**
 * ExtractedEntities interface matching Python ExtractedEntities model
 * Note: Backend extracts amounts and currency separately, not as monetary_values
 */
export interface ExtractedEntities {
  // Core fields from backend
  currency?: string | null;      // Currency code (USD, BHD, EUR, etc.)
  rates?: number[];              // Numerical rates or prices
  dates?: string[];              // Dates mentioned (ISO format)
  percentages?: number[];        // Percentage values (as decimals)
  amounts?: number[];            // Monetary amounts (just numbers)
  parties?: string[];            // Parties mentioned
  durations?: string[];          // Time durations mentioned

  // Legacy fields for backwards compatibility with some frontend components
  monetary_values?: MonetaryValue[];
  obligations?: string[];
  conditions?: string[];
  deadlines?: string[];
}

/**
 * @deprecated Backend extracts amounts and currency separately.
 * Use entities.amounts and entities.currency instead.
 */
export interface MonetaryValue {
  amount: number;
  currency: string;
  context?: string;
}
