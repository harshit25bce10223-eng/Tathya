import React from 'react';
import { Flag } from '../../api/types';
import { SeverityBadge, MaterialityBadge } from '../brand/TrustBadge';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Wrench
} from 'lucide-react';

interface FlagCardProps {
  flag: Flag;
  isSelected?: boolean;
  onSelect?: () => void;
}

export const FlagCard: React.FC<FlagCardProps> = ({
  flag,
  isSelected = false,
  onSelect,
}) => {
  const getStatusBadge = () => {
    switch (flag.status) {
      case 'ACCEPTED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-950/70 text-red-300 border border-red-700/60 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-red-400" />
            Confirmed Risk
          </span>
        );
      case 'DISMISSED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-900 text-slate-400 border border-slate-700 flex items-center gap-1">
            <XCircle className="w-3 h-3 text-slate-400" />
            Dismissed
          </span>
        );
      case 'FIXED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/70 text-emerald-300 border border-emerald-700/60 flex items-center gap-1">
            <Wrench className="w-3 h-3 text-emerald-400" />
            Remediated
          </span>
        );
      case 'PENDING':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950/70 text-amber-300 border border-amber-700/60 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            Review Required
          </span>
        );
    }
  };

  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-xl border transition-all cursor-pointer ${
        isSelected
          ? 'bg-tathya-surface-elevated border-tathya-accent ring-1 ring-tathya-accent/50 shadow-tathya-elevated'
          : 'bg-tathya-surface border-tathya-surface-border hover:border-slate-600 hover:bg-tathya-surface/80'
      }`}
    >
      {/* Top Header: Category, Severity, Materiality, Status */}
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-bold text-white uppercase tracking-wider">
            {flag.type}
          </span>
          <SeverityBadge severity={flag.severity} />
          <MaterialityBadge materiality={flag.materiality} />
        </div>
        <div>{getStatusBadge()}</div>
      </div>

      {/* Primary Question: Why Should I Care? (Reason) */}
      <div className="mb-3 p-2.5 rounded-lg bg-red-950/25 border border-red-900/40 text-xs text-red-200 leading-relaxed">
        <span className="font-semibold text-red-300 block mb-0.5">Finding Materiality:</span>
        {flag.reason}
      </div>

      {/* Claim vs Expected */}
      <div className="space-y-1.5 text-xs mb-3">
        <div className="text-tathya-text-muted">
          <span className="text-white font-medium">Document Claim: </span>
          <span className="italic text-slate-300">"{flag.claim}"</span>
        </div>
      </div>

      {/* Evidence Preview */}
      <div className="p-2.5 rounded-lg bg-tathya-surface-elevated/80 border border-tathya-surface-border text-xs mb-3">
        <div className="flex items-center justify-between text-[11px] text-tathya-text-muted mb-1 font-mono">
          <span className="truncate text-emerald-400 font-semibold">{flag.evidence.authority}</span>
          <span className="flex-shrink-0">{flag.evidence.location}</span>
        </div>
        <p className="text-slate-300 italic text-[11px] leading-relaxed">
          {flag.evidence.quote}
        </p>
      </div>

      {/* Suggested Fix */}
      <div className="flex items-start gap-1.5 text-xs text-emerald-300 bg-emerald-950/20 p-2 rounded border border-emerald-900/40">
        <span className="font-bold text-emerald-400 flex-shrink-0">Suggested Fix:</span>
        <span className="leading-snug">{flag.suggestedFix}</span>
      </div>
    </div>
  );
};
