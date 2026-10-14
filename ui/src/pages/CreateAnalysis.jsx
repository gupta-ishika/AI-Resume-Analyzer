import React, { useState } from 'react';
import { FileText, Upload, ArrowRight, AlertCircle, FileUp } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { apiClient } from '../api/client';

export function CreateAnalysis({ onAnalysisCreated, onCancel }) {
  const [name, setName] = useState('');
  const [activeTab, setActiveTab] = useState('paste'); // 'paste' | 'upload'
  const [jdText, setJdText] = useState('');
  const [jdFile, setJdFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (activeTab === 'paste' && !jdText.trim()) {
      setError('Please paste or type the job description text.');
      return;
    }

    if (activeTab === 'upload' && !jdFile) {
      setError('Please select a job description file (.pdf, .docx, or .txt).');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.createAnalysis({
        name: name.trim() || undefined,
        jd_text: activeTab === 'paste' ? jdText : undefined,
        jd_file: activeTab === 'upload' ? jdFile : undefined,
      });

      onAnalysisCreated(response);
    } catch (err) {
      setError(err.message || 'Failed to create analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Create New Analysis</h2>
          <p className="text-sm text-text-secondary mt-1">
            Provide a Job Description to extract structured candidate requirements.
          </p>
        </div>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-status-error-bg text-status-error rounded-lg border border-red-200 text-sm flex items-start space-x-2">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card title="1. Analysis Information">
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase mb-1.5">
              Analysis Name (Optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Senior Backend Engineer - Q4 Hiring"
              className="w-full px-3.5 py-2.5 text-sm bg-bg-surface border border-border rounded-md text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
            />
            <p className="text-xs text-text-muted mt-1.5">
              If omitted, a name will be automatically derived from the job title.
            </p>
          </div>
        </Card>

        <Card title="2. Job Description Input">
          {/* Tab Selector */}
          <div className="flex border-b border-border mb-4">
            <button
              type="button"
              onClick={() => setActiveTab('paste')}
              className={`px-4 py-2 text-sm font-medium border-b-2 cursor-pointer transition-colors ${
                activeTab === 'paste'
                  ? 'border-primary text-primary font-semibold'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4" />
                <span>Paste Text</span>
              </div>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('upload')}
              className={`px-4 py-2 text-sm font-medium border-b-2 cursor-pointer transition-colors ${
                activeTab === 'upload'
                  ? 'border-primary text-primary font-semibold'
                  : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <div className="flex items-center space-x-2">
                <FileUp className="w-4 h-4" />
                <span>Upload Document</span>
              </div>
            </button>
          </div>

          {activeTab === 'paste' ? (
            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase mb-1.5">
                Job Description Content
              </label>
              <textarea
                rows={10}
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the complete job description here, including responsibilities, required skills, preferred qualifications, and experience expectations..."
                className="w-full px-3.5 py-2.5 text-sm bg-bg-surface border border-border rounded-md text-text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary font-mono text-xs"
              />
            </div>
          ) : (
            <div className="space-y-4">
              <label className="block text-xs font-semibold text-text-secondary uppercase mb-1.5">
                Upload File (PDF, DOCX, or TXT)
              </label>
              <div className="border-2 border-dashed border-border rounded-lg p-8 text-center bg-bg-page hover:bg-bg-secondary/50 transition-colors">
                <Upload className="w-8 h-8 text-text-muted mx-auto mb-2" />
                <p className="text-sm font-medium text-text-primary">
                  {jdFile ? jdFile.name : 'Choose a file or drag and drop'}
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Supported formats: PDF, DOCX, TXT (Max 10MB)
                </p>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => setJdFile(e.target.files[0] || null)}
                  className="hidden"
                  id="jd-file-input"
                />
                <div className="mt-4">
                  <label
                    htmlFor="jd-file-input"
                    className="inline-flex items-center px-4 py-2 text-xs font-medium rounded border border-border bg-white text-text-primary hover:bg-bg-secondary cursor-pointer shadow-sm"
                  >
                    Browse Files
                  </label>
                </div>
              </div>
              <p className="text-xs text-text-muted">
                Note: Uploaded job description files are parsed and deleted immediately from storage per system privacy rules.
              </p>
            </div>
          )}
        </Card>

        <div className="flex items-center justify-end space-x-3">
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading} className="space-x-2">
            <span>{loading ? 'Extracting Requirements...' : 'Continue to Requirement Review'}</span>
            <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
