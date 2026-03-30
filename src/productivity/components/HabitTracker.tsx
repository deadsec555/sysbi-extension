import { useState, useEffect, useCallback } from 'react';
import { store, today, uid } from '../store';
import { Habit } from '../types';

const PRESET_EMOJIS = ['💧', '🏃', '📚', '🧘', '🥗', '😴', '💊', '✍️', '🎵', '🚶', '🧹', '📵'];

export default function HabitTracker() {
  const [habits, setHabits] = useState<Habit[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const todayStr = today();

  useEffect(() => { setHabits(store.getHabits()); }, []);

  const save = useCallback((updated: Habit[]) => {
    setHabits(updated);
    store.saveHabits(updated);
  }, []);

  const toggle = (id: string) => {
    save(habits.map(h => {
      if (h.id !== id) return h;
      const has = h.completedDates.includes(todayStr);
      return {
        ...h,
        completedDates: has
          ? h.completedDates.filter(d => d !== todayStr)
          : [...h.completedDates, todayStr],
      };
    }));
    if (navigator.vibrate) navigator.vibrate(50);
  };

  const remove = (id: string) => {
    save(habits.filter(h => h.id !== id));
  };

  const addHabit = (name: string, emoji: string) => {
    const h: Habit = { id: uid(), name, emoji, completedDates: [] };
    save([...habits, h]);
    setShowAdd(false);
  };

  const getStreak = (h: Habit): number => {
    let streak = 0;
    const d = new Date();
    while (true) {
      const dateStr = d.toISOString().slice(0, 10);
      if (!h.completedDates.includes(dateStr)) break;
      streak++;
      d.setDate(d.getDate() - 1);
    }
    return streak;
  };

  const doneCount = habits.filter(h => h.completedDates.includes(todayStr)).length;

  return (
    <div className="p-4 space-y-4">
      {/* Progress banner */}
      {habits.length > 0 && (
        <div className="bg-indigo-600 rounded-2xl p-4 text-white">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold">Today's Progress</span>
            <span className="text-indigo-200 text-sm">{doneCount}/{habits.length}</span>
          </div>
          <div className="bg-indigo-500 rounded-full h-2.5">
            <div
              className="bg-white rounded-full h-2.5 transition-all"
              style={{ width: `${habits.length ? (doneCount / habits.length) * 100 : 0}%` }}
            />
          </div>
          {doneCount === habits.length && habits.length > 0 && (
            <p className="text-indigo-100 text-xs mt-2">🎉 All habits done for today!</p>
          )}
        </div>
      )}

      {/* Habit list */}
      {habits.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">🎯</span>
          <p className="text-gray-400 text-sm">No habits tracked yet</p>
          <p className="text-gray-300 text-xs mt-1">Tap + to build your first habit</p>
        </div>
      ) : (
        <div className="space-y-3">
          {habits.map(h => {
            const done = h.completedDates.includes(todayStr);
            const streak = getStreak(h);
            return (
              <div
                key={h.id}
                className={`flex items-center gap-3 rounded-2xl p-4 transition-colors ${
                  done ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-100'
                }`}
              >
                {/* Emoji */}
                <span className="text-2xl">{h.emoji}</span>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className={`font-medium text-sm ${done ? 'text-green-800' : 'text-gray-700'}`}>
                    {h.name}
                  </p>
                  {streak > 0 && (
                    <p className="text-xs text-orange-500 mt-0.5">🔥 {streak} day streak</p>
                  )}
                </div>

                {/* Toggle */}
                <button
                  onClick={() => toggle(h.id)}
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-colors flex-shrink-0 ${
                    done ? 'bg-green-500 text-white' : 'bg-white border-2 border-gray-200'
                  }`}
                >
                  {done ? '✓' : ''}
                </button>

                {/* Delete */}
                <button onClick={() => remove(h.id)} className="text-gray-300 hover:text-red-400 text-lg pl-1">
                  ×
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Weekly view */}
      {habits.length > 0 && <WeeklyView habits={habits} />}

      {/* FAB */}
      <button
        onClick={() => setShowAdd(true)}
        className="fixed bottom-20 right-4 w-14 h-14 rounded-full bg-indigo-600 text-white shadow-lg text-2xl flex items-center justify-center active:scale-95 transition-transform"
      >
        +
      </button>

      {showAdd && <AddHabitSheet onAdd={addHabit} onClose={() => setShowAdd(false)} />}
    </div>
  );
}

function WeeklyView({ habits }: { habits: Habit[] }) {
  const days = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - 6 + i);
    return {
      label: d.toLocaleDateString('en-US', { weekday: 'short' }).slice(0, 1),
      date: d.toISOString().slice(0, 10),
      isToday: i === 6,
    };
  });

  return (
    <div className="bg-gray-50 rounded-2xl p-4">
      <h3 className="text-sm font-semibold text-gray-600 mb-3">Last 7 Days</h3>
      <div className="grid grid-cols-7 gap-1">
        {days.map(d => (
          <div key={d.date} className="flex flex-col items-center gap-1">
            <span className={`text-[10px] font-medium ${d.isToday ? 'text-indigo-600' : 'text-gray-400'}`}>
              {d.label}
            </span>
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-medium ${
                d.isToday ? 'ring-2 ring-indigo-400' : ''
              } ${
                habits.every(h => h.completedDates.includes(d.date)) && habits.length > 0
                  ? 'bg-indigo-500 text-white'
                  : habits.some(h => h.completedDates.includes(d.date))
                    ? 'bg-indigo-200 text-indigo-700'
                    : 'bg-gray-200 text-gray-400'
              }`}
            >
              {habits.filter(h => h.completedDates.includes(d.date)).length || ''}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AddHabitSheet({ onAdd, onClose }: {
  onAdd: (name: string, emoji: string) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState('');
  const [emoji, setEmoji] = useState('💧');

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-t-3xl p-5 space-y-4 shadow-2xl">
        <div className="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-2" />
        <h2 className="text-lg font-bold text-gray-800">New Habit</h2>

        <input
          autoFocus
          placeholder="Habit name (e.g. Drink Water)"
          value={name}
          onChange={e => setName(e.target.value)}
          className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-400"
        />

        <div>
          <label className="text-xs text-gray-500 font-medium mb-2 block">Pick an emoji</label>
          <div className="grid grid-cols-6 gap-2">
            {PRESET_EMOJIS.map(e => (
              <button
                key={e}
                onClick={() => setEmoji(e)}
                className={`text-2xl p-2 rounded-xl transition-colors ${
                  emoji === e ? 'bg-indigo-100 ring-2 ring-indigo-400' : 'bg-gray-50'
                }`}
              >
                {e}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => name.trim() && onAdd(name.trim(), emoji)}
          disabled={!name.trim()}
          className="w-full bg-indigo-600 text-white py-3.5 rounded-xl font-semibold disabled:opacity-40 active:scale-95 transition-transform"
        >
          Add Habit
        </button>
      </div>
    </div>
  );
}
