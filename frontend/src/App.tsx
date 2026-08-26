import { useEffect, useState } from 'react';
import Header from './components/Header';
import type { ActiveView } from './components/Header';
import ICurveAnalyticsPage from './pages/ICurveAnalyticsPage';
import InterProductLabPage from './pages/InterProductLabPage';
import LiveOrPage from './pages/LiveOrPage';
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
      ) : activeView === 'interproduct' ? (
        <InterProductLabPage />
      ) : (
        <LiveOrPage />
      )}
    </div>
  );
}
