/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0a0a0a',
          panel: '#141414',
          panel2: '#1a1a1a',
          border: '#262626',
          green: '#00ff88',
          red: '#ff3355',
          amber: '#ffaa00',
          blue: '#4aa8ff',
          text: '#e5e5e5',
          muted: '#666666',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
