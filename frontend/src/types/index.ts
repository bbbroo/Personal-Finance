export type ApiRecord = Record<string, unknown> & { id?: string };

export type Account = ApiRecord & {
  id: string;
  name: string;
  institution?: string | null;
  account_type: string;
  valuation_method: string;
  balance_sign_policy: string;
};

export type Transaction = ApiRecord & {
  id: string;
  transaction_date: string;
  merchant_name?: string | null;
  original_description: string;
  amount_cents: number;
  transaction_type: string;
  transfer_status: string;
  duplicate_status: string;
  review_status: string;
};

export type DataQualityIssue = ApiRecord & {
  id: string;
  severity: string;
  issue_type: string;
  title: string;
  description: string;
  recommended_action?: string | null;
  status: string;
};

export type TrustChecklist = {
  as_of: string;
  overall_status: string;
  warning_count: number;
  checks: Record<string, Record<string, unknown> & { status: string }>;
};

export type DashboardReport = {
  net_worth: {
    net_worth_cents: number;
    assets_cents: number;
    liabilities_cents: number;
    confidence: string;
    metadata: { warnings: string[] };
  };
  cash_flow: {
    income_cents: number;
    expenses_cents: number;
    savings_rate_decimal?: string | null;
    confidence: string;
    warnings: string[];
  };
  allocation: AllocationReport;
  cards: Record<string, number | string | null>;
  history: Array<{ date: string; net_worth_cents: number; assets_cents: number; liabilities_cents: number; confidence: string }>;
};

export type AllocationReport = {
  mode?: string;
  total_cents: number;
  confidence: string;
  warnings: string[];
  slices: Array<{ asset_class: string; value_cents: number; percent_decimal?: string | null }>;
};

export type ImportBatch = ApiRecord & {
  id: string;
  original_filename: string;
  status: string;
  row_count: number;
  valid_row_count: number;
  error_count: number;
  warning_count: number;
  duplicate_row_count: number;
  skipped_row_count?: number;
};

export type StagedRow = ApiRecord & {
  id: string;
  row_number: number;
  normalized_json: Record<string, unknown>;
  validation_status: string;
  duplicate_status: string;
  transfer_status: string;
  user_action: string;
  errors_json?: string[] | null;
  warnings_json?: string[] | null;
};
