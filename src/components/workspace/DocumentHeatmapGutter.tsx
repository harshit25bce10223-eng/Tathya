import React from 'react';
import { Flag, SeverityLevel } from '../../api/types';
import { AlertOctagon, AlertTriangle, ShieldCheck, HelpCircle } from 'lucide-react';

interface DocumentHeatmapGutterProps {
  totalSections?: number;
  flags: Flag[];
  selectedFlagId: string | null;
  onSelectFlag: (flagId: string) => void;
  onSectionClick?: (sectionIndex: number) => void;
}

export const DocumentHeatmapGutter: React.FC<DocumentHeatmapGutterProps> = ({
  totalSections = 5,
  flags,
  selectedFlagId,
  onSelectFlag,
  onSectionClick,
}) => {
  // Map sections (1-indexed) to their finding density and maximum severity
  const sectionData = Array.from({ length: totalSections }, (_, idx) => {
    const secNum = idx + 1;
    // Section 1: FLG-101, Section 2: FLG-102, Section 3: FLG-103, Section 4: FLG-104
    const sectionFlags = flags.filter((f, fIdx) => (fIdx + 1) === secNum);
    
    let highestSeverity: SeverityLevel | 'CLEAN' = 'CLEAN';
    if (sectionFlags.some(f => f.severity === 'CRITICAL')) {
      highestSeverity = 'CRITICAL';
    } else if (sectionFlags.some(f => f.severity === 'HIGH')) {
      highestSeverity = 'HIGH';
    } else if (sectionFlags.some(f => f.severity === 'MEDIUM')) {
      highestSeverity = 'MEDIUM';
    } else if (sectionFlags.some(f => f.severity === 'LOW')) {
      highestSeverity = 'LOW';
    }

    const hasSelected = sectionFlags.some(f => f.id === selectedFlagId);

    return {
      sectionNum: secNum,
      flags: sectionFlags,
      highestSeverity,
      hasSelected,
      isClean: sectionFlags.length === 0,
    };
  });

  const getSeverityStyle = (sev: SeverityLevel | 'CLEAN', hasSelected: boolean) => {
    if (sev === 'CLEAN') {
      return {
        bg: 'bg-emerald-950/40 hover:bg-emerald-900/50',
        border: 'border-emerald-800/40',
        bar: 'bg-emerald-500',
        textColor: 'text-emerald-400',
        label: 'Clean',
      };
    }
    if (sev === 'CRITICAL') {
      return {
        bg: hasSelected ? 'bg-red-950 ring-2 ring-red-500 border-red-500' : 'bg-red-950/60 hover:bg-red-900/70',
        border: 'border-red-700/60',
        bar: 'bg-red-500',
        textColor: 'text-red-300',
        label: 'Critical Risk',
      };
    }
    if (sev === 'HIGH') {
      return {
        bg: hasSelected ? 'bg-amber-950 ring-2 ring-amber-500 border-amber-500' : 'bg-amber-950/50 hover:bg-amber-900/60',
        border: 'border-amber-700/60',
        bar: 'bg-amber-500',
        textColor: 'text-amber-300',
        label: 'High Variance',
      };
    }
    if (sev === 'MEDIUM') {
      return {
        bg: hasSelected ? 'bg-amber-950/80 ring-2 ring-amber-400' : 'bg-amber-950/30 hover:bg-amber-900/40',
        border: 'border-amber-800/40',
        bar: 'bg-amber-400',
        textColor: 'text-amber-400',
        label: 'Review Needed',
      };
    }
    return {
      bg: 'bg-slate-900 hover:bg-slate-800',
      border: 'border-slate-700',
      bar: 'bg-slate-400',
      textColor: 'text-slate-300',
      label: 'Low',
    };
  };

  return (
    <div className="heatmap-gutter w-14 sm:w-16 flex flex-col h-full bg-[#080C14] border-r border-tathya-surface-border p-1.5 space-y-1.5 select-none">
      <div className="text-[9px] uppercase font-bold text-tathya-text-muted text-center tracking-wider py-1 border-b border-tathya-surface-border">
        Heatmap
      </div>

      <div className="flex-1 flex flex-col justify-between py-1 space-y-1.5">
        {sectionData.map((sec) => {
          const style = getSeverityStyle(sec.highestSeverity, sec.hasSelected);

          return (
            <div
              key={sec.sectionNum}
              onClick={() => {
                if (sec.flags[0]) {
                  onSelectFlag(sec.flags[0].id);
                }
                onSectionClick?.(sec.sectionNum);
              }}
              role="button"
              aria-pressed={sec.hasSelected}
              tabIndex={0}
              aria-label={`Document Section ${sec.sectionNum}: ${sec.isClean ? 'Clean' : `${sec.flags.length} findings, ${sec.highestSeverity}`}`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  if (sec.flags[0]) onSelectFlag(sec.flags[0].id);
                  onSectionClick?.(sec.sectionNum);
                }
              }}
              className={`group relative flex-1 flex flex-col items-center justify-center p-1 rounded-md border transition-all cursor-pointer ${style.bg} ${style.border}`}
              title={`Section ${sec.sectionNum}: ${style.label} ${sec.flags.length > 0 ? `(${sec.flags.length} finding${sec.flags.length > 1 ? 's' : ''})` : ''}`}
            >
              {/* Density Indicator Pill */}
              <div className="flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${style.bar}`} />
                <span className="text-[10px] font-mono font-bold text-slate-300">
                  §{sec.sectionNum}
                </span>
              </div>

              {/* Finding Count Tag */}
              {sec.flags.length > 0 ? (
                <span className={`text-[9px] font-mono font-bold mt-0.5 ${style.textColor}`}>
                  {sec.flags.length} {sec.flags.length === 1 ? 'issue' : 'issues'}
                </span>
              ) : (
                <span className="text-[9px] font-mono text-emerald-400/80 mt-0.5">
                  clean
                </span>
              )}

              {/* Hover tooltip for quick glance */}
              <div className="absolute left-full ml-2 z-50 hidden group-hover:flex group-focus-visible:flex flex-col w-48 p-2 rounded-lg bg-tathya-surface-elevated border border-tathya-surface-border shadow-tathya-elevated text-left pointer-events-none">
                <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider mb-1">
                  <span className="text-white">Section {sec.sectionNum}</span>
                  <span className={style.textColor}>{style.label}</span>
                </div>
                {sec.flags.length > 0 ? (
                  <p className="text-[10px] text-slate-300 line-clamp-2">
                    {sec.flags[0].reason}
                  </p>
                ) : (
                  <p className="text-[10px] text-emerald-400">
                    No discrepancies detected against ground truth.
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="text-[8px] font-mono text-center text-slate-500 pt-1 border-t border-tathya-surface-border">
        §1 - §{totalSections}
      </div>
    </div>
  );
};
