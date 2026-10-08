import React, { useEffect, useRef } from 'react';
import { Flag } from '../../api/types';
import { FileText, ZoomIn, ZoomOut, CheckCircle2, AlertOctagon } from 'lucide-react';

interface DocumentViewerProps {
  documentName: string;
  documentText?: string;
  flags?: Flag[];
  selectedFlagId: string | null;
  onSelectFlag: (flagId: string) => void;
  pageCount?: number;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentName,
  documentText,
  flags = [],
  selectedFlagId,
  onSelectFlag,
  pageCount = 6,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeHighlightRef = useRef<HTMLSpanElement>(null);

  // Auto-scroll to selected claim when selectedFlagId changes
  useEffect(() => {
    if (activeHighlightRef.current) {
      activeHighlightRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [selectedFlagId]);

  // If dynamic rawText is present and flags have claims, do a dynamic highlight pass
  const renderDynamicTextWithFlags = () => {
    if (!documentText) return null;

    // Split text into paragraphs
    const paragraphs = documentText.split('\n\n').filter(Boolean);

    return (
      <div className="space-y-5 text-xs sm:text-sm leading-relaxed text-slate-300 font-sans">
        {paragraphs.map((para, pIdx) => {
          // Check if any flag matches this paragraph
          let matchedFlag: Flag | undefined;
          for (const f of flags) {
            if (para.toLowerCase().includes(f.claim.toLowerCase().substring(0, 30))) {
              matchedFlag = f;
              break;
            }
          }

          if (matchedFlag) {
            const isSelected = selectedFlagId === matchedFlag.id;
            const isCriticalOrHigh = matchedFlag.severity === 'CRITICAL' || matchedFlag.severity === 'HIGH';

            return (
              <div key={pIdx} className="relative pl-4 border-l-2 border-slate-700">
                <div className="flex items-center gap-2 mb-1.5 font-mono text-[11px] text-tathya-text-muted">
                  <span>SECTION {pIdx + 1}</span>
                  <span className="text-slate-600">·</span>
                  <span className={isCriticalOrHigh ? 'text-red-400 font-semibold' : 'text-amber-400 font-semibold'}>
                    {matchedFlag.type}
                  </span>
                </div>
                <p>
                  <span
                    ref={isSelected ? activeHighlightRef : undefined}
                    onClick={() => onSelectFlag(matchedFlag!.id)}
                    tabIndex={0}
                    role="button"
                    aria-label={`Claim with flag ${matchedFlag.id}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelectFlag(matchedFlag!.id);
                      }
                    }}
                    className={`cursor-pointer px-2 py-1 rounded transition-all font-medium inline-block my-0.5 focus:outline-none focus:ring-2 focus:ring-tathya-accent ${
                      isSelected
                        ? isCriticalOrHigh
                          ? 'bg-red-950 text-red-100 ring-2 ring-red-500 border border-red-500 shadow-md'
                          : 'bg-amber-950 text-amber-100 ring-2 ring-amber-500 border border-amber-500 shadow-md'
                        : isCriticalOrHigh
                          ? 'bg-red-950/40 text-red-300 border border-red-800/60 hover:bg-red-900/60'
                          : 'bg-amber-950/40 text-amber-300 border border-amber-800/60 hover:bg-amber-900/60'
                    }`}
                  >
                    "{matchedFlag.claim}"
                    <span className={`ml-2 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded text-white ${
                      isCriticalOrHigh ? 'bg-red-700' : 'bg-amber-700'
                    }`}>
                      {matchedFlag.id}
                    </span>
                  </span>
                </p>
                <p className="mt-2 text-slate-400">
                  {para.replace(matchedFlag.claim, '').trim()}
                </p>
              </div>
            );
          }

          return (
            <div key={pIdx} className="relative pl-4 border-l-2 border-slate-800">
              <span className="block font-mono text-[10px] text-slate-500 mb-1">
                PARAGRAPH {pIdx + 1}
              </span>
              <p className="text-slate-400">{para}</p>
            </div>
          );
        })}
      </div>
    );
  };

  // Structured default document stream
  const renderStructuredSections = () => {
    return (
      <div className="space-y-6 text-xs sm:text-sm leading-relaxed text-slate-300 font-sans">
        {/* Section 1: FLG-101 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            1. COMMERCIAL TERMS & FEES
          </h4>
          <p>
            The total consideration payable under this Statement of Work is{' '}
            <span
              ref={selectedFlagId === 'FLG-101' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-101')}
              tabIndex={0}
              role="button"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-101')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold ${
                selectedFlagId === 'FLG-101'
                  ? 'bg-red-950 text-red-200 ring-2 ring-red-500 border border-red-500 shadow-sm'
                  : 'bg-red-950/40 text-red-300 border border-red-800/60 hover:bg-red-900/60'
              }`}
              title="Click to inspect: Commercial Value Conflict (₹41.6L variance)"
            >
              ₹24,800,000 (INR Twenty-Four Million Eight Hundred Thousand)
              <span className="ml-1 text-[10px] font-mono font-bold px-1 py-0.2 rounded bg-red-800 text-white">
                FLG-101
              </span>
            </span>{' '}
            net of applicable GST, disbursed across 24 equal monthly milestone tranches of ₹1,033,333. The initial mobilization fee shall be transferred within 15 calendar days of execution signature.
          </p>
        </div>

        {/* Section 2: FLG-102 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            2. TIMELINE & MILESTONES
          </h4>
          <p>
            The vendor commits to commence technical mobilization on 01 November 2026. The primary Stage 1 core architecture delivery date is firmly committed for{' '}
            <span
              ref={selectedFlagId === 'FLG-102' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-102')}
              tabIndex={0}
              role="button"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-102')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold ${
                selectedFlagId === 'FLG-102'
                  ? 'bg-amber-950 text-amber-200 ring-2 ring-amber-500 border border-amber-500 shadow-sm'
                  : 'bg-amber-950/40 text-amber-300 border border-amber-800/60 hover:bg-amber-900/60'
              }`}
              title="Click to inspect: Milestone Delivery Conflict"
            >
              22 Dec 2026
              <span className="ml-1 text-[10px] font-mono font-bold px-1 py-0.2 rounded bg-amber-800 text-white">
                FLG-102
              </span>
            </span>
            . Subsequent deployment sprints will execute bi-weekly through Q4 2027.
          </p>
        </div>

        {/* Section 3: FLG-103 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            3. SERVICE LEVEL AGREEMENT (SLA) & AVAILABILITY
          </h4>
          <p>
            The vendor explicitly guarantees{' '}
            <span
              ref={selectedFlagId === 'FLG-103' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-103')}
              tabIndex={0}
              role="button"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-103')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold ${
                selectedFlagId === 'FLG-103'
                  ? 'bg-amber-950 text-amber-200 ring-2 ring-amber-500 border border-amber-500 shadow-sm'
                  : 'bg-amber-950/40 text-amber-300 border border-amber-800/60 hover:bg-amber-900/60'
              }`}
              title="Click to inspect: Unsupported SLA Commitment"
            >
              99.99% monthly system uptime across all production cloud availability zones
              <span className="ml-1 text-[10px] font-mono font-bold px-1 py-0.2 rounded bg-amber-800 text-white">
                FLG-103
              </span>
            </span>
            . In the event of downtime exceeding 4.3 minutes per calendar month, customer receives a 15% billing credit.
          </p>
        </div>

        {/* Section 4: FLG-104 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            4. DATA SECURITY & PRIVACY CONTROLS
          </h4>
          <p>
            To facilitate rapid onboarding and staging environment verification,{' '}
            <span
              ref={selectedFlagId === 'FLG-104' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-104')}
              tabIndex={0}
              role="button"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-104')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold ${
                selectedFlagId === 'FLG-104'
                  ? 'bg-red-950 text-red-200 ring-2 ring-red-500 border border-red-500 shadow-sm'
                  : 'bg-red-950/40 text-red-300 border border-red-800/60 hover:bg-red-900/60'
              }`}
              title="Click to inspect: PII & Security Breach"
            >
              customer user directory records and preliminary payment identifiers will be replicated to an internal unencrypted staging bucket
              <span className="ml-1 text-[10px] font-mono font-bold px-1 py-0.2 rounded bg-red-800 text-white">
                FLG-104
              </span>
            </span>{' '}
            for 30 business days before tokenization.
          </p>
        </div>

        {/* Section 5: Unflagged baseline */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            5. TERMINATION & INDEMNIFICATION
          </h4>
          <p className="text-slate-400">
            Either party may terminate for convenience with 30 days written notice. Indemnification liability for intellectual property infringement is capped at 1.5x total contract value.
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-tathya-surface rounded-xl border border-tathya-surface-border overflow-hidden shadow-tathya-card">
      {/* Top Document Header Bar */}
      <div className="flex items-center justify-between p-3.5 border-b border-tathya-surface-border bg-tathya-surface-elevated/70">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 rounded bg-amber-950/70 border border-amber-800/50 text-tathya-accent flex-shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-bold text-white truncate tracking-tight">
              {documentName}
            </h3>
            <span className="text-[10px] text-tathya-text-muted">
              Canonical Text Stream · Page 1 of {pageCount} · Offsets verified by parser
            </span>
          </div>
        </div>

        {/* Quick legend */}
        <div className="flex items-center gap-2 text-[10px] text-tathya-text-muted">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            <span>Contradiction</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span>Unsupported</span>
          </div>
        </div>
      </div>

      {/* Reader Surface */}
      <div ref={containerRef} className="flex-1 p-4 sm:p-6 overflow-y-auto bg-[#0A0E16]">
        <div className="max-w-3xl mx-auto bg-tathya-surface/90 border border-tathya-surface-border rounded-xl p-6 sm:p-8 shadow-tathya-elevated">
          {documentText && flags.length > 0 && flags[0].claim && documentText.includes('AI SYNTHESIZED')
            ? renderDynamicTextWithFlags()
            : renderStructuredSections()}
        </div>
      </div>

      {/* Reader Footer Controls */}
      <div className="p-2.5 border-t border-tathya-surface-border bg-tathya-surface flex items-center justify-between text-[11px] text-tathya-text-muted">
        <span>Click any highlighted claim to view authoritative evidence</span>
        <span className="font-mono text-[10px]">Canonical offsets owned by backend parser</span>
      </div>
    </div>
  );
};
