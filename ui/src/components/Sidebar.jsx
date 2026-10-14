import React from 'react';
import { LayoutDashboard, PlusCircle } from 'lucide-react';

export function Sidebar({ currentView, setCurrentView }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'new_analysis', label: 'New Analysis', icon: PlusCircle },
  ];

  return (
    <aside className="w-64 bg-bg-surface border-r border-border min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between">
      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 text-sm font-medium rounded-md transition-colors cursor-pointer ${
                isActive
                  ? 'bg-primary-light text-primary font-semibold'
                  : 'text-text-secondary hover:bg-bg-secondary hover:text-text-primary'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-primary' : 'text-text-muted'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="pt-4 border-t border-border text-xs text-text-muted px-2">
        <p className="font-medium text-text-secondary">Decision-Support Tool</p>
        <p className="mt-1">Assists human recruiters; does not make hiring decisions.</p>
      </div>
    </aside>
  );
}
