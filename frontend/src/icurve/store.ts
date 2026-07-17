import { create } from 'zustand';
import type { CorrelationSelection, CurveSpecDTO, CurveStatsPayload } from './types';

interface ICurveState {
  curveSpec: CurveSpecDTO | null;
  stats: CurveStatsPayload | null;
  correlationSelection: CorrelationSelection | null;
  setCurveSpec: (spec: CurveSpecDTO) => void;
  setStats: (payload: CurveStatsPayload) => void;
  setCorrelationSelection: (selection: CorrelationSelection) => void;
}

export const useICurveStore = create<ICurveState>((set) => ({
  curveSpec: null,
  stats: null,
  correlationSelection: null,
  setCurveSpec: (spec) => set({ curveSpec: spec }),
  setStats: (payload) => set({ stats: payload }),
  setCorrelationSelection: (selection) => set({ correlationSelection: selection }),
}));
