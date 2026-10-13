import React from 'react';

export function Card({ children, title, subtitle, action, className = '' }) {
  return (
    <div className={`bg-bg-surface border border-border rounded-lg p-5 ${className}`}>
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
          <div>
            {title && <h3 className="text-base font-semibold text-text-primary">{title}</h3>}
            {subtitle && <p className="text-sm text-text-muted mt-0.5">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
