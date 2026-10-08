import React from 'react';
import { Flag, DocumentLocation, SourceDocument } from '../../api/types';
import {
  AlertOctagon,
  HelpCircle,
  Clock,
  Building,
  MapPin,
  ShieldCheck,
  CheckCircle,
  FileQuestion,
  FileX2,
  Sparkles,
  Layers,
  FileSpreadsheet,
  FileText,
  BadgeAlert,
  ArrowRight
} from 'lucide-react';

interface EvidencePanelProps {
  flag: Flag | null;
  onNavigateToClaim?: (claimId: string) => void;
  sourceDocument?: SourceDocument;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  flag,
  onNavigateToClaim,
  sourceDocument
}) => {
  if (!flag) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-tathya-text-muted">
        <FileQuestion className="w-10 h-10 mb-2 opacity-40 text-slate-500" />
        <h4 className="text-xs font-semibold text-white mb-1">No Finding Selected</h4>
        <p className="text-xs text-tathya-text-muted max-w-xs">
          Select a finding or document highlight to inspect grounding evidence, canonical source quotes, and authority level.
        </p>
      </div>
    );
  }

  // Explicit distinct verification relationship
  const getVerificationStatusHeader = () => {
    const status = flag.verificationStatus || (
      flag.severity === 'CRITICAL' || flag.severity === 'HIGH' ? 'CONTRADICTED' :
      flag.severity === 'MEDIUM' ? 'UNSUPPORTED' : 'UNCERTAIN'
    );

    switch (status) {
      case 'CONTRADICTED':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-950/70 border border-red-700/60 text-red-300 text-xs font-bold uppercase tracking-wider">
            <FileX2 className="w-4 h-4 text-red-400" />
            CONTRADICTED BY GROUND TRUTH
          </div>
        );
      case 'UNSUPPORTED':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-950/70 border border-amber-700/60 text-amber-300 text-xs font-bold uppercase tracking-wider">
            <AlertOctagon className="w-4 h-4 text-amber-400" />
            UNSUPPORTED (NO GROUND TRUTH FOUND)
          </div>
        );
      case 'UNCERTAIN':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-amber-800/60 text-amber-300 text-xs font-bold uppercase tracking-wider">
            <HelpCircle className="w-4 h-4 text-amber-400" />
            UNCERTAIN / INCONCLUSIVE EVIDENCE
          </div>
        );
      case 'SUPPORTED':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-950/70 border border-emerald-700/60 text-emerald-300 text-xs font-bold uppercase tracking-wider">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            SUPPORTED BY AUTHORITATIVE SOURCE
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 text-xs font-bold uppercase tracking-wider">
            <HelpCircle className="w-4 h-4 text-slate-400" />
            REVIEW REQUIRED
          </div>
        );
    }
  };

  const renderLocationBadge = (docLoc?: DocumentLocation) => {
    if (!docLoc) return null;
    switch (docLoc.type) {
      case 'pdf':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 border border-slate-700 text-slate-300">
            <Layers className="w-3 h-3 text-amber-400" />
            Page {docLoc.page}
          </span>
        );
      case 'xlsx':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 border border-slate-700 text-slate-300">
            <FileSpreadsheet className="w-3 h-3 text-emerald-400" />
            Sheet {docLoc.sheet}!{docLoc.cell}
          </span>
        );
      case 'docx':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 border border-slate-700 text-slate-300">
            <FileText className="w-3 h-3 text-sky-400" />
            Para {docLoc.paragraph} ({docLoc.charStart}-{docLoc.charEnd})
          </span>
        );
      case 'text':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 border border-slate-700 text-slate-300">
            chars {docLoc.charStart}..{docLoc.charEnd}
          </span>
        );
      default:
        return null;
    }
  };

  const hasQuote = Boolean(flag.evidence.quote && flag.evidence.quote.trim().length > 0);

  return (
    <div className="evidence-detail space-y-4">
      {/* 1. Header & Verification Relationship */}
      <div className="flex items-center justify-between gap-2">
        {getVerificationStatusHeader()}
        <span className="text-xs font-mono text-tathya-text-muted">
          {flag.id}
        </span>
      </div>

      {/* 2. Document Claim Under Audit with Jump Link */}
      <div className="p-3.5 rounded-xl bg-tathya-surface border border-tathya-surface-border">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider text-tathya-text-muted">
            <FileText className="w-3 h-3 text-tathya-accent" />
            <span>AI Synthesized Document Claim</span>
          </div>
          {onNavigateToClaim && (
            <button
              onClick={() => onNavigateToClaim(flag.claimId)}
              className="text-[11px] text-tathya-accent hover:underline font-medium flex items-center gap-0.5"
            >
              <span>Jump to document text</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
        <p className="text-xs font-medium text-white leading-relaxed font-mono bg-black/30 p-2.5 rounded border border-slate-800">
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
            {flag.evidence.authority || 'Approved Source'}
          </span>
        </div>

        {/* Source Quote or Honest Fallback */}
        {hasQuote ? (
          <div className="p-3 rounded-lg bg-black/40 border border-emerald-900/40 text-xs italic text-emerald-200 leading-relaxed font-mono">
            {flag.evidence.quote}
          </div>
        ) : (
          <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-900/30 text-xs text-amber-200/90 leading-relaxed">
            <HelpCircle className="w-4 h-4 inline mr-1 text-amber-400" />
            No supporting evidence found in approved grounding files for this claim.
          </div>
        )}

        {/* Authority & Version Metadata Grid */}
        <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
          <div className="flex items-center gap-1.5 text-tathya-text-secondary">
            <Building className="w-3.5 h-3.5 text-tathya-text-muted flex-shrink-0" />
            <span className="truncate font-medium text-slate-200">{flag.evidence.sourceName}</span>
          </div>
          <div className="flex items-center gap-1.5 text-tathya-text-secondary">
            <MapPin className="w-3.5 h-3.5 text-tathya-text-muted flex-shrink-0" />
            <span className="truncate">{flag.evidence.location}</span>
            {renderLocationBadge(flag.evidence.documentLocation)}
          </div>
          <div className="flex items-center gap-1.5 text-tathya-text-secondary">
            <Clock className="w-3.5 h-3.5 text-tathya-text-muted flex-shrink-0" />
            <span>Freshness: {flag.evidence.freshnessDate || 'Current'}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Cryptographically Bound</span>
          </div>
        </div>

        {/* Source Authority & Immutable Version tag */}
        {sourceDocument && (
          <div className="pt-2 border-t border-tathya-surface-border flex items-center justify-between text-[10px] text-tathya-text-muted font-mono">
            <span>Version: <strong className="text-slate-300">{sourceDocument.version}</strong></span>
            <span>Status: <strong className="text-emerald-400">{sourceDocument.authorityLabel}</strong></span>
          </div>
        )}

        {/* Retrieval ranking info (BGE-M3 / reranker top evidence) */}
        {flag.evidence.relevanceScore !== undefined && (
          <div className="pt-2 border-t border-tathya-surface-border flex items-center justify-between text-[10px] text-tathya-text-muted">
            <span className="flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-400" />
              Evidence Confidence Match
            </span>
            <span className="font-mono font-semibold text-slate-200">
              {Math.round(flag.evidence.relevanceScore * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* 4. Counter-Evidence / Superseded Source */}
      {flag.counterEvidence && (
        <div className="p-3.5 rounded-xl bg-tathya-surface border border-tathya-surface-border space-y-2">
          <div className="flex items-center justify-between text-amber-400 text-xs font-semibold uppercase tracking-wider">
            <span className="flex items-center gap-2">
              <AlertOctagon className="w-3.5 h-3.5" />
              Counter-Evidence / Deprecated Source
            </span>
            {renderLocationBadge(flag.counterEvidence.documentLocation)}
          </div>
          <div className="p-2.5 rounded bg-black/20 text-xs italic text-slate-300 leading-relaxed font-mono">
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

      {/* 6. What To Check / Reviewer Directive */}
      <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-900/40">
        <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400 block mb-1">
          Reviewer Action Required
        </span>
        <p className="text-xs text-white leading-relaxed font-medium">
          {flag.whatToCheck}
        </p>
      </div>
    </div>
  );
};
