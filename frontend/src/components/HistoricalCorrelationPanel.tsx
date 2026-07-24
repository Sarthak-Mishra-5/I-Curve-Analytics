import { useEffect, useMemo, useState } from 'react';
import type {
  CorrelationHistoryPayload,
  CurveSpecDTO,
  StructureCorrelationHistoryResponse,
} from '../icurve/types';
import { fmt } from '../plotlyTheme';
import { useICurveStore } from '../icurve/store';
import CorrelationOverTimeChart from './CorrelationOverTimeChart';
import Panel from './Panel';

type Category = '3ms' | '3mf';

interface Props {
  curveId: string;
  curveSpec: CurveSpecDTO;
}

function shortName(name: string) {
  return name.replace(/^[A-Z0-9]+\s+/, '').replace(/\s+3MF$/, ' 3MF');
}

function currentOptions(curveSpec: CurveSpecDTO, category: Category) {
  const names = category === '3ms' ? curveSpec.three_month_spreads : curveSpec.flies_3m;
  return names.slice(1);
}

export default function HistoricalCorrelationPanel({ curveId, curveSpec }: Props) {
  const selection = useICurveStore((s) => s.correlationSelections[curveId] ?? null);
  const setSelection = useICurveStore((s) => s.setCorrelationSelection);

  const [category, setCategory] = useState<Category>('3ms');
  const options = useMemo(() => currentOptions(curveSpec, category), [curveSpec, category]);
  const [current, setCurrent] = useState(options[0] ?? '');
  const [payload, setPayload] = useState<CorrelationHistoryPayload | StructureCorrelationHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [yMin, setYMin] = useState('-1');
  const [yMax, setYMax] = useState('1');

  const isCustom = selection?.kind === 'custom';

  useEffect(() => {
    if (selection?.kind !== 'builtin') return;
    setCategory(selection.category);
    setCurrent(selection.current);
  }, [selection]);

  useEffect(() => {
    if (isCustom) return;
    setCurrent((prev) => (options.includes(prev) ? prev : options[0] ?? ''));
  }, [options, isCustom]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const request = isCustom
      ? fetch(`/api/curves/${curveId}/custom-structure/correlation-history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal,
          body: JSON.stringify({
            legs_a: selection.legsPrevious,
            legs_b: selection.legsCurrent,
            label_a: selection.previous,
            label_b: selection.current,
          }),
        })
      : current
        ? fetch(`/api/curves/${curveId}/correlation-history?${new URLSearchParams({ category, current }).toString()}`, {
            signal: controller.signal,
          })
        : null;

    if (!request) {
      setLoading(false);
      return;
    }

    request
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setPayload)
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setPayload(null);
          setError(`Unable to load correlation history (${err.message})`);
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [curveId, category, current, isCustom, selection]);

  const points = payload?.points ?? [];
  const yRange = Number.isFinite(Number(yMin)) && Number.isFinite(Number(yMax))
    ? { yMin: Number(yMin), yMax: Number(yMax) }
    : {};
  const subtitle = isCustom && selection
    ? `${shortName(selection.current)} ${selection.structureName}`
    : payload && 'previous' in payload
      ? `${shortName(payload.previous)} -> ${shortName(payload.current)} | ${payload.history_days}d | ${payload.window_obs} obs`
      : 'cached correlation';

  return (
    <Panel title="Historical Correlation" subtitle={subtitle}>
      <div style={{ display: 'grid', gridTemplateColumns: 'auto minmax(180px, 1fr) auto auto', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', border: '1px solid #333333', borderRadius: '4px', overflow: 'hidden', opacity: isCustom ? 0.4 : 1 }}>
          {(['3ms', '3mf'] as Category[]).map((c) => (
            <button
              key={c}
              disabled={isCustom}
              onClick={() => setSelection({ kind: 'builtin', category: c, current: currentOptions(curveSpec, c)[0] ?? '' }, curveId)}
              style={{
                background: !isCustom && category === c ? '#262626' : '#141414',
                color: !isCustom && category === c ? '#e5e5e5' : '#888888',
                border: 0,
                borderRight: c === '3ms' ? '1px solid #333333' : 0,
                padding: '5px 10px',
                fontSize: '12px',
                cursor: isCustom ? 'default' : 'pointer',
              }}
            >
              {c === '3ms' ? 'Spread' : 'Fly'}
            </button>
          ))}
        </div>

        {isCustom ? (
          <div style={{ color: '#e5e5e5', fontSize: '12px', padding: '5px 8px' }}>
            {shortName(selection.current)} {selection.structureName}
          </div>
        ) : (
          <select
            value={current}
            onChange={(e) => setSelection({ kind: 'builtin', category, current: e.target.value }, curveId)}
            style={{ background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px', minWidth: 0 }}
          >
            {options.map((name) => (
              <option key={name} value={name}>{shortName(name)}</option>
            ))}
          </select>
        )}

        <label style={{ color: '#888888', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          Y
          <input value={yMin} onChange={(e) => setYMin(e.target.value)} style={{ width: '48px', background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '4px' }} />
          <input value={yMax} onChange={(e) => setYMax(e.target.value)} style={{ width: '48px', background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '4px' }} />
        </label>

        <div style={{ color: '#666666', fontSize: '11px', textAlign: 'right' }}>
          {loading ? 'loading...' : error ?? `${points.length} points`}
        </div>
      </div>

      <CorrelationOverTimeChart
        points={points}
        loading={loading}
        emptyMessage={error ?? 'No cached points yet'}
        {...yRange}
      />

      {payload && points.length > 0 && (
        <div style={{ color: '#666666', fontSize: '11px', marginTop: '4px' }}>
          Latest: {fmt.px(points[points.length - 1]?.correlation, 4)}
        </div>
      )}
    </Panel>
  );
}
