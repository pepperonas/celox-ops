import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Legacy semantic names — MD3 tonal palette via RGB channels so
        // Tailwind opacity modifiers (bg-danger/10, border-accent/40) keep working.
        bg: 'rgb(var(--c-bg) / <alpha-value>)',
        surface: 'rgb(var(--c-surface) / <alpha-value>)',
        'surface-2': 'rgb(var(--c-surface2) / <alpha-value>)',
        border: 'rgb(var(--c-border) / <alpha-value>)',
        text: 'rgb(var(--c-text) / <alpha-value>)',
        'text-muted': 'rgb(var(--c-text-muted) / <alpha-value>)',
        accent: 'rgb(var(--c-accent) / <alpha-value>)',
        'accent-hover': 'rgb(var(--c-accent-hover) / <alpha-value>)',
        success: 'rgb(var(--c-success) / <alpha-value>)',
        warning: 'rgb(var(--c-warning) / <alpha-value>)',
        danger: 'rgb(var(--c-danger) / <alpha-value>)',
        purple: 'rgb(var(--c-purple) / <alpha-value>)',
        cyan: 'rgb(var(--c-cyan) / <alpha-value>)',

        // MD3 role tokens (available as utilities, e.g. bg-md-primary, text-on-primary)
        'md-primary': 'var(--md-primary)',
        'on-primary': 'var(--md-on-primary)',
        'md-primary-container': 'var(--md-primary-container)',
        'on-primary-container': 'var(--md-on-primary-container)',
        'md-secondary': 'var(--md-secondary)',
        'md-secondary-container': 'var(--md-secondary-container)',
        'on-secondary-container': 'var(--md-on-secondary-container)',
        'md-tertiary': 'var(--md-tertiary)',
        'md-error': 'var(--md-error)',
        'md-error-container': 'var(--md-error-container)',
        'on-error-container': 'var(--md-on-error-container)',
        outline: 'var(--md-outline)',
        'outline-variant': 'var(--md-outline-variant)',
        'surface-lowest': 'var(--md-surface-container-lowest)',
        'surface-low': 'var(--md-surface-container-low)',
        'surface-container': 'var(--md-surface-container)',
        'surface-high': 'var(--md-surface-container-high)',
        'surface-highest': 'var(--md-surface-container-highest)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
      },
      maxWidth: {
        content: '1400px',
      },
      borderRadius: {
        // MD3 Expressive shape scale — moderate bump over Tailwind defaults
        // so existing rounded-* usages get more expressive without over-rounding.
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '20px',
        '2xl': '28px',
        card: 'var(--md-shape-md)',  // 16px
      },
      boxShadow: {
        'elev-1': 'var(--md-elev-1)',
        'elev-2': 'var(--md-elev-2)',
        'elev-3': 'var(--md-elev-3)',
      },
      transitionTimingFunction: {
        emphasized: 'var(--md-ease-emphasized)',
        decelerate: 'var(--md-ease-decelerate)',
        accelerate: 'var(--md-ease-accelerate)',
        spring: 'var(--md-ease-spring)',
        standard: 'var(--md-ease-standard)',
      },
      transitionDuration: {
        short: '180ms',
        medium: '320ms',
        long: '500ms',
      },
      keyframes: {
        'md-fade-up': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'md-scale-in': {
          from: { opacity: '0', transform: 'scale(0.92)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'md-pop': {
          '0%': { transform: 'scale(0.8)', opacity: '0' },
          '60%': { transform: 'scale(1.04)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      animation: {
        'md-enter': 'md-fade-up 0.32s cubic-bezier(0.05,0.7,0.1,1) both',
        'md-scale': 'md-scale-in 0.32s cubic-bezier(0.34,1.45,0.5,1) both',
        'md-pop': 'md-pop 0.32s cubic-bezier(0.34,1.45,0.5,1) both',
      },
    },
  },
  plugins: [],
} satisfies Config
