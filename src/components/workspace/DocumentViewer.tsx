import React, { useEffect, useRef, useState } from 'react';
import { Flag, SeverityLevel } from '../../api/types';
import { FileText, Layers, Eye, EyeOff } from 'lucide-react';
import { DocumentHeatmapGutter } from './DocumentHeatmapGutter';

interface DocumentViewerProps {
  documentName: string;
  documentText?: string;
  flags?: Flag[];
  selectedFlagId: string | null;
  onSelectFlag: (flagId: string) => void;
  pageCount?: number;
  activeFilter?: SeverityLevel | 'ALL' | 'UNCERTAIN';
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentName,
  documentText,
  flags = [],
  selectedFlagId,
  onSelectFlag,
  pageCount = 6,
  activeFilter = 'ALL',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeHighlightRef = useRef<HTMLSpanElement>(null);
  const [showHeatmapGutter, setShowHeatmapGutter] = useState(true);

  // Auto-scroll to selected claim when selectedFlagId changes
  useEffect(() => {
    if (activeHighlightRef.current) {
      activeHighlightRef.current.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
        block: 'center',
      });
    }
  }, [selectedFlagId]);

  // Filter flags according to activeFilter selection
  const isFlagVisible = (flagId: string) => {
    if (activeFilter === 'ALL') return true;
    const flag = flags.find(f => f.id === flagId);
    if (!flag) return true;
    if (activeFilter === 'UNCERTAIN') return flag.status === 'PENDING' || flag.severity === 'LOW';
    return flag.severity === activeFilter;
  };

  // Scroll to designated section when clicked on heatmap
  const handleScrollToSection = (sectionIndex: number) => {
    const el = document.getElementById(`doc-section-${sectionIndex}`);
    if (el) {
      el.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    }
  };

  // Dynamic rawText highlights
  const renderDynamicTextWithFlags = () => {
    if (!documentText) return null;
    const paragraphs = documentText.split('\n\n').filter(Boolean);

    return (
      <div className="space-y-6 text-xs sm:text-sm leading-relaxed text-slate-300 font-sans">
        {paragraphs.map((para, pIdx) => {
          let matchedFlag: Flag | undefined;
          for (const f of flags) {
            if (para.toLowerCase().includes(f.claim.toLowerCase().substring(0, 30))) {
              matchedFlag = f;
              break;
            }
          }

          if (matchedFlag) {
            const isSelected = selectedFlagId === matchedFlag.id;
            const isCritical = matchedFlag.severity === 'CRITICAL';
            const isHigh = matchedFlag.severity === 'HIGH';
            const visible = isFlagVisible(matchedFlag.id);

            return (
              <div 
                key={pIdx} 
                id={`doc-section-${pIdx + 1}`}
                className={`relative pl-4 border-l-2 transition-all ${
                  isSelected 
                    ? 'border-tathya-accent bg-tathya-accent/5 py-1.5 pr-2 rounded-r' 
                    : visible 
                    ? 'border-slate-700' 
                    : 'border-slate-800 opacity-40'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5 font-mono text-[11px] text-tathya-text-muted">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-300">§ {pIdx + 1}</span>
                    <span className="text-slate-600">·</span>
                    <span className={isCritical ? 'text-red-400 font-bold' : isHigh ? 'text-amber-400 font-bold' : 'text-slate-300'}>
                      {matchedFlag.type}
                    </span>
                  </div>
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-slate-900 border border-slate-700">
                    {matchedFlag.severity}
                  </span>
                </div>

                <p>
                  <span
                    ref={isSelected ? activeHighlightRef : undefined}
                    onClick={() => onSelectFlag(matchedFlag!.id)}
                    tabIndex={0}
                    role="button"
                    aria-label={`Claim in section ${pIdx + 1} with finding ${matchedFlag.id}: ${matchedFlag.claim}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelectFlag(matchedFlag!.id);
                      }
                    }}
                    className={`cursor-pointer px-2 py-1 rounded transition-all font-medium inline-block my-0.5 focus:outline-none focus:ring-2 focus:ring-tathya-accent ${
                      isSelected
                        ? isCritical
                          ? 'bg-red-950 text-red-100 ring-2 ring-red-500 border border-red-500 shadow-md font-semibold'
                          : 'bg-amber-950 text-amber-100 ring-2 ring-amber-500 border border-amber-500 shadow-md font-semibold'
                        : isCritical
                          ? 'bg-red-950/40 text-red-300 border border-red-800/60 hover:bg-red-900/60'
                          : 'bg-amber-950/40 text-amber-300 border border-amber-800/60 hover:bg-amber-900/60'
                    }`}
                  >
                    "{matchedFlag.claim}"
                    <span className={`ml-2 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded text-white ${
                      isCritical ? 'bg-red-700' : 'bg-amber-700'
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
            <div key={pIdx} id={`doc-section-${pIdx + 1}`} className="relative pl-4 border-l-2 border-slate-800">
              <span className="block font-mono text-[10px] text-slate-500 mb-1">
                PARAGRAPH {pIdx + 1} (CLEAN)
              </span>
              <p className="text-slate-400">{para}</p>
            </div>
          );
        })}
      </div>
    );
  };

  // Structured Section Highlighting
  const renderStructuredSections = () => {
    return (
      <div className="space-y-6 text-xs sm:text-sm leading-relaxed text-slate-300 font-sans">
        {/* Section 1: FLG-101 */}
        <div 
          id="doc-section-1"
          className={`relative pl-4 border-l-2 transition-all ${
            selectedFlagId === 'FLG-101' 
              ? 'border-red-500 bg-red-950/15 py-1.5 pr-2 rounded-r' 
              : isFlagVisible('FLG-101') 
              ? 'border-slate-700/60' 
              : 'border-slate-800 opacity-40'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent">
              1. COMMERCIAL TERMS & FEES
            </h4>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-red-950/60 text-red-300 border border-red-800/60">
              CRITICAL
            </span>
          </div>
          <p>
            The total consideration payable under this Statement of Work is{' '}
            <span
              ref={selectedFlagId === 'FLG-101' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-101')}
              tabIndex={0}
              role="button"
              aria-label="Claim FLG-101: Total consideration payable is 24,800,000 INR"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-101')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold focus:outline-none focus:ring-2 focus:ring-tathya-accent ${
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
        <div 
          id="doc-section-2"
          className={`relative pl-4 border-l-2 transition-all ${
            selectedFlagId === 'FLG-102' 
              ? 'border-amber-500 bg-amber-950/15 py-1.5 pr-2 rounded-r' 
              : isFlagVisible('FLG-102') 
              ? 'border-slate-700/60' 
              : 'border-slate-800 opacity-40'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent">
              2. TIMELINE & MILESTONES
            </h4>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-950/60 text-amber-300 border border-amber-800/60">
              HIGH
            </span>
          </div>
          <p>
            The vendor commits to commence technical mobilization on 01 November 2026. The primary Stage 1 core architecture delivery date is firmly committed for{' '}
            <span
              ref={selectedFlagId === 'FLG-102' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-102')}
              tabIndex={0}
              role="button"
              aria-label="Claim FLG-102: Stage 1 delivery date committed for 22 Dec 2026"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-102')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold focus:outline-none focus:ring-2 focus:ring-tathya-accent ${
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
        <div 
          id="doc-section-3"
          className={`relative pl-4 border-l-2 transition-all ${
            selectedFlagId === 'FLG-103' 
              ? 'border-amber-500 bg-amber-950/15 py-1.5 pr-2 rounded-r' 
              : isFlagVisible('FLG-103') 
              ? 'border-slate-700/60' 
              : 'border-slate-800 opacity-40'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent">
              3. SERVICE LEVEL AGREEMENT (SLA) & AVAILABILITY
            </h4>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-950/60 text-amber-300 border border-amber-800/60">
              HIGH
            </span>
          </div>
          <p>
            The vendor explicitly guarantees{' '}
            <span
              ref={selectedFlagId === 'FLG-103' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-103')}
              tabIndex={0}
              role="button"
              aria-label="Claim FLG-103: 99.99% monthly system uptime across all production cloud availability zones"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-103')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold focus:outline-none focus:ring-2 focus:ring-tathya-accent ${
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
        <div 
          id="doc-section-4"
          className={`relative pl-4 border-l-2 transition-all ${
            selectedFlagId === 'FLG-104' 
              ? 'border-red-500 bg-red-950/15 py-1.5 pr-2 rounded-r' 
              : isFlagVisible('FLG-104') 
              ? 'border-slate-700/60' 
              : 'border-slate-800 opacity-40'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent">
              4. DATA SECURITY & PRIVACY CONTROLS
            </h4>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-red-950/60 text-red-300 border border-red-800/60">
              CRITICAL
            </span>
          </div>
          <p>
            To facilitate rapid onboarding and staging environment verification,{' '}
            <span
              ref={selectedFlagId === 'FLG-104' ? activeHighlightRef : undefined}
              onClick={() => onSelectFlag('FLG-104')}
              tabIndex={0}
              role="button"
              aria-label="Claim FLG-104: customer user directory records replicated to unencrypted staging bucket"
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelectFlag('FLG-104')}
              className={`cursor-pointer px-1.5 py-0.5 rounded transition-all font-semibold focus:outline-none focus:ring-2 focus:ring-tathya-accent ${
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

        {/* Section 5: Clean Baseline */}
        <div id="doc-section-5" className="relative pl-4 border-l-2 border-emerald-800/40 bg-emerald-950/5 py-1.5 pr-2 rounded-r">
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-emerald-400">
              5. TERMINATION & INDEMNIFICATION
            </h4>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60">
              CLEAN
            </span>
          </div>
          <p className="text-slate-400">
            Either party may terminate for convenience with 30 days written notice. Indemnification liability for intellectual property infringement is capped at 1.5x total contract value. Reconciled against Master Agreement template.
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="document-reader flex flex-col h-full bg-tathya-surface rounded-xl border border-tathya-surface-border overflow-hidden shadow-tathya-card">
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
              Canonical Text Stream · Page 1 of {pageCount} · Offsets verified
            </span>
          </div>
        </div>

        {/* Toggle Heatmap gutter button */}
        <div className="flex items-center gap-2">
          <button
            aria-pressed={showHeatmapGutter}
            aria-label="Toggle document heatmap"
            onClick={() => setShowHeatmapGutter(!showHeatmapGutter)}
            className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium bg-slate-900 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Toggle risk density gutter"
          >
            {showHeatmapGutter ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
            <span className="hidden sm:inline">Heatmap</span>
          </button>
        </div>
      </div>

      {/* Main Reader Surface with Heatmap Gutter */}
      <div className="flex-1 flex overflow-hidden bg-[#0A0E16]">
        {showHeatmapGutter && (
          <DocumentHeatmapGutter
            totalSections={5}
            flags={flags}
            selectedFlagId={selectedFlagId}
            onSelectFlag={onSelectFlag}
            onSectionClick={handleScrollToSection}
          />
        )}

        <div ref={containerRef} className="flex-1 p-4 sm:p-6 overflow-y-auto">
          <div className="max-w-3xl mx-auto bg-tathya-surface/90 border border-tathya-surface-border rounded-xl p-6 sm:p-8 shadow-tathya-elevated">
            {documentText && flags.length > 0 && flags[0].claim && documentText.includes('AI SYNTHESIZED')
              ? renderDynamicTextWithFlags()
              : renderStructuredSections()}
          </div>
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
