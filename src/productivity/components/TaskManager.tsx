import { useState, useEffect, useCallback } from 'react';
import { store, today, uid } from '../store';
import { Task, Priority } from '../types';

type Filter = 'all' | 'todo' | 'done';

export default function TaskManager() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => { setTasks(store.getTasks()); }, []);

  const save = useCallback((updated: Task[]) => {
    setTasks(updated);
    store.saveTasks(updated);
  }, []);

  const toggle = (id: string) => {
    save(tasks.map(t => t.id === id ? { ...t, done: !t.done } : t));
  };

  const remove = (id: string) => {
    save(tasks.filter(t => t.id !== id));
  };

  const add = (title: string, priority: Priority, date: string) => {
    const task: Task = { id: uid(), title, priority, done: false, date, createdAt: new Date().toISOString() };
    save([task, ...tasks]);
    setShowAdd(false);
  };

  const visible = tasks.filter(t => {
    if (filter === 'todo') return !t.done;
    if (filter === 'done') return t.done;
    return true;
  });

  const counts = {
    all: tasks.length,
    todo: tasks.filter(t => !t.done).length,
    done: tasks.filter(t => t.done).length,
  };

  return (
    <div className="p-4 space-y-4">
      {/* Filter tabs */}
      <div className="flex gap-2 bg-gray-100 rounded-xl p-1">
        {(['all', 'todo', 'done'] as Filter[]).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`flex-1 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${
              filter === f ? 'bg-white shadow-sm text-indigo-600' : 'text-gray-500'
            }`}
          >
            {f} <span className="text-xs opacity-60">({counts[f]})</span>
          </button>
        ))}
      </div>

      {/* Task list */}
      <div className="space-y-2">
        {visible.length === 0 && (
          <div className="text-center text-gray-400 py-12 text-sm">
            {filter === 'done' ? 'No completed tasks yet' : 'No tasks — add one below!'}
          </div>
        )}
        {visible.map(t => (
          <TaskRow key={t.id} task={t} onToggle={toggle} onDelete={remove} />
        ))}
      </div>

      {/* Add button */}
      <button
        onClick={() => setShowAdd(true)}
        className="fixed bottom-20 right-4 w-14 h-14 rounded-full bg-indigo-600 text-white shadow-lg text-2xl flex items-center justify-center active:scale-95 transition-transform"
      >
        +
      </button>

      {showAdd && <AddTaskSheet onAdd={add} onClose={() => setShowAdd(false)} />}
    </div>
  );
}

function TaskRow({ task, onToggle, onDelete }: {
  task: Task;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const priorityColors: Record<Priority, string> = {
    high: 'bg-red-100 text-red-600',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700',
  };

  return (
    <div className="flex items-start gap-3 bg-gray-50 rounded-2xl p-3">
      <button
        onClick={() => onToggle(task.id)}
        className={`mt-0.5 flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
          task.done ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-gray-300'
        }`}
      >
        {task.done && <span className="text-xs">✓</span>}
      </button>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${task.done ? 'line-through text-gray-400' : 'text-gray-800'}`}>
          {task.title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium capitalize ${priorityColors[task.priority]}`}>
            {task.priority}
          </span>
          <span className="text-[10px] text-gray-400">{task.date}</span>
        </div>
      </div>
      <button onClick={() => onDelete(task.id)} className="text-gray-300 hover:text-red-400 text-lg leading-none pl-2">
        ×
      </button>
    </div>
  );
}

function AddTaskSheet({ onAdd, onClose }: {
  onAdd: (title: string, priority: Priority, date: string) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState<Priority>('medium');
  const [date, setDate] = useState(today());

  const submit = () => {
    if (!title.trim()) return;
    onAdd(title.trim(), priority, date);
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-t-3xl p-5 space-y-4 shadow-2xl">
        <div className="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-2" />
        <h2 className="text-lg font-bold text-gray-800">New Task</h2>

        <input
          autoFocus
          placeholder="What needs to be done?"
          value={title}
          onChange={e => setTitle(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-400"
        />

        <div>
          <label className="text-xs text-gray-500 font-medium mb-2 block">Priority</label>
          <div className="flex gap-2">
            {(['high', 'medium', 'low'] as Priority[]).map(p => (
              <button
                key={p}
                onClick={() => setPriority(p)}
                className={`flex-1 py-2 rounded-xl text-sm font-medium capitalize transition-colors border ${
                  priority === p
                    ? p === 'high' ? 'bg-red-500 text-white border-red-500'
                      : p === 'medium' ? 'bg-yellow-400 text-white border-yellow-400'
                      : 'bg-green-500 text-white border-green-500'
                    : 'bg-gray-50 text-gray-500 border-gray-200'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-500 font-medium mb-2 block">Date</label>
          <input
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-400"
          />
        </div>

        <button
          onClick={submit}
          disabled={!title.trim()}
          className="w-full bg-indigo-600 text-white py-3.5 rounded-xl font-semibold disabled:opacity-40 active:scale-95 transition-transform"
        >
          Add Task
        </button>
      </div>
    </div>
  );
}
