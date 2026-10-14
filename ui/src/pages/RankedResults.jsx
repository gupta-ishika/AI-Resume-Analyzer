import React, { useState, useEffect } from 'react';
import {
  Award,
  UserCheck,
  AlertCircle,
  FileQuestion,
  Trash2,
  ArrowLeft,
  ChevronRight,
  Info,
  RefreshCw,
  Eye,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, StatusBadge } from '../components/common/Badge';
import { CandidateDetailDrawer } from '../components/CandidateDetailDrawer';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';
import { apiClient } from '../api/client';

export function RankedResults({
  analysisId,
  analysisName,
  onBackToDashboard,
  onAnalysisDeleted,
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchResults = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.getCandidates(analysisId);
      setData(result);
    } catch (err) {
      setError(err.message || 'Failed to load candidate rankings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [analysisId]);

  const handleOpenCandidate = (candidateId) => {
    setSelectedCandidateId(candidateId);
    setIsDrawerOpen(true);
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await apiClient.deleteAnalysis(analysisId);
      setIsDeleteModalOpen(false);
      onAnalysisDeleted();
    } catch (err) {
      alert(`Failed to delete analysis: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const ranking = data?.ranking || [];
  const excludedFiles = data?.excluded_files || [];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-2xl font-bold text-text-primary">Candidate Rankings</h2>
            <StatusBadge status="RANKED" />
          </div>
          <p className="text-sm text-text-secondary mt-1">
            Analysis: <strong className="text-text-primary">{analysisName || analysisId}</strong>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button variant="secondary" onClick={onBackToDashboard}>
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            <span>Dashboard</span>
          </Button>

          <Button
            variant="secondary"
            onClick={() => setIsDeleteModalOpen(true)}
            className="text-status-error hover:bg-status-error-bg hover:border-red-200"
          >
            <Trash2 className="w-4 h-4 mr-1.5" />
            <span>Delete Analysis</span>
          </Button>
        </div>
      </div>

      {/* Decision-Support Advisory Notice */}
      <div className="p-4 bg-primary-light border border-indigo-200 rounded-lg flex items-start space-x-3 text-xs">
        <Info className="w-5 h-5 text-primary shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-primary">Recruiter Decision Support System</p>
          <p className="text-text-secondary mt-0.5">
            Rankings and match scores are deterministic, evidence-based matching indicators derived from
            extracted candidate skills and verified qualifications. Scores do not constitute hiring decisions
            and personal identity is withheld from this summary to protect review objectivity.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-status-error-bg text-status-error rounded-lg border border-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Main Ranking Table Card */}
      <Card
        title={`Ranked Candidates (${ranking.length})`}
        subtitle="Ordered by multi-component score with deterministic tie-breaking"
      >
        {loading ? (
          <div className="py-16 text-center text-text-muted text-sm">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-primary" />
            Loading ranked candidates...
          </div>
        ) : ranking.length === 0 ? (
          <div className="py-16 text-center text-text-muted text-sm">
            No candidates were successfully ranked for this analysis. Check excluded files below.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-bg-secondary text-text-secondary text-xs uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3">Rank</th>
                  <th className="px-4 py-3">Candidate Identifier</th>
                  <th className="px-4 py-3">Overall Match Score</th>
                  <th className="px-4 py-3">Required Skill Coverage</th>
                  <th className="px-4 py-3">Relevant Experience</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {ranking.map((item) => (
                  <tr
                    key={item.candidate_id}
                    onClick={() => handleOpenCandidate(item.candidate_id)}
                    className="hover:bg-bg-secondary/60 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3.5 font-bold text-text-primary text-base">
                      #{item.rank}
                    </td>
                    <td className="px-4 py-3.5 font-semibold text-text-primary flex items-center space-x-2">
                      <div className="w-7 h-7 bg-bg-secondary rounded-full flex items-center justify-center text-text-muted">
                        <UserCheck className="w-4 h-4" />
                      </div>
                      <span>{item.label}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center space-x-2.5">
                        <div className="w-24 bg-bg-secondary h-2 rounded-full overflow-hidden border border-border">
                          <div
                            className="bg-primary h-full rounded-full"
                            style={{ width: `${Math.min(item.match_score, 100)}%` }}
                          />
                        </div>
                        <span className="font-bold text-text-primary">
                          {item.match_score.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-xs">
                      {item.required_skill_coverage.value !== null ? (
                        <span className="font-medium text-text-secondary">
                          {item.required_skill_coverage.value.toFixed(0)}% coverage
                        </span>
                      ) : (
                        <span className="text-text-muted">Not specified</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-xs">
                      {item.relevant_experience.value !== null ? (
                        <span className="font-medium text-text-secondary">
                          {item.relevant_experience.value.toFixed(0)}% score
                        </span>
                      ) : (
                        <span className="text-text-muted">Not specified</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenCandidate(item.candidate_id);
                        }}
                        className="space-x-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View Evaluation</span>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Excluded & Needs Review Files Section */}
      {excludedFiles.length > 0 && (
        <Card
          title={`Excluded & Needs-Review Files (${excludedFiles.length})`}
          subtitle="Files that failed extraction or required manual recruiter inspection"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-bg-secondary text-text-secondary font-semibold uppercase">
                <tr>
                  <th className="px-4 py-2.5">File Name</th>
                  <th className="px-4 py-2.5">Outcome Category</th>
                  <th className="px-4 py-2.5">Diagnostic Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {excludedFiles.map((f) => (
                  <tr key={f.resume_id} className="hover:bg-bg-secondary/40">
                    <td className="px-4 py-3 font-medium text-text-primary flex items-center space-x-2">
                      <FileQuestion className="w-4 h-4 text-text-muted shrink-0" />
                      <span>{f.filename}</span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={f.status} />
                    </td>
                    <td className="px-4 py-3 text-text-muted">
                      {f.reason_code ? (
                        <span className="font-mono text-[11px] bg-bg-page px-1.5 py-0.5 rounded border border-border">
                          {f.reason_code}
                        </span>
                      ) : (
                        <span>{f.message || 'Extraction incomplete'}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Candidate Detail Drawer */}
      <CandidateDetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        analysisId={analysisId}
        candidateId={selectedCandidateId}
      />

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={isDeleteModalOpen}
        analysis={{ id: analysisId, name: analysisName || analysisId }}
        onConfirm={handleDelete}
        onCancel={() => setIsDeleteModalOpen(false)}
        isDeleting={isDeleting}
      />
    </div>
  );
}
