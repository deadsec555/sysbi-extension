import { useState, useEffect, useRef, useCallback } from 'react';
import { store, uid, today } from '../store';
import { PomodoroSession } from '../types';

type Mode = 'work' | 'short' | 'long';

const DURATIONS: Record<Mode, number> = {
  work: 25 * 60,
  short: 5 * 60,
  long: 15 * 60,
};

const LABELS: Record<Mode, string> = {
  work: 'Focus',
  short: 'Short Break',
  long: 'Long Break',
};

const COLORS: Record<Mode, { ring: string; bg: string; text: string }> = {
  work:  { ring: '#6366f1', bg: 'bg-indigo-50',  text: 'text-indigo-600' },
  short: { ring: '#22c55e', bg: 'bg-green-50',   text: 'text-green-600'  },
  long:  { ring: '#f59e0b', bg: 'bg-amber-50',   text: 'text-amber-600'  },
};

const RADIUS = 90;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function FocusTimer() {
  const [mode, setMode] = useState<Mode>('work');
  const [remaining, setRemaining] = useState(DURATIONS.work);
  const [running, setRunning] = useState(false);
  const [sessions, setSessions] = useState<PomodoroSession[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { setSessions(store.getSessions()); }, []);

  // Reset when mode changes
  useEffect(() => {
    setRunning(false);
    setRemaining(DURATIONS[mode]);
  }, [mode]);

  const completeSession = useCallback(() => {
    if (mode === 'work') {
      const s: PomodoroSession = { id: uid(), type: 'work', completedAt: new Date().toISOString() };
      const updated = [s, ...sessions];
      setSessions(updated);
      store.saveSessions(updated);
      // Vibrate on completion (mobile)
      if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
    }
    setRunning(false);
    setRemaining(DURATIONS[mode]);
  }, [mode, sessions]);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setRemaining(r => {
          if (r <= 1) {
            completeSession();
            return DURATIONS[mode];
          }
          return r - 1;
        });
      }, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [running, mode, completeSession]);

  const reset = () => {
    setRunning(false);
    setRemaining(DURATIONS[mode]);
  };

  const mins = String(Math.floor(remaining / 60)).padStart(2, '0');
  const secs = String(remaining % 60).padStart(2, '0');

  const progress = remaining / DURATIONS[mode];
  const strokeOffset = CIRCUMFERENCE * progress;

  const color = COLORS[mode];
  const todaySessions = sessions.filter(s => s.type === 'work' && s.completedAt.startsWith(today())).length;
  const totalMinutes = todaySessions * 25;

  return (
    <div className="p-4 space-y-6 flex flex-col items-center">
      {/* Mode selector */}
      <div className="flex gap-2 bg-gray-100 rounded-xl p-1 w-full">
        {(['work', 'short', 'long'] as Mode[]).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              mode === m ? `bg-white shadow-sm ${color.text}` : 'text-gray-500'
            }`}
          >
            {LABELS[m]}
          </button>
        ))}
      </div>

      {/* Ring timer */}
      <div className={`relative rounded-full p-2 ${color.bg}`}>
        <svg width="220" height="220" className="-rotate-90">
          {/* Background ring */}
          <circle cx="110" cy="110" r={RADIUS} fill="none" stroke="#e5e7eb" strokeWidth="10" />
          {/* Progress ring */}
          <circle
            cx="110" cy="110" r={RADIUS}
            fill="none"
            stroke={color.ring}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={strokeOffset}
            style={{ transition: running ? 'stroke-dashoffset 1s linear' : 'none' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-5xl font-bold text-gray-800 tabular-nums tracking-tighter">
            {mins}:{secs}
          </span>
          <span className={`text-sm font-medium mt-1 ${color.text}`}>{LABELS[mode]}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-4 items-center">
        <button
          onClick={reset}
          className="w-12 h-12 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-lg active:scale-95 transition-transform"
        >
          ↺
        </button>
        <button
          onClick={() => setRunning(r => !r)}
          className={`w-20 h-20 rounded-full text-white text-3xl flex items-center justify-center shadow-lg active:scale-95 transition-transform ${
            running ? 'bg-gray-400' : 'bg-indigo-600'
          }`}
        >
          {running ? '⏸' : '▶'}
        </button>
        <div className="w-12 h-12" />
      </div>

      {/* Today's stats */}
      <div className="w-full bg-gray-50 rounded-2xl p-4 grid grid-cols-2 gap-3">
        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">{todaySessions}</div>
          <div className="text-xs text-gray-500">Sessions today</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">{totalMinutes}</div>
          <div className="text-xs text-gray-500">Minutes focused</div>
        </div>
      </div>

      {/* Tips */}
      <div className="w-full bg-indigo-50 rounded-2xl p-4">
        <p className="text-xs text-indigo-700 font-medium mb-1">💡 Pomodoro Technique</p>
        <p className="text-xs text-indigo-600">
          Work for 25 minutes, then take a 5-minute break. After 4 sessions, take a 15-minute long break.
        </p>
      </div>
    </div>
  );
}
