export type CatalogFile = {
  order: number;
  kind: "vertex" | "edge";
  file: string;
  target: string;
  expected_rows: number;
  actual_rows: number;
  valid: boolean;
  errors: string[];
  hash?: string;
  dependencies?: string[];
};

export type IngestionFile = {
  file_path: string;
  target: string;
  kind: string;
  status: string;
  total_rows: number;
  processed_rows: number;
  succeeded_rows: number;
  failed_rows: number;
  skipped_rows: number;
  next_row_number?: number;
  message?: string;
};

export type RowError = {
  error_id: number;
  file_path: string;
  row_no: number;
  business_key?: string;
  error_code: string;
  error_message: string;
};

export type IngestionRun = {
  run_id: string;
  status: string;
  mode: string;
  total_files: number;
  completed_files: number;
  total_rows: number;
  processed_rows: number;
  succeeded_rows: number;
  failed_rows: number;
  skipped_rows: number;
  progress_pct: number;
  message?: string;
  files: IngestionFile[];
  errors: RowError[];
};

export type QueryCatalogEntry = {
  id: string;
  name: string;
  parameters: string;
  purpose: string;
  outputs: string;
  status: string;
  file: string;
};
