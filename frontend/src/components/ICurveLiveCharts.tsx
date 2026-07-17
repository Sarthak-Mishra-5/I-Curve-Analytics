import { useEffect, useMemo } from 'react';
import CurveSnapshotChart from './CurveSnapshotChart';
import { useICurveStore } from '../icurve/store';

const CURVE_ID = 'I';

function shortLabels(names: string[]): string[] {
  return names.map((n) => n.replace(/^I\s+/, '').replace(/\s+3MF$/, ''));
}

export default function ICurveLiveCharts() {
  const curveSpec = useICurveStore((s) => s.curveSpec);

  useEffect(() => {
    if (useICurveStore.getState().curveSpec) return;

    fetch(`/api/curves/${CURVE_ID}`)
      .then((r) => r.json())
      .then(useICurveStore.getState().setCurveSpec)
      .catch(() => {});
  }, []);

  const outrightLabels = useMemo(() => (curveSpec ? shortLabels(curveSpec.outrights) : []), [curveSpec]);
  const msLabels = useMemo(() => (curveSpec ? shortLabels(curveSpec.three_month_spreads) : []), [curveSpec]);
  const flyLabels = useMemo(() => (curveSpec ? shortLabels(curveSpec.flies_3m) : []), [curveSpec]);

  if (!curveSpec) {
    return <div style={{ color: '#666666', padding: '16px' }}>loading I curve live charts…</div>;
  }

  return (
    <div
      className="grid gap-1.5"
      style={{
        gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
        gridAutoRows: '360px',
      }}
    >
      <CurveSnapshotChart
        title="I Outrights"
        labels={outrightLabels}
        instruments={curveSpec.outrights}
        color="#00ff88"
      />
      <CurveSnapshotChart
        title="I 3-Month Spreads (3MS)"
        labels={msLabels}
        instruments={curveSpec.three_month_spreads}
        color="#4aa8ff"
      />
      <CurveSnapshotChart
        title="I 3-Month Fly (3MF)"
        labels={flyLabels}
        instruments={curveSpec.flies_3m}
        color="#ff3355"
      />
    </div>
  );
}
