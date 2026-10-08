/**
 * TATHYA (तथ्य) CENTRALIZED DESIGN TOKEN SYSTEM
 * 
 * Strict enterprise trust/compliance design tokens.
 * All components and views derive styling from this central specification.
 */

export const tokens = {
  colors: {
    // Backgrounds
    background: '#0B0F17',
    backgroundSecondary: '#070A0F',
    backgroundSubtle: '#101725',

    // Surfaces
    surface: '#121A27',
    surfaceElevated: '#172233',
    surfaceHover: '#1D2A3F',
    surfaceActive: '#24344E',
    border: '#1E2C40',
    borderSubtle: '#152030',

    // Typography
    textPrimary: '#F1F5F9',
    textSecondary: '#94A3B8',
    textMuted: '#64748B',
    textDisabled: '#475569',

    // Accents & Brand
    accent: '#38BDF8',
    accentHover: '#0EA5E9',
    accentSubtle: 'rgba(56, 189, 248, 0.1)',
    accentBorder: 'rgba(56, 189, 248, 0.3)',

    // Status Colors (Restrained, High-Materiality)
    // SUCCESS: Confirmed / Healthy
    success: '#10B981',
    successSubtle: 'rgba(16, 185, 129, 0.12)',
    successBorder: 'rgba(16, 185, 129, 0.28)',

    // WARNING: Review Needed
    warning: '#F59E0B',
    warningSubtle: 'rgba(245, 158, 11, 0.12)',
    warningBorder: 'rgba(245, 158, 11, 0.28)',

    // DANGER: Contradiction / Serious Problem
    danger: '#EF4444',
    dangerSubtle: 'rgba(239, 68, 68, 0.12)',
    dangerBorder: 'rgba(239, 68, 68, 0.28)',

    // CRITICAL: Material Business Risk
    critical: '#DC2626',
    criticalSubtle: 'rgba(220, 38, 38, 0.16)',
    criticalBorder: 'rgba(220, 38, 38, 0.36)',

    // INFO: Neutral Information
    info: '#3B82F6',
    infoSubtle: 'rgba(59, 130, 246, 0.12)',
    infoBorder: 'rgba(59, 130, 246, 0.28)',

    // Focus & Overlay
    focus: '#38BDF8',
    selection: 'rgba(56, 189, 248, 0.2)',
    overlay: 'rgba(3, 7, 18, 0.75)',
  },

  typography: {
    fontSans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontMono: "'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    sizes: {
      xs: '0.75rem',    // 12px - metadata, badges, hashes
      sm: '0.875rem',   // 14px - table data, card body, secondary text
      base: '1rem',     // 16px - body, document text, inputs
      lg: '1.125rem',   // 18px - section headings, subheaders
      xl: '1.25rem',    // 20px - card headers, panel titles
      '2xl': '1.5rem',  // 24px - page headers, metrics
      '3xl': '1.875rem',// 30px - hero display, score ring number
    },
    weights: {
      regular: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    lineHeights: {
      tight: '1.2',
      normal: '1.5',
      relaxed: '1.65',
    },
  },

  spacing: {
    1: '0.25rem',  // 4px
    2: '0.5rem',   // 8px
    3: '0.75rem',  // 12px
    4: '1rem',     // 16px
    5: '1.25rem',  // 20px
    6: '1.5rem',   // 24px
    8: '2rem',     // 32px
    10: '2.5rem',  // 40px
    12: '3rem',    // 48px
  },

  radii: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    full: '9999px',
  },

  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
    card: '0 4px 16px -2px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3)',
    elevated: '0 10px 30px -5px rgba(0, 0, 0, 0.6), 0 4px 8px -2px rgba(0, 0, 0, 0.4)',
    focusRing: '0 0 0 2px #0B0F17, 0 0 0 4px #38BDF8',
  },

  transitions: {
    fast: '150ms cubic-bezier(0.16, 1, 0.3, 1)',
    normal: '200ms cubic-bezier(0.16, 1, 0.3, 1)',
  },

  // Locked Score Bands (Mandated by Tathya Core)
  scoreBands: {
    trustworthy: { min: 80, max: 100, label: 'Trustworthy', color: '#10B981', bg: 'rgba(16, 185, 129, 0.12)' },
    reviewNeeded: { min: 50, max: 79, label: 'Review Needed', color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)' },
    highRisk: { min: 0, max: 49, label: 'High Risk', color: '#DC2626', bg: 'rgba(220, 38, 38, 0.16)' },
  },
} as const;

export type TathyaTokens = typeof tokens;
