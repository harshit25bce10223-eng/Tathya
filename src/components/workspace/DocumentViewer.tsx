import { Flag } from '../../api/types';
import { FileText } from 'lucide-react';

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
  documentText: _documentText,
  flags: _flags,
  selectedFlagId,
  onSelectFlag,
  pageCount = 14,
}) => {
  // Map sentences / sections to flags for dynamic highlighting
  const renderHighlightedContent = () => {
    // For AUD-1042 mock document, render rich formatted paragraphs with interactive claim highlights
    return (
      <div className="space-y-6 text-sm leading-relaxed text-slate-300 font-sans">
        {/* Section 1 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            1. COMMERCIAL TERMS & FEES
          </h4>
          <p>
            The total consideration payable under this Statement of Work is{' '}
            <span
              onClick={() => onSelectFlag('FLG-101')}
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

        {/* Section 2 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            2. TIMELINE & MILESTONES
          </h4>
          <p>
            The vendor commits to commence technical mobilization on 01 November 2026. The primary Stage 1 core architecture delivery date is firmly committed for{' '}
            <span
              onClick={() => onSelectFlag('FLG-102')}
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

        {/* Section 3 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            3. SERVICE LEVEL AGREEMENT (SLA) & AVAILABILITY
          </h4>
          <p>
            The vendor explicitly guarantees{' '}
            <span
              onClick={() => onSelectFlag('FLG-103')}
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

        {/* Section 4 */}
        <div className="relative pl-4 border-l-2 border-slate-700/60">
          <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-tathya-accent mb-2">
            4. DATA SECURITY & PRIVACY CONTROLS
          </h4>
          <p>
            To facilitate rapid onboarding and staging environment verification,{' '}
            <span
              onClick={() => onSelectFlag('FLG-104')}
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

        {/* Section 5 (Unflagged baseline) */}
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
          <div className="p-1.5 rounded bg-sky-950/70 border border-sky-800/50 text-tathya-accent flex-shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-bold text-white truncate tracking-tight">
              {documentName}
            </h3>
            <span className="text-[10px] text-tathya-text-muted">
              PDF Render · Page 1 of {pageCount} · Canonical Token Stream
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
      <div className="flex-1 p-6 sm:p-8 overflow-y-auto bg-[#0A0E16]">
        <div className="max-w-2xl mx-auto bg-tathya-surface/90 border border-tathya-surface-border rounded-xl p-8 shadow-tathya-elevated">
          {renderHighlightedContent()}
        </div>
      </div>

      {/* Reader Footer Controls */}
      <div className="p-2.5 border-t border-tathya-surface-border bg-tathya-surface flex items-center justify-between text-[11px] text-tathya-text-muted">
        <span>Click highlighted claim to synchronize evidence panel</span>
        <span className="font-mono">Zoom: 100% · Fit Width</span>
      </div>
    </div>
  );
};
