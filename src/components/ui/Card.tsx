import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
  highlighted?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  elevated = false,
  highlighted = false,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`rounded-lg transition-all duration-150 ${
        elevated
          ? 'bg-tathya-surface-elevated border border-tathya-surface-border shadow-tathya-elevated'
          : 'bg-tathya-surface border border-tathya-surface-border shadow-tathya-card'
      } ${
        highlighted ? 'ring-1 ring-tathya-accent/50 border-tathya-accent/50' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
