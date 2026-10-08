import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { TathyaLogo } from '../components/brand/TathyaLogo';
import { Button } from '../components/ui/Button';
import { Lock, Mail, ArrowRight, ShieldCheck } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('lokesh@tathya.ai');
  const [password, setPassword] = useState('••••••••••••');
  const [loading, setLoading] = useState(false);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      navigate('/control');
    }, 500);
  };

  return (
    <div className="min-h-screen bg-tathya-bg text-tathya-text-primary flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Brand */}
        <div className="text-center flex flex-col items-center gap-3">
          <TathyaLogo size="lg" showTagline={true} />
          <p className="text-xs text-tathya-text-muted">
            Sign in to access your audit workspace
          </p>
        </div>

        {/* Login Card */}
        <div className="p-6 rounded-2xl bg-tathya-surface border border-tathya-surface-border shadow-tathya-elevated">
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-tathya-text-muted absolute left-3 top-2.5" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-tathya-surface-elevated text-white text-xs pl-9 pr-3.5 py-2 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent focus:outline-none"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-white">
                  Password
                </label>
                <a href="#reset" className="text-[11px] text-tathya-accent hover:underline">
                  Forgot?
                </a>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-tathya-text-muted absolute left-3 top-2.5" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-tathya-surface-elevated text-white text-xs pl-9 pr-3.5 py-2 rounded-lg border border-tathya-surface-border focus:ring-1 focus:ring-tathya-accent focus:outline-none"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={loading}
              rightIcon={<ArrowRight className="w-4 h-4" />}
              className="w-full mt-2"
            >
              Sign In
            </Button>
          </form>

          <div className="mt-4 pt-4 border-t border-tathya-surface-border text-center text-[11px] text-tathya-text-muted flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>SSO via Okta · SAML 2.0</span>
          </div>
        </div>

        {/* Demo access */}
        <div className="text-center text-xs text-tathya-text-muted">
          Evaluating Tathya?{' '}
          <Link to="/control" className="text-tathya-accent font-semibold hover:underline">
            Open the demo →
          </Link>
        </div>
      </div>
    </div>
  );
};
