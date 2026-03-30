import { useMemo } from 'react';
import { store, today } from '../store';
import { Tab } from '../types';

interface Props {
  onNavigate: (t: Tab) => void;
}

export default function Dashboard({ onNavigate }: Props) {
  const todayStr = today();

  const stats = useMemo(() => {
    const tasks   = store.getTasks();
    const habits  = store.getHabits();
    const sessions = store.getSessions();

    const todayTasks    = tasks.filter(t => t.date === todayStr);
    const doneTasks     = todayTasks.filter(t => t.done).length;
    const totalTasks    = todayTasks.length;

    const totalHabits   = habits.length;
    const doneHabits    = habits.filter(h => h.completedDates.includes(todayStr)).length;

    const focusSessions = sessions.filter(
      s => s.type === 'work' && s.completedAt.startsWith(todayStr)
    ).length;

    return { doneTasks, totalTasks, doneHabits, totalHabits, focusSessions };
  }, [todayStr]);

  const greetHour = new Date().getHours();
  const greeting = greetHour < 12 ? 'Good morning' : greetHour < 17 ? 'Good afternoon' : 'Good evening';

  const dateLabel = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
  });

  return (
    <div className="p-4 space-y-5">
      {/* Header */}
      <div className="pt-2">
        <p className="text-gray-400 text-sm">{dateLabel}</p>
        <h1 className="text-2xl font-bold text-gray-800">{greeting} 👋</h1>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard
          emoji="✅"
          label="Tasks"
          value={`${stats.doneTasks}/${stats.totalTasks}`}
          color="bg-indigo-50"
          onClick={() => onNavigate('tasks')}
        />
        <StatCard
          emoji="⏱️"
          label="Focus"
          value={`${stats.focusSessions}`}
          sub="sessions"
          color="bg-orange-50"
          onClick={() => onNavigate('focus')}
        />
        <StatCard
          emoji="🎯"
          label="Habits"
          value={`${stats.doneHabits}/${stats.totalHabits}`}
          color="bg-green-50"
          onClick={() => onNavigate('habits')}
        />
      </div>

      {/* Today's tasks preview */}
      <TodayTasks todayStr={todayStr} onNavigate={onNavigate} />

      {/* Habits preview */}
      <TodayHabits todayStr={todayStr} onNavigate={onNavigate} />
    </div>
  );
}

function StatCard({
  emoji, label, value, sub, color, onClick,
}: {
  emoji: string; label: string; value: string; sub?: string;
  color: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`${color} rounded-2xl p-3 text-left active:scale-95 transition-transform`}
    >
      <div className="text-2xl mb-1">{emoji}</div>
      <div className="text-xl font-bold text-gray-800 leading-none">{value}</div>
      {sub && <div className="text-[10px] text-gray-400">{sub}</div>}
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </button>
  );
}

function TodayTasks({ todayStr, onNavigate }: { todayStr: string; onNavigate: (t: Tab) => void }) {
  const tasks = useMemo(
    () => store.getTasks().filter(t => t.date === todayStr).slice(0, 4),
    [todayStr]
  );

  return (
    <section>
      <div className="flex justify-between items-center mb-2">
        <h2 className="font-semibold text-gray-700">Today's Tasks</h2>
        <button onClick={() => onNavigate('tasks')} className="text-indigo-500 text-sm">See all</button>
      </div>
      {tasks.length === 0 ? (
        <div
          className="rounded-2xl border-2 border-dashed border-gray-200 p-4 text-center text-gray-400 text-sm"
          onClick={() => onNavigate('tasks')}
        >
          No tasks yet — tap to add one
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map(t => (
            <div key={t.id} className="flex items-center gap-3 bg-gray-50 rounded-xl px-3 py-2.5">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                t.priority === 'high' ? 'bg-red-400' :
                t.priority === 'medium' ? 'bg-yellow-400' : 'bg-green-400'
              }`} />
              <span className={`text-sm flex-1 ${t.done ? 'line-through text-gray-400' : 'text-gray-700'}`}>
                {t.title}
              </span>
              {t.done && <span className="text-green-500 text-xs">✓</span>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function TodayHabits({ todayStr, onNavigate }: { todayStr: string; onNavigate: (t: Tab) => void }) {
  const habits = useMemo(() => store.getHabits(), []);
  if (habits.length === 0) return null;

  return (
    <section>
      <div className="flex justify-between items-center mb-2">
        <h2 className="font-semibold text-gray-700">Habits</h2>
        <button onClick={() => onNavigate('habits')} className="text-indigo-500 text-sm">See all</button>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-1">
        {habits.map(h => {
          const done = h.completedDates.includes(todayStr);
          return (
            <div
              key={h.id}
              className={`flex-shrink-0 flex flex-col items-center gap-1 rounded-2xl p-3 w-16 ${
                done ? 'bg-green-100' : 'bg-gray-50'
              }`}
            >
              <span className="text-2xl">{h.emoji}</span>
              <span className={`text-[10px] text-center leading-tight ${done ? 'text-green-700' : 'text-gray-500'}`}>
                {h.name}
              </span>
              {done && <span className="text-green-500 text-xs">✓</span>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
