import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { Alert, AnalyticsPayload, Quote } from './types';

type Snapshot = {
  quotes: Record<string, Quote>;
  analytics: AnalyticsPayload | {};
  alerts: Alert[];
  contracts: { SA3: string[]; ER3: string[] };
  stream_status: string;
};

interface State {
  connected: boolean;
  streamStatus: string;
  quotes: Record<string, Quote>;
  analytics: AnalyticsPayload | null;
  alerts: Alert[];
  contracts: { SA3: string[]; ER3: string[] };
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
    contracts: { SA3: [], ER3: [] },
    lastTickAt: 0,
    setConnected: (v) => set({ connected: v }),
    applySnapshot: (s) =>
      set({
        quotes: s.quotes ?? {},
        analytics: (s.analytics as AnalyticsPayload) ?? null,
        alerts: s.alerts ?? [],
        contracts: s.contracts ?? { SA3: [], ER3: [] },
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
