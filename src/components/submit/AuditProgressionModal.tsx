import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, ShieldCheck, ArrowRight } from 'lucide-react';
import { Button } from '../ui/Button';

interface AuditProgressionModalProps {
  isOpen: boolean;
  auditId: string;
  onComplete: () => void;
}

export const AuditProgressionModal: React.FC<AuditProgressionModalProps> = ({
  isOpen,
  auditId,
  onComplete,
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    { label: 'Analyzing document structure & segmenting claims...', duration: 600 },
    { label: 'Indexing ground-truth source evidence & authority ranking...', duration: 800 },
    { label: 'Running deterministic fact verification & numeric variance checks...', duration: 900 },
    { label: 'Computing deterministic trust score & populating review workspace...', duration: 700 },
  ];

  useEffect(() => {
    if (!isOpen) {
      setCurrentStep(0);
      return;
    }

    let stepIndex = 0;
    const executeStep = () => {
      if (stepIndex < steps.length - 1) {
        setTimeout(() => {
          stepIndex++;
          setCurrentStep(stepIndex);
          executeStep();
        }, steps[stepIndex].duration);
      } else {
        // Complete
        setTimeout(() => {
          setCurrentStep(steps.length);
        }, steps[stepIndex].duration);
      }
    };

    executeStep();
  }, [isOpen]);

  if (!isOpen) return null;

  const isFinished = currentStep >= steps.length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-md bg-tathya-surface-elevated border border-tathya-surface-border rounded-xl shadow-tathya-elevated p-6 overflow-hidden">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2.5 rounded-lg bg-amber-950/80 border border-amber-800/60 text-tathya-accent">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">
              Executing Tathya Trust Audit
            </h3>
            <span className="text-xs font-mono text-tathya-text-muted">
              Audit ID: {auditId}
            </span>
          </div>
        </div>

        {/* Progress Stages List */}
        <div className="space-y-3.5 mb-6">
          {steps.map((s, idx) => {
            const isDone = currentStep > idx;
            const isCurrent = currentStep === idx;

            return (
              <div key={idx} className="flex items-center gap-3 text-xs">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-tathya-accent animate-spin flex-shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
                )}
                <span
                  className={
                    isDone
                      ? 'text-tathya-text-muted line-through'
                      : isCurrent
                      ? 'text-white font-medium'
                      : 'text-tathya-text-disabled'
                  }
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Footer Action */}
        <div className="pt-4 border-t border-tathya-surface-border flex justify-end">
          {isFinished ? (
            <Button
              variant="primary"
              size="md"
              rightIcon={<ArrowRight className="w-4 h-4" />}
              onClick={onComplete}
              className="w-full"
            >
              Open Investigation Workspace
            </Button>
          ) : (
            <div className="w-full py-2 text-center text-xs text-tathya-text-muted font-medium flex items-center justify-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-tathya-accent" />
              <span>Verifying facts against evidence...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
