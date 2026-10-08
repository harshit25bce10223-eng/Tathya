import React from 'react';

interface TathyaLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showTagline?: boolean;
  showHindi?: boolean;
  className?: string;
}

export const TathyaLogo: React.FC<TathyaLogoProps> = ({
  size = 'md',
  showTagline = true,
  showHindi = true,
  className = '',
}) => {
  const sizeMap = {
    sm: { icon: 24, text: 'text-base', devanagari: 'text-xs', tag: 'text-[10px]' },
    md: { icon: 32, text: 'text-lg', devanagari: 'text-xs', tag: 'text-xs' },
    lg: { icon: 40, text: 'text-xl', devanagari: 'text-sm', tag: 'text-xs' },
    xl: { icon: 48, text: 'text-2xl', devanagari: 'text-base', tag: 'text-sm' },
  };

  const currentSize = sizeMap[size];

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {/* Precision Geometric SVG Shield / Balance Vector Mark */}
      <div 
        className="relative flex items-center justify-center rounded-lg bg-gradient-to-b from-[#182335] to-[#0F1723] border border-[#22334A] shadow-sm flex-shrink-0"
        style={{ width: currentSize.icon + 8, height: currentSize.icon + 8 }}
      >
        <svg
          width={currentSize.icon}
          height={currentSize.icon}
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="text-tathya-accent"
        >
          {/* Outer cryptographic hexagon */}
          <path
            d="M16 3L27.25 9.5V22.5L16 29L4.75 22.5V9.5L16 3Z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
            className="opacity-70"
          />
          {/* Inner balance scales of truth */}
          <path
            d="M16 8V24"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
          <path
            d="M10 12H22"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
          <path
            d="M10 12L8 17H12L10 12Z"
            fill="#38BDF8"
            fillOpacity="0.25"
            stroke="currentColor"
            strokeWidth="1.25"
            strokeLinejoin="round"
          />
          <path
            d="M22 12L20 17H24L22 12Z"
            fill="#38BDF8"
            fillOpacity="0.25"
            stroke="currentColor"
            strokeWidth="1.25"
            strokeLinejoin="round"
          />
          <circle cx="16" cy="24" r="1.5" fill="currentColor" />
        </svg>
      </div>

      <div className="flex flex-col justify-center">
        <div className="flex items-baseline gap-1.5 leading-none">
          <span className={`font-bold tracking-tight text-white ${currentSize.text}`}>
            Tathya
          </span>
          {showHindi && (
            <span className={`font-semibold text-tathya-accent/80 tracking-normal ${currentSize.devanagari}`}>
              तथ्य
            </span>
          )}
        </div>
        {showTagline && (
          <span className={`text-tathya-text-muted font-normal tracking-wide mt-0.5 ${currentSize.tag}`}>
            Every fact, checked.
          </span>
        )}
      </div>
    </div>
  );
};
