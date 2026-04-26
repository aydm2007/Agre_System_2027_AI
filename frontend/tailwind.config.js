export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Tajawal', 'ui-sans-serif', 'system-ui'],
        arabic: ['Cairo', 'Tajawal', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#047857', // Deep Emerald
          light: '#34D399',
          dark: '#064E3B',
          50: '#ECFDF5',
          100: '#D1FAE5',
          900: '#064E3B',
        },
        secondary: {
          DEFAULT: '#D97706', // Golden Harvest
          light: '#FBBF24',
          dark: '#B45309',
        },
        accent: {
          DEFAULT: '#92400E', // Rich Earth
          light: '#B45309',
          dark: '#78350F',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          subtle: '#F9FAFB',
          warm: '#FFFBEB', // Warm Cream
        },
        danger: { DEFAULT: '#EF4444', dark: '#DC2626' },
        success: { DEFAULT: '#10B981', dark: '#059669' },
        gray: {
          50: '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827',
        },
        // Phase 12: Semantic Theme Tokens (CSS Variable Based)
        bg: {
          primary: 'rgb(var(--color-bg-primary) / <alpha-value>)',
          secondary: 'rgb(var(--color-bg-secondary) / <alpha-value>)',
          surface: 'rgb(var(--color-bg-surface) / <alpha-value>)',
          elevated: 'rgb(var(--color-bg-elevated) / <alpha-value>)',
        },
        text: {
          primary: 'rgb(var(--color-text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--color-text-secondary) / <alpha-value>)',
          muted: 'rgb(var(--color-text-muted) / <alpha-value>)',
        },
        border: {
          DEFAULT: 'rgb(var(--color-border) / <alpha-value>)',
          strong: 'rgb(var(--color-border-strong) / <alpha-value>)',
        },
      },
    },
  },
  plugins: [],
}
