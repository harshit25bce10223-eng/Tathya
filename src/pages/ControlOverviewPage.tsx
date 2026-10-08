import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Audit } from '../api/types';
import { QueueTable } from '../components/queue/QueueTable';
import { TrustScoreChart } from '../components/charts/TrustScoreChart';
import { Button } from '../components/ui/Button';
import { 
  ArrowRight, 
  Plus
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8">
      {/* 1. HERO MISSION CONTROL HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-tathya-surface via-tathya-surface-elevated to-slate-900 border border-tathya-surface-border shadow-tathya-elevated">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Tathya Control Center
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-400 border border-emerald-800">
              Live Compliance Engine
            </span>
          </div>
          <p className="text-xs text-tathya-text-secondary max-w-xl leading-relaxed">
            Deterministic truth grounding for AI-generated enterprise documents. Continuous reconciliation of commercial, schedule, and regulatory commitments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/control/queue">
            <Button variant="secondary" size="md">
              Review Queue ({audits.filter(a => a.status === 'REVIEW REQUIRED').length})
            </Button>
          </Link>
          <Link to="/submit">
            <Button variant="primary" size="md" leftIcon={<Plus className="w-4 h-4" />}>
              Start Trust Audit
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. ENTERPRISE DRIFT & ANALYTICS SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recharts Trust Progression */}
        <div className="lg:col-span-2">
          <TrustScoreChart />
        </div>

        {/* Right: Key Facts Under Audit */}
        <div className="p-5 rounded-xl bg-tathya-surface border border-tathya-surface-border shadow-tathya-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                Material Business Variance
              </h3>
              <span className="text-[10px] font-mono text-red-400">HIGH EXPOSURE</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-red-950/20 border border-red-900/30">
                <span className="text-[10px] uppercase font-bold text-red-400 block mb-1">
                  Active Commercial Conflict
                </span>
                <span className="text-white font-semibold text-sm font-tabular block">
                  ₹41.6L unauthorized excess
                </span>
                <p className="text-[11px] text-tathya-text-muted mt-1">
                  AI document states ₹24.8M vs Purchase Order v2 cap of ₹20,640,000.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-900/30">
                <span className="text-[10px] uppercase font-bold text-amber-400 block mb-1">
                  Schedule Slippage Risk
                </span>
                <span className="text-white font-semibold text-sm font-tabular block">
                  +37 days delay unapproved
                </span>
                <p className="text-[11px] text-tathya-text-muted mt-1">
                  AI summary committed 22 Dec 2026 vs Master Schedule 15 Nov 2026.
                </p>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-tathya-surface-border flex items-center justify-between text-xs">
            <span className="text-tathya-text-muted">Target Investigation:</span>
            <Link to="/control/workspace/AUD-1042" className="text-tathya-accent font-semibold hover:underline flex items-center gap-1">
              <span>Open AUD-1042</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* 3. RECENT AUDITS IN TRIAGE */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Recent Audits Pending Compliance Sign-off
            </h2>
            <p className="text-xs text-tathya-text-muted">
              Live documents sorted by risk severity and pending reviewer action.
            </p>
          </div>

          <Link
            to="/control/queue"
            className="text-xs text-tathya-accent font-semibold hover:underline flex items-center gap-1"
          >
            <span>View Full Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <QueueTable audits={audits.slice(0, 4)} />
      </div>
    </div>
  );
};
