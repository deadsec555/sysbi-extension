export type Priority = 'high' | 'medium' | 'low';

export interface Task {
  id: string;
  title: string;
  priority: Priority;
  done: boolean;
  date: string; // YYYY-MM-DD
  createdAt: string;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  color: string;
  updatedAt: string;
}

export interface Habit {
  id: string;
  name: string;
  emoji: string;
  completedDates: string[]; // YYYY-MM-DD
}

export interface PomodoroSession {
  id: string;
  type: 'work' | 'break';
  completedAt: string; // ISO
}

export type Tab = 'home' | 'tasks' | 'focus' | 'notes' | 'habits';
