import { useEffect, useState } from 'react';
import ComparisonLab from '../components/ComparisonLab';
import CurveStatsTable from '../components/CurveStatsTable';
import HistoricalCorrelationPanel from '../components/HistoricalCorrelationPanel';
import StructureBuilder from '../components/StructureBuilder';
import { useICurveStore } from '../icurve/store';
import type { CurvePairStatRow } from '../icurve/types';

const CURVES = [
  { id: 'I', label: 'Euribor I' },
  { id: 'SR3', label: 'SOFR SR3' },
  { id: 'SA3', label: 'SARON SA3' },
  { id: 'SO3', label: 'SONIA SO3' },
];

export default function ICurveAnalyticsPage() {
  const [curveId, setCurveId] = useState('I');
  const curveSpec = useICurveStore((s) => s.curveSpecs[curveId] ?? null);
  const stats = useICurveStore((s) => s.statsByCurve[curveId] ?? null);
  const selection = useICurveStore((s) => s.correlationSelections[curveId] ?? null);
  const setSelection = useICurveStore((s) => s.setCorrelationSelection);

  useEffect(() => {
    fetch(`/api/curves/${curveId}`)
      .then((r) => r.json())
      .then(useICurveStore.getState().setCurveSpec)
      .catch(() => {});
    fetch(`/api/curves/${curveId}/stats`)
      .then((r) => r.json())
      .then((payload) => {
        if (payload && payload.tables) useICurveStore.getState().setStats(payload);
      })
      .catch(() => {});
  }, [curveId]);

  if (!curveSpec) {
    return <div style={{ color: '#666666', padding: '16px' }}>loading curve config...</div>;
  }

  return (
    <main className="flex-1 overflow-auto p-1.5">
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
        {CURVES.map((curve) => (
          <button
            key={curve.id}
            onClick={() => setCurveId(curve.id)}
            style={{
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 'bold',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              borderRadius: '3px',
              border: '1px solid #333333',
              backgroundColor: curve.id === curveId ? '#262626' : '#111111',
              color: curve.id === curveId ? '#e5e5e5' : '#777777',
              cursor: 'pointer',
            }}
          >
            {curve.label}
          </button>
        ))}
        <div style={{ color: '#666666', fontSize: '11px', marginLeft: '6px' }}>
          {curveSpec.label}
        </div>
      </div>

      <div>
        <HistoricalCorrelationPanel curveId={curveId} curveSpec={curveSpec} />
      </div>

      <div
        className="grid gap-1.5 mt-1.5"
        style={{
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        }}
      >
        {/* <CurveStatsTable
          title="3MS Statistical Analysis"
          subtitle={`rolling ${stats?.window_days ?? 30}d`}
          rows={stats?.tables?.["3ms"] ?? []}
          onRowClick={(row: CurvePairStatRow) => setSelection({ kind: 'builtin', category: '3ms', current: row.current }, curveId)}
          selectedCurrent={selection?.kind === 'builtin' && selection.category === '3ms' ? selection.current : null}
        />

        <CurveStatsTable
          title="3MF Statistical Analysis"
          subtitle={`rolling ${stats?.window_days ?? 30}d`}
          rows={stats?.tables?.["3mf"] ?? []}
          onRowClick={(row: CurvePairStatRow) => setSelection({ kind: 'builtin', category: '3mf', current: row.current }, curveId)}
          selectedCurrent={selection?.kind === 'builtin' && selection.category === '3mf' ? selection.current : null}
        /> */}

        {/* <CurveStatsTable
          title="6MS Statistical Analysis"
          subtitle={`rolling ${stats?.window_days ?? 30}d`}
          rows={stats?.tables?.["6ms"] ?? []}
        /> */}
      </div>

      <div className="mt-1.5">
        <div style={{ color: '#666666', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
          Custom Structure Analytics
        </div>
        <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <StructureBuilder key={`${curveId}:1`} curveId={curveId} curveSpec={curveSpec} defaultName="Structure 1" />
          <StructureBuilder key={`${curveId}:2`} curveId={curveId} curveSpec={curveSpec} defaultName="Structure 2" />
          <StructureBuilder key={`${curveId}:3`} curveId={curveId} curveSpec={curveSpec} defaultName="Structure 3" />
          <StructureBuilder key={`${curveId}:4`} curveId={curveId} curveSpec={curveSpec} defaultName="Structure 4" />
        </div>
      </div>

      <div className="mt-1.5">
        <ComparisonLab key={curveId} curveId={curveId} curveSpec={curveSpec} />
      </div>
    </main>
  );
}
