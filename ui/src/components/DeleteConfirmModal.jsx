import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Button } from './common/Button';

export function DeleteConfirmModal({ isOpen, analysis, onConfirm, onCancel, isDeleting }) {
  if (!isOpen || !analysis) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-bg-surface rounded-lg shadow-xl border border-border max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-status-error-bg text-status-error rounded-full">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-text-primary">Delete Analysis</h3>
          </div>
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="text-text-muted hover:text-text-primary cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-4 text-sm text-text-secondary space-y-2">
          <p>
            Are you sure you want to permanently delete{' '}
            <strong className="text-text-primary">"{analysis.name}"</strong>?
          </p>
          <p className="text-xs text-text-muted bg-bg-secondary p-3 rounded border border-border">
            This will permanently remove all candidate rankings, extracted structured profiles, AI explanations,
            and associated semantic vector embeddings from memory and disk.
          </p>
        </div>

        <div className="mt-6 flex items-center justify-end space-x-3">
          <Button variant="secondary" onClick={onCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => onConfirm(analysis.id)}
            disabled={isDeleting}
            className="space-x-1.5"
          >
            <span>{isDeleting ? 'Deleting...' : 'Delete Permanently'}</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
