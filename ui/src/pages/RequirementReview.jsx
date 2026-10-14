import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  Plus,
  X,
  Save,
  ArrowRight,
  ArrowLeft,
  Check,
  Clock,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { apiClient } from '../api/client';

export function RequirementReview({
  analysisId,
  analysisName,
  initialRequirements,
  needsManualInput,
  onProceedToUpload,
  onBack,
}) {
  const [requirements, setRequirements] = useState(
    initialRequirements || {
      required_skills: [],
      preferred_skills: [],
      experience_requirements: [],
      education_requirements: [],
      explicit_requirements: [],
    }
  );

  const [newRequiredSkill, setNewRequiredSkill] = useState('');
  const [newPreferredSkill, setNewPreferredSkill] = useState('');
  const [newExperience, setNewExperience] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [confirmedAt, setConfirmedAt] = useState(
    initialRequirements?.confirmed_at || null
  );

  useEffect(() => {
    if (!initialRequirements) {
      setLoading(true);
      apiClient
        .getRequirements(analysisId)
        .then((data) => {
          setRequirements(data);
          setConfirmedAt(data.confirmed_at);
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [analysisId, initialRequirements]);

  // Skill Handlers
  const addRequiredSkill = (e) => {
    e.preventDefault();
    if (!newRequiredSkill.trim()) return;
    const skill = newRequiredSkill.trim();
    if (!requirements.required_skills.includes(skill)) {
      setRequirements({
        ...requirements,
        required_skills: [...requirements.required_skills, skill],
      });
    }
    setNewRequiredSkill('');
  };

  const removeRequiredSkill = (skillToRemove) => {
    setRequirements({
      ...requirements,
      required_skills: requirements.required_skills.filter((s) => s !== skillToRemove),
    });
  };

  const addPreferredSkill = (e) => {
    e.preventDefault();
    if (!newPreferredSkill.trim()) return;
    const skill = newPreferredSkill.trim();
    if (!requirements.preferred_skills.includes(skill)) {
      setRequirements({
        ...requirements,
        preferred_skills: [...requirements.preferred_skills, skill],
      });
    }
    setNewPreferredSkill('');
  };

  const removePreferredSkill = (skillToRemove) => {
    setRequirements({
      ...requirements,
      preferred_skills: requirements.preferred_skills.filter((s) => s !== skillToRemove),
    });
  };

  const addExperience = (e) => {
    e.preventDefault();
    if (!newExperience.trim()) return;
    setRequirements({
      ...requirements,
      experience_requirements: [
        ...requirements.experience_requirements,
        newExperience.trim(),
      ],
    });
    setNewExperience('');
  };

  const removeExperience = (indexToRemove) => {
    setRequirements({
      ...requirements,
      experience_requirements: requirements.experience_requirements.filter(
        (_, i) => i !== indexToRemove
      ),
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await apiClient.updateRequirements(analysisId, requirements);
      setRequirements(updated);
      setSuccessMessage('Requirements saved successfully.');
    } catch (err) {
      setError(err.message || 'Failed to save requirements.');
    } finally {
      setSaving(false);
    }
  };

  const handleConfirm = async () => {
    if (requirements.required_skills.length === 0) {
      setError('Please add at least one required skill before confirming requirements.');
      return;
    }

    setConfirming(true);
    setError(null);
    try {
      // Auto-save changes first
      await apiClient.updateRequirements(analysisId, requirements);
      const confirmed = await apiClient.confirmRequirements(analysisId);
      setConfirmedAt(confirmed.confirmed_at);
      setSuccessMessage('Requirements confirmed! Unlocked resume upload.');
      setTimeout(() => {
        onProceedToUpload(analysisId);
      }, 700);
    } catch (err) {
      setError(err.message || 'Failed to confirm requirements.');
    } finally {
      setConfirming(false);
    }
  };

  const isConfirmed = Boolean(confirmedAt);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-2xl font-bold text-text-primary">
              Review Job Requirements
            </h2>
            {isConfirmed ? (
              <Badge variant="success" className="flex items-center space-x-1">
                <Check className="w-3 h-3" />
                <span>Confirmed</span>
              </Badge>
            ) : (
              <Badge variant="warning">Draft / Pending Confirmation</Badge>
            )}
          </div>
          <p className="text-sm text-text-secondary mt-1">
            Analysis: <strong className="text-text-primary">{analysisName || analysisId}</strong>
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button variant="secondary" onClick={onBack} disabled={confirming}>
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            <span>Back</span>
          </Button>
          {isConfirmed ? (
            <Button onClick={() => onProceedToUpload(analysisId)}>
              <span>Proceed to Resume Upload</span>
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          ) : (
            <Button
              onClick={handleConfirm}
              disabled={confirming || requirements.required_skills.length === 0}
              className="space-x-1.5"
            >
              <Check className="w-4 h-4" />
              <span>{confirming ? 'Confirming...' : 'Confirm Requirements'}</span>
            </Button>
          )}
        </div>
      </div>

      {/* Manual Input or Insufficient Warning */}
      {needsManualInput && !isConfirmed && (
        <div className="p-4 bg-status-warning-bg border border-amber-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-status-warning shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-text-primary">
              Manual Requirement Review Recommended
            </p>
            <p className="text-text-secondary mt-0.5">
              The job description did not clearly distinguish between required and preferred qualifications.
              Please inspect the tags below, add missing skills, and confirm criteria before proceeding.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-status-error-bg text-status-error rounded-lg border border-red-200 text-sm">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="p-4 bg-status-success-bg text-status-success rounded-lg border border-green-200 text-sm flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* 1. Required Skills */}
      <Card
        title="Required Skills (Core Qualifications)"
        subtitle="Mandatory technical competencies. Candidate coverage directly impacts the required-skill score component."
      >
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 min-h-12 p-3 bg-bg-page rounded-md border border-border">
            {requirements.required_skills.length === 0 ? (
              <span className="text-xs text-status-error italic">
                No required skills identified. At least one required skill must be added.
              </span>
            ) : (
              requirements.required_skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center space-x-1.5 px-3 py-1 bg-white border border-border rounded-full text-xs font-semibold text-text-primary shadow-2xs"
                >
                  <span>{skill}</span>
                  {!isConfirmed && (
                    <button
                      type="button"
                      onClick={() => removeRequiredSkill(skill)}
                      className="text-text-muted hover:text-status-error cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </span>
              ))
            )}
          </div>

          {!isConfirmed && (
            <form onSubmit={addRequiredSkill} className="flex gap-2">
              <input
                type="text"
                value={newRequiredSkill}
                onChange={(e) => setNewRequiredSkill(e.target.value)}
                placeholder="Add required skill (e.g. Python, Docker, PostgreSQL)..."
                className="flex-1 px-3 py-2 text-xs bg-bg-surface border border-border rounded-md text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <Button type="submit" size="sm" variant="secondary" className="space-x-1">
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </Button>
            </form>
          )}
        </div>
      </Card>

      {/* 2. Preferred Skills */}
      <Card
        title="Preferred Skills (Bonus Qualifications)"
        subtitle="Optional skills that boost match scores if demonstrated by candidates."
      >
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 min-h-12 p-3 bg-bg-page rounded-md border border-border">
            {requirements.preferred_skills.length === 0 ? (
              <span className="text-xs text-text-muted italic">
                No preferred skills specified.
              </span>
            ) : (
              requirements.preferred_skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center space-x-1.5 px-3 py-1 bg-primary-light border border-indigo-200 rounded-full text-xs font-medium text-primary shadow-2xs"
                >
                  <span>{skill}</span>
                  {!isConfirmed && (
                    <button
                      type="button"
                      onClick={() => removePreferredSkill(skill)}
                      className="text-primary/70 hover:text-status-error cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </span>
              ))
            )}
          </div>

          {!isConfirmed && (
            <form onSubmit={addPreferredSkill} className="flex gap-2">
              <input
                type="text"
                value={newPreferredSkill}
                onChange={(e) => setNewPreferredSkill(e.target.value)}
                placeholder="Add preferred skill (e.g. Kubernetes, GraphQL, AWS)..."
                className="flex-1 px-3 py-2 text-xs bg-bg-surface border border-border rounded-md text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <Button type="submit" size="sm" variant="secondary" className="space-x-1">
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </Button>
            </form>
          )}
        </div>
      </Card>

      {/* 3. Experience Requirements */}
      <Card
        title="Experience Criteria"
        subtitle="Identified role responsibilities and required years of relevant experience."
      >
        <div className="space-y-3">
          {requirements.experience_requirements.length === 0 ? (
            <p className="text-xs text-text-muted italic p-3 bg-bg-page rounded">
              No specific experience years extracted.
            </p>
          ) : (
            requirements.experience_requirements.map((exp, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 bg-bg-page border border-border rounded text-xs text-text-primary"
              >
                <span>{exp}</span>
                {!isConfirmed && (
                  <button
                    type="button"
                    onClick={() => removeExperience(idx)}
                    className="text-text-muted hover:text-status-error cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))
          )}

          {!isConfirmed && (
            <form onSubmit={addExperience} className="flex gap-2 pt-2">
              <input
                type="text"
                value={newExperience}
                onChange={(e) => setNewExperience(e.target.value)}
                placeholder="e.g. 3+ years of professional backend software engineering..."
                className="flex-1 px-3 py-2 text-xs bg-bg-surface border border-border rounded-md text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <Button type="submit" size="sm" variant="secondary" className="space-x-1">
                <Plus className="w-3.5 h-3.5" />
                <span>Add Criterion</span>
              </Button>
            </form>
          )}
        </div>
      </Card>

      {/* Bottom Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-border">
        <div>
          {isConfirmed && confirmedAt && (
            <span className="text-xs text-text-muted flex items-center space-x-1">
              <Clock className="w-3.5 h-3.5 inline" />
              <span>Confirmed at: {new Date(confirmedAt).toLocaleString()}</span>
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {!isConfirmed && (
            <Button
              variant="secondary"
              onClick={handleSave}
              disabled={saving || confirming}
              className="space-x-1.5"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Saving...' : 'Save Draft'}</span>
            </Button>
          )}

          {isConfirmed ? (
            <Button onClick={() => onProceedToUpload(analysisId)}>
              <span>Proceed to Resume Upload</span>
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          ) : (
            <Button
              onClick={handleConfirm}
              disabled={confirming || requirements.required_skills.length === 0}
              className="space-x-1.5"
            >
              <Check className="w-4 h-4" />
              <span>{confirming ? 'Confirming...' : 'Confirm & Proceed to Upload'}</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
