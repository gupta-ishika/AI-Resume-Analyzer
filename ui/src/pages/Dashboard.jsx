import React, { useState, useEffect } from 'react';
import {
  Card,
} from '../components/common/Card';
import { Button } from '../components/common/Button';
import { StatusBadge } from '../components/common/Badge';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';
import {
  PlusCircle,
  FileText,
  CheckCircle2,
  Clock,
  Trash2,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { apiClient } from '../api/client';

export function Dashboard({ onNewAnalysis, onOpenAnalysis }) {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadAnalyses = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getAnalyses(1, 50);
      setAnalyses(data.items || []);
    } catch (err) {
      setError(err.message || 'Failed to load analyses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalyses();
  }, []);

  const handleDeleteConfirm = async (analysisId) => {
    setIsDeleting(true);
    try {
      await apiClient.deleteAnalysis(analysisId);
      setAnalyses((prev) => prev.filter((a) => a.id !== analysisId));
      setDeleteTarget(null);
    } catch (err) {
      alert(`Deletion failed: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const totalAnalyses = analyses.length;
  const totalRankedCandidates = analyses
    .filter((a) => a.status === 'RANKED')
    .reduce((sum, a) => sum + (a.candidate_count || 0), 0);
  const activeProcessing = analyses.filter((a) => a.status === 'PROCESSING').length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Recruiter Dashboard</h2>
          <p className="text-sm text-text-secondary mt-1">
            Compare, evaluate, and rank candidate resumes against structured job requirements.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button
            variant="secondary"
            onClick={loadAnalyses}
            disabled={loading}
            className="space-x-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>

          <Button onClick={onNewAnalysis} className="flex items-center space-x-2">
            <PlusCircle className="w-4 h-4" />
            <span>New Analysis</span>
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-status-error-bg text-status-error rounded-lg border border-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Card className="flex items-center space-x-4">
          <div className="p-3 bg-primary-light rounded-lg text-primary">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-text-muted">Total Analyses</p>
            <p className="text-2xl font-bold text-text-primary mt-0.5">{totalAnalyses}</p>
          </div>
        </Card>

        <Card className="flex items-center space-x-4">
          <div className="p-3 bg-status-success-bg rounded-lg text-status-success">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-text-muted">Ranked Candidates</p>
            <p className="text-2xl font-bold text-text-primary mt-0.5">{totalRankedCandidates}</p>
          </div>
        </Card>

        <Card className="flex items-center space-x-4">
          <div className="p-3 bg-status-info-bg rounded-lg text-status-info">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-text-muted">Active Processing</p>
            <p className="text-2xl font-bold text-text-primary mt-0.5">{activeProcessing}</p>
          </div>
        </Card>
      </div>

      {/* Recent Analyses Section */}
      <Card
        title="Saved Analyses"
        subtitle="Manage candidate evaluations and ranking outcomes"
      >
        {loading ? (
          <div className="py-16 text-center text-text-muted text-sm">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-primary" />
            Loading saved analyses...
          </div>
        ) : analyses.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="w-12 h-12 bg-bg-secondary rounded-full flex items-center justify-center mx-auto mb-3 text-text-muted">
              <FileText className="w-6 h-6" />
            </div>
            <h4 className="text-base font-semibold text-text-primary">No analyses yet</h4>
            <p className="text-sm text-text-muted mt-1 max-w-sm mx-auto">
              Create your first resume analysis to compare candidates against a job description.
            </p>
            <div className="mt-5">
              <Button onClick={onNewAnalysis} className="inline-flex items-center space-x-2">
                <PlusCircle className="w-4 h-4" />
                <span>Create New Analysis</span>
              </Button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-bg-secondary text-text-secondary text-xs uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3">Analysis Name</th>
                  <th className="px-4 py-3">Ranked Candidates</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Last Updated</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {analyses.map((item) => {
                  const isProcessing = item.status === 'PROCESSING';

                  return (
                    <tr
                      key={item.id}
                      onClick={() => onOpenAnalysis(item)}
                      className="hover:bg-bg-secondary/60 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3.5 font-medium text-text-primary">
                        {item.name}
                      </td>
                      <td className="px-4 py-3.5 text-text-secondary">
                        {item.candidate_count} candidates
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-4 py-3.5 text-xs text-text-muted">
                        {new Date(item.updated_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5 text-right space-x-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenAnalysis(item);
                          }}
                          className="space-x-1"
                        >
                          <span>Open</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Button>

                        <button
                          type="button"
                          disabled={isProcessing}
                          title={
                            isProcessing
                              ? 'Deletion is disabled while analysis is actively processing.'
                              : 'Delete analysis'
                          }
                          onClick={(e) => {
                            e.stopPropagation();
                            if (!isProcessing) {
                              setDeleteTarget(item);
                            }
                          }}
                          className={`p-1.5 rounded transition-colors ${
                            isProcessing
                              ? 'opacity-30 cursor-not-allowed text-text-muted'
                              : 'text-text-muted hover:text-status-error hover:bg-status-error-bg cursor-pointer'
                          }`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={Boolean(deleteTarget)}
        analysis={deleteTarget}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
        isDeleting={isDeleting}
      />
    </div>
  );
}
