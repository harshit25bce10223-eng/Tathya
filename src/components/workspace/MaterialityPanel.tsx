import React from 'react';
import { MaterialityDetail, PolicyFinding, OmissionFinding } from '../../api/types';
import { AlertCircle, FileWarning, ShieldAlert, CheckCircle, Info } from 'lucide-react';

interface MaterialityPanelProps {
  materialityDetail?: MaterialityDetail;
  policyFindings?: PolicyFinding[];
  omissionFindings?: OmissionFinding[];
  className?: string;
}

export const MaterialityPanel: React.FC<MaterialityPanelProps> = ({
  materialityDetail,
  policyFindings,
  omissionFindings,
  className = ''
}) => {
  const getMaterialityColor = (level: string) => {
    if (['MATERIAL', 'CRITICAL', 'Regulatory'].includes(level)) return 'bg-red-400/10 text-red-400 border-red-400/30';
    if (['HIGH', 'MODERATE', 'Operational'].includes(level)) return 'bg-amber-400/10 text-amber-400 border-amber-400/30';
    return 'bg-slate-400/10 text-slate-400 border-slate-400/30';
  };

  const getPolicyColor = (status: string) => {
    switch (status) {
      case 'VIOLATED': return 'bg-red-400/10 text-red-400 border-red-400/30';
      case 'AT_RISK': return 'bg-amber-400/10 text-amber-400 border-amber-400/30';
      case 'COMPLIANT': return 'bg-emerald-400/10 text-emerald-400 border-emerald-400/30';
      default: return 'bg-slate-400/10 text-slate-400 border-slate-400/30';
    }
  };

  const getPolicyIcon = (status: string) => {
    switch (status) {
      case 'VIOLATED': return <ShieldAlert className="w-3.5 h-3.5" />;
      case 'AT_RISK': return <AlertCircle className="w-3.5 h-3.5" />;
      case 'COMPLIANT': return <CheckCircle className="w-3.5 h-3.5" />;
      default: return <Info className="w-3.5 h-3.5" />;
    }
  };

  if (!materialityDetail && (!policyFindings || policyFindings.length === 0) && (!omissionFindings || omissionFindings.length === 0)) {
    return (
      <div className={`p-4 rounded-xl bg-tathya-surface border border-tathya-surface-border flex items-center justify-center text-tathya-text-muted text-xs italic ${className}`}>
        No policy or materiality data from backend
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Materiality Detail */}
      {materialityDetail && (
        <div className="p-4 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border shadow-tathya-card">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-semibold text-white">Materiality Assessment</h3>
            <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${getMaterialityColor(materialityDetail.category)}`}>
              {materialityDetail.category}
            </span>
          </div>
          
          <div className="space-y-3 text-xs">
            <div>
              <div className="text-tathya-text-muted mb-1">Impact Rationale</div>
              <div className="text-white leading-relaxed bg-tathya-bg p-2.5 rounded border border-tathya-surface-border">
                {materialityDetail.impactRationale}
              </div>
            </div>

            <div className="flex flex-wrap gap-4">
              {materialityDetail.financialExposure && (
                <div className="flex flex-col">
                  <span className="text-tathya-text-muted text-[11px]">Financial Exposure</span>
                  <span className="text-amber-400 font-semibold">{materialityDetail.financialExposure}</span>
                </div>
              )}
              {materialityDetail.legalExposure && (
                <div className="flex flex-col">
                  <span className="text-tathya-text-muted text-[11px]">Legal Exposure</span>
                  <span className="text-red-400 font-semibold">{materialityDetail.legalExposure}</span>
                </div>
              )}
            </div>

            {materialityDetail.isProvisional && (
              <div className="flex items-start gap-2 p-2.5 bg-amber-950/30 border border-amber-900/50 rounded-lg text-amber-300 mt-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>
                  <strong>Provisional Calculation:</strong> Final impact may change pending further legal review.
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Policy Findings */}
      {policyFindings && policyFindings.length > 0 && (
        <div className="p-4 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border shadow-tathya-card">
          <h3 className="text-sm font-semibold text-white mb-3">Policy Findings</h3>
          <div className="space-y-2.5">
            {policyFindings.map((policy, idx) => (
              <div key={idx} className="p-3 bg-tathya-bg rounded-lg border border-tathya-surface-border">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2">
                  <div className="font-semibold text-white flex items-center gap-2">
                    <span className={`flex items-center justify-center w-5 h-5 rounded-full ${getPolicyColor(policy.policyStatus).replace('border', '')}`}>
                      {getPolicyIcon(policy.policyStatus)}
                    </span>
                    {policy.policyName}
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border shrink-0 ${getPolicyColor(policy.policyStatus)}`}>
                    {policy.policyStatus}
                  </span>
                </div>
                <div className="text-xs text-slate-300 ml-7 space-y-1.5">
                  <div>{policy.rationale}</div>
                  {policy.consequence && (
                    <div className="text-tathya-text-muted"><span className="font-medium text-slate-400">Consequence:</span> {policy.consequence}</div>
                  )}
                  {policy.relevantClause && (
                    <div className="text-tathya-text-muted"><span className="font-medium text-slate-400">Clause:</span> {policy.relevantClause}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Omission Findings */}
      {omissionFindings && omissionFindings.length > 0 && (
        <div className="p-4 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border shadow-tathya-card">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <FileWarning className="w-4 h-4 text-slate-400" />
            Potential Omissions
          </h3>
          <div className="space-y-2.5">
            {omissionFindings.map((omission, idx) => (
              <div key={idx} className="p-3 bg-tathya-bg rounded-lg border border-tathya-surface-border relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-slate-600"></div>
                <div className="pl-3 space-y-2 text-xs">
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-medium text-slate-200">{omission.description}</div>
                    <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold border bg-slate-800 text-slate-300 border-slate-700 shrink-0">
                      UNCERTAIN
                    </span>
                  </div>
                  
                  <div className="text-tathya-text-muted leading-relaxed">
                    <span className="font-medium text-slate-400">Why it matters:</span> {omission.whyItMatters}
                  </div>

                  <div className="flex items-center gap-3 pt-1">
                    <div className="flex items-center gap-1 text-[11px]">
                      <span className="text-tathya-text-muted">Confidence:</span>
                      <span className={`font-semibold ${omission.confidence === 'HIGH' ? 'text-amber-400' : 'text-slate-300'}`}>{omission.confidence}</span>
                    </div>
                    {omission.requiresHumanReview && (
                      <div className="px-1.5 py-0.5 rounded-full text-[9px] uppercase font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                        Requires human review
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
