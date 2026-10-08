import '../components/page-specific/trust-workspace.css';
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { Audit, SeverityLevel } from '../api/types';
import { DocumentViewer } from '../components/workspace/DocumentViewer';
import { ScoreRing } from '../components/workspace/ScoreRing';
import { TrustWaterfall } from '../components/workspace/TrustWaterfall';
import { WhatToCheckPanel } from '../components/workspace/WhatToCheckPanel';
import { FlagCard } from '../components/workspace/FlagCard';
import { EvidencePanel } from '../components/workspace/EvidencePanel';
import { ReviewerActionBar } from '../components/workspace/ReviewerActionBar';
import { ResultSummaryBar } from '../components/workspace/ResultSummaryBar';
import { StatusBadge, SeverityBadge } from '../components/brand/TrustBadge';
import { EvidenceGraphFoundation } from '../components/graph/EvidenceGraphFoundation';
import { EmptyState } from '../components/ui/EmptyState';
import {
  ShieldCheck,
  ChevronRight,
  ExternalLink,
  AlertTriangle,
  Loader2,
  AlertOctagon,
  Eye,
  CheckCircle2,
  FileCheck2,
  Filter
} from 'lucide-react';

export const WorkspacePage: React.FC = () => {
  const { auditId } = useParams<{ auditId: string }>();

  const [audit, setAudit] = useState<Audit | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedFlagId, setSelectedFlagId] = useState<string | null>(null);

  // Phase 3 Filter state for findings & document
  const [activeSeverityFilter, setActiveSeverityFilter] = useState<SeverityLevel | 'ALL' | 'UNCERTAIN'>('ALL');

  // Right panel tab selector
  const [activeRightTab, setActiveRightTab] = useState<'EVIDENCE' | 'WATERFALL' | 'GRAPH'>('EVIDENCE');
  // Mobile column switcher ('DOC' | 'FLAGS' | 'EVIDENCE')
  const [mobileView, setMobileView] = useState<'DOC' | 'FLAGS' | 'EVIDENCE'>('DOC');

  // Load audit data
  const loadAudit = async () => {
    if (!auditId) {
      setErrorMsg('No audit identifier provided in route.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await api.getAudit(auditId);
      setAudit(data);
      if (data.flags.length > 0) {
        setSelectedFlagId(data.flags[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load audit', err);
      setErrorMsg(err?.message || `Unable to locate audit with identifier ${auditId}.`);
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
    try {
      const result = await api.submitDecision(audit.id, selectedFlagId, { action, note });
      setAudit(result.audit);
    } catch (e) {
      console.error('Action submission failed', e);
    }
  };

  if (loading) {
    return (
      <div className="h-[calc(100vh-3.75rem)] flex flex-col items-center justify-center p-8 text-center space-y-4">
        <Loader2 className="w-8 h-8 text-tathya-accent animate-spin mx-auto" />
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-white">Loading Trust Pipeline Workspace...</h3>
          <p className="text-xs text-tathya-text-muted font-mono">
            Retrieving {auditId || 'audit'} canonical text, claim heatmap, and ground truth anchors...
          </p>
        </div>
      </div>
    );
  }

  if (errorMsg || !audit) {
    return (
      <div className="p-8 max-w-xl mx-auto">
        <EmptyState
          icon={<AlertTriangle className="w-8 h-8 text-amber-400" />}
          title="Audit Not Found"
          description={errorMsg || `Unable to locate audit with identifier ${auditId}.`}
          actionLabel="Return to Review Queue"
          onAction={() => window.location.href = '/control/queue'}
        />
      </div>
    );
  }

  // Calculate or retrieve backend result summary
  const summary = audit.resultSummary || {
    claimsChecked: audit.claims.length || 4,
    evidenceMatched: audit.sourceDocuments.length > 0 ? (audit.claims.length || 4) : 0,
    contradictions: audit.flags.filter(f => f.severity === 'CRITICAL' || f.severity === 'HIGH').length,
    unsupportedClaims: audit.flags.filter(f => f.severity === 'MEDIUM').length,
    uncertainClaims: audit.flags.filter(f => f.severity === 'LOW').length,
    criticalFindings: audit.flags.filter(f => f.severity === 'CRITICAL').length,
    highFindings: audit.flags.filter(f => f.severity === 'HIGH').length,
    mediumFindings: audit.flags.filter(f => f.severity === 'MEDIUM').length,
    lowFindings: audit.flags.filter(f => f.severity === 'LOW').length,
    resultState: audit.status === 'PROCESSING'
      ? 'PROCESSING'
      : audit.flags.length > 0
      ? 'FINDINGS_PRESENT'
      : 'NO_FINDINGS',
  };

  // Filter findings according to activeSeverityFilter
  const filteredFlags = audit.flags.filter(f => {
    if (activeSeverityFilter === 'ALL') return true;
    if (activeSeverityFilter === 'UNCERTAIN') return f.status === 'PENDING' || f.severity === 'LOW';
    return f.severity === activeSeverityFilter;
  });

  const selectedFlag = audit.flags.find((f) => f.id === selectedFlagId) || (filteredFlags[0] || audit.flags[0] || null);

  return (
    <div className="trust-workspace flex flex-col h-[calc(100vh-3.75rem)] overflow-hidden">
      {/* 1. TOP BREADCRUMB & AUDIT CONTROL HEADER */}
      <div className="workspace-header flex-shrink-0 px-4 py-2 border-b border-tathya-surface-border bg-tathya-surface/90 backdrop-blur flex flex-col sm:flex-row sm:items-center justify-between gap-2 z-20">
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

        {/* Passport link, Mobile Switcher tabs */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Mobile column switch buttons */}
          <div className="workspace-mobile-tabs flex xl:hidden bg-slate-900 p-0.5 rounded-lg border border-slate-800 text-[11px]">
            <button
              onClick={() => setMobileView('DOC')}
              className={`px-2.5 py-1 rounded font-medium ${mobileView === 'DOC' ? 'bg-tathya-surface text-white' : 'text-slate-400'}`}
            >
              Document & Heatmap
            </button>
            <button
              onClick={() => setMobileView('FLAGS')}
              className={`px-2.5 py-1 rounded font-medium ${mobileView === 'FLAGS' ? 'bg-tathya-surface text-white' : 'text-slate-400'}`}
            >
              Findings ({audit.flags.length})
            </button>
            <button
              onClick={() => setMobileView('EVIDENCE')}
              className={`px-2.5 py-1 rounded font-medium ${mobileView === 'EVIDENCE' ? 'bg-tathya-surface text-white' : 'text-slate-400'}`}
            >
              Evidence
            </button>
          </div>

          <Link
            to={`/verify/${audit.passportToken || 'PASSPORT-88219-AUD1042-CRIT'}`}
            target="_blank"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900/80 transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Trust Passport</span>
            <ExternalLink className="w-3 h-3 text-emerald-400 opacity-70" />
          </Link>
        </div>
      </div>

      {/* 2. PHASE 3 RESULT SUMMARY BAR */}
      <div className="flex-shrink-0 px-4 py-2 border-b border-tathya-surface-border bg-tathya-surface/40">
        <ResultSummaryBar
          summary={summary}
          activeFilter={activeSeverityFilter}
          onFilterChange={(flt) => setActiveSeverityFilter(flt)}
          documentVersion={audit.aiDocument.version || 'v3.2'}
        />
      </div>

      {/* 3. THREE-COLUMN ENTERPRISE AUDIT WORKSPACE */}
      <div className="workspace-panels flex-1 flex overflow-hidden">

        {/* COLUMN 1: DOCUMENT VIEWER WITH INTEGRATED HEATMAP */}
        <div className={`workspace-document min-w-0 w-full xl:w-5/12 h-full p-2.5 sm:p-3 border-r border-tathya-surface-border overflow-hidden ${
          mobileView === 'DOC' ? 'block' : 'hidden xl:block'
        }`}>
          <DocumentViewer
            documentName={audit.documentName}
            documentText={audit.aiDocument.rawText}
            flags={audit.flags}
            selectedFlagId={selectedFlagId}
            onSelectFlag={(flagId) => {
              setSelectedFlagId(flagId);
              setMobileView('EVIDENCE');
            }}
            pageCount={audit.aiDocument.pageCount}
            activeFilter={activeSeverityFilter}
          />
        </div>

        {/* COLUMN 2: FINDINGS LIST & WHAT TO CHECK */}
        <div className={`workspace-findings min-w-0 w-full xl:w-3/12 h-full flex flex-col bg-tathya-surface border-r border-tathya-surface-border overflow-hidden ${
          mobileView === 'FLAGS' ? 'block' : 'hidden xl:flex'
        }`}>
          {/* Header of Column 2 */}
          <div className="workspace-section-heading p-3 border-b border-tathya-surface-border bg-tathya-surface-elevated/70 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <AlertOctagon className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                Prioritized Findings ({filteredFlags.length})
              </span>
            </div>
            <SeverityBadge severity={audit.priority} />
          </div>

          <div className="flex-1 p-3 overflow-y-auto space-y-3">
            {/* What to check checklist */}
            {audit.whatToCheck && audit.whatToCheck.length > 0 && (
              <div className="workspace-guidance"><WhatToCheckPanel
                items={audit.whatToCheck}
                selectedFlagId={selectedFlagId}
                onSelectItem={(flagId) => {
                  setSelectedFlagId(flagId);
                  setMobileView('EVIDENCE');
                }}
              /></div>
            )}

            {/* List of Flag Cards */}
            <div className="workspace-finding-list space-y-2.5 pt-1">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-tathya-text-muted">
                <span>Findings ({filteredFlags.length})</span>
                {activeSeverityFilter !== 'ALL' && (
                  <button
                    onClick={() => setActiveSeverityFilter('ALL')}
                    className="text-tathya-accent hover:underline font-mono"
                  >
                    Clear Filter
                  </button>
                )}
              </div>

              {filteredFlags.length > 0 ? (
                filteredFlags.map((flag) => (
                  <FlagCard
                    key={flag.id}
                    flag={flag}
                    isSelected={selectedFlagId === flag.id}
                    onSelect={() => {
                      setSelectedFlagId(flag.id);
                      setMobileView('EVIDENCE');
                    }}
                  />
                ))
              ) : (
                <div className="p-6 text-center text-xs text-tathya-text-muted bg-tathya-surface-elevated/50 rounded-xl border border-tathya-surface-border">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-1.5 opacity-80" />
                  <p className="font-semibold text-white">No findings in this category</p>
                  <p className="mt-0.5">Filter: {activeSeverityFilter}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* COLUMN 3: EVIDENCE & SCORE INVESTIGATION PANEL */}
        <div className={`workspace-evidence min-w-0 w-full xl:w-4/12 h-full flex flex-col bg-tathya-surface-elevated/30 overflow-hidden ${
          mobileView === 'EVIDENCE' ? 'block' : 'hidden xl:flex'
        }`}>
          {/* Top Score Banner */}
          <div className="flex-shrink-0 p-3 border-b border-tathya-surface-border bg-tathya-surface flex items-center justify-between gap-3">
            <ScoreRing
              score={audit.trustScore}
              initialScore={audit.initialScore}
              size={80}
              strokeWidth={7}
              state="available"
            />

            <div className="flex-1 space-y-1 text-left">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-white">
                  Deterministic Score
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  {audit.riskBand}
                </span>
              </div>
              <p className="text-[11px] text-tathya-text-muted leading-tight">
                {audit.findingsCount > 0
                  ? `${audit.findingsCount} active contradiction(s) require auditor resolution.`
                  : 'All business claims reconciled 100% against approved ground truth.'}
              </p>
              <div className="text-[10px] font-mono text-tathya-text-muted">
                Initial: 100 → Reviewed: <span className="font-bold text-white">{audit.trustScore}</span> / 100
              </div>
            </div>
          </div>

          {/* Subtabs for Right Panel */}
          <div className="workspace-evidence-tabs flex-shrink-0 px-3 pt-1 border-b border-tathya-surface-border bg-tathya-surface flex items-center gap-2">
            {[
              { id: 'EVIDENCE', label: 'Ground Truth Evidence' },
              { id: 'WATERFALL', label: 'Trust Waterfall' },
              { id: 'GRAPH', label: 'Evidence Graph' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveRightTab(tab.id as any)}
                className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                  activeRightTab === tab.id
                    ? 'border-tathya-accent text-tathya-accent'
                    : 'border-transparent text-tathya-text-muted hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content Body (Scrollable) */}
          <div className="flex-1 p-3.5 overflow-y-auto space-y-3">
            {activeRightTab === 'EVIDENCE' && (
              <EvidencePanel
                flag={selectedFlag}
                onNavigateToClaim={() => setMobileView('DOC')}
                sourceDocument={audit.sourceDocuments[0]}
              />
            )}

            {activeRightTab === 'WATERFALL' && (
              <div className="space-y-3">
                <div className="p-2.5 rounded-lg bg-tathya-surface border border-tathya-surface-border text-xs text-tathya-text-secondary leading-relaxed">
                  Deterministic point deductions computed directly from verified commercial, date, and security variances.
                </div>
                <TrustWaterfall steps={audit.waterfall} currentScore={audit.trustScore} />
              </div>
            )}

            {activeRightTab === 'GRAPH' && (
              <div className="space-y-2.5 h-full">
                <div className="p-2.5 rounded-lg bg-tathya-surface border border-tathya-surface-border text-xs text-tathya-text-secondary">
                  Interactive claim-to-source topology graph.
                </div>
                <EvidenceGraphFoundation auditId={audit.id} />
              </div>
            )}
          </div>

          {/* Fixed Reviewer Action Bar at Bottom of Column 3 */}
          <div className="workspace-actions flex-shrink-0 p-3 border-t border-tathya-surface-border bg-tathya-surface">
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
