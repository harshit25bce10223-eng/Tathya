/**
 * TATHYA (तथ्य) API & DOMAIN CONTRACT TYPES
 * Centralized strictly typed definitions for all frontend models.
 * Phase 4: Trust Center, Review Queue, Workspace & Evidence UI.
 */

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type MaterialityLevel = 'MATERIAL' | 'HIGH' | 'MODERATE' | 'LOW';
export type ClaimVerificationStatus = 'SUPPORTED' | 'CONTRADICTED' | 'UNSUPPORTED' | 'UNCERTAIN';

/** Phase 3: Trust Pipeline Result States */
export type TrustResultState =
  | 'PROCESSING'
  | 'READY'
  | 'PARTIAL'
  | 'FAILED'
  | 'NO_FINDINGS'
  | 'FINDINGS_PRESENT'
  | 'UNCERTAIN';

/** Full processing status lifecycle */
export type ProcessingStatus =
  | 'QUEUED'
  | 'UPLOADING'
  | 'PARSING'
  | 'CANONICALIZING'
  | 'EXTRACTING_FACTS'
  | 'INDEXING'
  | 'RETRIEVING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'FAILED';

export type AuditStatus =
  | 'QUEUED'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'REVIEW REQUIRED'
  | 'VERIFIED'
  | 'TAMPER DETECTED';

export type FlagStatus = 'PENDING' | 'ACCEPTED' | 'DISMISSED' | 'FIXED';

/** Document location — backend-canonical, never LLM-derived */
export type DocumentLocation =
  | { type: 'pdf'; page: number; bbox?: [number, number, number, number] }
  | { type: 'docx'; paragraph: number; charStart: number; charEnd: number }
  | { type: 'xlsx'; sheet: string; cell: string }
  | { type: 'text'; charStart: number; charEnd: number }
  | { type: 'unknown'; description: string };

/** Phase 3: Location-aware heatmap region model */
export interface HeatmapRegion {
  id: string;
  sectionIndex: number;
  sectionTitle: string;
  location: DocumentLocation;
  highestSeverity?: SeverityLevel;
  findingCount: number;
  flagIds: string[];
  clean: boolean;
}

export interface SourceDocument {
  id: string;
  name: string;
  type: string;
  sizeBytes: number;
  uploadedAt: string;
  authority: 'LATEST_APPROVED' | 'SIGNED_EXECUTED' | 'SUPERSEDED' | 'DRAFT';
  authorityLabel: string;
  freshnessDate: string;
  version: string;
  approvalStatus?: 'APPROVED' | 'PENDING' | 'SUPERSEDED' | 'REJECTED';
  modifiedDate?: string;
  hash: string;
}

export interface GroundTruthEvidence {
  sourceId: string;
  sourceName: string;
  authority: string;
  freshnessDate: string;
  quote: string;
  location: string; // human-readable e.g. "Section 4.2 · Page 18"
  documentLocation?: DocumentLocation; // structured backend location
  relevanceScore?: number; // 0-1 from reranker, optional
  relationship?: 'SUPPORTED' | 'CONTRADICTED' | 'UNSUPPORTED' | 'UNCERTAIN';
}

export interface CounterEvidence {
  sourceName: string;
  quote: string;
  location: string;
  documentLocation?: DocumentLocation;
}

export interface Claim {
  id: string;
  claimNumber: number;
  text: string;
  category: 'COMMERCIAL_VALUE' | 'DELIVERY_DATE' | 'SLA_GUARANTEE' | 'INDEMNITY' | 'PII_SECURITY' | 'COMPLIANCE';
  status: ClaimVerificationStatus;
  documentLocation?: DocumentLocation; // from backend canonicalization
  expectedTruth?: string;
  variance?: string;
}

export interface MaterialityDetail {
  category: string;
  impactRationale: string;
  financialExposure?: string;
  legalExposure?: string;
  isProvisional: boolean;
  methodologyVersion?: string;
}

export interface PolicyFinding {
  policyName: string;
  policyStatus: 'VIOLATED' | 'AT_RISK' | 'COMPLIANT' | 'NOT_CONFIGURED' | 'EVALUATION_FAILED';
  rationale: string;
  consequence?: string;
  relevantClause?: string;
}

export interface OmissionFinding {
  description: string;
  relatedSection?: string;
  whyItMatters: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNCERTAIN';
  requiresHumanReview: boolean;
}

export interface DecisionHistoryEntry {
  action: 'ACCEPT' | 'DISMISS' | 'FIX';
  reviewerNote?: string;
  timestamp: string;
  reviewedBy?: string;
}

export interface Flag {
  id: string;
  auditId: string;
  claimId: string;
  type: string;
  severity: SeverityLevel;
  materiality: MaterialityLevel;
  claim: string;
  reason: string;
  evidence: GroundTruthEvidence;
  counterEvidence?: CounterEvidence;
  suggestedFix: string;
  whatToCheck: string;
  status: FlagStatus;
  reviewerNote?: string;
  impactScore: number; // negative point deduction
  verificationStatus?: ClaimVerificationStatus;
  materialityDetail?: MaterialityDetail;
  policyFindings?: PolicyFinding[];
  omissionFindings?: OmissionFinding[];
  decisionHistory?: DecisionHistoryEntry[];
}

export interface WhatToCheckItem {
  id: string;
  order: number;
  title: string;
  severity: SeverityLevel;
  materiality: MaterialityLevel;
  flagId: string;
  summary: string;
  actionRequired: string;
}

export interface TrustWaterfallStep {
  name: string;
  deduction: number;
  scoreAfter: number;
  description: string;
  severity: SeverityLevel | 'NEUTRAL';
}

/** Processing stage for ingestion progress UI */
export interface IngestionStage {
  status: ProcessingStatus;
  label: string;
  description: string;
  completedAt?: string;
}

/** Phase 3: Comprehensive backend-driven verification result summary */
export interface VerificationResultSummary {
  claimsChecked: number;
  evidenceMatched: number;
  contradictions: number;
  unsupportedClaims: number;
  uncertainClaims: number;
  criticalFindings: number;
  highFindings: number;
  mediumFindings: number;
  lowFindings: number;
  resultState: TrustResultState;
}

/**
 * Phase 4: Aggregate dashboard summary stats.
 * Returned by a future `getAuditSummary()` API endpoint (Harshit).
 * Until that endpoint ships, ControlOverviewPage derives these from the audits list.
 */
export interface AuditSummaryStats {
  total: number;
  processing: number;
  awaitingReview: number;
  critical: number;
  verified: number;
  avgAiScore: number;
  avgReviewedScore: number | null; // null when no reviewer decisions have been made yet
}

export interface Audit {
  id: string;
  title: string;
  documentName: string;
  documentVersion?: string; // Immutable version support
  documentType: 'Procurement Contract' | 'Master Services Agreement' | 'Financial Report' | 'Technical Spec' | 'Compliance Filing';
  language: string;
  uploadedAt: string;
  updatedAt: string;
  status: AuditStatus;
  processingStatus?: ProcessingStatus;
  resultState?: TrustResultState; // Phase 3 trust result state
  resultSummary?: VerificationResultSummary; // Phase 3 counts summary
  priority: SeverityLevel;
  trustScore: number;
  initialScore: number;
  riskBand: 'High Risk' | 'Review Needed' | 'Trustworthy';
  /** Phase 4: Score after reviewer has accepted/dismissed/fixed findings. Null until first decision. */
  reviewedScore?: number | null;
  /** Phase 4: Risk band derived from reviewedScore. Null until first decision. */
  reviewedRiskBand?: 'High Risk' | 'Review Needed' | 'Trustworthy' | null;
  /** Phase 4: Number of reviewer decisions made on this audit's flags. */
  reviewerDecisionCount?: number;
  findingsCount: number;
  aiDocument: {
    name: string;
    version?: string;
    size: string;
    hash: string;
    pageCount: number;
    rawText: string;
  };
  sourceDocuments: SourceDocument[];
  flags: Flag[];
  claims: Claim[];
  whatToCheck: WhatToCheckItem[];
  waterfall: TrustWaterfallStep[];
  passportToken?: string;
}

export interface Decision {
  flagId: string;
  action: 'ACCEPT' | 'DISMISS' | 'FIX';
  note?: string;
  reviewedBy: string;
  timestamp: string;
}

export interface Passport {
  token: string;
  auditId: string;
  documentName: string;
  documentHash: string;
  claimTreeRoot: string; // SHA-256 claim digest chain root
  signature: string;
  signedBy: string; // ECDSA P-256 / prime256v1
  signedAt: string;
  trustScore: number;
  reviewedScore?: number | null; // Phase 5
  reviewedRiskBand?: string | null; // Phase 5
  status: 'VERIFIED' | 'REVOKED' | 'TAMPER_DETECTED';
  totalClaimsChecked: number;
  verifiedClaimsCount: number;
  unresolvedFlagsCount: number;
}

export type VerificationOutcome = 'VERIFIED' | 'TAMPERED' | 'INVALID' | 'NETWORK_ERROR';

export interface VerificationResult {
  valid: boolean;
  outcome: VerificationOutcome;
  passport: Passport;
  verifiedAt: string;
  verifierNode: string;
  auditTrail: {
    step: string;
    status: 'PASS' | 'WARN' | 'FAIL';
    detail: string;
  }[];
  errorMessage?: string;
}
