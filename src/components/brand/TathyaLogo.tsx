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
    sm: { icon: 28, text: 'text-base', devanagari: 'text-xs', tag: 'text-[10px]' },
    md: { icon: 36, text: 'text-lg', devanagari: 'text-xs', tag: 'text-xs' },
    lg: { icon: 44, text: 'text-xl', devanagari: 'text-sm', tag: 'text-xs' },
    xl: { icon: 56, text: 'text-2xl', devanagari: 'text-base', tag: 'text-sm' },
  };

  const currentSize = sizeMap[size];

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {/* Actual Tathya brand logo from /tathya-mark-v2.png */}
      <img
        src="/tathya-mark-v2.png"
        alt="Tathya"
        width={currentSize.icon}
        height={currentSize.icon}
        className="flex-shrink-0 rounded-sm"
        style={{ objectFit: 'contain' }}
      />

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
