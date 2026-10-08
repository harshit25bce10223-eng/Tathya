import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon } from 'lucide-react';

interface ScoreRingProps {
  score: number;
  initialScore?: number;
  size?: number;
  strokeWidth?: number;
}

export const ScoreRing: React.FC<ScoreRingProps> = ({
  score,
  initialScore: _initialScore = 100,
  size = 120,
  strokeWidth = 10,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.max(0, Math.min(100, score));
  const offset = circumference - (clampedScore / 100) * circumference;

  const getScoreColor = (val: number) => {
    if (val >= 80) return { stroke: '#10B981', text: 'text-emerald-400', label: 'Trustworthy', bg: 'bg-emerald-950/40 border-emerald-800/40' };
    if (val >= 50) return { stroke: '#F59E0B', text: 'text-amber-400', label: 'Review Needed', bg: 'bg-amber-950/40 border-amber-800/40' };
    return { stroke: '#DC2626', text: 'text-red-400', label: 'High Risk', bg: 'bg-red-950/40 border-red-800/40' };
  };

  const theme = getScoreColor(clampedScore);

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
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center Numbers */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className={`text-3xl font-bold tracking-tight font-tabular ${theme.text}`}>
            {clampedScore}
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-tathya-text-muted">
            Score / 100
          </span>
        </div>
      </div>

      {/* Band indicator & explicit reminder */}
      <div className="mt-3 text-center">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${theme.bg} ${theme.text}`}>
          {clampedScore >= 80 && <ShieldCheck className="w-3.5 h-3.5" />}
          {clampedScore >= 50 && clampedScore < 80 && <AlertTriangle className="w-3.5 h-3.5" />}
          {clampedScore < 50 && <AlertOctagon className="w-3.5 h-3.5" />}
          {theme.label}
        </span>
        <p className="text-[11px] text-tathya-text-muted mt-1.5">
          Deterministic fact score (not model confidence)
        </p>
      </div>
    </div>
  );
};
