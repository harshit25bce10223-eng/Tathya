import React from 'react';
import { TrustWaterfallStep } from '../../api/types';
import { ArrowDownRight, ShieldCheck } from 'lucide-react';

interface TrustWaterfallProps {
  steps: TrustWaterfallStep[];
  currentScore: number;
}

export const TrustWaterfall: React.FC<TrustWaterfallProps> = ({ steps, currentScore }) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-semibold text-tathya-text-muted uppercase tracking-wider mb-2">
        <span>Factor / Conflict</span>
        <span>Impact</span>
      </div>

      <div className="space-y-1.5">
        {steps.map((step, idx) => {
          const isInitial = idx === 0;
          return (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded-md bg-tathya-surface border border-tathya-surface-border text-xs"
            >
              <div className="flex items-center gap-2 min-w-0 pr-2">
                {isInitial ? (
                  <ShieldCheck className="w-3.5 h-3.5 text-tathya-accent flex-shrink-0" />
                ) : (
                  <ArrowDownRight className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                )}
                <div className="min-w-0">
                  <span className="font-medium text-white truncate block">
                    {step.name}
                  </span>
                  <span className="text-[10px] text-tathya-text-muted truncate block">
                    {step.description}
                  </span>
                </div>
              </div>

              <div className="text-right flex-shrink-0">
                <span
                  className={`font-mono font-semibold font-tabular ${
                    isInitial
                      ? 'text-tathya-accent'
                      : step.deduction < 0
                      ? 'text-red-400'
                      : 'text-emerald-400'
                  }`}
                >
                  {isInitial ? '100' : `${step.deduction} pts`}
                </span>
                <span className="text-[10px] text-tathya-text-muted block font-mono font-tabular">
                  → {step.scoreAfter}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Row */}
      <div className="pt-2 mt-2 border-t border-tathya-surface-border flex items-center justify-between text-xs">
        <span className="font-semibold text-white">Resulting Deterministic Trust:</span>
        <span className="font-mono font-bold text-sm text-tathya-accent font-tabular">
          {currentScore} / 100
        </span>
      </div>
    </div>
  );
};
