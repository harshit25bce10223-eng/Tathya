import React from 'react';
import { AuditStatus, SeverityLevel, MaterialityLevel } from '../../api/types';
import { 
  ShieldCheck, 
  AlertTriangle, 
  AlertOctagon, 
  Clock, 
  RotateCw, 
  CheckCircle2, 
  XCircle, 
  ShieldAlert,
  Info
} from 'lucide-react';

interface ScoreBandBadgeProps {
  score: number;
  className?: string;
}

export const ScoreBandBadge: React.FC<ScoreBandBadgeProps> = ({ score, className = '' }) => {
  if (score >= 80) {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-950/70 text-emerald-400 border border-emerald-800/60 shadow-sm ${className}`}>
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        Trustworthy ({score}/100)
      </span>
    );
  }
  if (score >= 50) {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-950/70 text-amber-400 border border-amber-800/60 shadow-sm ${className}`}>
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
        Review Needed ({score}/100)
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-red-950/70 text-red-400 border border-red-800/60 shadow-sm ${className}`}>
      <AlertOctagon className="w-3.5 h-3.5 text-red-400" />
      High Risk ({score}/100)
    </span>
  );
};

interface StatusBadgeProps {
  status: AuditStatus;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  switch (status) {
    case 'VERIFIED':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/50 ${className}`}>
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          VERIFIED
        </span>
      );
    case 'REVIEW REQUIRED':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-800/50 ${className}`}>
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          REVIEW REQUIRED
        </span>
      );
    case 'PROCESSING':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-800/50 ${className}`}>
          <RotateCw className="w-3 h-3 text-amber-400 animate-spin" />
          PROCESSING
        </span>
      );
    case 'QUEUED':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-slate-900 text-slate-300 border border-slate-700/60 ${className}`}>
          <Clock className="w-3 h-3 text-slate-400" />
          QUEUED
        </span>
      );
    case 'FAILED':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-red-950/60 text-red-300 border border-red-800/50 ${className}`}>
          <XCircle className="w-3 h-3 text-red-400" />
          FAILED
        </span>
      );
    case 'TAMPER DETECTED':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-red-950 text-red-200 border border-red-600 animate-pulse ${className}`}>
          <ShieldAlert className="w-3 h-3 text-red-400" />
          TAMPER DETECTED
        </span>
      );
    case 'COMPLETED':
    default:
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-slate-900 text-slate-300 border border-slate-700 ${className}`}>
          <CheckCircle2 className="w-3 h-3 text-slate-400" />
          COMPLETED
        </span>
      );
  }
};

interface SeverityBadgeProps {
  severity: SeverityLevel;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, className = '' }) => {
  switch (severity) {
    case 'CRITICAL':
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide bg-red-950/80 text-red-300 border border-red-700/60 ${className}`}>
          <AlertOctagon className="w-2.5 h-2.5 text-red-400" />
          CRITICAL
        </span>
      );
    case 'HIGH':
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide bg-amber-950/80 text-amber-300 border border-amber-700/60 ${className}`}>
          <AlertTriangle className="w-2.5 h-2.5 text-amber-400" />
          HIGH
        </span>
      );
    case 'MEDIUM':
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium tracking-wide bg-amber-950/60 text-amber-300 border border-amber-800/50 ${className}`}>
          <Info className="w-2.5 h-2.5 text-amber-400" />
          MEDIUM
        </span>
      );
    case 'LOW':
    default:
      return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium tracking-wide bg-slate-900 text-slate-400 border border-slate-700/60 ${className}`}>
          LOW
        </span>
      );
  }
};

interface MaterialityBadgeProps {
  materiality: MaterialityLevel;
  className?: string;
}

export const MaterialityBadge: React.FC<MaterialityBadgeProps> = ({ materiality, className = '' }) => {
  if (materiality === 'MATERIAL') {
    return (
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-red-950/60 text-red-400 border border-red-800/40 ${className}`}>
        MATERIAL RISK
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-slate-900 text-slate-400 border border-slate-800 ${className}`}>
      {materiality}
    </span>
  );
};
