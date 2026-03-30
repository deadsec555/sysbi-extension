import { Task, Note, Habit, PomodoroSession } from './types';

const KEYS = {
  tasks: 'prod_tasks',
  notes: 'prod_notes',
  habits: 'prod_habits',
  sessions: 'prod_sessions',
};

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save<T>(key: string, data: T): void {
  localStorage.setItem(key, JSON.stringify(data));
}

export const store = {
  getTasks: (): Task[] => load(KEYS.tasks, []),
  saveTasks: (t: Task[]) => save(KEYS.tasks, t),

  getNotes: (): Note[] => load(KEYS.notes, []),
  saveNotes: (n: Note[]) => save(KEYS.notes, n),

  getHabits: (): Habit[] => load(KEYS.habits, []),
  saveHabits: (h: Habit[]) => save(KEYS.habits, h),

  getSessions: (): PomodoroSession[] => load(KEYS.sessions, []),
  saveSessions: (s: PomodoroSession[]) => save(KEYS.sessions, s),
};

export function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

export function uid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
