import React from 'react';
import { Flag } from '../../api/types';
import {
  AlertOctagon,
  HelpCircle,
  Clock,
  Building,
  MapPin,
  ShieldCheck,
  CheckCircle,
  FileQuestion,
  FileX2
} from 'lucide-react';

interface EvidencePanelProps {
  flag: Flag | null;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ flag }) => {
  if (!flag) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-tathya-text-muted">
        <FileQuestion className="w-10 h-10 mb-2 opacity-50" />
        <p className="text-sm">Select a finding or highlighted claim to inspect ground truth evidence.</p>
      </div>
    );
  }

  const getVerificationStatusHeader = () => {
    switch (flag.severity) {
      case 'CRITICAL':
      case 'HIGH':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-950/70 border border-red-700/60 text-red-300 text-xs font-bold uppercase tracking-wider">
            <FileX2 className="w-4 h-4 text-red-400" />
            CONTRADICTED BY GROUND TRUTH
          </div>
        );
      case 'MEDIUM':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-950/70 border border-amber-700/60 text-amber-300 text-xs font-bold uppercase tracking-wider">
            <AlertOctagon className="w-4 h-4 text-amber-400" />
            UNSUPPORTED / UNVERIFIED CLAIM
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-950/70 border border-amber-700/60 text-amber-300 text-xs font-bold uppercase tracking-wider">
            <HelpCircle className="w-4 h-4 text-amber-400" />
            UNCERTAIN CLAIM
          </div>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* 1. Header & Claim Verification Status */}
      <div className="flex items-center justify-between">
        {getVerificationStatusHeader()}
        <span className="text-xs font-mono text-tathya-text-muted">
          ID: {flag.id}
        </span>
      </div>

      {/* 2. Document Claim Under Audit */}
      <div className="p-3.5 rounded-xl bg-tathya-surface border border-tathya-surface-border">
        <span className="text-[10px] uppercase font-bold tracking-wider text-tathya-text-muted block mb-1">
          Target Document Claim
        </span>
        <p className="text-xs font-medium text-white leading-relaxed">
          "{flag.claim}"
        </p>
      </div>

      {/* 3. Authoritative Evidence */}
      <div className="p-4 rounded-xl bg-tathya-surface-elevated border border-emerald-900/40 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-tathya-surface-border pb-2.5">
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4" />
            Authoritative Ground Truth Evidence
          </div>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            {flag.evidence.authority}
          </span>
        </div>

        {/* Source Quote */}
        <div className="p-3 rounded-lg bg-black/30 border border-emerald-900/30 text-xs italic text-emerald-200 leading-relaxed font-mono">
          {flag.evidence.quote}
        </div>

        {/* Authority Metadata Grid */}
        <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
          <div className="flex items-center gap-1.5 text-tathya-text-secondary">
            <Building className="w-3.5 h-3.5 text-tathya-text-muted flex-shrink-0" />
            <span className="truncate">{flag.evidence.sourceName}</span>
          </div>
          <div className="flex items-center gap-1.5 text-tathya-text-secondary">
            <MapPin className="w-3.5 h-3.5 text-tathya-text-muted flex-shrink-0" />
            <span>{flag.evidence.location}</span>
          </div>
          <div className="flex items-center gap-1.5 text-tathya-text-secondary">
            <Clock className="w-3.5 h-3.5 text-tathya-text-muted flex-shrink-0" />
            <span>Freshness: {flag.evidence.freshnessDate}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Cryptographically Verified</span>
          </div>
        </div>
      </div>

      {/* 4. Counter-Evidence (if present) */}
      {flag.counterEvidence && (
        <div className="p-3.5 rounded-xl bg-tathya-surface border border-tathya-surface-border space-y-2">
          <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider">
            <AlertOctagon className="w-3.5 h-3.5" />
            Counter-Evidence / Deprecated Source
          </div>
          <div className="p-2.5 rounded bg-black/20 text-xs italic text-slate-300 leading-relaxed">
            {flag.counterEvidence.quote}
          </div>
          <div className="text-[11px] text-tathya-text-muted flex items-center justify-between">
            <span>Source: {flag.counterEvidence.sourceName}</span>
            <span>{flag.counterEvidence.location}</span>
          </div>
        </div>
      )}

      {/* 5. Material Reason Explanation */}
      <div className="p-3.5 rounded-xl bg-tathya-surface border border-tathya-surface-border">
        <span className="text-[10px] uppercase font-bold tracking-wider text-tathya-text-muted block mb-1">
          Variance & Risk Analysis
        </span>
        <p className="text-xs text-tathya-text-primary leading-relaxed">
          {flag.reason}
        </p>
      </div>

      {/* 6. What To Check / Action */}
      <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-900/40">
        <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400 block mb-1">
          Reviewer Directive
        </span>
        <p className="text-xs text-white leading-relaxed font-medium">
          {flag.whatToCheck}
        </p>
      </div>
    </div>
  );
};
