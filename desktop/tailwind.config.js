/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        neon: {
          green: '#00ff00',
          'bright-green': '#00ff88',
          teal: '#00cc88',
          cyan: '#00ffff',
          pink: '#ff00ff',
          blue: '#00aaff',
          violet: '#aa00ff',
          orange: '#ff6600',
        },
        panel: {
          bg: 'rgba(0, 17, 8, 0.4)',
          border: 'rgba(0, 170, 68, 0.2)',
        },
        cyber: {
          black: '#0a0a0f',
          dark: '#0d1117',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'neon-green': '0 0 15px rgba(0, 255, 0, 0.15), 0 0 30px rgba(0, 255, 0, 0.05)',
        'neon-cyan': '0 0 15px rgba(0, 255, 255, 0.15), 0 0 30px rgba(0, 255, 255, 0.05)',
        'neon-pink': '0 0 15px rgba(255, 0, 255, 0.15), 0 0 30px rgba(255, 0, 255, 0.05)',
        'panel': '0 4px 24px rgba(0, 0, 0, 0.4)',
      },
    },
  },
  plugins: [],
};