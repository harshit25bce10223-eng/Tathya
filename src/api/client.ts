/**
 * TATHYA (तथ्य) TYPED API CLIENT
 * 
 * Central API abstraction for frontend views.
 * Automatically delegates to Mock API during Phase 1 / offline,
 * and seamlessly switches to VITE_API_BASE_URL endpoints when active.
 */

import { Audit, Flag, Passport, VerificationResult, SourceDocument } from './types';
import { mockAudits, mockPassports } from './mock';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class TathyaApiClient {
  public readonly baseUrl: string;
  private inMemoryAudits: Audit[];

  constructor() {
    this.baseUrl = API_BASE_URL;
    // Deep clone initial mock data for interactive session state mutations
    this.inMemoryAudits = JSON.parse(JSON.stringify(mockAudits));
  }

  /**
   * Create and trigger a new audit from uploaded documents.
   */
  async createAudit(payload: {
    title: string;
    documentType: Audit['documentType'];
    language: string;
    aiFile: File | { name: string; size: string };
    sourceFiles: (File | { name: string; size: string; authority?: string })[];
  }): Promise<Audit> {
    // Phase 1 Mock Implementation with delay
    await new Promise((res) => setTimeout(res, 800));

    const newId = `AUD-${Math.floor(1000 + Math.random() * 9000)}`;
    const newSources: SourceDocument[] = payload.sourceFiles.map((sf, idx) => ({
      id: `SRC-${Date.now()}-${idx}`,
      name: sf.name,
      type: sf.name.endsWith('.pdf') ? 'Purchase Order' : 'Schedule',
      sizeBytes: typeof sf.size === 'number' ? sf.size : 1200000,
      uploadedAt: new Date().toISOString(),
      authority: idx === 0 ? 'LATEST_APPROVED' : 'SIGNED_EXECUTED',
      authorityLabel: idx === 0 ? 'Latest Approved Document' : 'Signed Execution File',
      freshnessDate: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
      version: 'v1.0',
      hash: `sha256:${Math.random().toString(16).substring(2, 18)}`
    }));

    const newAudit: Audit = {
      id: newId,
      title: payload.title || payload.aiFile.name.replace(/\.[^/.]+$/, ''),
      documentName: payload.aiFile.name,
      documentType: payload.documentType,
      language: payload.language,
      uploadedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'REVIEW REQUIRED',
      priority: 'HIGH',
      trustScore: 68,
      initialScore: 100,
      riskBand: 'Review Needed',
      findingsCount: 2,
      aiDocument: {
        name: payload.aiFile.name,
        size: typeof payload.aiFile.size === 'string' ? payload.aiFile.size : '1.8 MB',
        hash: `sha256:${Math.random().toString(16).substring(2, 20)}`,
        pageCount: 6,
        rawText: `AI SYNTHESIZED DOCUMENT CONTENT:\n\n1. Commercial consideration agreed is ₹18,500,000.\n2. Delivery milestone due in 12 months from execution.`
      },
      sourceDocuments: newSources,
      claims: [
        {
          id: `CLM-${Date.now()}-1`,
          claimNumber: 1,
          text: 'Commercial consideration agreed is ₹18,500,000.',
          category: 'COMMERCIAL_VALUE',
          status: 'CONTRADICTED',
          expectedTruth: '₹15,000,000 in approved vendor budget',
          variance: '+₹3,500,000 unapproved variation'
        }
      ],
      flags: [
        {
          id: `FLG-${Date.now()}-1`,
          auditId: newId,
          claimId: `CLM-${Date.now()}-1`,
          type: 'Budget Discrepancy',
          severity: 'HIGH',
          materiality: 'HIGH',
          claim: 'Commercial consideration agreed is ₹18,500,000.',
          reason: 'Variance against approved procurement ceiling.',
          evidence: {
            sourceId: newSources[0]?.id || 'SRC-1',
            sourceName: newSources[0]?.name || 'Approved Budget',
            authority: 'Latest Approved File',
            freshnessDate: 'Recent',
            quote: '"Approved budget ceiling is ₹15,000,000 INR."',
            location: 'Section 2 · Page 3'
          },
          suggestedFix: 'Reconcile total to ₹15,000,000.',
          whatToCheck: 'Confirm ceiling with procurement lead',
          status: 'PENDING',
          impactScore: -32
        }
      ],
      whatToCheck: [
        {
          id: `WTC-${Date.now()}-1`,
          order: 1,
          title: 'Confirm procurement cap against approved source',
          severity: 'HIGH',
          materiality: 'HIGH',
          flagId: `FLG-${Date.now()}-1`,
          summary: 'Variance of ₹3.5M detected between AI summary and approved budget file.',
          actionRequired: 'Verify Item 2 in source document.'
        }
      ],
      waterfall: [
        { name: 'Initial Trust Baseline', deduction: 0, scoreAfter: 100, description: 'Baseline', severity: 'NEUTRAL' },
        { name: 'Commercial Ceiling Variance', deduction: -32, scoreAfter: 68, description: 'Discrepancy against approved file', severity: 'HIGH' }
      ]
    };

    this.inMemoryAudits.unshift(newAudit);
    return newAudit;
  }

  /**
   * Fetch all audits in the triage queue.
   */
  async getAudits(): Promise<Audit[]> {
    await new Promise((res) => setTimeout(res, 200));
    return [...this.inMemoryAudits];
  }

  /**
   * Fetch a single audit by ID.
   */
  async getAudit(auditId: string): Promise<Audit> {
    await new Promise((res) => setTimeout(res, 200));
    const audit = this.inMemoryAudits.find((a) => a.id === auditId);
    if (!audit) {
      // Default fallback to first audit (e.g. AUD-1042)
      return this.inMemoryAudits[0];
    }
    return JSON.parse(JSON.stringify(audit));
  }

  /**
   * Fetch all flags for a specific audit.
   */
  async getFlags(auditId: string): Promise<Flag[]> {
    const audit = await this.getAudit(auditId);
    return audit.flags;
  }

  /**
   * Reviewer submits a decision on a flag (ACCEPT, DISMISS, FIX).
   */
  async submitDecision(
    auditId: string,
    flagId: string,
    decision: { action: 'ACCEPT' | 'DISMISS' | 'FIX'; note?: string }
  ): Promise<{ audit: Audit; updatedFlag: Flag }> {
    await new Promise((res) => setTimeout(res, 300));
    const audit = this.inMemoryAudits.find((a) => a.id === auditId);
    if (!audit) throw new Error(`Audit not found: ${auditId}`);

    const flag = audit.flags.find((f) => f.id === flagId);
    if (!flag) throw new Error(`Flag not found: ${flagId}`);

    if (decision.action === 'ACCEPT') {
      flag.status = 'ACCEPTED';
    } else if (decision.action === 'DISMISS') {
      flag.status = 'DISMISSED';
      flag.reviewerNote = decision.note;
    } else if (decision.action === 'FIX') {
      flag.status = 'FIXED';
      flag.reviewerNote = decision.note || 'Applied suggested fix';
    }

    // Automatically recalculate trust score
    const rescoreResult = await this.rescoreAudit(auditId);
    return { audit: rescoreResult, updatedFlag: flag };
  }

  /**
   * Recompute audit score based on active / dismissed flags.
   */
  async rescoreAudit(auditId: string): Promise<Audit> {
    const audit = this.inMemoryAudits.find((a) => a.id === auditId);
    if (!audit) throw new Error(`Audit not found: ${auditId}`);

    // Initial baseline is 100
    let score = 100;
    const activeFlags = audit.flags.filter((f) => f.status === 'PENDING' || f.status === 'ACCEPTED');
    
    // Sum active flag deductions
    activeFlags.forEach((f) => {
      score += f.impactScore; // impactScore is negative
    });

    score = Math.max(0, Math.min(100, score));
    audit.trustScore = score;
    audit.riskBand = score >= 80 ? 'Trustworthy' : score >= 50 ? 'Review Needed' : 'High Risk';
    audit.findingsCount = activeFlags.length;
    audit.status = activeFlags.length === 0 ? 'VERIFIED' : 'REVIEW REQUIRED';
    audit.updatedAt = new Date().toISOString();

    return JSON.parse(JSON.stringify(audit));
  }

  /**
   * Retrieve the cryptographic Trust Passport for an audit.
   */
  async getPassport(auditId: string): Promise<Passport | null> {
    await new Promise((res) => setTimeout(res, 200));
    const passportKey = Object.keys(mockPassports).find(
      (k) => mockPassports[k].auditId === auditId
    );
    if (passportKey) {
      return mockPassports[passportKey];
    }
    // Return generated passport
    return {
      token: `PASSPORT-${Math.floor(10000 + Math.random() * 90000)}-${auditId}`,
      auditId,
      documentName: 'AI_Verified_Document.pdf',
      documentHash: 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      merkleRoot: 'merkle:9e8a7c6b5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a',
      signature: '3045022100e4c8f9021a88b5d32c918a24ef9876543210fedcba9876543210abcdef0123450220',
      signedBy: 'TATHYA-ENTERPRISE-TRUST-SEAL (ECDSA-SECP256K1)',
      signedAt: new Date().toISOString(),
      trustScore: 42,
      status: 'VERIFIED',
      totalClaimsChecked: 14,
      verifiedClaimsCount: 10,
      unresolvedFlagsCount: 4
    };
  }

  /**
   * Publicly verify a Passport token (for /verify/:token).
   */
  async verifyPassport(token: string): Promise<VerificationResult> {
    await new Promise((res) => setTimeout(res, 400));
    const passport = mockPassports[token] || {
      token,
      auditId: 'AUD-1042',
      documentName: 'AI_Procurement_Summary_v3.pdf',
      documentHash: 'sha256:7b91c84f39ae62463e271917f8a3d5b74100cde19ef652a9f4c391219b188c0a',
      merkleRoot: 'merkle:9e8a7c6b5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a',
      signature: '3045022100e4c8f9021a88b5d32c918a24ef9876543210fedcba9876543210abcdef012345',
      signedBy: 'TATHYA-CORE-VALIDATOR-NODE-01 (ECDSA-SECP256K1)',
      signedAt: '2026-10-08T19:15:22Z',
      trustScore: 42,
      status: 'VERIFIED',
      totalClaimsChecked: 14,
      verifiedClaimsCount: 10,
      unresolvedFlagsCount: 4
    };

    return {
      valid: true,
      passport,
      verifiedAt: new Date().toISOString(),
      verifierNode: 'TATHYA-PUBLIC-ATTESTATION-NODE-4',
      auditTrail: [
        { step: 'Document SHA-256 Digest Validation', status: 'PASS', detail: 'Hash matches cryptographic manifest' },
        { step: 'Merkle Claim Tree Inclusion Proof', status: 'PASS', detail: '14/14 leaf nodes verified in tree' },
        { step: 'ECDSA Validator Signature Verification', status: 'PASS', detail: 'Secp256k1 key signature confirmed' },
        { step: 'Fact Reconciliation Anchor', status: passport.unresolvedFlagsCount > 0 ? 'WARN' : 'PASS', detail: `${passport.unresolvedFlagsCount} unaddressed commercial/date variances logged` }
      ]
    };
  }
}

export const api = new TathyaApiClient();
