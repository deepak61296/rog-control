/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'cyber-black': '#0a0a0f',
        'cyber-panel': 'rgba(0,17,8,0.4)',
        'neon-green': '#00ff00',
        'neon-cyan': '#00ffff',
        'neon-pink': '#ff00ff',
        'neon-orange': '#ff6600',
        'neon-teal': '#00cc88',
        'neon-yellow': '#ffff00',
        'neon-red': '#ff4444',
        'dim-green': '#008844',
        'border-green': '#00aa44',
        'glass-bg': 'rgba(0,17,8,0.4)',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
      boxShadow: {
        'glow-green': '0 0 15px rgba(0,255,0,0.15), inset 0 0 15px rgba(0,255,0,0.05)',
        'glow-cyan': '0 0 15px rgba(0,255,255,0.15), inset 0 0 15px rgba(0,255,255,0.05)',
        'glow-pink': '0 0 15px rgba(255,0,255,0.15), inset 0 0 15px rgba(255,0,255,0.05)',
      },
    },
  },
  plugins: [],
}