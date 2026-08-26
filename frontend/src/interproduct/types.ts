// Mirrors backend/api/inter_product_routes.py's request model and
// backend/analytics/inter_product.py's response shape exactly.

export type LegSide = 'LONG' | 'SHORT';

export type LegRequest = {
  curve_id: string;
  weights: Record<string, number>;
  side: LegSide;
  lots: number;
  label: string;
};

export type InterProductAnalyzeRequest = {
  legs: LegRequest[];
  window: string;
  start_date?: string;
  end_date?: string;
};

export type LegStatistics = {
  n: number;
  current: number | null;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  percentile: number | null;
  z_score: number | null;
  volatility: number | null;
  rolling_volatility: number | null;
};

export type RVStatistics = LegStatistics & {
  median: number | null;
  rolling_mean: number | null;
  rolling_std: number | null;
  rolling_z_score: number | null;
  max_drawdown: number | null;
  sharpe_like: number | null;
  win_rate: number | null;
  avg_positive_move: number | null;
  avg_negative_move: number | null;
  range: number | null;
};

export type RollingCorrelationPoint = { date: string; correlation: number | null; n: number };

export type RelationshipStatistics = {
  n: number;
  correlation: number | null;
  correlation_returns: number | null;
  rolling_correlation: number | null;
  rolling_correlation_points: RollingCorrelationPoint[];
  regression_alpha: number | null;
  regression_beta: number | null;
  r_squared: number | null;
  lowess_beta: number | null;
  hedge_ratio: number | null;
  residual_std: number | null;
  residual_z_score: number | null;
  cointegrated: boolean | null;
  adf_pvalue: number | null;
  regression_definition: string;
};

export type ResolvedLegResponse = {
  curve_id: string;
  label: string;
  side: LegSide;
  lots: number;
  formula: string;
  statistics: LegStatistics;
};

export type RVSideResult = {
  side_summary: string;
  statistics: RVStatistics;
};

export type RVHedgeAdjustedResult = RVSideResult & {
  hedge_ratio: number | null;
  adjusted_lots_leg2: number | null;
};

export type LegPricePoint = { date: string; a: number; b: number };
export type RVBandPoint = {
  date: string;
  rv: number;
  rolling_mean: number;
  upper_1sd: number;
  lower_1sd: number;
  upper_2sd: number;
  lower_2sd: number;
};
export type ZScorePoint = { date: string; z_score: number | null };
export type ScatterPoint = { a: number; b: number };

export type InterProductAnalyzeResponse = {
  generated_at: string;
  window: string;
  n: number;
  legs: ResolvedLegResponse[];
  relationship: RelationshipStatistics;
  rv: {
    raw: RVSideResult;
    hedge_adjusted: RVHedgeAdjustedResult;
  };
  chart_data: {
    leg_price_points: LegPricePoint[];
    rolling_correlation_points: RollingCorrelationPoint[];
    rv_points: RVBandPoint[];
    zscore_points: ZScorePoint[];
    scatter_points: ScatterPoint[];
  };
};

// -- Frontend-local leg configuration, before it's resolved to a LegRequest --

export type StructureKind = 'outright' | '3ms' | '6ms' | '3mf';

export type LegConfig = {
  curveId: string;
  mode: 'predefined' | 'custom';
  structureKind: StructureKind;
  structureName: string; // predefined mode: exact instrument name chosen from that kind's list
  weights: Record<string, number>; // custom mode: arbitrary WeightGrid formula over outrights
  side: LegSide;
  lots: number;
  label: string;
};

export function defaultLegConfig(curveId: string): LegConfig {
  return {
    curveId, mode: 'predefined', structureKind: '3ms', structureName: '',
    weights: {}, side: 'LONG', lots: 1, label: '',
  };
}

// The weights dict this leg would send to the backend — {} until the user
// has actually picked/entered something (callers should treat that as "not
// ready to analyze" rather than sending an empty formula).
export function legConfigWeights(leg: LegConfig): Record<string, number> {
  if (leg.mode === 'predefined') return leg.structureName ? { [leg.structureName]: 1 } : {};
  return leg.weights;
}

export function legConfigIsReady(leg: LegConfig): boolean {
  return Object.keys(legConfigWeights(leg)).length > 0;
}

export function legConfigToRequest(leg: LegConfig): LegRequest {
  const weights = legConfigWeights(leg);
  const defaultLabel = leg.mode === 'predefined' ? leg.structureName : `${leg.curveId} custom`;
  return {
    curve_id: leg.curveId, weights, side: leg.side, lots: leg.lots,
    label: leg.label.trim() || defaultLabel,
  };
}

export const WINDOW_OPTIONS = ['5D', '10D', '20D', '30D', '60D', '90D', '180D', '1Y'] as const;
export type WindowOption = (typeof WINDOW_OPTIONS)[number];
