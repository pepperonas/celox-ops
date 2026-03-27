import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0d1117',
        surface: '#161b22',
        'surface-2': '#1c2128',
        border: '#30363d',
        text: '#e6edf3',
        'text-muted': '#8b949e',
        accent: '#58a6ff',
        'accent-hover': '#79b8ff',
        success: '#3fb950',
        warning: '#d29922',
        danger: '#f85149',
        purple: '#bc8cff',
        cyan: '#39d2c0',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
      },
      maxWidth: {
        content: '1400px',
      },
      borderRadius: {
        card: '12px',
      },
    },
  },
  plugins: [],
} satisfies Config
