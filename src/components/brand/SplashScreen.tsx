import React, { useEffect, useState } from 'react';

interface SplashScreenProps {
  onDone: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onDone }) => {
  const [phase, setPhase] = useState<'logo' | 'tagline' | 'exit'>('logo');

  useEffect(() => {
    // Phase 1: logo appears (0ms)
    // Phase 2: tagline appears (700ms)
    const t1 = setTimeout(() => setPhase('tagline'), 700);
    // Phase 3: exit fade (1800ms)
    const t2 = setTimeout(() => setPhase('exit'), 1800);
    // Phase 4: unmount (2300ms)
    const t3 = setTimeout(() => onDone(), 2300);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onDone]);

  return (
    <div
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#0B0F17]"
      style={{
        transition: 'opacity 0.5s ease',
        opacity: phase === 'exit' ? 0 : 1,
      }}
    >
      {/* Ambient glow behind logo */}
      <div
        className="absolute w-64 h-64 rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, #F59E0B 0%, transparent 70%)',
          filter: 'blur(40px)',
          transition: 'opacity 0.8s ease',
        }}
      />

      {/* Logo image — scales in */}
      <div
        style={{
          transition: 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.6s ease',
          transform: phase === 'logo' ? 'scale(0.7)' : 'scale(1)',
          opacity: phase === 'logo' ? 0 : 1,
        }}
        className="relative z-10 flex flex-col items-center gap-5"
      >
        <img
          src="/tathya_logo.svg"
          alt="Tathya"
          width={96}
          height={96}
          className="rounded-lg"
          style={{ objectFit: 'contain' }}
        />

        {/* Word mark */}
        <div className="flex flex-col items-center gap-1">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">
              Tathya
            </span>
            <span className="text-lg font-semibold text-amber-400/80">
              तथ्य
            </span>
          </div>

          {/* Tagline — fades in after logo */}
          <p
            className="text-sm text-slate-400 tracking-widest uppercase font-light"
            style={{
              transition: 'opacity 0.5s ease, transform 0.5s ease',
              opacity: phase === 'tagline' || phase === 'exit' ? 1 : 0,
              transform: phase === 'tagline' || phase === 'exit' ? 'translateY(0)' : 'translateY(6px)',
            }}
          >
            Every fact, checked.
          </p>
        </div>
      </div>

      {/* Bottom progress bar */}
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 w-32 h-[2px] bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-amber-400 rounded-full"
          style={{
            transition: 'width 1.8s linear',
            width: phase === 'logo' ? '0%' : '100%',
          }}
        />
      </div>
    </div>
  );
};
