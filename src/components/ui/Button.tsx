import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-150 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tathya-accent focus-visible:ring-offset-2 focus-visible:ring-offset-[#0B0F17] disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5 font-semibold',
  };

  const variantStyles = {
    primary: 'bg-tathya-accent hover:bg-tathya-accent-hover text-slate-950 font-semibold shadow-sm hover:shadow active:bg-sky-500',
    secondary: 'bg-tathya-surface-elevated hover:bg-tathya-surface-hover text-tathya-text-primary border border-tathya-surface-border shadow-sm',
    danger: 'bg-red-600 hover:bg-red-700 text-white font-semibold shadow-sm border border-red-500/50',
    outline: 'bg-transparent hover:bg-tathya-surface-elevated text-tathya-text-primary border border-tathya-surface-border',
    ghost: 'bg-transparent hover:bg-tathya-surface-elevated text-tathya-text-secondary hover:text-white',
  };

  return (
    <button
      disabled={disabled || isLoading}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : (
        leftIcon && <span className="flex-shrink-0">{leftIcon}</span>
      )}
      <span>{children}</span>
      {!isLoading && rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
    </button>
  );
};
