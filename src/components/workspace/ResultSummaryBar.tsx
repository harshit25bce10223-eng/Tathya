import React from 'react';
import {
  VerificationResultSummary,
  TrustResultState,
  SeverityLevel
} from '../../api/types';
import {
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  HelpCircle,
  Scale,
  FileSearch,
  FileCheck2,
  Filter,
  Info
} from 'lucide-react';

interface ResultSummaryBarProps {
  summary: VerificationResultSummary;
  activeFilter?: SeverityLevel | 'ALL' | 'UNCERTAIN';
  onFilterChange?: (filter: SeverityLevel | 'ALL' | 'UNCERTAIN') => void;
  documentVersion?: string;
}

export const ResultSummaryBar: React.FC<ResultSummaryBarProps> = ({
  summary,
  activeFilter = 'ALL',
  onFilterChange,
  documentVersion
}) => {
  const getResultStateBadge = (state: TrustResultState) => {
    switch (state) {
      case 'READY':
      case 'FINDINGS_PRESENT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-red-950/60 border border-red-700/60 text-red-300">
            <AlertOctagon className="w-3.5 h-3.5 text-red-400" />
            Material Conflicts Detected
          </span>
        );
      case 'NO_FINDINGS':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-950/60 border border-emerald-700/60 text-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            100% Ground Truth Confirmed
          </span>
        );
      case 'UNCERTAIN':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-950/60 border border-amber-700/60 text-amber-300">
            <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
            Inconclusive / Reviewer Verification Needed
          </span>
        );
      case 'PARTIAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-900 border border-amber-700/50 text-amber-300">
            <Info className="w-3.5 h-3.5 text-amber-400" />
            Partial Ingestion Completed
          </span>
        );
      case 'PROCESSING':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-900 border border-slate-700 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            Verification Running
          </span>
        );
    }
  };

  return (
    <div className="result-summary bg-tathya-surface border border-tathya-surface-border rounded-xl p-3.5 sm:p-4 shadow-tathya-sm space-y-3">
      {/* Top Banner: Status & Version */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-tathya-surface-border">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold uppercase tracking-wider text-white">
            Trust Pipeline Result
          </span>
          {getResultStateBadge(summary.resultState)}
        </div>

        {documentVersion && (
          <div className="flex items-center gap-2 text-[11px] font-mono text-tathya-text-muted">
            <span>Canonical Doc:</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 font-semibold">
              {documentVersion} (Immutable)
            </span>
          </div>
        )}
      </div>

      {/* Metrics Row: Strict backend values without fabrication */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3 text-left">
        {/* Metric 1: Claims Checked */}
        <div className="p-2.5 rounded-lg bg-tathya-surface-elevated/70 border border-tathya-surface-border">
          <div className="flex items-center gap-1.5 text-tathya-text-muted text-[10px] uppercase font-bold tracking-wider mb-1">
            <Scale className="w-3 h-3 text-slate-400" />
            Claims Checked
          </div>
          <div className="text-lg font-bold text-white font-tabular">
            {summary.claimsChecked}
          </div>
          <div className="text-[10px] text-tathya-text-muted">Deterministic statements</div>
        </div>

        {/* Metric 2: Evidence Matched */}
        <div className="p-2.5 rounded-lg bg-tathya-surface-elevated/70 border border-tathya-surface-border">
          <div className="flex items-center gap-1.5 text-emerald-400 text-[10px] uppercase font-bold tracking-wider mb-1">
            <FileSearch className="w-3 h-3" />
            Evidence Matched
          </div>
          <div className="text-lg font-bold text-emerald-400 font-tabular">
            {summary.evidenceMatched}
          </div>
          <div className="text-[10px] text-tathya-text-muted">Approved source anchors</div>
        </div>

        {/* Metric 3: Contradictions */}
        <div className="p-2.5 rounded-lg bg-red-950/20 border border-red-900/40">
          <div className="flex items-center gap-1.5 text-red-400 text-[10px] uppercase font-bold tracking-wider mb-1">
            <AlertOctagon className="w-3 h-3" />
            Contradictions
          </div>
          <div className="text-lg font-bold text-red-400 font-tabular">
            {summary.contradictions}
          </div>
          <div className="text-[10px] text-red-300/80">Conflicts with source</div>
        </div>

        {/* Metric 4: Unsupported */}
        <div className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-900/40">
          <div className="flex items-center gap-1.5 text-amber-400 text-[10px] uppercase font-bold tracking-wider mb-1">
            <AlertTriangle className="w-3 h-3" />
            Unsupported
          </div>
          <div className="text-lg font-bold text-amber-400 font-tabular">
            {summary.unsupportedClaims}
          </div>
          <div className="text-[10px] text-amber-300/80">No ground truth found</div>
        </div>

        {/* Metric 5: Uncertain */}
        <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/60">
          <div className="flex items-center gap-1.5 text-slate-300 text-[10px] uppercase font-bold tracking-wider mb-1">
            <HelpCircle className="w-3 h-3 text-slate-400" />
            Uncertain
          </div>
          <div className="text-lg font-bold text-slate-200 font-tabular">
            {summary.uncertainClaims}
          </div>
          <div className="text-[10px] text-tathya-text-muted">Inconclusive evidence</div>
        </div>

        {/* Metric 6: Critical Findings */}
        <div className="p-2.5 rounded-lg bg-red-950/30 border border-red-700/60">
          <div className="flex items-center gap-1.5 text-red-300 text-[10px] uppercase font-bold tracking-wider mb-1">
            <AlertOctagon className="w-3 h-3 text-red-400" />
            Critical Findings
          </div>
          <div className="text-lg font-bold text-red-300 font-tabular">
            {summary.criticalFindings}
          </div>
          <div className="text-[10px] text-red-400 font-medium">Material business risk</div>
        </div>
      </div>

      {/* Filter Tabs for interactive triage */}
      {onFilterChange && (
        <div className="flex items-center justify-between pt-2 border-t border-tathya-surface-border text-xs">
          <div className="flex items-center gap-1.5 text-tathya-text-muted">
            <Filter className="w-3.5 h-3.5" />
            <span className="text-[11px] font-semibold uppercase tracking-wider">Filter Findings:</span>
          </div>

          <div className="flex items-center gap-1 overflow-x-auto">
            {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'UNCERTAIN'] as const).map((lvl) => {
              const isActive = activeFilter === lvl;
              let label = lvl === 'ALL' ? 'All Findings' : lvl;
              if (lvl === 'CRITICAL' && summary.criticalFindings > 0) label += ` (${summary.criticalFindings})`;
              if (lvl === 'HIGH' && summary.highFindings > 0) label += ` (${summary.highFindings})`;

              return (
                <button
                  key={lvl}
                  onClick={() => onFilterChange(lvl)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                    isActive
                      ? 'bg-tathya-accent text-slate-950 font-bold shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-tathya-surface-elevated'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
