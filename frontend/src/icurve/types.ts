export type CurveSpecDTO = {
  curve_id: string;
  label: string;
  outrights: string[];
  three_month_spreads: string[];
  six_month_spreads: string[];
  flies_3m: string[];
  spreads_mode: 'direct_feed' | 'computed';
};

export type CurvePairStatRow = {
  previous: string;
  current: string;
  n: number;
  correlation: number | null;
  beta: number | null;
  prev_max: number | null;
  prev_max_ts: string | null;
  curr_at_prev_max: number | null;
  prev_min: number | null;
  prev_min_ts: string | null;
  curr_at_prev_min: number | null;
};

export type CurveStatsPayload = {
  curve_id: string;
  generated_at: string;
  window_days: number;
  tables: {
    '3ms': CurvePairStatRow[];
    '6ms': CurvePairStatRow[];
    '3mf': CurvePairStatRow[];
  };
  compute_ms?: number;
};

export type CorrelationHistoryPoint = {
  date: string;
  correlation: number | null;
  n: number;
};

export type StructurePriceHistoryPoint = {
  date: string;
  a: number | null;
  b: number | null;
};

export type CorrelationHistoryPayload = {
  curve_id: string;
  category: '3ms' | '3mf';
  previous: string;
  current: string;
  window_obs: number;
  min_obs: number;
  history_days: number;
  updated_at: string;
  points: CorrelationHistoryPoint[];
};

// -- Custom Structure Analytics + Structure Comparison Lab --------------

export type StructureRoll = {
  label: string;
  legs: Record<string, number>;
};

export type StructureRollRow = {
  previous: string;
  current: string;
  n: number;
  correlation: number | null;
  regression_beta: number | null;
  lowess_beta: number | null;
  hedge_ratio: number | null;
  prev_max: number | null;
  prev_max_ts: string | null;
  curr_at_prev_max: number | null;
  prev_min: number | null;
  prev_min_ts: string | null;
  curr_at_prev_min: number | null;
  live_price: number | null;
};

export type CustomStructureRequest = {
  name: string;
  weights: Record<string, number>;
};

export type CustomStructureResponse = {
  name: string;
  outrights: string[];
  formula: number[];
  rolls: StructureRoll[];
  table: StructureRollRow[];
  generated_at: string;
};

export type ComparisonRequest = {
  weights_a: Record<string, number>;
  weights_b: Record<string, number>;
};

export type ComparisonResponse = {
  formula_a: number[];
  formula_b: number[];
  n: number;
  correlation: number | null;
  regression_beta: number | null;
  lowess_beta: number | null;
  hedge_ratio: number | null;
  current_spread: number | null;
  z_score: number | null;
  historical_percentile: number | null;
  volatility_ratio: number | null;
  cointegrated: boolean | null;
  adf_pvalue: number | null;
  live_price_a: number | null;
  live_price_b: number | null;
  generated_at: string;
};

export type StructureCorrelationHistoryRequest = {
  legs_a: Record<string, number>;
  legs_b: Record<string, number>;
  label_a?: string;
  label_b?: string;
  start_date?: string;
  end_date?: string;
};

export type StructureCorrelationHistoryResponse = {
  label_a: string;
  label_b: string;
  window_obs: number;
  min_obs: number;
  history_days: number;
  updated_at: string;
  points: CorrelationHistoryPoint[];
  price_points?: StructurePriceHistoryPoint[];
};

export type StructurePriceHistoryResponse = {
  label_a: string;
  label_b: string;
  history_days: number;
  updated_at: string;
  points: StructurePriceHistoryPoint[];
};

// What currently drives the one shared Historical Correlation Chart. A
// built-in table row picks a category + display name (existing endpoint); a
// custom-structure table row instead carries the two rolls' own weight
// vectors straight to the generic correlation-history endpoint.
export type CorrelationSelection =
  | { kind: 'builtin'; category: '3ms' | '3mf'; current: string }
  | {
      kind: 'custom';
      structureName: string;
      previous: string;
      current: string;
      legsPrevious: Record<string, number>;
      legsCurrent: Record<string, number>;
    };
