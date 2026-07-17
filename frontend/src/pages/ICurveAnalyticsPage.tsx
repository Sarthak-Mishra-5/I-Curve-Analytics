import { useEffect } from 'react';
import ComparisonLab from '../components/ComparisonLab';
import CurveStatsTable from '../components/CurveStatsTable';
import HistoricalCorrelationPanel from '../components/HistoricalCorrelationPanel';
import StructureBuilder from '../components/StructureBuilder';
import { useICurveStore } from '../icurve/store';
import type { CurvePairStatRow } from '../icurve/types';

const CURVE_ID = 'I';

export default function ICurveAnalyticsPage() {
  const curveSpec = useICurveStore((s) => s.curveSpec);
  const stats = useICurveStore((s) => s.stats);
  const selection = useICurveStore((s) => s.correlationSelection);
  const setSelection = useICurveStore((s) => s.setCorrelationSelection);

  useEffect(() => {
    fetch(`/api/curves/${CURVE_ID}`)
      .then((r) => r.json())
      .then(useICurveStore.getState().setCurveSpec)
      .catch(() => {});
    fetch(`/api/curves/${CURVE_ID}/stats`)
      .then((r) => r.json())
      .then((payload) => {
        if (payload && payload.tables) useICurveStore.getState().setStats(payload);
      })
      .catch(() => {});
  }, []);

  if (!curveSpec) {
    return <div style={{ color: '#666666', padding: '16px' }}>loading curve config…</div>;
  }

  return (
    <main className="flex-1 overflow-auto p-1.5">
  <div>
    <HistoricalCorrelationPanel curveId={CURVE_ID} curveSpec={curveSpec} />
  </div>

  {/* Tables */}
  <div
    className="grid gap-1.5 mt-1.5"
    style={{
      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    }}
  >
    <CurveStatsTable
      title="3MS Statistical Analysis"
      subtitle={`rolling ${stats?.window_days ?? 30}d`}
      rows={stats?.tables?.["3ms"] ?? []}
      onRowClick={(row: CurvePairStatRow) => setSelection({ kind: 'builtin', category: '3ms', current: row.current })}
      selectedCurrent={selection?.kind === 'builtin' && selection.category === '3ms' ? selection.current : null}
    />

    <CurveStatsTable
      title="3MF Statistical Analysis"
      subtitle={`rolling ${stats?.window_days ?? 30}d`}
      rows={stats?.tables?.["3mf"] ?? []}
      onRowClick={(row: CurvePairStatRow) => setSelection({ kind: 'builtin', category: '3mf', current: row.current })}
      selectedCurrent={selection?.kind === 'builtin' && selection.category === '3mf' ? selection.current : null}
    />

    {/* <CurveStatsTable
      title="6MS Statistical Analysis"
      subtitle={`rolling ${stats?.window_days ?? 30}d`}
      rows={stats?.tables?.["6ms"] ?? []}
    /> */}
  </div>

  {/* Custom Structure Analytics */}
  <div className="mt-1.5">
    <div style={{ color: '#666666', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
      Custom Structure Analytics
    </div>
    <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
      <StructureBuilder curveId={CURVE_ID} curveSpec={curveSpec} defaultName="Structure 1" />
      <StructureBuilder curveId={CURVE_ID} curveSpec={curveSpec} defaultName="Structure 2" />
      <StructureBuilder curveId={CURVE_ID} curveSpec={curveSpec} defaultName="Structure 3" />
      <StructureBuilder curveId={CURVE_ID} curveSpec={curveSpec} defaultName="Structure 4" />
    </div>
  </div>

  {/* Structure Comparison Lab */}
  <div className="mt-1.5">
    <ComparisonLab curveId={CURVE_ID} curveSpec={curveSpec} />
  </div>

</main>
  );
}
