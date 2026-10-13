/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4F46E5',
          hover: '#4338CA',
          light: '#EEF2FF',
        },
        bg: {
          page: '#F8FAFC',
          surface: '#FFFFFF',
          secondary: '#F1F5F9',
        },
        text: {
          primary: '#0F172A',
          secondary: '#475569',
          muted: '#64748B',
          disabled: '#94A3B8',
        },
        border: {
          DEFAULT: '#E2E8F0',
          strong: '#CBD5E1',
        },
        status: {
          success: '#16A34A',
          'success-bg': '#F0FDF4',
          warning: '#D97706',
          'warning-bg': '#FFFBEB',
          error: '#DC2626',
          'error-bg': '#FEF2F2',
          info: '#2563EB',
          'info-bg': '#EFF6FF',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
      },
      borderRadius: {
        sm: '6px',
        DEFAULT: '8px',
        md: '8px',
        lg: '10px',
        xl: '12px',
      }
    },
  },
  plugins: [],
}
