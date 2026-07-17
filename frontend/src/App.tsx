import { useEffect, useState } from 'react';
import Header from './components/Header';
import type { ActiveView } from './components/Header';
import TopQuotesPanel from './components/TopQuotesPanel';
import CurvePanel from './components/CurvePanel';
import SpreadPanel from './components/SpreadPanel';
import RegressionPanel from './components/RegressionPanel';
import AlertsPanel from './components/AlertsPanel';
import AnalyticsPanel from './components/AnalyticsPanel';
import ICurveLiveCharts from './components/ICurveLiveCharts';
import ICurveAnalyticsPage from './pages/ICurveAnalyticsPage';
import { connectWS } from './ws';

export default function App() {
  const [activeView, setActiveView] = useState<ActiveView>('icurve');

  useEffect(() => {
    connectWS();
  }, []);

  return (
    <div className="h-screen flex flex-col bg-terminal-bg">
      <Header activeView={activeView} onChangeView={setActiveView} />
      {activeView === 'icurve' ? (
        <ICurveAnalyticsPage />
      ) : (
        <main className="flex-1 overflow-auto p-1.5 grid gap-1.5"
          style={{
            gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
            gridTemplateRows: 'auto 360px auto',
          }}>
          <div className="col-span-4"><TopQuotesPanel /></div>
          <div className="col-span-4"><ICurveLiveCharts /></div>
          <div className="col-span-2"><CurvePanel /></div>
          <div className="col-span-2"><SpreadPanel /></div>
          <div className="col-span-4"><AnalyticsPanel /></div>
          <div className="col-span-4"><RegressionPanel /></div>
          <div className="col-span-4"><AlertsPanel /></div>
        </main>
      )}
    </div>
  );
}
