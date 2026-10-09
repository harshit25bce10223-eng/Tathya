import React from 'react';
import { Link } from 'react-router-dom';
import { Audit } from '../../api/types';
import { StatusBadge, SeverityBadge } from '../brand/TrustBadge';
import { FileText, ChevronRight } from 'lucide-react';

interface QueueTableProps {
  audits: Audit[];
}

export const QueueTable: React.FC<QueueTableProps> = ({ audits }) => {
  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-tathya-surface-border bg-tathya-surface shadow-tathya-card">
      <table className="w-full text-left text-xs border-collapse">
        {/* Table Header */}
        <thead>
          <tr className="border-b border-tathya-surface-border bg-tathya-surface-elevated/60 text-tathya-text-muted uppercase text-[10px] font-bold tracking-wider">
            <th className="py-3 px-4">Audit ID</th>
            <th className="py-3 px-4">Document / Title</th>
            <th className="py-3 px-3 hidden md:table-cell">Type</th>
            <th className="py-3 px-3">Risk Band</th>
            <th className="py-3 px-3 text-center">Trust Score</th>
            <th className="py-3 px-3 text-center">Findings</th>
            <th className="py-3 px-3">Status</th>
            <th className="py-3 px-3 hidden lg:table-cell">Updated</th>
            <th className="py-3 px-4 text-right">Action</th>
          </tr>
        </thead>

        {/* Table Body */}
        <tbody className="divide-y divide-tathya-surface-border">
          {audits.map((audit) => {
            return (
              <tr
                key={audit.id}
                className="hover:bg-tathya-surface-elevated/50 transition-colors group"
              >
                {/* 1. Audit ID */}
                <td className="py-3.5 px-4 font-mono font-semibold text-tathya-accent whitespace-nowrap">
                  {audit.id}
                </td>

                {/* 2. Document & Title */}
                <td className="py-3.5 px-4 max-w-xs">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-tathya-text-muted flex-shrink-0" />
                    <div className="min-w-0">
                      <span className="font-semibold text-white block truncate tracking-tight">
                        {audit.title}
                      </span>
                      <span className="text-[11px] text-tathya-text-muted truncate block">
                        {audit.documentName}
                      </span>
                    </div>
                  </div>
                </td>

                {/* 3. Type */}
                <td className="py-3.5 px-3 text-tathya-text-secondary whitespace-nowrap hidden md:table-cell">
                  {audit.documentType}
                </td>

                {/* 4. Risk Band */}
                <td className="py-3.5 px-3 whitespace-nowrap">
                  <SeverityBadge severity={audit.priority} />
                </td>

                {/* 5. Trust Score */}
                <td className="py-3.5 px-3 text-center whitespace-nowrap font-mono font-bold font-tabular">
                  {audit.status === 'PROCESSING' ? (
                    <span className="text-slate-500">—</span>
                  ) : (
                    <div>
                      <span
                        className={`text-sm ${
                          (audit.reviewedScore ?? audit.trustScore) >= 80
                            ? 'text-emerald-400'
                            : (audit.reviewedScore ?? audit.trustScore) >= 50
                            ? 'text-amber-400'
                            : 'text-red-400'
                        }`}
                      >
                        {audit.reviewedScore ?? audit.trustScore}/100
                      </span>
                      {audit.reviewedScore !== null && audit.reviewedScore !== undefined && (
                        <span className="block text-[9px] font-mono text-emerald-400 uppercase tracking-wider">
                          Reviewed
                        </span>
                      )}
                    </div>
                  )}
                </td>

                {/* 6. Findings count */}
                <td className="py-3.5 px-3 text-center whitespace-nowrap">
                  {audit.findingsCount > 0 ? (
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-950/70 text-red-300 border border-red-800/50">
                      {audit.findingsCount} findings
                    </span>
                  ) : (
                    <span className="text-tathya-text-muted">0</span>
                  )}
                </td>

                {/* 7. Status */}
                <td className="py-3.5 px-3 whitespace-nowrap">
                  <StatusBadge status={audit.status} />
                </td>

                {/* 8. Updated */}
                <td className="py-3.5 px-3 text-tathya-text-muted whitespace-nowrap hidden lg:table-cell font-mono text-[11px]">
                  {formatDate(audit.updatedAt)}
                </td>

                {/* 9. Action */}
                <td className="py-3.5 px-4 text-right whitespace-nowrap">
                  <Link
                    to={`/control/workspace/${audit.id}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-semibold bg-tathya-surface-elevated hover:bg-tathya-accent hover:text-slate-950 text-white border border-tathya-surface-border transition-all"
                  >
                    <span>Investigate</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
