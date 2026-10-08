import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Check, X, Wrench, AlertCircle, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';
import { MaterialityDetail, PolicyFinding, DecisionHistoryEntry } from '../../api/types';

interface ReviewerActionBarProps {
  flagId: string;
  onAction: (action: 'ACCEPT' | 'DISMISS' | 'FIX', note?: string) => Promise<void>;
  disabled?: boolean;
  materialityDetail?: MaterialityDetail;
  policyFindings?: PolicyFinding[];
  decisionHistory?: DecisionHistoryEntry[];
}

export const ReviewerActionBar: React.FC<ReviewerActionBarProps> = ({
  flagId: _flagId,
  onAction,
  disabled = false,
  materialityDetail,
  policyFindings,
  decisionHistory
}) => {
  const [loadingAction, setLoadingAction] = useState<'ACCEPT' | 'DISMISS' | 'FIX' | null>(null);
  const [modalMode, setModalMode] = useState<'DISMISS' | 'FIX' | null>(null);
  const [reviewerNote, setReviewerNote] = useState('');
  const [successFeedback, setSuccessFeedback] = useState<string | null>(null);
  const [errorFeedback, setErrorFeedback] = useState<string | null>(null);
  const [materialityExpanded, setMaterialityExpanded] = useState(false);

  const handleExecute = async (action: 'ACCEPT' | 'DISMISS' | 'FIX', note?: string) => {
    try {
      setLoadingAction(action);
      setErrorFeedback(null);
      await onAction(action, note);

      const feedbackText = 
        action === 'ACCEPT' 
          ? 'Finding accepted. Risk confirmed on audit record.'
          : action === 'FIX'
          ? 'Marked as fixed. Trust score recalibrated.'
          : 'Finding dismissed with documented rationale.';
      
      setSuccessFeedback(feedbackText);
      setTimeout(() => setSuccessFeedback(null), 3500);
    } catch (err: any) {
      setErrorFeedback(err?.message || 'Action failed to persist.');
    } finally {
      setLoadingAction(null);
    }
  };

  const submitWithNote = () => {
    if (!reviewerNote.trim() || !modalMode) return;
    const actionToTake = modalMode;
    setModalMode(null);
    handleExecute(actionToTake, reviewerNote);
    // Note: Don't clear note if we want to preserve it on error, but the existing code clears it. Let's keep it in state, if error it stays, if success we can clear it or not. Actually we should clear on success.
    // Actually the instruction says "Note preservation on error - Already implemented. Keep it." But the original code cleared it before awaiting!
    // I will not clear it here.
  };

  const handleFixInitiate = () => {
    setReviewerNote(''); // Reset before opening
    setModalMode('FIX');
  };

  const handleDismissInitiate = () => {
    setReviewerNote(''); // Reset before opening
    setModalMode('DISMISS');
  };

  const getMaterialityColor = (level: string) => {
    if (['MATERIAL', 'CRITICAL', 'Regulatory'].includes(level)) return 'text-red-400 border-red-400/30 bg-red-400/10';
    if (['HIGH', 'MODERATE', 'Operational'].includes(level)) return 'text-amber-400 border-amber-400/30 bg-amber-400/10';
    return 'text-slate-400 border-slate-400/30 bg-slate-400/10';
  };

  const hasMaterialityContext = !!materialityDetail || (policyFindings && policyFindings.length > 0);

  return (
    <div className="flex flex-col gap-3">
      {hasMaterialityContext && (
        <div className="p-3 rounded-xl bg-tathya-surface border border-tathya-surface-border text-xs">
          <div 
            className="flex items-center justify-between cursor-pointer group"
            onClick={() => setMaterialityExpanded(!materialityExpanded)}
          >
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white">Materiality & Policy Context</span>
              {materialityDetail && (
                <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold border ${getMaterialityColor(materialityDetail.category)}`}>
                  {materialityDetail.category}
                </span>
              )}
              {policyFindings && policyFindings.length > 0 && (
                <span className="text-[10px] text-amber-400 border border-amber-400/30 bg-amber-400/10 px-1.5 py-0.5 rounded">
                  {policyFindings.length} Policy Flag(s)
                </span>
              )}
            </div>
            {materialityExpanded ? (
              <ChevronUp className="w-4 h-4 text-tathya-text-muted group-hover:text-white transition-colors" />
            ) : (
              <ChevronDown className="w-4 h-4 text-tathya-text-muted group-hover:text-white transition-colors" />
            )}
          </div>
          
          {materialityExpanded && (
            <div className="mt-3 pt-3 border-t border-tathya-surface-border space-y-3">
              {materialityDetail && (
                <div className="space-y-1.5">
                  <div className="text-tathya-text-muted">Impact Rationale:</div>
                  <div className="text-white leading-relaxed">{materialityDetail.impactRationale}</div>
                  <div className="flex gap-4 pt-1">
                    {materialityDetail.financialExposure && (
                      <div><span className="text-tathya-text-muted">Financial:</span> <span className="text-white">{materialityDetail.financialExposure}</span></div>
                    )}
                    {materialityDetail.legalExposure && (
                      <div><span className="text-tathya-text-muted">Legal:</span> <span className="text-white">{materialityDetail.legalExposure}</span></div>
                    )}
                  </div>
                  {materialityDetail.isProvisional && (
                    <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-amber-950/40 border border-amber-900/50 rounded text-amber-300 mt-1">
                      <AlertCircle className="w-3 h-3" /> Provisional calculation
                    </div>
                  )}
                </div>
              )}
              
              {policyFindings && policyFindings.length > 0 && (
                <div className="space-y-2">
                  <div className="text-tathya-text-muted">Affected Policies:</div>
                  {policyFindings.map((p, i) => (
                    <div key={i} className="flex flex-col sm:flex-row sm:items-start justify-between p-2 rounded bg-tathya-surface-elevated border border-tathya-surface-border gap-2">
                      <div>
                        <div className="text-white font-medium">{p.policyName}</div>
                        <div className="text-tathya-text-muted mt-0.5">{p.rationale}</div>
                      </div>
                      <span className={`px-1.5 py-0.5 text-[10px] rounded uppercase font-bold shrink-0 ${p.policyStatus === 'VIOLATED' ? 'bg-red-400/10 text-red-400 border border-red-400/30' : 'bg-amber-400/10 text-amber-400 border border-amber-400/30'}`}>
                        {p.policyStatus}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="p-3.5 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border shadow-tathya-card">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div>
            <span className="text-xs font-bold text-white uppercase tracking-wider block">
              Reviewer Decision Bar
            </span>
            <span className="text-[11px] text-tathya-text-muted">
              Record authoritative audit resolution for this finding
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="danger"
              size="sm"
              disabled={disabled || loadingAction !== null}
              isLoading={loadingAction === 'ACCEPT'}
              leftIcon={<Check className="w-3.5 h-3.5" />}
              onClick={() => handleExecute('ACCEPT')}
            >
              Accept Finding
            </Button>

            <Button
              variant="secondary"
              size="sm"
              disabled={disabled || loadingAction !== null}
              leftIcon={<X className="w-3.5 h-3.5 text-slate-400" />}
              onClick={handleDismissInitiate}
            >
              Dismiss...
            </Button>

            <Button
              variant="primary"
              size="sm"
              disabled={disabled || loadingAction !== null}
              leftIcon={<Wrench className="w-3.5 h-3.5" />}
              onClick={handleFixInitiate}
            >
              Mark as Fixed
            </Button>
          </div>
        </div>

        {successFeedback && (
          <div className="mt-3 flex items-center gap-2 p-2 rounded-md bg-emerald-950/70 border border-emerald-800 text-xs text-emerald-300 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{successFeedback}</span>
          </div>
        )}

        {errorFeedback && (
          <div className="mt-3 flex items-center gap-2 p-2 rounded-md bg-red-950/70 border border-red-800 text-xs text-red-300 animate-fadeIn">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorFeedback}</span>
          </div>
        )}

        <Modal
          isOpen={modalMode !== null}
          onClose={() => setModalMode(null)}
          title={modalMode === 'DISMISS' ? 'Dismiss Finding' : 'Apply Fix'}
          subtitle={modalMode === 'DISMISS' ? 'Auditors require documented rationale when overriding detected contradictions.' : 'Provide details on how this finding was fixed or remediated.'}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">
                {modalMode === 'DISMISS' ? 'Reviewer Override Justification' : 'Fix Description'} <span className="text-red-400">*</span>
              </label>
              <textarea
                rows={3}
                value={reviewerNote}
                onChange={(e) => setReviewerNote(e.target.value)}
                placeholder={modalMode === 'DISMISS' ? "e.g. Commercial variance approved via Change Request CR-902 signed by CFO on 04 Oct 2026." : "e.g. Corrected contract draft based on CFO approval."}
                className="w-full bg-tathya-surface text-white text-xs p-3 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-tathya-surface-border">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setModalMode(null)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!reviewerNote.trim() || loadingAction !== null}
                isLoading={loadingAction === modalMode}
                onClick={submitWithNote}
              >
                Confirm {modalMode === 'DISMISS' ? 'Dismissal' : 'Fix'}
              </Button>
            </div>
          </div>
        </Modal>
      </div>

      {decisionHistory && decisionHistory.length > 0 && (
        <div className="p-3 rounded-xl bg-tathya-surface border border-tathya-surface-border text-xs">
          <div className="font-semibold text-white mb-2 uppercase tracking-wider text-[10px]">Decision History</div>
          <div className="space-y-2">
            {decisionHistory.map((h, i) => (
              <div key={i} className="flex flex-col gap-1 text-[11px] p-2 bg-tathya-bg rounded border border-tathya-surface-border">
                <div className="flex items-center justify-between">
                  <span className={`font-bold ${h.action === 'ACCEPT' ? 'text-red-400' : h.action === 'FIX' ? 'text-emerald-400' : 'text-slate-300'}`}>{h.action}</span>
                  <span className="text-tathya-text-muted">{new Date(h.timestamp).toLocaleString()} by {h.reviewedBy}</span>
                </div>
                {h.reviewerNote && <div className="text-slate-300 italic">"{h.reviewerNote}"</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
