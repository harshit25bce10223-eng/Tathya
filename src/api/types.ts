/**
 * TATHYA (तथ्य) API & DOMAIN CONTRACT TYPES
 * Centralized strictly typed definitions for all frontend models.
 * Phase 2: Ingestion + Retrieval experience.
 */

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type MaterialityLevel = 'MATERIAL' | 'HIGH' | 'MODERATE' | 'LOW';
export type ClaimVerificationStatus = 'SUPPORTED' | 'CONTRADICTED' | 'UNSUPPORTED' | 'UNCERTAIN';

/** Phase 2: Full processing status lifecycle */
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

/** Phase 2: Document location — backend-canonical, never LLM-derived */
export type DocumentLocation =
  | { type: 'pdf'; page: number; bbox?: [number, number, number, number] }
  | { type: 'docx'; paragraph: number; charStart: number; charEnd: number }
  | { type: 'xlsx'; sheet: string; cell: string }
  | { type: 'text'; charStart: number; charEnd: number }
  | { type: 'unknown'; description: string };

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

/** Phase 2: Processing stage for ingestion progress UI */
export interface IngestionStage {
  status: ProcessingStatus;
  label: string;
  description: string;
  completedAt?: string;
}

export interface Audit {
  id: string;
  title: string;
  documentName: string;
  documentType: 'Procurement Contract' | 'Master Services Agreement' | 'Financial Report' | 'Technical Spec' | 'Compliance Filing';
  language: string;
  uploadedAt: string;
  updatedAt: string;
  status: AuditStatus;
  processingStatus?: ProcessingStatus; // Phase 2: granular pipeline state
  priority: SeverityLevel;
  trustScore: number;
  initialScore: number;
  riskBand: 'High Risk' | 'Review Needed' | 'Trustworthy';
  findingsCount: number;
  aiDocument: {
    name: string;
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
  status: 'VERIFIED' | 'REVOKED' | 'TAMPER_DETECTED';
  totalClaimsChecked: number;
  verifiedClaimsCount: number;
  unresolvedFlagsCount: number;
}

export interface VerificationResult {
  valid: boolean;
  passport: Passport;
  verifiedAt: string;
  verifierNode: string;
  auditTrail: {
    step: string;
    status: 'PASS' | 'WARN' | 'FAIL';
    detail: string;
  }[];
}
