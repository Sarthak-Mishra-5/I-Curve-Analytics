import { create } from 'zustand';
import type { CorrelationSelection, CurveSpecDTO, CurveStatsPayload } from './types';

interface ICurveState {
  curveSpecs: Record<string, CurveSpecDTO>;
  statsByCurve: Record<string, CurveStatsPayload>;
  correlationSelections: Record<string, CorrelationSelection | null>;
  curveSpec: CurveSpecDTO | null;
  stats: CurveStatsPayload | null;
  correlationSelection: CorrelationSelection | null;
  setCurveSpec: (spec: CurveSpecDTO) => void;
  setStats: (payload: CurveStatsPayload) => void;
  setCorrelationSelection: (selection: CorrelationSelection | null, curveId?: string) => void;
}

export const useICurveStore = create<ICurveState>((set) => ({
  curveSpecs: {},
  statsByCurve: {},
  correlationSelections: {},
  curveSpec: null,
  stats: null,
  correlationSelection: null,
  setCurveSpec: (spec) => set((state) => ({
    curveSpecs: { ...state.curveSpecs, [spec.curve_id]: spec },
    curveSpec: spec.curve_id === 'I' ? spec : state.curveSpec,
  })),
  setStats: (payload) => set((state) => ({
    statsByCurve: { ...state.statsByCurve, [payload.curve_id]: payload },
    stats: payload.curve_id === 'I' ? payload : state.stats,
  })),
  setCorrelationSelection: (selection, curveId = 'I') => set((state) => ({
    correlationSelections: { ...state.correlationSelections, [curveId]: selection },
    correlationSelection: curveId === 'I' ? selection : state.correlationSelection,
  })),
}));
