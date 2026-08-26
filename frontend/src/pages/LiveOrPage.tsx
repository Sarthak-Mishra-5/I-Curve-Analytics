import { useStore } from '../store';
import TopQuotesPanel from '../components/TopQuotesPanel';
import CandleChart from '../components/CandleChart';
import DailyChangeTable from '../components/DailyChangeTable';

const OUTRIGHTS: { curveId: string; instrument: string; title: string }[] = [
  { curveId: 'SR3', instrument: 'SR3 Sep27', title: 'SOFR (SR3) Sep27' },
  { curveId: 'SO3', instrument: 'SO3 Sep27', title: 'SONIA (SO3) Sep27' },
  { curveId: 'I', instrument: 'I Sep27', title: 'Euribor (I) Sep27' },
  { curveId: 'SA3', instrument: 'SA3 Sep27', title: 'SARON (SA3) Sep27' },
];

export default function LiveOrPage() {
  const quotes = useStore((s) => s.quotes);

  return (
    <main
      className="flex-1 overflow-auto p-1.5"
      style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}
    >
      <div style={{ flexShrink: 0 }}>
        <DailyChangeTable />
      </div>
      {/* <TopQuotesPanel /> */}

      {/* 2x2 chart grid — grows to fill the viewport, with a floor so the
          charts stay usable on short windows (the page scrolls instead). */}
      <div
        style={{
          flex: '1 1 auto',
          display: 'grid',
          gap: '6px',
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
          gridTemplateRows: 'repeat(2, minmax(300px, 1fr))',
          minHeight: '620px',
        }}
      >
        {OUTRIGHTS.map((o) => {
          // Today's opening print is a genuine fixed reference level for this
          // page (whose whole point is change-from-open), and is deliberately
          // distinct from the current-price marker the chart draws itself.
          const open = quotes[o.instrument]?.open ?? null;
          return (
            <CandleChart
              key={o.instrument}
              curveId={o.curveId}
              instrument={o.instrument}
              title={o.title}
              levels={open != null ? [open] : []}
            />
          );
        })}
      </div>
    </main>
  );
}
