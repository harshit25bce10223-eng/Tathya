import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { Audit } from '../api/types';
import { DocumentViewer } from '../components/workspace/DocumentViewer';
import { ScoreRing } from '../components/workspace/ScoreRing';
import { TrustWaterfall } from '../components/workspace/TrustWaterfall';
import { WhatToCheckPanel } from '../components/workspace/WhatToCheckPanel';
import { FlagCard } from '../components/workspace/FlagCard';
import { EvidencePanel } from '../components/workspace/EvidencePanel';
import { ReviewerActionBar } from '../components/workspace/ReviewerActionBar';
import { StatusBadge, SeverityBadge } from '../components/brand/TrustBadge';
import { EvidenceGraphFoundation } from '../components/graph/EvidenceGraphFoundation';
import { EmptyState } from '../components/ui/EmptyState';
import { 
  ShieldCheck, 
  ChevronRight, 
  ExternalLink, 
  AlertTriangle,
  Loader2
} from 'lucide-react';

export const WorkspacePage: React.FC = () => {
  const { auditId = 'AUD-1042' } = useParams<{ auditId: string }>();

  const [audit, setAudit] = useState<Audit | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFlagId, setSelectedFlagId] = useState<string | null>('FLG-101');
  const [activeTab, setActiveTab] = useState<'FINDINGS' | 'EVIDENCE' | 'WATERFALL' | 'GRAPH'>('FINDINGS');

  // Load audit data
  const loadAudit = async () => {
    try {
      setLoading(true);
      const data = await api.getAudit(auditId);
      setAudit(data);
      if (data.flags.length > 0 && !selectedFlagId) {
        setSelectedFlagId(data.flags[0].id);
      }
    } catch (err) {
      console.error('Failed to load audit', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, [auditId]);

  // Handle Reviewer action
  const handleReviewerAction = async (action: 'ACCEPT' | 'DISMISS' | 'FIX', note?: string) => {
    if (!audit || !selectedFlagId) return;
    const result = await api.submitDecision(audit.id, selectedFlagId, { action, note });
    setAudit(result.audit);
  };

  if (loading) {
    return (
      <div className="h-[calc(100vh-3.75rem)] flex flex-col items-center justify-center p-8 text-center">
        <Loader2 className="w-8 h-8 text-tathya-accent animate-spin mb-3" />
        <h3 className="text-sm font-semibold text-white">Loading Investigation Workspace...</h3>
        <p className="text-xs text-tathya-text-muted mt-1 font-mono">Retrieving {auditId} canonical claims and ground truth...</p>
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="p-8">
        <EmptyState
          icon={<AlertTriangle className="w-8 h-8 text-amber-400" />}
          title="Audit Not Found"
          description={`Unable to locate audit with identifier ${auditId}.`}
          actionLabel="Return to Review Queue"
          onAction={() => window.location.href = '/control/queue'}
        />
      </div>
    );
  }

  const selectedFlag = audit.flags.find((f) => f.id === selectedFlagId) || (audit.flags[0] || null);

  return (
    <div className="flex flex-col h-[calc(100vh-3.75rem)] overflow-hidden">
      {/* 1. TOP BREADCRUMB & AUDIT CONTROL HEADER */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-tathya-surface-border bg-tathya-surface/80 backdrop-blur flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <Link to="/control/queue" className="text-xs text-tathya-text-muted hover:text-white transition-colors">
            Review Queue
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
          <span className="font-mono text-xs font-bold text-tathya-accent flex-shrink-0">
            {audit.id}
          </span>
          <span className="text-slate-600 hidden sm:inline">·</span>
          <h2 className="text-xs font-semibold text-white truncate max-w-sm sm:max-w-md">
            {audit.title}
          </h2>
          <StatusBadge status={audit.status} className="hidden md:inline-flex ml-2" />
        </div>

        {/* Quick actions: Passport link, Export, Share */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Link
            to={`/verify/${audit.passportToken || 'PASSPORT-88219-AUD1042-CRIT'}`}
            target="_blank"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900/80 transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Trust Passport</span>
            <ExternalLink className="w-3 h-3 text-emerald-400 opacity-70" />
          </Link>
        </div>
      </div>

      {/* 2. MAIN TWO-COLUMN INVESTIGATION WORKSPACE */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* LEFT COLUMN: DOCUMENT VIEWER */}
        <div className="w-full lg:w-7/12 h-1/2 lg:h-full p-3 sm:p-4 border-b lg:border-b-0 lg:border-r border-tathya-surface-border overflow-hidden">
          <DocumentViewer
            documentName={audit.documentName}
            documentText={audit.aiDocument.rawText}
            flags={audit.flags}
            selectedFlagId={selectedFlagId}
            onSelectFlag={(flagId) => {
              setSelectedFlagId(flagId);
              setActiveTab('EVIDENCE');
            }}
            pageCount={audit.aiDocument.pageCount}
          />
        </div>

        {/* RIGHT COLUMN: INVESTIGATION & EVIDENCE CONTROL */}
        <div className="w-full lg:w-5/12 h-1/2 lg:h-full flex flex-col bg-tathya-surface-elevated/40 overflow-hidden">
          {/* Top Score Banner */}
          <div className="flex-shrink-0 p-4 border-b border-tathya-surface-border bg-tathya-surface flex items-center justify-between gap-4">
            <ScoreRing score={audit.trustScore} initialScore={audit.initialScore} size={92} strokeWidth={8} />

            <div className="flex-1 space-y-1.5 text-right sm:text-left">
              <div className="flex items-center justify-end sm:justify-start gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-white">
                  Investigation Status
                </span>
                <SeverityBadge severity={audit.priority} />
              </div>
              <p className="text-xs text-tathya-text-secondary leading-relaxed">
                {audit.findingsCount > 0 
                  ? `${audit.findingsCount} material contradictions or unsupported claims require auditor decision.`
                  : 'All business claims reconciled 100% against approved ground truth.'}
              </p>
              <div className="text-[11px] font-mono text-tathya-text-muted">
                Initial: 100 → Reviewed: <span className="font-bold text-white">{audit.trustScore}</span> / 100
              </div>
            </div>
          </div>

          {/* Navigation Tabs for Right Panel */}
          <div className="flex-shrink-0 px-4 pt-2 border-b border-tathya-surface-border bg-tathya-surface flex items-center gap-2 overflow-x-auto">
            {[
              { id: 'FINDINGS', label: `Findings (${audit.flags.length})` },
              { id: 'EVIDENCE', label: 'Ground Truth Evidence' },
              { id: 'WATERFALL', label: 'Trust Waterfall' },
              { id: 'GRAPH', label: 'Evidence Graph' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-tathya-accent text-tathya-accent'
                    : 'border-transparent text-tathya-text-muted hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content Body (Scrollable) */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {/* TAB 1: FINDINGS & WHAT TO CHECK */}
            {activeTab === 'FINDINGS' && (
              <div className="space-y-4 animate-fadeIn">
                {/* 1. What To Check First (Differentiator) */}
                <WhatToCheckPanel
                  items={audit.whatToCheck}
                  selectedFlagId={selectedFlagId}
                  onSelectItem={(flagId) => {
                    setSelectedFlagId(flagId);
                    setActiveTab('EVIDENCE');
                  }}
                />

                {/* 2. Flag Cards List */}
                <div className="space-y-3 pt-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-tathya-text-muted block">
                    Detailed Findings ({audit.flags.length})
                  </span>
                  {audit.flags.map((flag) => (
                    <FlagCard
                      key={flag.id}
                      flag={flag}
                      isSelected={selectedFlagId === flag.id}
                      onSelect={() => setSelectedFlagId(flag.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* TAB 2: EVIDENCE PANEL */}
            {activeTab === 'EVIDENCE' && (
              <div className="animate-fadeIn">
                <EvidencePanel flag={selectedFlag} />
              </div>
            )}

            {/* TAB 3: TRUST WATERFALL */}
            {activeTab === 'WATERFALL' && (
              <div className="animate-fadeIn space-y-4">
                <div className="p-3 rounded-lg bg-tathya-surface border border-tathya-surface-border text-xs text-tathya-text-secondary leading-relaxed">
                  The Trust Waterfall illustrates deterministic point deductions based on verified commercial, date, and security variances.
                </div>
                <TrustWaterfall steps={audit.waterfall} currentScore={audit.trustScore} />
              </div>
            )}

            {/* TAB 4: EVIDENCE GRAPH */}
            {activeTab === 'GRAPH' && (
              <div className="animate-fadeIn space-y-3">
                <div className="p-3 rounded-lg bg-tathya-surface border border-tathya-surface-border text-xs text-tathya-text-secondary">
                  Interactive node topology mapping extracted claims to their underlying grounding sources.
                </div>
                <EvidenceGraphFoundation auditId={audit.id} />
              </div>
            )}
          </div>

          {/* 3. FIXED BOTTOM REVIEWER ACTION BAR */}
          <div className="flex-shrink-0 p-3 sm:p-4 border-t border-tathya-surface-border bg-tathya-surface">
            {selectedFlag && (
              <ReviewerActionBar
                flagId={selectedFlag.id}
                onAction={handleReviewerAction}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
