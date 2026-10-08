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
  TrendingDown
} from 'lucide-react';

export const ControlOverviewPage: React.FC = () => {
  const [audits, setAudits] = useState<Audit[]>([]);
  const [_loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAudits().then((data) => {
      setAudits(data);
      setLoading(false);
    });
  }, []);

  const reviewRequired = audits.filter(a => a.status === 'REVIEW REQUIRED').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">

      {/* 1. PAGE HEADER — specific, human, not generic */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] font-mono text-emerald-400 uppercase tracking-widest">Live · Oct 2026</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Control Center
          </h1>
          <p className="text-sm text-tathya-text-secondary mt-1 max-w-lg">
            {reviewRequired > 0
              ? `${reviewRequired} audit${reviewRequired > 1 ? 's' : ''} flagged for reviewer decision. Highest risk: AUD-1042 (₹41.6L commercial conflict).`
              : 'All active audits are processed. No reviewer action outstanding.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/control/queue">
            <Button variant="secondary" size="md">
              Review Queue {reviewRequired > 0 && <span className="ml-1.5 px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400 font-bold">{reviewRequired}</span>}
            </Button>
          </Link>
          <Link to="/submit">
            <Button variant="primary" size="md" leftIcon={<Plus className="w-4 h-4" />}>
              New Audit
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. QUICK STAT PILLS — 4 key numbers, compact */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <AlertOctagon className="w-4 h-4 text-red-400" />
            <span className="text-[11px] font-semibold text-tathya-text-muted uppercase tracking-wider">Critical</span>
          </div>
          <div className="text-2xl font-bold text-white tabular-nums">1</div>
          <div className="text-[11px] text-tathya-text-muted mt-0.5">AUD-1042 · ₹41.6L at risk</div>
        </div>

        <div className="p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-amber-400" />
            <span className="text-[11px] font-semibold text-tathya-text-muted uppercase tracking-wider">Pending</span>
          </div>
          <div className="text-2xl font-bold text-white tabular-nums">{reviewRequired}</div>
          <div className="text-[11px] text-tathya-text-muted mt-0.5">Need reviewer sign-off</div>
        </div>

        <div className="p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-tathya-accent" />
            <span className="text-[11px] font-semibold text-tathya-text-muted uppercase tracking-wider">Avg Score</span>
          </div>
          <div className="text-2xl font-bold text-white tabular-nums">66<span className="text-sm text-tathya-text-muted font-normal">/100</span></div>
          <div className="text-[11px] text-tathya-text-muted mt-0.5">Down from 81 last week</div>
        </div>

        <div className="p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-[11px] font-semibold text-tathya-text-muted uppercase tracking-wider">Cleared</span>
          </div>
          <div className="text-2xl font-bold text-white tabular-nums">1</div>
          <div className="text-[11px] text-tathya-text-muted mt-0.5">AUD-1104 · Score 94</div>
        </div>
      </div>

      {/* 3. CHART + ACTIVE RISK CARD */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <TrustScoreChart />
        </div>

        {/* Active Risk Summary */}
        <div className="p-5 rounded-xl bg-tathya-surface border border-tathya-surface-border shadow-tathya-card flex flex-col gap-4">
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-0.5">
              Open Exposure
            </h3>
            <p className="text-[11px] text-tathya-text-muted">Unresolved findings in AUD-1042</p>
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
            <Link to="/control/workspace/AUD-1042" className="text-tathya-accent font-semibold hover:underline flex items-center gap-1">
              <span>AUD-1042</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* 4. AUDIT QUEUE — recent items */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight">Recent Audits</h2>
            <p className="text-xs text-tathya-text-muted">Sorted by risk. Click any row to open the workspace.</p>
          </div>
          <Link to="/control/queue" className="text-xs text-tathya-accent font-semibold hover:underline flex items-center gap-1">
            <span>All audits</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <QueueTable audits={audits.slice(0, 4)} />
      </div>
    </div>
  );
};
