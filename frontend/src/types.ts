export type Quote = {
  instrument: string;
  bid: number | null;
  bid_qty: number | null;
  ask: number | null;
  ask_qty: number | null;
  last: number | null;
  mid: number | null;
  vwap: number | null;
  price: number | null;
  settle: number | null;
  prev_settle: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  net_change: number | null;
  ts: string;
  updated_at: string;
  product: string;
};

export type Spread = {
  name: string;
  legs: string[];
  value: number;
  mean: number;
  std: number;
  zscore: number;
  percentile: number;
  vol: number;
};

export type Fly = {
  name: string;
  legs: string[];
  value: number;
  mean: number;
  std: number;
  zscore: number;
  vol: number;
};

export type Regression = {
  x: string;
  y: string;
  alpha: number;
  beta: number;
  r2: number;
  residual: number;
  residual_z: number;
  rolling_beta: number;
  n: number;
};

export type CorrelationMatrix = {
  rows: string[];
  cols: string[];
  matrix: number[][];
};

export type CurvePoint = {
  tenor: string;
  instrument: string;
  mid: number | null;
  price: number | null;
  bid: number | null;
  ask: number | null;
};

export type Curve = {
  SA3: CurvePoint[];
  ER3: CurvePoint[];
  pca: {
    SA3: { level_var_pct: number | null; slope_var_pct: number | null; curvature_var_pct: number | null };
    ER3: { level_var_pct: number | null; slope_var_pct: number | null; curvature_var_pct: number | null };
  };
};

export type Alert = {
  id: string;
  ts: string;
  severity: 'info' | 'warn' | 'critical';
  category: string;
  message: string;
};

export type AnalyticsPayload = {
  spreads: Spread[];
  flies: Fly[];
  regressions: Regression[];
  tick_sensitivity: any[];
  cointegration: any[];
  volatility: any[];
  microstructure: any[];
  curve: Curve;
  correlation?: CorrelationMatrix;
  compute_ms?: number;
};
