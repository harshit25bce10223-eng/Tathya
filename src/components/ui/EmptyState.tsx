import React from 'react';
import { Button } from './Button';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center text-center p-8 rounded-lg border border-dashed border-tathya-surface-border bg-tathya-surface/40 ${className}`}>
      <div className="p-3 rounded-xl bg-tathya-surface-elevated border border-tathya-surface-border text-tathya-accent mb-4 shadow-sm">
        {icon}
      </div>
      <h4 className="text-base font-semibold text-white mb-1.5">{title}</h4>
      <p className="text-sm text-tathya-text-secondary max-w-sm mb-5 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
