import React, { useState, useEffect } from 'react';
import {
  X,
  User,
  Mail,
  Phone,
  Briefcase,
  GraduationCap,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  Award,
  Layers,
} from 'lucide-react';
import { Button } from './common/Button';
import { Badge, StatusBadge } from './common/Badge';
import { apiClient } from '../api/client';

export function CandidateDetailDrawer({
  isOpen,
  onClose,
  analysisId,
  candidateId,
}) {
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [explanationState, setExplanationState] = useState('NOT_REQUESTED');
  const [explanationData, setExplanationData] = useState(null);
  const [explanationFailure, setExplanationFailure] = useState(null);
  const [requestingExplanation, setRequestingExplanation] = useState(false);

  useEffect(() => {
    if (!isOpen || !analysisId || !candidateId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    apiClient
      .getCandidateDetail(analysisId, candidateId)
      .then((data) => {
        if (!isMounted) return;
        setCandidate(data);
        if (data.explanation) {
          setExplanationState(data.explanation.state);
          setExplanationData(data.explanation.explanation);
          setExplanationFailure(data.explanation.failure_reason);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to load candidate details.');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, analysisId, candidateId]);

  // Polling for explanation if in GENERATING state
  useEffect(() => {
    if (explanationState !== 'GENERATING' || !isOpen || !analysisId || !candidateId) {
      return;
    }

    const interval = setInterval(() => {
      apiClient
        .getExplanation(analysisId, candidateId)
        .then((res) => {
          setExplanationState(res.state);
          if (res.state === 'READY') {
            setExplanationData(res.explanation);
            setExplanationFailure(null);
          } else if (res.state === 'FAILED') {
            setExplanationFailure(res.failure_reason);
          }
        })
        .catch(() => {});
    }, 2000);

    return () => clearInterval(interval);
  }, [explanationState, isOpen, analysisId, candidateId]);

  const handleRequestExplanation = async () => {
    setRequestingExplanation(true);
    try {
      const res = await apiClient.requestExplanation(analysisId, candidateId);
      setExplanationState(res.state);
      if (res.state === 'READY') {
        setExplanationData(res.explanation);
      }
    } catch (err) {
      setExplanationState('FAILED');
      setExplanationFailure(err.message);
    } finally {
      setRequestingExplanation(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-bg-surface h-full shadow-2xl flex flex-col border-l border-border animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between bg-bg-surface sticky top-0 z-10">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-primary-light text-primary rounded-lg">
              <User className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold text-text-primary">
                  {candidate?.label || 'Candidate Details'}
                </h3>
                {candidate?.rank && (
                  <Badge variant="info">Rank #{candidate.rank}</Badge>
                )}
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Comprehensive Evaluation & Matching Breakdown
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-text-muted hover:text-text-primary rounded hover:bg-bg-secondary cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-20 text-center">
              <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto mb-3" />
              <p className="text-sm text-text-muted">Loading candidate evaluation...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-status-error-bg text-status-error rounded-lg border border-red-200 text-sm">
              {error}
            </div>
          ) : candidate ? (
            <>
              {/* BLOCK 1: Candidate Identity */}
              <div className="bg-bg-secondary/60 border border-border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center space-x-1.5">
                    <User className="w-4 h-4 text-text-secondary" />
                    <span>Candidate Identity (Restricted Recruiter View)</span>
                  </h4>
                  <span className="text-[11px] text-text-muted bg-white px-2 py-0.5 rounded border border-border">
                    Hidden from ranking table
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-xs text-text-muted block">Full Name</span>
                    <span className="font-semibold text-text-primary">
                      {candidate.identity.name || 'Not provided'}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-text-muted block">Email</span>
                    <span className="text-text-primary flex items-center space-x-1">
                      <Mail className="w-3.5 h-3.5 text-text-muted inline" />
                      <span>{candidate.identity.contact.email || 'None'}</span>
                    </span>
                  </div>
                  {candidate.identity.contact.phone && (
                    <div>
                      <span className="text-xs text-text-muted block">Phone</span>
                      <span className="text-text-primary flex items-center space-x-1">
                        <Phone className="w-3.5 h-3.5 text-text-muted inline" />
                        <span>{candidate.identity.contact.phone}</span>
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* BLOCK 3: Matching Results (Evidence First) */}
              <div className="border border-border rounded-lg p-5 bg-white space-y-5">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-text-primary flex items-center space-x-2">
                    <Award className="w-4 h-4 text-primary" />
                    <span>Deterministic Match Results</span>
                  </h4>
                  <div className="text-right">
                    <span className="text-2xl font-extrabold text-primary">
                      {candidate.matching.match_score.toFixed(1)}%
                    </span>
                    <span className="text-xs text-text-muted block">Overall Match</span>
                  </div>
                </div>

                {/* Score Breakdown Grid */}
                <div className="grid grid-cols-2 gap-3 text-xs bg-bg-page p-3.5 rounded border border-border">
                  <div>
                    <span className="text-text-muted block">Required Skills Coverage</span>
                    <span className="font-semibold text-text-primary text-sm">
                      {candidate.matching.breakdown.required_skill_coverage.value !== null
                        ? `${candidate.matching.breakdown.required_skill_coverage.value.toFixed(0)}%`
                        : 'Not Specified'}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-muted block">Relevant Experience</span>
                    <span className="font-semibold text-text-primary text-sm">
                      {candidate.matching.breakdown.relevant_experience.value !== null
                        ? `${candidate.matching.breakdown.relevant_experience.value.toFixed(0)}%`
                        : 'Not Specified'}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-muted block">Semantic Relevance</span>
                    <span className="font-semibold text-text-primary text-sm">
                      {candidate.matching.breakdown.semantic_relevance.value !== null
                        ? `${candidate.matching.breakdown.semantic_relevance.value.toFixed(0)}%`
                        : 'Not Specified'}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-muted block">Preferred Skills</span>
                    <span className="font-semibold text-text-primary text-sm">
                      {candidate.matching.breakdown.preferred_skill_coverage.value !== null
                        ? `${candidate.matching.breakdown.preferred_skill_coverage.value.toFixed(0)}%`
                        : 'Not Specified'}
                    </span>
                  </div>
                </div>

                {/* Required Skills Match Evidence */}
                <div>
                  <h5 className="text-xs font-bold text-text-secondary uppercase mb-2">
                    Required Skills Evidence
                  </h5>
                  <div className="space-y-2">
                    <div>
                      <span className="text-xs text-status-success font-medium block mb-1">
                        Matched Required ({candidate.matching.required_skills.matched.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {candidate.matching.required_skills.matched.length > 0 ? (
                          candidate.matching.required_skills.matched.map((s) => (
                            <Badge key={s} variant="success">
                              ✓ {s}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-text-muted">None matched</span>
                        )}
                      </div>
                    </div>

                    {candidate.matching.required_skills.missing.length > 0 && (
                      <div>
                        <span className="text-xs text-status-error font-medium block mb-1">
                          Missing Required ({candidate.matching.required_skills.missing.length})
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {candidate.matching.required_skills.missing.map((s) => (
                            <Badge key={s} variant="error">
                              ✕ {s}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Preferred Skills */}
                {candidate.matching.preferred_skills.matched.length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-text-secondary uppercase mb-1.5">
                      Matched Preferred Skills
                    </h5>
                    <div className="flex flex-wrap gap-1.5">
                      {candidate.matching.preferred_skills.matched.map((s) => (
                        <Badge key={s} variant="info">
                          + {s}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Experience Evidence */}
                {candidate.matching.experience_evidence.length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-text-secondary uppercase mb-2">
                      Experience Evidence
                    </h5>
                    <div className="space-y-1.5">
                      {candidate.matching.experience_evidence.map((ev, i) => (
                        <div
                          key={i}
                          className="text-xs text-text-secondary bg-bg-page p-2.5 rounded border border-border flex items-start space-x-2"
                        >
                          <CheckCircle2 className="w-4 h-4 text-status-success shrink-0 mt-0.5" />
                          <span>{ev.summary}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* BLOCK 4: AI Explanation (Secondary & Grounded) */}
              <div className="border border-border rounded-lg p-5 bg-bg-surface space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="p-1.5 bg-primary-light text-primary rounded">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-text-primary">
                        AI Decision Support Explanation
                      </h4>
                      <p className="text-[11px] text-text-muted">
                        Evidence-grounded qualitative synthesis by local Ollama
                      </p>
                    </div>
                  </div>
                  <StatusBadge status={explanationState} />
                </div>

                {explanationState === 'NOT_REQUESTED' && (
                  <div className="bg-bg-page p-4 rounded border border-border text-center">
                    <p className="text-xs text-text-secondary mb-3">
                      Generate an AI-powered analysis of candidate strengths, qualifications alignment,
                      and potential gaps without impacting scores or ranks.
                    </p>
                    <Button
                      size="sm"
                      onClick={handleRequestExplanation}
                      disabled={requestingExplanation}
                      className="space-x-1.5"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{requestingExplanation ? 'Queuing...' : 'Generate AI Explanation'}</span>
                    </Button>
                  </div>
                )}

                {explanationState === 'GENERATING' && (
                  <div className="bg-status-info-bg p-5 rounded border border-blue-200 text-center">
                    <RefreshCw className="w-6 h-6 text-status-info animate-spin mx-auto mb-2" />
                    <p className="text-xs font-semibold text-text-primary">
                      Synthesizing qualitative explanation...
                    </p>
                    <p className="text-[11px] text-text-muted mt-1">
                      Extracting grounded insights via local LLM. This typically takes 5–15 seconds.
                    </p>
                  </div>
                )}

                {explanationState === 'FAILED' && (
                  <div className="bg-status-error-bg p-4 rounded border border-red-200 space-y-3">
                    <div className="flex items-start space-x-2 text-xs text-status-error">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold block">Explanation Generation Failed</span>
                        <span>{explanationFailure || 'Failed to generate grounded explanation.'}</span>
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleRequestExplanation}
                      disabled={requestingExplanation}
                      className="text-xs"
                    >
                      <RefreshCw className="w-3 h-3 mr-1.5" />
                      Retry Generation
                    </Button>
                  </div>
                )}

                {explanationState === 'READY' && explanationData && (
                  <div className="space-y-4 pt-2 text-xs">
                    {/* Strengths */}
                    {explanationData.strengths?.length > 0 && (
                      <div>
                        <span className="font-bold text-text-primary block mb-1.5 flex items-center space-x-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-status-success" />
                          <span>Candidate Strengths</span>
                        </span>
                        <ul className="list-disc list-inside space-y-1 text-text-secondary pl-1">
                          {explanationData.strengths.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Gaps */}
                    {explanationData.gaps?.length > 0 && (
                      <div>
                        <span className="font-bold text-text-primary block mb-1.5 flex items-center space-x-1">
                          <AlertCircle className="w-3.5 h-3.5 text-status-warning" />
                          <span>Identified Gaps</span>
                        </span>
                        <ul className="list-disc list-inside space-y-1 text-text-secondary pl-1">
                          {explanationData.gaps.map((g, i) => (
                            <li key={i}>{g}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Experience Alignment */}
                    {explanationData.experience_alignment && (
                      <div>
                        <span className="font-bold text-text-primary block mb-1">
                          Experience Alignment
                        </span>
                        <p className="text-text-secondary bg-bg-page p-2.5 rounded border border-border leading-relaxed">
                          {explanationData.experience_alignment}
                        </p>
                      </div>
                    )}

                    {/* Assessment */}
                    {explanationData.assessment && (
                      <div>
                        <span className="font-bold text-text-primary block mb-1">
                          Overall Analytical Assessment
                        </span>
                        <p className="text-text-secondary bg-bg-page p-2.5 rounded border border-border leading-relaxed">
                          {explanationData.assessment}
                        </p>
                      </div>
                    )}

                    <div className="pt-2 border-t border-border flex items-center justify-between text-[11px] text-text-muted">
                      <span>Grounded Output • Factual Evidence Only</span>
                      <span>No regeneration permitted once generated</span>
                    </div>
                  </div>
                )}
              </div>

              {/* BLOCK 2: Extracted Structured Profile */}
              <div className="border border-border rounded-lg p-5 bg-white space-y-4">
                <h4 className="text-sm font-bold text-text-primary flex items-center space-x-2">
                  <Layers className="w-4 h-4 text-text-secondary" />
                  <span>Extracted Structured Data</span>
                </h4>

                {/* Skills */}
                <div>
                  <span className="text-xs font-semibold text-text-muted uppercase block mb-1.5">
                    Extracted Candidate Skills ({candidate.extracted.skills.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {candidate.extracted.skills.map((s) => (
                      <Badge key={s} variant="neutral">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Work Experience */}
                {candidate.extracted.experience?.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-text-muted uppercase block mb-2">
                      Work Experience
                    </span>
                    <div className="space-y-3">
                      {candidate.extracted.experience.map((exp, idx) => (
                        <div key={idx} className="bg-bg-page p-3 rounded border border-border text-xs">
                          <div className="flex justify-between items-start">
                            <span className="font-bold text-text-primary text-sm">
                              {exp.title || 'Role'}
                            </span>
                            <span className="text-text-muted">
                              {exp.duration || (exp.duration_months ? `${(exp.duration_months / 12).toFixed(1)} yrs` : '')}
                            </span>
                          </div>
                          {exp.company && (
                            <span className="text-text-secondary block mt-0.5">{exp.company}</span>
                          )}
                          {exp.responsibilities?.length > 0 && (
                            <ul className="list-disc list-inside mt-2 space-y-0.5 text-text-secondary">
                              {exp.responsibilities.slice(0, 3).map((r, i) => (
                                <li key={i}>{r}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
