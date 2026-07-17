import { useMemo } from 'react';
import { useStore } from '../store';
import Panel from './Panel';
import { fmt } from '../plotlyTheme';
import {
  buildContractPairs,
  buildOutrightRows,
  build3MSRows,
  build3MFRows,
  type OutrightRow,
  type SpreadRow,
} from '../utils/analytics';
import clsx from 'clsx';

function getDiffColor(value: number | null) {
  if (value === null) return 'text-terminal-muted';
  if (Math.abs(value) < 0.01) return 'text-terminal-muted';
  return value > 0 ? 'text-terminal-green' : 'text-terminal-red';
}

function formatExpiryLabel(expiry: OutrightRow['pair']['expiry']) {
  return `${expiry.month}${String(expiry.year).slice(-2)}`;
}

function OutrightsTable({ rows }: { rows: OutrightRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px] tabular-nums border-collapse">
        <thead>
          <tr className="bg-terminal-panel2 border-b border-terminal-border sticky top-0">
            <th className="px-2 py-1.5 text-left font-semibold text-terminal-muted">Expiry</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">SA3</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">Change</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">ER3</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">Change</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">Diff</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.pair.sa3}-${row.pair.er3}`} className="border-b border-terminal-border hover:bg-terminal-panel2 transition-colors">
              <td className="px-2 py-1.5 text-terminal-text font-medium">{formatExpiryLabel(row.pair.expiry)}</td>
              <td className="px-2 py-1.5 text-right text-terminal-text">{fmt.px(row.sa3Value)}</td>
              <td className={clsx('px-2 py-1.5 text-right', row.sa3Change ? (row.sa3Change > 0 ? 'text-terminal-green' : 'text-terminal-red') : 'text-terminal-muted')}>
                {fmt.chg(row.sa3Change)}
              </td>
              <td className="px-2 py-1.5 text-right text-terminal-text">{fmt.px(row.er3Value)}</td>
              <td className={clsx('px-2 py-1.5 text-right', row.er3Change ? (row.er3Change > 0 ? 'text-terminal-green' : 'text-terminal-red') : 'text-terminal-muted')}>
                {fmt.chg(row.er3Change)}
              </td>
              <td className={clsx('px-2 py-1.5 text-right font-medium', getDiffColor(row.difference))}>
                {fmt.px(row.difference)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SpreadTable({ rows, title }: { rows: SpreadRow[]; title: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px] tabular-nums border-collapse">
        <thead>
          <tr className="bg-terminal-panel2 border-b border-terminal-border sticky top-0">
            <th className="px-2 py-1.5 text-left font-semibold text-terminal-muted">{title}</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">SA3</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">ER3</th>
            <th className="px-2 py-1.5 text-right font-semibold text-terminal-muted">Diff</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.name}-${row.type}`} className="border-b border-terminal-border hover:bg-terminal-panel2 transition-colors">
              <td className="px-2 py-1.5 text-terminal-text font-medium text-[10px]">{row.name}</td>
              <td className="px-2 py-1.5 text-right text-terminal-text">{fmt.px(row.sa3Value, 2)}</td>
              <td className="px-2 py-1.5 text-right text-terminal-text">{fmt.px(row.er3Value, 2)}</td>
              <td className={clsx('px-2 py-1.5 text-right font-medium', getDiffColor(row.difference))}>
                {fmt.px(row.difference, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AnalyticsPanel() {
  const quotes = useStore((s) => s.quotes);
  const contracts = useStore((s) => s.contracts);

  const { pairs, outrights, spreads3m, flies3m } = useMemo(() => {
    const contractPairs = buildContractPairs(contracts);
    const outrightRows = buildOutrightRows(contractPairs, quotes);
    const spreadRows = build3MSRows(contractPairs, quotes);
    const flyRows = build3MFRows(contractPairs, quotes);

    return {
      pairs: contractPairs,
      outrights: outrightRows,
      spreads3m: spreadRows,
      flies3m: flyRows,
    };
  }, [quotes, contracts]);

  return (
    <div className="grid gap-1.5 grid-cols-1">
      <Panel title="Outrights" subtitle={`${pairs.length} contracts`}>
        <OutrightsTable rows={outrights} />
      </Panel>
      <div className="grid gap-1.5 grid-cols-2">
          <Panel title="3-Month Spreads (3MS)" subtitle={`${spreads3m.length} spreads`}>
        <SpreadTable rows={spreads3m} title="Period" />
        </Panel>

        <Panel title="3-Month Flies (3MF)" subtitle={`${flies3m.length} flies`}>
        <SpreadTable rows={flies3m} title="Period" />
        </Panel>
      </div>

      
    </div>
  );
}
