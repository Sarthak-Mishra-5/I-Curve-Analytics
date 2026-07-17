import { useStore } from './store';
import { useICurveStore } from './icurve/store';

let socket: WebSocket | null = null;
let reconnectDelay = 1000;
let pingTimer: number | null = null;

export function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${location.host}/ws`;
  socket = new WebSocket(url);

  socket.onopen = () => {
    reconnectDelay = 1000;
    useStore.getState().setConnected(true);
    if (pingTimer) clearInterval(pingTimer);
    pingTimer = window.setInterval(() => {
      try {
        socket?.send('ping');
      } catch {}
    }, 15000);
  };

  socket.onmessage = (e) => {
    let msg: any;
    try {
      msg = JSON.parse(e.data);
    } catch {
      return;
    }
    const s = useStore.getState();
    switch (msg.type) {
      case 'snapshot':
        s.applySnapshot(msg.payload);
        break;
      case 'tick':
        s.applyTickBatch(msg.payload);
        break;
      case 'analytics':
        s.applyAnalytics(msg.payload);
        break;
      case 'curve_stats':
        useICurveStore.getState().setStats(msg.payload);
        break;
      case 'alert':
        s.pushAlert(msg.payload);
        break;
      case 'pong':
        break;
    }
  };

  socket.onclose = () => {
    useStore.getState().setConnected(false);
    if (pingTimer) clearInterval(pingTimer);
    setTimeout(connectWS, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  };

  socket.onerror = () => {
    try {
      socket?.close();
    } catch {}
  };
}
