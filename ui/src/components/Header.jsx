import React from 'react';
import { Layers } from 'lucide-react';

export function Header() {
  return (
    <header className="h-16 bg-bg-surface border-b border-border px-6 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-primary-light rounded text-primary">
          <Layers className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-base font-bold text-text-primary leading-tight">
            AI Resume Analyzer & Job Matching
          </h1>
          <p className="text-xs text-text-muted">Recruiter Decision Support System</p>
        </div>
      </div>
      <div className="flex items-center space-x-3 text-xs text-text-muted">
        <span className="inline-flex items-center px-2 py-1 rounded bg-bg-secondary text-text-secondary border border-border">
          Full Specification Mode
        </span>
      </div>
    </header>
  );
}
