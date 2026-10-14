import React, { useState } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { CreateAnalysis } from './pages/CreateAnalysis';
import { RequirementReview } from './pages/RequirementReview';
import { ResumeUpload } from './pages/ResumeUpload';
import { ProcessingView } from './pages/ProcessingView';
import { RankedResults } from './pages/RankedResults';
import { apiClient } from './api/client';

export function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [initialRequirements, setInitialRequirements] = useState(null);
  const [needsManualInput, setNeedsManualInput] = useState(false);

  // Handlers for workflow navigation
  const handleStartNewAnalysis = () => {
    setActiveAnalysis(null);
    setInitialRequirements(null);
    setCurrentView('create_analysis');
  };

  const handleAnalysisCreated = (createResponse) => {
    setActiveAnalysis(createResponse.analysis);
    setInitialRequirements(createResponse.requirements);
    setNeedsManualInput(createResponse.needs_manual_input);
    setCurrentView('requirement_review');
  };

  const handleProceedToUpload = (analysisId) => {
    setCurrentView('resume_upload');
  };

  const handleStartAnalysis = (analysisId) => {
    setCurrentView('processing');
  };

  const handleProcessingCompleted = (analysisId) => {
    setCurrentView('ranked_results');
  };

  const handleOpenAnalysis = async (analysis) => {
    setActiveAnalysis(analysis);

    if (analysis.status === 'REQUIREMENTS_PENDING') {
      try {
        const reqs = await apiClient.getRequirements(analysis.id);
        setInitialRequirements(reqs);
        if (reqs.confirmed_at) {
          setCurrentView('resume_upload');
        } else {
          setCurrentView('requirement_review');
        }
      } catch (err) {
        setCurrentView('requirement_review');
      }
    } else if (analysis.status === 'PROCESSING') {
      setCurrentView('processing');
    } else if (analysis.status === 'RANKED') {
      setCurrentView('ranked_results');
    } else {
      // FAILED or other
      setCurrentView('processing');
    }
  };

  const handleReturnToDashboard = () => {
    setActiveAnalysis(null);
    setInitialRequirements(null);
    setCurrentView('dashboard');
  };

  return (
    <div className="min-h-screen bg-bg-page flex flex-col font-sans text-text-primary">
      <Header />
      <div className="flex-1 flex">
        <Sidebar
          currentView={currentView}
          setCurrentView={(view) => {
            if (view === 'dashboard') {
              handleReturnToDashboard();
            } else if (view === 'new_analysis') {
              handleStartNewAnalysis();
            }
          }}
        />

        <main className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-[1280px] mx-auto">
            {currentView === 'dashboard' && (
              <Dashboard
                onNewAnalysis={handleStartNewAnalysis}
                onOpenAnalysis={handleOpenAnalysis}
              />
            )}

            {currentView === 'create_analysis' && (
              <CreateAnalysis
                onAnalysisCreated={handleAnalysisCreated}
                onCancel={handleReturnToDashboard}
              />
            )}

            {currentView === 'requirement_review' && activeAnalysis && (
              <RequirementReview
                analysisId={activeAnalysis.id}
                analysisName={activeAnalysis.name}
                initialRequirements={initialRequirements}
                needsManualInput={needsManualInput}
                onProceedToUpload={handleProceedToUpload}
                onBack={handleReturnToDashboard}
              />
            )}

            {currentView === 'resume_upload' && activeAnalysis && (
              <ResumeUpload
                analysisId={activeAnalysis.id}
                analysisName={activeAnalysis.name}
                onStartAnalysis={handleStartAnalysis}
                onBackToRequirements={() => setCurrentView('requirement_review')}
              />
            )}

            {currentView === 'processing' && activeAnalysis && (
              <ProcessingView
                analysisId={activeAnalysis.id}
                analysisName={activeAnalysis.name}
                onCompleted={handleProcessingCompleted}
              />
            )}

            {currentView === 'ranked_results' && activeAnalysis && (
              <RankedResults
                analysisId={activeAnalysis.id}
                analysisName={activeAnalysis.name}
                onBackToDashboard={handleReturnToDashboard}
                onAnalysisDeleted={handleReturnToDashboard}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
