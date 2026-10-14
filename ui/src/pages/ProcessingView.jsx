import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { apiClient } from '../api/client';

export function ProcessingView({ analysisId, analysisName, onCompleted }) {
  const [statusData, setStatusData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const poll = async () => {
      try {
        const data = await apiClient.getAnalysisStatus(analysisId);
        if (!isMounted) return;

        setStatusData(data);

        if (data.status === 'RANKED') {
          // Transition to ranked results
          setTimeout(() => {
            if (isMounted) onCompleted(analysisId);
          }, 1000);
        }
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || 'Error checking analysis status.');
      }
    };

    poll();
    const interval = setInterval(poll, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [analysisId, onCompleted]);

  const total = statusData?.total || 0;
  const processed = statusData?.processed || 0;
  const progressPercent = total > 0 ? Math.min(Math.round((processed / total) * 100), 100) : 0;
  const isRanked = statusData?.status === 'RANKED';
  const isFailed = statusData?.status === 'FAILED';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-text-primary">
          {isRanked ? 'Analysis Complete' : isFailed ? 'Analysis Failed' : 'Analyzing Resumes...'}
        </h2>
        <p className="text-sm text-text-secondary">
          Analysis: <strong className="text-text-primary">{analysisName || analysisId}</strong>
        </p>
      </div>

      {error && (
        <div className="p-4 bg-status-error-bg text-status-error rounded-lg border border-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Main Status Card */}
      <Card className="text-center p-8 space-y-6">
        {!isRanked && !isFailed && (
          <div className="relative w-20 h-20 mx-auto flex items-center justify-center">
            <RefreshCw className="w-12 h-12 text-primary animate-spin" />
          </div>
        )}

        {isRanked && (
          <div className="w-16 h-16 bg-status-success-bg text-status-success rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-10 h-10" />
          </div>
        )}

        {isFailed && (
          <div className="w-16 h-16 bg-status-error-bg text-status-error rounded-full flex items-center justify-center mx-auto">
            <AlertCircle className="w-10 h-10" />
          </div>
        )}

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-text-muted font-medium">
            <span>Extraction & Deterministic Scoring</span>
            <span>{progressPercent}% Complete</span>
          </div>
          <div className="w-full h-3 bg-bg-secondary rounded-full overflow-hidden border border-border">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                isFailed ? 'bg-status-error' : isRanked ? 'bg-status-success' : 'bg-primary'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Message */}
        <p className="text-xs text-text-muted">
          {isRanked
            ? 'Candidate profiles scored and ranked deterministically. Transitioning to results...'
            : isFailed
            ? `Analysis failed: ${statusData?.failure_reason || 'An internal error occurred.'}`
            : 'Extracting skills, evaluating experience, and calculating isolated vector embeddings in background Celery workers.'}
        </p>

        {isRanked && (
          <div className="pt-2">
            <Button onClick={() => onCompleted(analysisId)} className="space-x-1.5">
              <span>View Ranked Candidates</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </Card>

      {/* Detailed Counts Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center text-xs">
        <div className="p-3 bg-white rounded-lg border border-border">
          <span className="text-text-muted block">Total Resumes</span>
          <span className="text-lg font-bold text-text-primary mt-0.5">{total}</span>
        </div>
        <div className="p-3 bg-white rounded-lg border border-border">
          <span className="text-text-muted block">Processed</span>
          <span className="text-lg font-bold text-text-primary mt-0.5">{processed}</span>
        </div>
        <div className="p-3 bg-white rounded-lg border border-border">
          <span className="text-status-success block font-medium">Successful</span>
          <span className="text-lg font-bold text-status-success mt-0.5">
            {statusData?.successful || 0}
          </span>
        </div>
        <div className="p-3 bg-white rounded-lg border border-border">
          <span className="text-text-muted block">Remaining</span>
          <span className="text-lg font-bold text-text-muted mt-0.5">
            {statusData?.remaining || 0}
          </span>
        </div>
      </div>

      {/* Exclusions & Review Counts */}
      {((statusData?.needs_review || 0) > 0 ||
        (statusData?.failed || 0) > 0 ||
        (statusData?.duplicates_excluded || 0) > 0) && (
        <Card title="Excluded or Needs-Review Resumes">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-status-warning-bg border border-amber-200 rounded">
              <span className="font-semibold text-status-warning block">Needs Review</span>
              <p className="text-text-secondary mt-1">
                {statusData?.needs_review || 0} resumes with partial readability or extraction ambiguity.
              </p>
            </div>
            <div className="p-3 bg-status-error-bg border border-red-200 rounded">
              <span className="font-semibold text-status-error block">Failed Extractions</span>
              <p className="text-text-secondary mt-1">
                {statusData?.failed || 0} corrupt, password-protected, or unreadable files.
              </p>
            </div>
            <div className="p-3 bg-bg-secondary border border-border rounded">
              <span className="font-semibold text-text-secondary block">Duplicates Excluded</span>
              <p className="text-text-muted mt-1">
                {statusData?.duplicates_excluded || 0} identical files skipped from queue.
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
