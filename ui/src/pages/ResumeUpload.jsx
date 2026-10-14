import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  FileCheck,
  AlertTriangle,
  Play,
  ArrowLeft,
  CheckCircle2,
  RefreshCw,
  File,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, StatusBadge } from '../components/common/Badge';
import { apiClient } from '../api/client';

export function ResumeUpload({
  analysisId,
  analysisName,
  onStartAnalysis,
  onBackToRequirements,
}) {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const fetchResumes = async () => {
    try {
      const data = await apiClient.getResumes(analysisId);
      setResumes(data.items || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch uploaded resumes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, [analysisId]);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;

    setUploading(true);
    setError(null);

    // Small batch upload (up to 5 at a time) for responsive feedback
    const fileArray = Array.from(files);
    const batchSize = 5;

    try {
      for (let i = 0; i < fileArray.length; i += batchSize) {
        const chunk = fileArray.slice(i, i + batchSize);
        await apiClient.uploadResumes(analysisId, chunk);
      }
      await fetchResumes();
    } catch (err) {
      setError(err.message || 'Error occurred during resume upload.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleStartAnalysis = async () => {
    setStarting(true);
    setError(null);
    try {
      await apiClient.startAnalysis(analysisId);
      onStartAnalysis(analysisId);
    } catch (err) {
      setError(err.message || 'Failed to start analysis.');
      setStarting(false);
    }
  };

  const acceptedCount = resumes.filter((r) => r.status === 'READY').length;
  const duplicateCount = resumes.filter((r) => r.status === 'DUPLICATE').length;
  const rejectedCount = resumes.filter((r) => r.status === 'REJECTED').length;
  const maxAccepted = 50;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-2xl font-bold text-text-primary">Resume Upload</h2>
            <Badge variant="neutral">
              {acceptedCount} / {maxAccepted} Resumes Accepted
            </Badge>
          </div>
          <p className="text-sm text-text-secondary mt-1">
            Analysis: <strong className="text-text-primary">{analysisName || analysisId}</strong>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button variant="secondary" onClick={onBackToRequirements} disabled={uploading || starting}>
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            <span>Edit Requirements</span>
          </Button>

          <Button
            onClick={handleStartAnalysis}
            disabled={starting || uploading || acceptedCount === 0}
            className="space-x-2"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>{starting ? 'Starting Analysis...' : `Start Analysis (${acceptedCount} Ready)`}</span>
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-status-error-bg text-status-error rounded-lg border border-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Upload Dropzone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
          dragActive
            ? 'border-primary bg-primary-light/40'
            : 'border-border bg-bg-surface hover:bg-bg-secondary/40'
        }`}
      >
        <Upload className="w-10 h-10 text-primary mx-auto mb-3" />
        <h3 className="text-base font-bold text-text-primary">
          Upload Candidate Resumes
        </h3>
        <p className="text-xs text-text-muted mt-1 max-w-md mx-auto">
          Drag and drop PDF or DOCX resume files here, or click to browse. Max 10MB per file; up to 50 accepted resumes per analysis.
        </p>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx"
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
          id="resume-batch-input"
          disabled={uploading}
        />

        <div className="mt-5 flex justify-center">
          <label
            htmlFor="resume-batch-input"
            className={`inline-flex items-center space-x-2 px-5 py-2.5 rounded-md text-sm font-medium border border-border bg-white text-text-primary hover:bg-bg-secondary cursor-pointer shadow-xs ${
              uploading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {uploading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-primary" />
                <span>Uploading batch...</span>
              </>
            ) : (
              <>
                <File className="w-4 h-4 text-text-secondary" />
                <span>Select Resume Files</span>
              </>
            )}
          </label>
        </div>
      </div>

      {/* Resumes List Card */}
      <Card
        title="Uploaded Files & Outcome Verification"
        subtitle="Automatic duplicate detection and format validation run immediately upon receipt."
      >
        {/* Counts summary bar */}
        <div className="grid grid-cols-3 gap-3 mb-4 p-3 bg-bg-page rounded-md border border-border text-xs">
          <div className="text-center">
            <span className="text-text-muted block">Ready for Processing</span>
            <span className="font-bold text-status-success text-base">{acceptedCount}</span>
          </div>
          <div className="text-center border-x border-border">
            <span className="text-text-muted block">Duplicate Files</span>
            <span className="font-bold text-status-warning text-base">{duplicateCount}</span>
          </div>
          <div className="text-center">
            <span className="text-text-muted block">Rejected Files</span>
            <span className="font-bold text-status-error text-base">{rejectedCount}</span>
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-text-muted text-sm">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary" />
            Loading uploaded files...
          </div>
        ) : resumes.length === 0 ? (
          <div className="py-12 text-center text-text-muted text-sm">
            No resume files uploaded yet. Add candidate resumes above to begin.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-bg-secondary text-text-secondary font-semibold uppercase">
                <tr>
                  <th className="px-4 py-2.5">Filename</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Verification Detail</th>
                  <th className="px-4 py-2.5 text-right">Uploaded At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {resumes.map((r) => (
                  <tr key={r.resume_id} className="hover:bg-bg-secondary/40">
                    <td className="px-4 py-3 font-medium text-text-primary flex items-center space-x-2">
                      <FileCheck className="w-4 h-4 text-text-muted shrink-0" />
                      <span className="truncate max-w-xs">{r.filename}</span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-3 text-text-muted">
                      {r.status === 'READY' ? (
                        <span className="text-status-success flex items-center space-x-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Accepted into batch</span>
                        </span>
                      ) : r.status === 'DUPLICATE' ? (
                        <span className="text-status-warning flex items-center space-x-1">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>SHA-256 duplicate; skipped from queue</span>
                        </span>
                      ) : (
                        <span className="text-status-error font-medium">
                          {r.reason_code || 'Format or limit violation'}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-text-muted">
                      {new Date(r.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
