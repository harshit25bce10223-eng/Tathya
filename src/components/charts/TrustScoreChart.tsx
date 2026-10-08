import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';

interface TrustDataPoint {
  iteration: string;
  score: number;
  unresolvedFlags: number;
}

interface TrustScoreChartProps {
  data?: TrustDataPoint[];
}

export const TrustScoreChart: React.FC<TrustScoreChartProps> = ({
  data = [
    { iteration: 'Raw AI Draft', score: 42, unresolvedFlags: 4 },
    { iteration: 'Review Round 1', score: 68, unresolvedFlags: 2 },
    { iteration: 'Vendor Reconciled', score: 84, unresolvedFlags: 1 },
    { iteration: 'Final Executed', score: 94, unresolvedFlags: 0 },
  ],
}) => {
  return (
    <div className="w-full h-64 p-4 rounded-xl border border-tathya-surface-border bg-tathya-surface shadow-tathya-card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-white">
            Trust Score Progression Across Iterations
          </h4>
          <span className="text-[11px] text-tathya-text-muted">
            Deterministic score recalibration over review cycle
          </span>
        </div>
        <span className="text-xs font-mono font-bold text-emerald-400">
          Peak: 94 / 100
        </span>
      </div>

      <ResponsiveContainer width="100%" height="80%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="trustScoreGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#F59E0B" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E2C40" vertical={false} />
          <XAxis 
            dataKey="iteration" 
            stroke="#64748B" 
            tick={{ fill: '#94A3B8', fontSize: 11 }} 
            axisLine={{ stroke: '#1E2C40' }}
          />
          <YAxis 
            domain={[0, 100]} 
            stroke="#64748B" 
            tick={{ fill: '#94A3B8', fontSize: 11 }} 
            axisLine={{ stroke: '#1E2C40' }}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#172233', borderColor: '#1E2C40', borderRadius: '8px', fontSize: '12px' }}
            itemStyle={{ color: '#F1F5F9' }}
          />
          <Area 
            type="monotone" 
            dataKey="score" 
            stroke="#F59E0B" 
            strokeWidth={2.5} 
            fillOpacity={1} 
            fill="url(#trustScoreGrad)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
