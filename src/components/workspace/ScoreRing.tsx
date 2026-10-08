import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon, Loader2 } from 'lucide-react';

export type ScoreState = 'calculating' | 'available' | 'unavailable' | 'failed';

interface ScoreRingProps {
  score?: number | null;
  state?: ScoreState;
  initialScore?: number;
  size?: number;
  strokeWidth?: number;
  supportingCaption?: string;
  isCeilingCapped?: boolean; // When backend caps score due to critical severity
  ceilingReason?: string;
}

export const ScoreRing: React.FC<ScoreRingProps> = ({
  score,
  state,
  initialScore: _initialScore = 100,
  size = 120,
  strokeWidth = 10,
  supportingCaption,
  isCeilingCapped = false,
  ceilingReason
}) => {
  // Infer state if not explicitly passed
  const resolvedState: ScoreState = state || (score === undefined || score === null ? 'calculating' : 'available');

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  
  const clampedScore = typeof score === 'number' ? Math.max(0, Math.min(100, score)) : 0;
  const offset = resolvedState === 'available'
    ? circumference - (clampedScore / 100) * circumference
    : circumference; // empty arc if calculating/unavailable

  const getScoreTheme = (val: number, curState: ScoreState) => {
    if (curState === 'calculating') {
      return {
        stroke: '#F59E0B',
        text: 'text-amber-400',
        label: 'Score Calculating',
        badgeClass: 'bg-amber-950/40 border-amber-800/40 text-amber-400'
      };
    }
    if (curState === 'unavailable' || curState === 'failed') {
      return {
        stroke: '#64748B',
        text: 'text-slate-400',
        label: curState === 'failed' ? 'Score Evaluation Failed' : 'Score Unavailable',
        badgeClass: 'bg-slate-900 border-slate-700 text-slate-400'
      };
    }
    // Locked score bands: 80+ Trustworthy, 50-79 Review Needed, <50 High Risk
    if (val >= 80) {
      return {
        stroke: '#10B981',
        text: 'text-emerald-400',
        label: 'Trustworthy',
        badgeClass: 'bg-emerald-950/40 border-emerald-800/40 text-emerald-400'
      };
    }
    if (val >= 50) {
      return {
        stroke: '#F59E0B',
        text: 'text-amber-400',
        label: 'Review Needed',
        badgeClass: 'bg-amber-950/40 border-amber-800/40 text-amber-400'
      };
    }
    return {
      stroke: '#DC2626',
      text: 'text-red-400',
      label: 'High Risk',
      badgeClass: 'bg-red-950/40 border-red-800/40 text-red-400'
    };
  };

  const theme = getScoreTheme(clampedScore, resolvedState);

  return (
    <div className="flex flex-col items-center">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#1E2C40"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Active Score Arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={theme.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            fill="transparent"
            className={resolvedState === 'calculating' ? 'animate-pulse' : 'transition-all duration-700 ease-out'}
          />
        </svg>

        {/* Center Numbers or State Indicator */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-2">
          {resolvedState === 'calculating' ? (
            <>
              <Loader2 className="w-6 h-6 text-amber-400 animate-spin mb-1" />
              <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400/90 leading-tight">
                Evaluating
              </span>
            </>
          ) : resolvedState === 'unavailable' || resolvedState === 'failed' ? (
            <>
              <span className="text-xl font-bold tracking-tight text-slate-500 font-mono">
                --
              </span>
              <span className="text-[9px] uppercase font-bold tracking-wider text-slate-500">
                Pending
              </span>
            </>
          ) : (
            <>
              <span className={`text-3xl font-bold tracking-tight font-tabular ${theme.text}`}>
                {clampedScore}
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider text-tathya-text-muted">
                Score / 100
              </span>
            </>
          )}
        </div>
      </div>

      {/* Band indicator & explicit state label */}
      <div className="mt-3 text-center">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${theme.badgeClass}`}>
          {resolvedState === 'calculating' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {resolvedState === 'available' && clampedScore >= 80 && <ShieldCheck className="w-3.5 h-3.5" />}
          {resolvedState === 'available' && clampedScore >= 50 && clampedScore < 80 && <AlertTriangle className="w-3.5 h-3.5" />}
          {resolvedState === 'available' && clampedScore < 50 && <AlertOctagon className="w-3.5 h-3.5" />}
          {theme.label}
        </span>

        {/* Backend Critical Risk Ceiling Notification */}
        {isCeilingCapped && (
          <div className="mt-1.5 text-[10px] font-mono text-red-400 bg-red-950/40 border border-red-800/40 px-2 py-0.5 rounded">
            ⚠ Ceiling Capped: {ceilingReason || 'Critical materiality conflict'}
          </div>
        )}

        <p className="text-[11px] text-tathya-text-muted mt-1.5 max-w-[200px] mx-auto leading-tight">
          {supportingCaption || (
            resolvedState === 'calculating'
              ? 'Analyzing extracted claims against grounding sources...'
              : 'Deterministic fact grounding score'
          )}
        </p>
      </div>
    </div>
  );
};
