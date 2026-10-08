import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Audit } from '../api/types';
import { QueueTable } from '../components/queue/QueueTable';
import { Button } from '../components/ui/Button';
import {
  Search,
  Plus,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const ReviewQueuePage: React.FC = () => {
  const [audits, setAudits] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'NORMAL'>('ALL');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<'ALL' | 'REVIEW REQUIRED' | 'VERIFIED' | 'PROCESSING'>('ALL');

  const fetchAudits = async () => {
    try {
      setLoading(true);
      const data = await api.getAudits();
      setAudits(data);
    } catch (err) {
      console.error('Failed to load audits queue', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudits();
  }, []);

  // Filter logic
  const filteredAudits = audits.filter((a) => {
    const matchesSearch =
      a.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.documentName.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRisk = selectedRiskFilter === 'ALL' || a.priority === selectedRiskFilter;
    const matchesStatus = selectedStatusFilter === 'ALL' || a.status === selectedStatusFilter;

    return matchesSearch && matchesRisk && matchesStatus;
  });

  // Metric counts
  const criticalCount = audits.filter((a) => a.priority === 'CRITICAL').length;
  const reviewNeededCount = audits.filter((a) => a.status === 'REVIEW REQUIRED').length;
  const verifiedCount = audits.filter((a) => a.status === 'VERIFIED').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      {/* 1. PAGE HEADER & QUICK ACTIONS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Operational Review Queue
            </h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-950/70 text-amber-300 border border-amber-800/60 font-mono">
              {audits.length} Audits
            </span>
          </div>
          <p className="text-xs text-tathya-text-secondary mt-1">
            Prioritized compliance triage queue. High-materiality commercial contradictions surfaced at the top.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={fetchAudits}
          >
            Refresh
          </Button>

          <Link to="/submit">
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
            >
              Start New Audit
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. OPERATIONAL KPI SUMMARY CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border">
          <span className="text-[11px] font-bold uppercase tracking-wider text-tathya-text-muted block mb-1">
            Total Audits
          </span>
          <div className="text-2xl font-bold font-tabular text-white">{audits.length}</div>
          <span className="text-[11px] text-tathya-text-secondary mt-1 block">Active Ingestion Pipeline</span>
        </div>

        <div className="p-4 rounded-xl bg-tathya-surface border border-red-900/40">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-red-400">
              Critical Risk
            </span>
            <AlertOctagon className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold font-tabular text-red-300">{criticalCount}</div>
          <span className="text-[11px] text-red-400/80 mt-1 block">Material Business Exposure</span>
        </div>

        <div className="p-4 rounded-xl bg-tathya-surface border border-amber-900/40">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">
              Review Required
            </span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-tabular text-amber-300">{reviewNeededCount}</div>
          <span className="text-[11px] text-amber-400/80 mt-1 block">Pending Auditor Decision</span>
        </div>

        <div className="p-4 rounded-xl bg-tathya-surface border border-emerald-900/40">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
              Verified & Sealed
            </span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-tabular text-emerald-300">{verifiedCount}</div>
          <span className="text-[11px] text-emerald-400/80 mt-1 block">100% Truth Grounded</span>
        </div>
      </div>

      {/* 3. FILTER & SEARCH CONTROL BAR */}
      <div className="p-3 rounded-xl bg-tathya-surface border border-tathya-surface-border flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-tathya-text-muted absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by Audit ID, Document title, or filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-tathya-surface-elevated text-white text-xs pl-9 pr-3.5 py-2 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent focus:outline-none"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto">
          <div className="flex items-center gap-1 bg-tathya-surface-elevated p-1 rounded-lg border border-tathya-surface-border text-xs">
            {(['ALL', 'CRITICAL', 'HIGH'] as const).map((risk) => (
              <button
                key={risk}
                onClick={() => setSelectedRiskFilter(risk)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                  selectedRiskFilter === risk
                    ? 'bg-tathya-surface text-white font-semibold shadow-sm'
                    : 'text-tathya-text-muted hover:text-white'
                }`}
              >
                {risk === 'ALL' ? 'All Risks' : risk}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 bg-tathya-surface-elevated p-1 rounded-lg border border-tathya-surface-border text-xs">
            {(['ALL', 'REVIEW REQUIRED', 'VERIFIED'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setSelectedStatusFilter(status)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                  selectedStatusFilter === status
                    ? 'bg-tathya-surface text-white font-semibold shadow-sm'
                    : 'text-tathya-text-muted hover:text-white'
                }`}
              >
                {status === 'ALL' ? 'All Statuses' : status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 4. OPERATIONAL QUEUE TABLE */}
      {loading ? (
        <div className="py-16 text-center">
          <Loader2 className="w-8 h-8 text-tathya-accent animate-spin mx-auto mb-2" />
          <span className="text-xs text-tathya-text-muted">Loading audit queue...</span>
        </div>
      ) : filteredAudits.length === 0 ? (
        <div className="p-8 text-center rounded-xl border border-dashed border-tathya-surface-border bg-tathya-surface/40">
          <p className="text-xs text-tathya-text-muted">No audits match your search and filter criteria.</p>
        </div>
      ) : (
        <QueueTable audits={filteredAudits} />
      )}
    </div>
  );
};
