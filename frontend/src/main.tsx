import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

const root = document.getElementById('root');
if (!root) {
  document.body.innerHTML = '<div style="color: red; padding: 20px;">Root element not found!</div>';
} else {
  try {
    createRoot(root).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
  } catch (e) {
    console.error('Render error:', e);
    document.body.innerHTML = `<div style="color: #ff3355; padding: 20px; font-family: monospace; white-space: pre-wrap;">${String(e)}</div>`;
  }
}

window.addEventListener('error', (e) => {
  console.error('Global error:', e);
});
