/**
 * TypeScript interfaces for the Enterprise AI Data Assistant.
 */

// ==========================================
// Dataset
// ==========================================
export interface ColumnInfo {
  original_name: string;
  clean_name: string;
  data_type: string;
  non_null_count: number;
  null_count: number;
  unique_count: number;
  sample_values: string[];
}

export interface Dataset {
  id: number;
  name: string;
  original_filename: string;
  table_name: string;
  description: string | null;
  file_size_bytes: number | null;
  row_count: number;
  column_count: number;
  columns_info: ColumnInfo[] | null;
  created_at: string;
}

// ==========================================
// Query
// ==========================================
export interface ModelResponse {
  provider: string;
  model: string;
  sql: string;
  score: number;
  is_valid: boolean;
  latency_ms: number;
}

export interface QueryResult {
  success: boolean;
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  execution_time_ms: number;
  sql_executed: string;
  error: string | null;
}

export interface ChartConfig {
  chart_type: string;
  x_column?: string;
  y_column?: string;
  title?: string;
  config?: any;
}

export interface QueryResponse {
  question: string;
  sql: string;
  confidence: number;
  results: QueryResult;
  models: ModelResponse[];
  chart_recommendation: ChartConfig | null;
  insights: string | null;
  execution_time_ms: number;
}

export interface QueryHistoryItem {
  id: number;
  question: string;
  sql: string | null;
  confidence: number | null;
  is_successful: boolean;
  row_count: number | null;
  execution_time_ms: number | null;
  created_at: string;
}

// ==========================================
// Admin
// ==========================================
export interface SystemStats {
  total_datasets: number;
  total_queries: number;
  success_rate: number;
  average_confidence: number;
  llm_providers: LLMProvider[];
  rag_index: {
    total_vectors: number;
    metadata_count: number;
    embedding_model: string;
  };
}

export interface LLMProvider {
  provider: string;
  model: string;
  is_available: boolean;
}

export interface AuditLog {
  id: number;
  question: string;
  sql: string | null;
  model: string | null;
  confidence: number | null;
  is_successful: boolean;
  execution_time_ms: number | null;
  row_count: number | null;
  error: string | null;
  created_at: string;
}
