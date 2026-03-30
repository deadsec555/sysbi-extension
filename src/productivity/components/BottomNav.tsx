import { Tab } from '../types';

interface Props {
  active: Tab;
  onChange: (t: Tab) => void;
}

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: 'home',   label: 'Home',   icon: '🏠' },
  { id: 'tasks',  label: 'Tasks',  icon: '✅' },
  { id: 'focus',  label: 'Focus',  icon: '⏱️' },
  { id: 'notes',  label: 'Notes',  icon: '📝' },
  { id: 'habits', label: 'Habits', icon: '🎯' },
];

export default function BottomNav({ active, onChange }: Props) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex justify-around items-center bg-white border-t border-gray-200 safe-bottom"
         style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex flex-col items-center py-2 px-3 min-w-0 flex-1 transition-colors ${
            active === t.id ? 'text-indigo-600' : 'text-gray-400'
          }`}
        >
          <span className="text-xl leading-none">{t.icon}</span>
          <span className={`text-[10px] mt-0.5 font-medium ${active === t.id ? 'text-indigo-600' : 'text-gray-400'}`}>
            {t.label}
          </span>
          {active === t.id && (
            <span className="absolute top-0 h-0.5 w-8 bg-indigo-500 rounded-b-full" />
          )}
        </button>
      ))}
    </nav>
  );
}
