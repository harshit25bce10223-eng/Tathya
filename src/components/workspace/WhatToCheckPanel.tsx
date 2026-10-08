import React from 'react';
import { WhatToCheckItem } from '../../api/types';
import { SeverityBadge } from '../brand/TrustBadge';
import { ChevronRight, CheckSquare } from 'lucide-react';

interface WhatToCheckPanelProps {
  items: WhatToCheckItem[];
  selectedFlagId: string | null;
  onSelectItem: (flagId: string) => void;
}

export const WhatToCheckPanel: React.FC<WhatToCheckPanelProps> = ({
  items,
  selectedFlagId,
  onSelectItem,
}) => {
  if (!items || items.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-tathya-surface border border-tathya-surface-border text-center">
        <p className="text-xs text-tathya-text-muted">No high-materiality action items remaining.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckSquare className="w-4 h-4 text-tathya-accent" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-white">
            What To Check First
          </h4>
        </div>
        <span className="text-[10px] text-tathya-text-muted">Ranked by Materiality</span>
      </div>

      <div className="space-y-2">
        {items.map((item) => {
          const isSelected = selectedFlagId === item.flagId;

          return (
            <div
              key={item.id}
              onClick={() => onSelectItem(item.flagId)}
              className={`p-3 rounded-lg border transition-all cursor-pointer ${
                isSelected
                  ? 'bg-tathya-surface-elevated border-tathya-accent shadow-sm ring-1 ring-tathya-accent/40'
                  : 'bg-tathya-surface border-tathya-surface-border hover:border-slate-600 hover:bg-tathya-surface/80'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2.5">
                  <span className="font-mono text-xs font-bold text-tathya-accent mt-0.5">
                    {String(item.order).padStart(2, '0')}
                  </span>
                  <div>
                    <h5 className="text-xs font-semibold text-white leading-snug">
                      {item.title}
                    </h5>
                    <p className="text-[11px] text-tathya-text-secondary mt-1 leading-normal">
                      {item.summary}
                    </p>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <SeverityBadge severity={item.severity} />
                  <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isSelected ? 'text-tathya-accent translate-x-0.5' : 'text-slate-600'}`} />
                </div>
              </div>

              {isSelected && (
                <div className="mt-2.5 pt-2 border-t border-tathya-surface-border text-[11px] text-emerald-400 flex items-center gap-1.5 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>Action: {item.actionRequired}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
