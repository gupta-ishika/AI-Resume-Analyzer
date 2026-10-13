import React, { useState } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';

export function App() {
  const [currentView, setCurrentView] = useState('dashboard');

  return (
    <div className="min-h-screen bg-bg-page flex flex-col font-sans">
      <Header />
      <div className="flex-1 flex">
        <Sidebar currentView={currentView} setCurrentView={setCurrentView} />
        <main className="flex-1 p-8">
          <div className="max-w-[1280px] mx-auto">
            {currentView === 'dashboard' && (
              <Dashboard onNewAnalysis={() => setCurrentView('new_analysis')} />
            )}
            {currentView === 'new_analysis' && (
              <div className="bg-bg-surface border border-border rounded-lg p-6">
                <h2 className="text-xl font-bold text-text-primary mb-2">Create New Analysis</h2>
                <p className="text-sm text-text-secondary">
                  Job Description upload & requirement extraction flow (configured in Phase 2 & 6).
                </p>
              </div>
            )}
            {currentView === 'saved_analyses' && (
              <div className="bg-bg-surface border border-border rounded-lg p-6">
                <h2 className="text-xl font-bold text-text-primary mb-2">Saved Analyses</h2>
                <p className="text-sm text-text-secondary">
                  Historical analyses and candidate evaluations.
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
