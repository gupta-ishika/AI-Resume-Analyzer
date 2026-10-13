import React from 'react';

export function Badge({ children, variant = 'neutral', className = '' }) {
  const variants = {
    neutral: 'bg-bg-secondary text-text-secondary border-border',
    success: 'bg-status-success-bg text-status-success border-green-200',
    warning: 'bg-status-warning-bg text-status-warning border-amber-200',
    error: 'bg-status-error-bg text-status-error border-red-200',
    info: 'bg-status-info-bg text-status-info border-blue-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        variants[variant] || variants.neutral
      } ${className}`}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }) {
  const mapStatus = (statusStr) => {
    switch (statusStr?.toUpperCase()) {
      case 'RANKED':
      case 'SUCCESS':
      case 'READY':
        return { label: statusStr, variant: 'success' };
      case 'PROCESSING':
      case 'GENERATING':
        return { label: statusStr, variant: 'info' };
      case 'REQUIREMENTS_PENDING':
      case 'PENDING':
      case 'NOT_REQUESTED':
        return { label: statusStr, variant: 'neutral' };
      case 'NEEDS_REVIEW':
      case 'DUPLICATE':
        return { label: statusStr, variant: 'warning' };
      case 'FAILED':
      case 'REJECTED':
      case 'UPLOAD_EXPIRED':
        return { label: statusStr, variant: 'error' };
      default:
        return { label: statusStr || 'Unknown', variant: 'neutral' };
    }
  };

  const { label, variant } = mapStatus(status);

  return <Badge variant={variant}>{label}</Badge>;
}
