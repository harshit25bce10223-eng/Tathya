import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { TathyaLogo } from '../brand/TathyaLogo';
import { SidebarNav } from './SidebarNav';
import { 
  Building2, 
  ChevronDown, 
  Bell, 
  Menu, 
  X,
  UserCheck
} from 'lucide-react';

interface AppShellProps {
  children?: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  // Determine if on public submit / verify / login page or in control center
  const isSubmitPage = location.pathname === '/submit';
  const isVerifyPage = location.pathname.startsWith('/verify');
  const isLoginPage = location.pathname === '/login';

  return (
    <div className="min-h-screen bg-tathya-bg text-tathya-text-primary flex flex-col font-sans">
      {/* GLOBAL TOP ENTERPRISE HEADER */}
      <header className="h-15 border-b border-tathya-surface-border bg-tathya-surface/90 backdrop-blur sticky top-0 z-40 px-4 lg:px-6 flex items-center justify-between">
        {/* Left: Brand & Mobile Toggle */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-1.5 rounded-md text-tathya-text-secondary hover:text-white hover:bg-tathya-surface-hover"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <Link to="/control" className="hover:opacity-95 transition-opacity">
            <TathyaLogo size="md" showTagline={false} />
          </Link>

          {/* Live environment indicator */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-700/50 text-[11px] text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-slate-300 font-medium">Production</span>
          </div>
        </div>

        {/* Center / Right: Workspace Selector & Reviewer Profile */}
        <div className="flex items-center gap-3">
          {/* Workspace Switcher */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-tathya-surface-elevated border border-tathya-surface-border text-xs text-tathya-text-secondary hover:border-slate-600 transition-colors cursor-pointer">
            <Building2 className="w-3.5 h-3.5 text-tathya-accent" />
            <span className="text-white font-medium">Procurement</span>
            <span className="text-tathya-text-muted">· Space Alpha</span>
            <ChevronDown className="w-3.5 h-3.5 text-tathya-text-muted" />
          </div>

          {/* Quick Submit Link if not on submit page */}
          {!isSubmitPage && !isLoginPage && (
            <Link
              to="/submit"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-tathya-accent hover:bg-tathya-accent-hover text-slate-950 transition-colors shadow-sm"
            >
              New Audit
            </Link>
          )}

          {/* Notifications / Alerts Indicator */}
          <button 
            className="relative p-2 rounded-lg text-tathya-text-secondary hover:text-white hover:bg-tathya-surface-hover transition-colors"
            aria-label="System notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
          </button>

          {/* Reviewer / Enterprise Identity */}
          <div className="flex items-center gap-2 pl-2 border-l border-tathya-surface-border">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-950 to-slate-800 border border-tathya-accent/40 flex items-center justify-center text-xs font-bold text-tathya-accent">
              <UserCheck className="w-4 h-4 text-tathya-accent" />
            </div>
            <div className="hidden xl:flex flex-col text-left">
              <span className="text-xs font-semibold text-white leading-tight">Lokesh</span>
              <span className="text-[10px] text-tathya-text-muted">Lead Reviewer</span>
            </div>
          </div>
        </div>
      </header>

      {/* BODY CONTENT WRAPPER */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop Sidebar (visible on control center routes) */}
        {!isLoginPage && !isVerifyPage && (
          <div className="hidden lg:block">
            <SidebarNav />
          </div>
        )}

        {/* Mobile Slide-in Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden fixed inset-0 z-50 flex">
            <div 
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileMenuOpen(false)}
            />
            <div className="relative w-64 max-w-[80%] bg-tathya-surface border-r border-tathya-surface-border h-full z-10 flex flex-col">
              <div className="p-4 border-b border-tathya-surface-border flex items-center justify-between">
                <TathyaLogo size="sm" showTagline={false} />
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1 rounded text-tathya-text-muted hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <SidebarNav onItemClick={() => setMobileMenuOpen(false)} />
            </div>
          </div>
        )}

        {/* Main Content Workspace */}
        <main className="flex-1 overflow-y-auto bg-tathya-bg-secondary/40">
          {children}
        </main>
      </div>
    </div>
  );
};
