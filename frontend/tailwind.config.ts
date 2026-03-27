import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        celox: {
          50: '#e6f7fb',
          100: '#b3e8f3',
          200: '#80d9eb',
          300: '#4dcae3',
          400: '#1abbdb',
          500: '#00b4d8',
          600: '#0090ad',
          700: '#006c82',
          800: '#004856',
          900: '#00242b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
