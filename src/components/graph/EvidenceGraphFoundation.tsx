import React from 'react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { GitBranch } from 'lucide-react';

interface EvidenceGraphFoundationProps {
  auditId?: string;
}

export const EvidenceGraphFoundation: React.FC<EvidenceGraphFoundationProps> = ({ auditId = 'CURRENT_AUDIT' }) => {
  const initialNodes = [
    {
      id: 'doc-1',
      position: { x: 50, y: 100 },
      data: { label: '📄 AI Document: AI_Procurement_Summary.pdf' },
      style: { background: '#121A27', color: '#F1F5F9', border: '1px solid #1E2C40', borderRadius: '8px', fontSize: '11px', padding: '10px' }
    },
    {
      id: 'claim-1',
      position: { x: 340, y: 50 },
      data: { label: '⚖️ Claim CLM-01: Fee ₹24.8M (Variance: +₹41.6L)' },
      style: { background: '#3F1212', color: '#FCA5A5', border: '1px solid #B91C1C', borderRadius: '8px', fontSize: '11px', padding: '10px' }
    },
    {
      id: 'source-1',
      position: { x: 620, y: 50 },
      data: { label: '🛡️ Source PO v2: Approved Ceiling ₹20,640,000' },
      style: { background: '#064E3B', color: '#6EE7B7', border: '1px solid #059669', borderRadius: '8px', fontSize: '11px', padding: '10px' }
    },
    {
      id: 'claim-2',
      position: { x: 340, y: 160 },
      data: { label: '📅 Claim CLM-02: Target 22 Dec 2026 (+37d slip)' },
      style: { background: '#451A03', color: '#FCD34D', border: '1px solid #D97706', borderRadius: '8px', fontSize: '11px', padding: '10px' }
    },
    {
      id: 'source-2',
      position: { x: 620, y: 160 },
      data: { label: '🛡️ Source Schedule: Completion 15 Nov 2026' },
      style: { background: '#064E3B', color: '#6EE7B7', border: '1px solid #059669', borderRadius: '8px', fontSize: '11px', padding: '10px' }
    }
  ];

  const initialEdges = [
    { id: 'e1-2', source: 'doc-1', target: 'claim-1', animated: true, style: { stroke: '#EF4444' } },
    { id: 'e2-3', source: 'claim-1', target: 'source-1', label: 'Contradicts PO v2', style: { stroke: '#B91C1C' } },
    { id: 'e1-4', source: 'doc-1', target: 'claim-2', animated: true, style: { stroke: '#F59E0B' } },
    { id: 'e4-5', source: 'claim-2', target: 'source-2', label: 'Contradicts Schedule', style: { stroke: '#D97706' } }
  ];

  return (
    <div className="w-full h-80 rounded-xl border border-tathya-surface-border bg-tathya-bg-secondary overflow-hidden relative shadow-tathya-card">
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 px-2.5 py-1 rounded bg-tathya-surface border border-tathya-surface-border text-xs text-white">
        <GitBranch className="w-3.5 h-3.5 text-tathya-accent" />
        <span className="font-semibold">Evidence Graph Topology</span>
        <span className="text-[10px] text-tathya-text-muted">(@xyflow/react canvas)</span>
      </div>

      <ReactFlow
        nodes={initialNodes}
        edges={initialEdges}
        fitView
      >
        <Background color="#1E2C40" gap={16} />
        <Controls className="bg-tathya-surface border border-tathya-surface-border fill-white" />
      </ReactFlow>
    </div>
  );
};
