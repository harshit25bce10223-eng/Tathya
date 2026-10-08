/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        tathya: {
          bg: {
            DEFAULT: '#0B0F17',
            secondary: '#070A0F',
            subtle: '#101725',
          },
          surface: {
            DEFAULT: '#121A27',
            elevated: '#172233',
            hover: '#1D2A3F',
            active: '#24344E',
            border: '#1E2C40',
            borderSubtle: '#152030',
          },
          text: {
            primary: '#F1F5F9',
            secondary: '#94A3B8',
            muted: '#64748B',
            disabled: '#475569',
          },
          accent: {
            DEFAULT: '#F59E0B',
            hover: '#D97706',
            subtle: 'rgba(245, 158, 11, 0.15)',
            border: 'rgba(245, 158, 11, 0.4)',
          },
          status: {
            success: '#10B981',
            successSubtle: 'rgba(16, 185, 129, 0.12)',
            successBorder: 'rgba(16, 185, 129, 0.28)',

            warning: '#F59E0B',
            warningSubtle: 'rgba(245, 158, 11, 0.12)',
            warningBorder: 'rgba(245, 158, 11, 0.28)',

            danger: '#EF4444',
            dangerSubtle: 'rgba(239, 68, 68, 0.12)',
            dangerBorder: 'rgba(239, 68, 68, 0.28)',

            critical: '#DC2626',
            criticalSubtle: 'rgba(220, 38, 38, 0.16)',
            criticalBorder: 'rgba(220, 38, 38, 0.36)',

            info: '#3B82F6',
            infoSubtle: 'rgba(59, 130, 246, 0.12)',
            infoBorder: 'rgba(59, 130, 246, 0.28)',
          },
          gold: {
            DEFAULT: '#EAB308',
            subtle: 'rgba(234, 179, 8, 0.12)',
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'tathya-sm': '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
        'tathya-card': '0 4px 16px -2px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3)',
        'tathya-elevated': '0 10px 30px -5px rgba(0, 0, 0, 0.6), 0 4px 8px -2px rgba(0, 0, 0, 0.4)',
        'tathya-focus': '0 0 0 2px #0B0F17, 0 0 0 4px #F59E0B',
      },
      borderRadius: {
        'tathya-sm': '4px',
        'tathya': '8px',
        'tathya-md': '10px',
        'tathya-lg': '12px',
      }
    },
  },
  plugins: [],
}
