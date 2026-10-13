import React from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { StatusBadge } from '../components/common/Badge';
import { PlusCircle, FileText, CheckCircle2, Clock } from 'lucide-react';

export function Dashboard({ onNewAnalysis }) {
  // Initial placeholder data / empty state
  const recentAnalyses = [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Recruiter Dashboard</h2>
          <p className="text-sm text-text-secondary mt-1">
            Compare, evaluate, and rank candidate resumes against structured job requirements.
          </p>
        </div>
        <Button onClick={onNewAnalysis} className="flex items-center space-x-2">
          <PlusCircle className="w-4 h-4" />
          <span>New Analysis</span>
        </Button>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Card className="flex items-center space-x-4">
          <div className="p-3 bg-primary-light rounded-lg text-primary">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-text-muted">Total Analyses</p>
            <p className="text-2xl font-bold text-text-primary mt-0.5">0</p>
          </div>
        </Card>

        <Card className="flex items-center space-x-4">
          <div className="p-3 bg-status-success-bg rounded-lg text-status-success">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-text-muted">Ranked Candidates</p>
            <p className="text-2xl font-bold text-text-primary mt-0.5">0</p>
          </div>
        </Card>

        <Card className="flex items-center space-x-4">
          <div className="p-3 bg-status-info-bg rounded-lg text-status-info">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-text-muted">Active Processing</p>
            <p className="text-2xl font-bold text-text-primary mt-0.5">0</p>
          </div>
        </Card>
      </div>

      {/* Recent Analyses Section */}
      <Card
        title="Recent Analyses"
        subtitle="Manage previous candidate evaluations and ranking outcomes"
      >
        {recentAnalyses.length === 0 ? (
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
              <thead className="bg-bg-secondary text-text-secondary text-xs uppercase font-medium">
                <tr>
                  <th className="px-4 py-3">Analysis Name</th>
                  <th className="px-4 py-3">Candidates</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Updated</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {recentAnalyses.map((item) => (
                  <tr key={item.id} className="hover:bg-bg-secondary/50">
                    <td className="px-4 py-3.5 font-medium text-text-primary">{item.name}</td>
                    <td className="px-4 py-3.5 text-text-secondary">{item.candidate_count}</td>
                    <td className="px-4 py-3.5">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-3.5 text-text-muted">{item.updated_at}</td>
                    <td className="px-4 py-3.5 text-right">
                      <Button variant="secondary" size="sm">
                        Open
                      </Button>
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
