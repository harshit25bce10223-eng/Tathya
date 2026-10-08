import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ListFilter, 
  FolderLock, 
  Database, 
  ShieldAlert, 
  BarChart3, 
  Sliders, 
  PlusCircle,
  ExternalLink
} from 'lucide-react';

interface SidebarNavProps {
  queueCount?: number;
  onItemClick?: () => void;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({ queueCount = 4, onItemClick }) => {
  const navItems = [
    { name: 'Overview', to: '/control', icon: LayoutDashboard },
    { name: 'Review Queue', to: '/control/queue', icon: ListFilter, badge: queueCount },
    { name: 'Audits', to: '/control/audits', icon: FolderLock },
    { name: 'Sources & Truth', to: '/control/sources', icon: Database },
    { name: 'Trust Policies', to: '/control/policies', icon: ShieldAlert },
    { name: 'Metrics & Drift', to: '/control/metrics', icon: BarChart3 },
    { name: 'Governance & Admin', to: '/control/admin', icon: Sliders },
  ];

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col justify-between h-[calc(100vh-3.75rem)] border-r border-tathya-surface-border bg-tathya-surface/80 backdrop-blur select-none">
      <div className="p-3 space-y-4">
        {/* Quick CTA to start audit */}
        <NavLink
          to="/submit"
          onClick={onItemClick}
          className="flex items-center justify-between w-full px-3.5 py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-tathya-accent to-sky-400 text-slate-950 hover:opacity-95 shadow-sm transition-all"
        >
          <span className="flex items-center gap-2">
            <PlusCircle className="w-4 h-4" />
            Start Trust Audit
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-black/15 text-slate-950">
            Submit
          </span>
        </NavLink>

        {/* Navigation list */}
        <nav className="space-y-1">
          <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-tathya-text-muted">
            Control Center
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.to}
                end={item.to === '/control'}
                onClick={onItemClick}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-tathya-surface-elevated text-tathya-accent font-semibold border-l-2 border-tathya-accent'
                      : 'text-tathya-text-secondary hover:text-white hover:bg-tathya-surface-hover'
                  }`
                }
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-1.5 py-0.5 text-[11px] font-bold rounded-full bg-amber-950/80 text-amber-400 border border-amber-800/60">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* External Verifier Link & System Status footer */}
      <div className="p-3 border-t border-tathya-surface-border space-y-2 bg-tathya-surface/40">
        <NavLink
          to="/verify/PASSPORT-88219-AUD1042-CRIT"
          onClick={onItemClick}
          className="flex items-center justify-between px-3 py-2 rounded text-xs font-medium text-tathya-text-secondary hover:text-white hover:bg-tathya-surface-hover transition-colors"
        >
          <span className="flex items-center gap-2">
            <ExternalLink className="w-3.5 h-3.5 text-tathya-accent" />
            Public Trust Verifier
          </span>
          <span className="text-[10px] text-tathya-text-muted font-mono">ECDSA</span>
        </NavLink>

        <div className="px-3 py-2 rounded bg-tathya-surface-elevated/50 border border-tathya-surface-border text-[11px] text-tathya-text-muted flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Deterministic Node 01</span>
          </div>
          <span className="font-mono text-[10px] text-slate-400">v1.4.0</span>
        </div>
      </div>
    </aside>
  );
};
