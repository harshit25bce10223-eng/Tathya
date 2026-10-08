import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Check, X, Wrench, AlertCircle, CheckCircle2 } from 'lucide-react';

interface ReviewerActionBarProps {
  flagId: string;
  onAction: (action: 'ACCEPT' | 'DISMISS' | 'FIX', note?: string) => Promise<void>;
  disabled?: boolean;
}

export const ReviewerActionBar: React.FC<ReviewerActionBarProps> = ({
  flagId: _flagId,
  onAction,
  disabled = false,
}) => {
  const [loadingAction, setLoadingAction] = useState<'ACCEPT' | 'DISMISS' | 'FIX' | null>(null);
  const [dismissModalOpen, setDismissModalOpen] = useState(false);
  const [dismissNote, setDismissNote] = useState('');
  const [successFeedback, setSuccessFeedback] = useState<string | null>(null);
  const [errorFeedback, setErrorFeedback] = useState<string | null>(null);

  const handleExecute = async (action: 'ACCEPT' | 'DISMISS' | 'FIX', note?: string) => {
    try {
      setLoadingAction(action);
      setErrorFeedback(null);
      await onAction(action, note);

      const feedbackText = 
        action === 'ACCEPT' 
          ? 'Finding accepted. Risk confirmed on audit record.'
          : action === 'FIX'
          ? 'Suggested fix applied. Trust score recalibrated.'
          : 'Finding dismissed with documented rationale.';
      
      setSuccessFeedback(feedbackText);
      setTimeout(() => setSuccessFeedback(null), 3500);
    } catch (err: any) {
      setErrorFeedback(err?.message || 'Action failed to persist.');
    } finally {
      setLoadingAction(null);
    }
  };

  const submitDismissal = () => {
    if (!dismissNote.trim()) return;
    setDismissModalOpen(false);
    handleExecute('DISMISS', dismissNote);
    setDismissNote('');
  };

  return (
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

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {/* 1. Accept Finding (Confirm Risk) */}
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

          {/* 2. Dismiss Finding (Requires Note) */}
          <Button
            variant="secondary"
            size="sm"
            disabled={disabled || loadingAction !== null}
            leftIcon={<X className="w-3.5 h-3.5 text-slate-400" />}
            onClick={() => setDismissModalOpen(true)}
          >
            Dismiss...
          </Button>

          {/* 3. Apply Suggested Fix */}
          <Button
            variant="primary"
            size="sm"
            disabled={disabled || loadingAction !== null}
            isLoading={loadingAction === 'FIX'}
            leftIcon={<Wrench className="w-3.5 h-3.5" />}
            onClick={() => handleExecute('FIX')}
          >
            Apply Fix
          </Button>
        </div>
      </div>

      {/* Success / Error Feedback Toast */}
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

      {/* Dismissal Reason Required Modal */}
      <Modal
        isOpen={dismissModalOpen}
        onClose={() => setDismissModalOpen(false)}
        title="Dismiss Finding"
        subtitle="Auditors require documented rationale when overriding detected contradictions."
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-white mb-1.5">
              Reviewer Override Justification <span className="text-red-400">*</span>
            </label>
            <textarea
              rows={3}
              value={dismissNote}
              onChange={(e) => setDismissNote(e.target.value)}
              placeholder="e.g. Commercial variance approved via Change Request CR-902 signed by CFO on 04 Oct 2026."
              className="w-full bg-tathya-surface text-white text-xs p-3 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-tathya-surface-border">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setDismissModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={!dismissNote.trim()}
              onClick={submitDismissal}
            >
              Confirm Dismissal
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
