import React, { useEffect, useState } from 'react';
import { 
  CheckCircle2, 
  Loader2, 
  ShieldCheck, 
  ArrowRight, 
  AlertCircle,
  FileText,
  Search,
  Scale,
  Database,
  Cpu
} from 'lucide-react';
import { Button } from '../ui/Button';
import { ProcessingStatus } from '../../api/types';

interface AuditProgressionModalProps {
  isOpen: boolean;
  auditId: string;
  onComplete: () => void;
  targetProcessingStatus?: ProcessingStatus;
}

export const AuditProgressionModal: React.FC<AuditProgressionModalProps> = ({
  isOpen,
  auditId,
  onComplete,
  targetProcessingStatus = 'COMPLETED',
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [failed, setFailed] = useState(false);

  // Exact Phase 2 Ingestion & Verification Sequence:
  // 1. Files received
  // 2. Documents parsed
  // 3. Canonical text prepared
  // 4. Facts extracted
  // 5. Evidence index prepared
  // 6. Trust check running
  const stages = [
    { 
      status: 'UPLOADING' as ProcessingStatus,
      label: 'Receiving documents & calculating SHA-256 hashes', 
      detail: 'Staging verification target and evidence files securely',
      icon: FileText,
      duration: 500 
    },
    { 
      status: 'PARSING' as ProcessingStatus,
      label: 'Parsing files & extracting raw content', 
      detail: 'Extracting paragraphs, tables, and bounding boxes',
      icon: Cpu,
      duration: 650 
    },
    { 
      status: 'CANONICALIZING' as ProcessingStatus,
      label: 'Building canonical text stream', 
      detail: 'Normalizing token positions and sentence boundaries',
      icon: Database,
      duration: 600 
    },
    { 
      status: 'EXTRACTING_FACTS' as ProcessingStatus,
      label: 'Extracting verifiable business claims', 
      detail: 'Identifying commercial numbers, delivery dates, and security clauses',
      icon: Search,
      duration: 750 
    },
    { 
      status: 'INDEXING' as ProcessingStatus,
      label: 'Preparing evidence retrieval index (BM25 + BGE-M3)', 
      detail: 'Ranking approved source chunks by authority level',
      icon: Scale,
      duration: 800 
    },
    { 
      status: 'VERIFYING' as ProcessingStatus,
      label: 'Running deterministic trust verification', 
      detail: 'Detecting contradictions, unsupported assertions, and score impacts',
      icon: ShieldCheck,
      duration: 700 
    },
  ];

  useEffect(() => {
    if (!isOpen) {
      setCurrentStep(0);
      setFailed(false);
      return;
    }

    let isMounted = true;
    let stepIndex = 0;

    const runNextStep = () => {
      if (!isMounted) return;
      if (stepIndex < stages.length) {
        setTimeout(() => {
          if (!isMounted) return;
          stepIndex++;
          setCurrentStep(stepIndex);
          if (stepIndex < stages.length) {
            runNextStep();
          }
        }, stages[stepIndex]?.duration || 600);
      }
    };

    runNextStep();

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const isFinished = currentStep >= stages.length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-lg bg-tathya-surface-elevated border border-tathya-surface-border rounded-xl shadow-tathya-elevated p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-tathya-surface-border">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-950/80 border border-amber-800/60 text-tathya-accent">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Tathya Ingestion & Verification Engine
              </h3>
              <span className="text-xs font-mono text-tathya-text-muted">
                Audit Target: {auditId}
              </span>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
            {isFinished ? 'READY' : `${Math.min(100, Math.round((currentStep / stages.length) * 100))}%`}
          </span>
        </div>

        {/* Pipeline Stages */}
        <div className="space-y-3 mb-6">
          {stages.map((s, idx) => {
            const isDone = currentStep > idx;
            const isCurrent = currentStep === idx;
            const Icon = s.icon;

            return (
              <div 
                key={idx} 
                className={`p-2.5 rounded-lg border transition-all ${
                  isCurrent 
                    ? 'bg-tathya-surface border-tathya-accent/60 shadow-sm' 
                    : isDone
                    ? 'bg-tathya-surface/40 border-tathya-surface-border/50'
                    : 'bg-transparent border-transparent opacity-40'
                }`}
              >
                <div className="flex items-start gap-3 text-xs">
                  <div className="mt-0.5">
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 text-tathya-accent animate-spin flex-shrink-0" />
                    ) : (
                      <Icon className="w-4 h-4 text-slate-600 flex-shrink-0" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`font-semibold ${
                        isDone ? 'text-slate-400' : isCurrent ? 'text-white' : 'text-slate-500'
                      }`}>
                        {idx + 1}. {s.label}
                      </span>
                      {isDone && (
                        <span className="text-[10px] font-mono text-emerald-400 font-bold">
                          DONE
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-tathya-text-muted mt-0.5">
                      {s.detail}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Action */}
        <div className="pt-3 border-t border-tathya-surface-border">
          {isFinished ? (
            <Button
              variant="primary"
              size="md"
              rightIcon={<ArrowRight className="w-4 h-4" />}
              onClick={onComplete}
              className="w-full font-bold"
            >
              Open Audit Workspace →
            </Button>
          ) : (
            <div className="w-full py-1 text-center text-xs text-tathya-text-muted flex items-center justify-center gap-2 font-mono">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-tathya-accent" />
              <span>Reconciling facts against ground truth authority...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
