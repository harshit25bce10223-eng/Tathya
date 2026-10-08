import React from 'react';
import { FileText, Trash2 } from 'lucide-react';

export interface UploadedSourceFile {
  id: string;
  file: File | { name: string; size: string | number };
  authority: 'LATEST_APPROVED' | 'SIGNED_EXECUTED' | 'SUPERSEDED' | 'DRAFT';
}

interface SourceFileCardProps {
  source: UploadedSourceFile;
  onRemove: (id: string) => void;
  onAuthorityChange: (id: string, authority: UploadedSourceFile['authority']) => void;
}

export const SourceFileCard: React.FC<SourceFileCardProps> = ({
  source,
  onRemove,
  onAuthorityChange,
}) => {
  const formatSize = (size: string | number) => {
    if (typeof size === 'string') return size;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  const authorityLabels = {
    LATEST_APPROVED: { label: '✓ Latest Approved', style: 'bg-emerald-950/70 text-emerald-300 border-emerald-700/60' },
    SIGNED_EXECUTED: { label: '✓ Signed & Executed', style: 'bg-sky-950/70 text-sky-300 border-sky-700/60' },
    SUPERSEDED: { label: 'Older / Superseded', style: 'bg-slate-900 text-slate-400 border-slate-700/60' },
    DRAFT: { label: 'Preliminary Draft', style: 'bg-amber-950/70 text-amber-300 border-amber-700/60' },
  };

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-tathya-surface border border-tathya-surface-border hover:border-slate-600 transition-all">
      <div className="flex items-center gap-3 min-w-0">
        <div className="p-2 rounded bg-tathya-surface-elevated border border-tathya-surface-border text-emerald-400 flex-shrink-0">
          <FileText className="w-4 h-4" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-white truncate max-w-[200px] sm:max-w-xs">
              {source.file.name}
            </span>
            <span className="text-[11px] font-mono text-tathya-text-muted">
              {formatSize(source.file.size)}
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="text-[10px] text-tathya-text-muted">Authority Level:</span>
            <select
              value={source.authority}
              onChange={(e) => onAuthorityChange(source.id, e.target.value as UploadedSourceFile['authority'])}
              className="bg-tathya-surface-elevated text-white text-[11px] px-2 py-0.5 rounded border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent"
            >
              <option value="LATEST_APPROVED">Latest Approved Version (Highest Priority)</option>
              <option value="SIGNED_EXECUTED">Signed & Executed Master Schedule</option>
              <option value="SUPERSEDED">Superseded / Deprecated Version</option>
              <option value="DRAFT">Preliminary Draft / Pre-approval</option>
            </select>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className={`hidden sm:inline-flex px-2 py-0.5 text-[10px] font-semibold rounded border ${authorityLabels[source.authority].style}`}>
          {authorityLabels[source.authority].label}
        </span>
        <button
          onClick={() => onRemove(source.id)}
          className="p-1.5 text-tathya-text-muted hover:text-red-400 hover:bg-tathya-surface-hover rounded transition-colors"
          title="Remove source file"
          aria-label="Remove source file"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
