import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { VerificationResult } from '../api/types';
import { TathyaLogo } from '../components/brand/TathyaLogo';
import { Button } from '../components/ui/Button';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Key,
  Loader2
} from 'lucide-react';

export const VerifyPassportPage: React.FC = () => {
  const { token = 'PASSPORT-88219-AUD1042-CRIT' } = useParams<{ token: string }>();

  const [inputToken, setInputToken] = useState(token);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);

  const performVerification = async (tok: string) => {
    try {
      setLoading(true);
      const res = await api.verifyPassport(tok);
      setResult(res);
    } catch (err) {
      console.error('Verification failed', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    performVerification(token);
  }, [token]);

  return (
    <div className="min-h-screen bg-tathya-bg text-tathya-text-primary p-4 sm:p-8 flex flex-col items-center justify-between">
      {/* Top Brand Header */}
      <div className="w-full max-w-4xl flex items-center justify-between mb-8 pb-4 border-b border-tathya-surface-border">
        <Link to="/control">
          <TathyaLogo size="md" showTagline={true} />
        </Link>
        <span className="text-xs text-tathya-text-muted font-mono">
          Public Attestation Gateway · Node 04
        </span>
      </div>

      {/* Main Attestation Certificate */}
      <div className="w-full max-w-3xl space-y-6">
        {/* Token Search Bar */}
        <div className="p-3 rounded-xl bg-tathya-surface border border-tathya-surface-border shadow-tathya-card flex gap-2">
          <div className="relative flex-1">
            <Key className="w-4 h-4 text-tathya-text-muted absolute left-3 top-2.5" />
            <input
              type="text"
              value={inputToken}
              onChange={(e) => setInputToken(e.target.value)}
              placeholder="Paste Trust Passport Token (e.g. PASSPORT-88219-AUD1042-CRIT)..."
              className="w-full bg-tathya-surface-elevated text-white text-xs pl-9 pr-3.5 py-2 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent focus:outline-none font-mono"
            />
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => performVerification(inputToken)}
          >
            Verify Seal
          </Button>
        </div>

        {loading ? (
          <div className="p-16 text-center">
            <Loader2 className="w-8 h-8 text-tathya-accent animate-spin mx-auto mb-2" />
            <span className="text-xs text-tathya-text-muted">Verifying cryptographic seal and claim hash chain proofs...</span>
          </div>
        ) : result ? (
          <div className="rounded-2xl bg-tathya-surface border border-tathya-surface-border overflow-hidden shadow-tathya-elevated">
            {/* Certificate Header Banner */}
            <div className={`p-6 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
              result.passport.unresolvedFlagsCount === 0
                ? 'bg-emerald-950/40 border-emerald-800/60'
                : 'bg-red-950/40 border-red-800/60'
            }`}>
              <div className="flex items-center gap-3.5">
                <div className={`p-3 rounded-xl border ${
                  result.passport.unresolvedFlagsCount === 0
                    ? 'bg-emerald-950 border-emerald-600 text-emerald-400'
                    : 'bg-red-950 border-red-600 text-red-400'
                }`}>
                  <ShieldCheck className="w-7 h-7" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                      Tathya Cryptographic Trust Passport
                    </h2>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-black/40 text-white border border-white/20">
                      SEAL VALID
                    </span>
                  </div>
                  <span className="text-xs font-mono text-tathya-text-muted">
                    {result.passport.token}
                  </span>
                </div>
              </div>

              <div className="text-right sm:text-right">
                <span className="text-[10px] uppercase font-bold text-tathya-text-muted block">
                  Deterministic Trust Score
                </span>
                <span className={`text-2xl font-bold font-mono font-tabular ${
                  result.passport.trustScore >= 80 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {result.passport.trustScore} / 100
                </span>
              </div>
            </div>

            {/* Certificate Body Details */}
            <div className="p-6 space-y-6">
              {/* Document Metadata Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-3.5 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border">
                  <span className="text-[10px] uppercase font-bold text-tathya-text-muted block mb-1">
                    Audited Document
                  </span>
                  <span className="font-semibold text-white block truncate">
                    {result.passport.documentName}
                  </span>
                  <span className="text-[10px] text-tathya-text-muted mt-1 block">
                    Audit ID Reference: <Link to={`/control/workspace/${result.passport.auditId}`} className="text-tathya-accent hover:underline">{result.passport.auditId}</Link>
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border">
                  <span className="text-[10px] uppercase font-bold text-tathya-text-muted block mb-1">
                    Validator Node Authority
                  </span>
                  <span className="font-semibold text-emerald-400 block truncate">
                    {result.passport.signedBy}
                  </span>
                  <span className="text-[10px] text-tathya-text-muted mt-1 block font-mono">
                    Timestamp: {new Date(result.passport.signedAt).toUTCString()}
                  </span>
                </div>
              </div>

              {/* Cryptographic Hashes */}
              <div className="p-4 rounded-xl bg-black/30 border border-tathya-surface-border font-mono text-xs space-y-2">
                <div>
                  <span className="text-[10px] text-tathya-text-muted block">DOCUMENT SHA-256 DIGEST:</span>
                  <span className="text-slate-300 break-all">{result.passport.documentHash}</span>
                </div>
                <div>
                  <span className="text-[10px] text-tathya-text-muted block">SHA-256 CLAIM CHAIN ROOT:</span>
                  <span className="text-tathya-accent break-all">{result.passport.claimTreeRoot}</span>
                </div>
                <div>
                  <span className="text-[10px] text-tathya-text-muted block">ECDSA P-256 SIGNATURE:</span>
                  <span className="text-emerald-400/90 break-all text-[11px]">{result.passport.signature}</span>
                </div>
              </div>

              {/* Step-by-Step Audit Verification Trail */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-3">
                  Attestation Verification Trail
                </h4>
                <div className="space-y-2">
                  {result.auditTrail.map((step, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-tathya-surface-elevated/60 border border-tathya-surface-border flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        {step.status === 'PASS' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        )}
                        <div>
                          <span className="font-semibold text-white block">
                            {step.step}
                          </span>
                          <span className="text-[11px] text-tathya-text-muted block">
                            {step.detail}
                          </span>
                        </div>
                      </div>

                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          step.status === 'PASS'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-amber-950 text-amber-400 border border-amber-800'
                        }`}
                      >
                        {step.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 bg-tathya-surface-elevated border-t border-tathya-surface-border flex items-center justify-between text-xs text-tathya-text-muted">
              <span>Verified against Tathya Trust Core Engine</span>
              <Link to="/control" className="text-tathya-accent hover:underline font-semibold">
                Go to Control Center →
              </Link>
            </div>
          </div>
        ) : null}
      </div>

      {/* Footer Branding */}
      <div className="w-full max-w-4xl text-center text-xs text-tathya-text-muted mt-8 pt-4 border-t border-tathya-surface-border">
        Tathya (तथ्य) Enterprise Trust Engine · Every fact, checked.
      </div>
    </div>
  );
};
