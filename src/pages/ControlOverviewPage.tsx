import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Audit } from '../api/types';
import { QueueTable } from '../components/queue/QueueTable';
import { TrustScoreChart } from '../components/charts/TrustScoreChart';
import { Button } from '../components/ui/Button';
import {
  ArrowRight,
  Plus,
  Clock,
  AlertOctagon,
  CheckCircle2,
  TrendingDown,
  Loader2,
  BrainCircuit,
  UserCheck,
} from 'lucide-react';

// ─── Phase 4 helpers ────────────────────────────────────────────────────────

function deriveDashboardStats(audits: Audit[]) {
  const completedAudits = audits.filter((a) => a.status !== 'PROCESSING');
  const avgAiScore =
    completedAudits.length > 0
      ? Math.round(
          completedAudits.reduce((acc, a) => acc + a.trustScore, 0) /
            completedAudits.length
        )
      : null;

  const decidedAudits = audits.filter(
    (a) => typeof a.reviewedScore === 'number' && a.reviewedScore !== null
  );
  const avgReviewedScore =
    decidedAudits.length > 0
      ? Math.round(
          decidedAudits.reduce((acc, a) => acc + (a.reviewedScore as number), 0) /
            decidedAudits.length
        )
      : null;

  return {
    total: audits.length,
    processing: audits.filter((a) => a.status === 'PROCESSING').length,
    awaitingReview: audits.filter((a) => a.status === 'REVIEW REQUIRED').length,
    critical: audits.filter((a) => a.priority === 'CRITICAL').length,
    verified: audits.filter((a) => a.status === 'VERIFIED').length,
    avgAiScore,
    avgReviewedScore,
  };
}

// ─── Component ───────────────────────────────────────────────────────────────

export const ControlOverviewPage: React.FC = () => {
  const [audits, setAudits] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAudits().then((data) => {
      setAudits(data);
      setLoading(false);
    });
  }, []);

  const stats = deriveDashboardStats(audits);
  const highestRiskAudit =
    audits.find((a) => a.priority === 'CRITICAL' || a.priority === 'HIGH') ||
    audits[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">

      {/* 1. PAGE HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] font-mono text-emerald-400 uppercase tracking-widest">
              Live · Oct 2026
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Control Center
          </h1>
          <p className="text-sm text-tathya-text-secondary mt-1 max-w-lg">
            {loading
              ? 'Loading audit pipeline status...'
              : stats.awaitingReview > 0
              ? `${stats.awaitingReview} audit${stats.awaitingReview > 1 ? 's' : ''} flagged for reviewer decision.${
                  highestRiskAudit
                    ? ` Highest risk: ${highestRiskAudit.id} (${highestRiskAudit.title}).`
                    : ''
                }`
              : 'All active audits are processed. No reviewer action outstanding.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/control/queue">
            <Button variant="secondary" size="md">
              Review Queue{' '}
              {stats.awaitingReview > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400 font-bold">
                  {stats.awaitingReview}
                </span>
              )}
            </Button>
          </Link>
          <Link to="/submit">
            <Button
              variant="primary"
              size="md"
              leftIcon={<Plus className="w-4 h-4" />}
            >
              New Audit
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. QUICK STAT CARDS — 5 cards (Phase 4 adds Processing + Score distinction) */}
      {loading ? (
        <div className="py-8 flex items-center justify-center gap-2 text-xs text-tathya-text-muted">
          <Loader2 className="w-4 h-4 animate-spin text-tathya-accent" />
          Loading pipeline metrics...
        </div>
      ) : (
        <>
          {/* Row 1: 5 operational metric cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            {/* Critical */}
            <div className="p-4 rounded-xl bg-tathya-surface border border-red-900/40">
              <div className="flex items-center gap-2 mb-2">
                <AlertOctagon className="w-4 h-4 text-red-400" />
                <span className="text-[11px] font-semibold text-red-400 uppercase tracking-wider">
                  Critical
                </span>
              </div>
              <div className="text-2xl font-bold text-red-300 tabular-nums">
                {stats.critical}
              </div>
              <div className="text-[11px] text-red-400/70 mt-0.5">
                {highestRiskAudit ? `${highestRiskAudit.id} · Priority` : 'None detected'}
              </div>
            </div>

            {/* Pending review */}
            <div className="p-4 rounded-xl bg-tathya-surface border border-amber-900/40">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">
                  Pending
                </span>
              </div>
              <div className="text-2xl font-bold text-amber-300 tabular-nums">
                {stats.awaitingReview}
              </div>
              <div className="text-[11px] text-amber-400/70 mt-0.5">
                Awaiting reviewer sign-off
              </div>
            </div>

            {/* Processing — Phase 4 new card */}
            <div className="p-4 rounded-xl bg-tathya-surface border border-slate-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Processing
                </span>
              </div>
              <div className="text-2xl font-bold text-white tabular-nums">
                {stats.processing}
              </div>
              <div className="text-[11px] text-tathya-text-muted mt-0.5">
                Active ingestion pipeline
              </div>
            </div>

            {/* Verified */}
            <div className="p-4 rounded-xl bg-tathya-surface border border-emerald-900/40">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">
                  Verified
                </span>
              </div>
              <div className="text-2xl font-bold text-emerald-300 tabular-nums">
                {stats.verified}
              </div>
              <div className="text-[11px] text-emerald-400/70 mt-0.5">
                100% ground truth grounded
              </div>
            </div>

            {/* Total */}
            <div className="p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border">
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown className="w-4 h-4 text-tathya-accent" />
                <span className="text-[11px] font-semibold text-tathya-text-muted uppercase tracking-wider">
                  Total
                </span>
              </div>
              <div className="text-2xl font-bold text-white tabular-nums">
                {stats.total}
              </div>
              <div className="text-[11px] text-tathya-text-muted mt-0.5">
                Audits in pipeline
              </div>
            </div>
          </div>

          {/* Row 2: Phase 4 — AI Score vs Reviewed Score distinction panel */}
          <div className="p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border flex flex-col sm:flex-row items-stretch sm:items-center gap-4 sm:gap-8">
            <div className="flex-shrink-0">
              <span className="text-[10px] font-bold uppercase tracking-widest text-tathya-text-muted block mb-1.5">
                Score Comparison · Across Non-Processing Audits
              </span>
              <p className="text-[11px] text-tathya-text-secondary leading-snug max-w-sm">
                AI Score is deterministic — computed from verified contradictions. Reviewed Score
                reflects post-reviewer decisions and is available only when at least one flag has
                been accepted, dismissed, or fixed.
              </p>
            </div>

            <div className="flex items-center gap-6 sm:ml-auto flex-wrap">
              {/* AI Score */}
              <div className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-md bg-tathya-surface-elevated border border-tathya-surface-border flex items-center justify-center flex-shrink-0 mt-0.5">
                  <BrainCircuit className="w-4 h-4 text-tathya-accent" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-tathya-text-muted block">
                    Avg AI Score
                  </span>
                  <span
                    className={`text-xl font-bold font-tabular tabular-nums ${
                      stats.avgAiScore !== null && stats.avgAiScore >= 80
                        ? 'text-emerald-400'
                        : stats.avgAiScore !== null && stats.avgAiScore >= 50
                        ? 'text-amber-400'
                        : stats.avgAiScore !== null
                        ? 'text-red-400'
                        : 'text-tathya-text-muted'
                    }`}
                  >
                    {stats.avgAiScore !== null ? `${stats.avgAiScore}/100` : '—'}
                  </span>
                  <span className="text-[10px] text-tathya-text-muted block mt-0.5">
                    Deterministic · AI engine
                  </span>
                </div>
              </div>

              <div className="w-px h-10 bg-tathya-surface-border hidden sm:block" />

              {/* Reviewed Score */}
              <div className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-md bg-tathya-surface-elevated border border-tathya-surface-border flex items-center justify-center flex-shrink-0 mt-0.5">
                  <UserCheck className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-tathya-text-muted block">
                    Avg Reviewed Score
                  </span>
                  <span
                    className={`text-xl font-bold font-tabular tabular-nums ${
                      stats.avgReviewedScore !== null && stats.avgReviewedScore >= 80
                        ? 'text-emerald-400'
                        : stats.avgReviewedScore !== null && stats.avgReviewedScore >= 50
                        ? 'text-amber-400'
                        : stats.avgReviewedScore !== null
                        ? 'text-red-400'
                        : 'text-tathya-text-muted'
                    }`}
                  >
                    {stats.avgReviewedScore !== null ? `${stats.avgReviewedScore}/100` : '—'}
                  </span>
                  <span className="text-[10px] text-tathya-text-muted block mt-0.5">
                    {stats.avgReviewedScore !== null
                      ? 'Post-reviewer decisions'
                      : 'No decisions recorded yet'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* 3. CHART + ACTIVE RISK CARD */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <TrustScoreChart />
        </div>

        {/* Active Risk Summary */}
        <div className="p-5 rounded-xl bg-tathya-surface border border-tathya-surface-border shadow-tathya-card flex flex-col gap-4">
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-0.5">
              Open Exposure Summary
            </h3>
            <p className="text-[11px] text-tathya-text-muted">
              {highestRiskAudit ? `Key findings in ${highestRiskAudit.id}` : 'All audits verified'}
            </p>
          </div>

          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-red-950/25 border border-red-900/40">
              <div className="text-[10px] uppercase font-bold text-red-400 mb-1 tracking-wide">
                Commercial Overrun
              </div>
              <div className="text-white font-bold text-sm">₹41.6L excess billing</div>
              <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                AI doc: ₹24.8M. PO v2 cap: ₹2.064Cr. Flagged by FLG-101.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-900/30">
              <div className="text-[10px] uppercase font-bold text-amber-400 mb-1 tracking-wide">
                Schedule Slip
              </div>
              <div className="text-white font-bold text-sm">+37 days, unapproved</div>
              <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                AI commits 22 Dec 2026. Master Schedule: 15 Nov 2026.
              </p>
            </div>
          </div>

          <div className="mt-auto pt-3 border-t border-tathya-surface-border flex items-center justify-between text-xs">
            <span className="text-tathya-text-muted">Open audit:</span>
            {highestRiskAudit && (
              <Link
                to={`/control/workspace/${highestRiskAudit.id}`}
                className="text-tathya-accent font-semibold hover:underline flex items-center gap-1"
              >
                <span>{highestRiskAudit.id}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* 4. AUDIT QUEUE — recent items */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight">Recent Audits</h2>
            <p className="text-xs text-tathya-text-muted">
              Sorted by risk. Click any row to open the workspace.
            </p>
          </div>
          <Link
            to="/control/queue"
            className="text-xs text-tathya-accent font-semibold hover:underline flex items-center gap-1"
          >
            <span>All audits</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <QueueTable audits={audits.slice(0, 4)} />
      </div>
    </div>
  );
};
