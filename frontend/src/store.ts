import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { Alert, AnalyticsPayload, Quote } from './types';

type Contracts = { SA3: string[]; ER3: string[]; I: string[]; SR3: string[]; SO3: string[] };

const EMPTY_CONTRACTS: Contracts = { SA3: [], ER3: [], I: [], SR3: [], SO3: [] };

type Snapshot = {
  quotes: Record<string, Quote>;
  analytics: AnalyticsPayload | {};
  alerts: Alert[];
  contracts: Partial<Contracts>;
  stream_status: string;
};

interface State {
  connected: boolean;
  streamStatus: string;
  quotes: Record<string, Quote>;
  analytics: AnalyticsPayload | null;
  alerts: Alert[];
  contracts: Contracts;
  lastTickAt: number;
  setConnected: (v: boolean) => void;
  applySnapshot: (s: Snapshot) => void;
  applyTickBatch: (batch: Quote[]) => void;
  applyAnalytics: (p: AnalyticsPayload) => void;
  pushAlert: (a: Alert) => void;
}

export const useStore = create<State>()(
  subscribeWithSelector((set) => ({
    connected: false,
    streamStatus: 'INIT',
    quotes: {},
    analytics: null,
    alerts: [],
    contracts: EMPTY_CONTRACTS,
    lastTickAt: 0,
    setConnected: (v) => set({ connected: v }),
    applySnapshot: (s) =>
      set({
        quotes: s.quotes ?? {},
        analytics: (s.analytics as AnalyticsPayload) ?? null,
        alerts: s.alerts ?? [],
        contracts: { ...EMPTY_CONTRACTS, ...(s.contracts ?? {}) },
        streamStatus: s.stream_status ?? 'INIT',
      }),
    applyTickBatch: (batch) =>
      set((st) => {
        const next = { ...st.quotes };
        for (const q of batch) next[q.instrument] = q;
        return { quotes: next, lastTickAt: Date.now() };
      }),
    applyAnalytics: (p) => set({ analytics: p }),
    pushAlert: (a) =>
      set((st) => ({ alerts: [a, ...st.alerts].slice(0, 200) })),
  }))
);
