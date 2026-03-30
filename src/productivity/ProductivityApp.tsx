import { useState } from 'react';
import { Tab } from './types';
import BottomNav from './components/BottomNav';
import Dashboard from './components/Dashboard';
import TaskManager from './components/TaskManager';
import FocusTimer from './components/FocusTimer';
import Notes from './components/Notes';
import HabitTracker from './components/HabitTracker';

export default function ProductivityApp() {
  const [tab, setTab] = useState<Tab>('home');

  const titles: Record<Tab, string> = {
    home:   '',
    tasks:  'Tasks',
    focus:  'Focus Timer',
    notes:  'Notes',
    habits: 'Habits',
  };

  return (
    <div className="flex flex-col min-h-screen bg-white max-w-md mx-auto relative">
      {/* Desktop hint */}
      <div className="hidden md:flex fixed top-0 left-0 right-0 bg-indigo-600 text-white text-center text-xs py-2 z-50">
        📱 Best experienced on a mobile device — add to home screen for the full app feel!
      </div>

      {/* Top bar (non-home tabs) */}
      {tab !== 'home' && (
        <header className="sticky top-0 bg-white border-b border-gray-100 z-40 px-4 py-3"
                style={{ paddingTop: 'max(12px, env(safe-area-inset-top, 12px))' }}>
          <h1 className="text-lg font-bold text-gray-800">{titles[tab]}</h1>
        </header>
      )}

      {/* Content */}
      <main className="flex-1 overflow-y-auto pb-20"
            style={{ paddingTop: tab === 'home' ? 'env(safe-area-inset-top, 0px)' : undefined }}>
        {tab === 'home'   && <Dashboard onNavigate={setTab} />}
        {tab === 'tasks'  && <TaskManager />}
        {tab === 'focus'  && <FocusTimer />}
        {tab === 'notes'  && <Notes />}
        {tab === 'habits' && <HabitTracker />}
      </main>

      <BottomNav active={tab} onChange={setTab} />
    </div>
  );
}
