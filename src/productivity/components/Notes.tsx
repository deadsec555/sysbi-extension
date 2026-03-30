import { useState, useEffect, useCallback } from 'react';
import { store, uid } from '../store';
import { Note } from '../types';

const NOTE_COLORS = [
  'bg-yellow-100', 'bg-pink-100', 'bg-blue-100',
  'bg-green-100',  'bg-purple-100', 'bg-orange-100',
];

export default function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [editing, setEditing] = useState<Note | null>(null);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => { setNotes(store.getNotes()); }, []);

  const save = useCallback((updated: Note[]) => {
    setNotes(updated);
    store.saveNotes(updated);
  }, []);

  const createNote = () => {
    const note: Note = {
      id: uid(),
      title: '',
      content: '',
      color: NOTE_COLORS[Math.floor(Math.random() * NOTE_COLORS.length)],
      updatedAt: new Date().toISOString(),
    };
    setEditing(note);
    setShowNew(true);
  };

  const saveNote = (note: Note) => {
    if (!note.title.trim() && !note.content.trim()) {
      setEditing(null);
      setShowNew(false);
      return;
    }
    const updated = note.title.trim() === '' && note.content.trim() === ''
      ? notes.filter(n => n.id !== note.id)
      : notes.some(n => n.id === note.id)
        ? notes.map(n => n.id === note.id ? { ...note, updatedAt: new Date().toISOString() } : n)
        : [{ ...note, updatedAt: new Date().toISOString() }, ...notes];
    save(updated);
    setEditing(null);
    setShowNew(false);
  };

  const deleteNote = (id: string) => {
    save(notes.filter(n => n.id !== id));
    setEditing(null);
    setShowNew(false);
  };

  const openNote = (note: Note) => {
    setEditing({ ...note });
    setShowNew(true);
  };

  if (showNew && editing) {
    return <NoteEditor note={editing} onChange={setEditing} onSave={saveNote} onDelete={deleteNote} />;
  }

  return (
    <div className="p-4">
      {notes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <span className="text-5xl mb-4">📝</span>
          <p className="text-gray-400 text-sm">No notes yet</p>
          <p className="text-gray-300 text-xs mt-1">Tap + to create your first note</p>
        </div>
      ) : (
        <div className="columns-2 gap-3">
          {notes.map(n => (
            <button
              key={n.id}
              onClick={() => openNote(n)}
              className={`${n.color} rounded-2xl p-3 w-full text-left mb-3 break-inside-avoid active:scale-95 transition-transform`}
            >
              {n.title && <p className="font-semibold text-gray-800 text-sm mb-1 truncate">{n.title}</p>}
              {n.content && (
                <p className="text-xs text-gray-600 line-clamp-6 whitespace-pre-wrap">{n.content}</p>
              )}
              <p className="text-[10px] text-gray-400 mt-2">
                {new Date(n.updatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* FAB */}
      <button
        onClick={createNote}
        className="fixed bottom-20 right-4 w-14 h-14 rounded-full bg-indigo-600 text-white shadow-lg text-2xl flex items-center justify-center active:scale-95 transition-transform"
      >
        +
      </button>
    </div>
  );
}

function NoteEditor({ note, onChange, onSave, onDelete }: {
  note: Note;
  onChange: (n: Note) => void;
  onSave: (n: Note) => void;
  onDelete: (id: string) => void;
}) {
  const isExisting = !!note.updatedAt && note.title !== '' || note.content !== '';

  return (
    <div className={`min-h-screen ${note.color} flex flex-col`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-black/5">
        <button
          onClick={() => onSave(note)}
          className="text-gray-600 font-medium text-sm px-2 py-1"
        >
          ← Done
        </button>
        <div className="flex gap-3 items-center">
          {/* Color picker */}
          <div className="flex gap-1.5">
            {NOTE_COLORS.map(c => (
              <button
                key={c}
                onClick={() => onChange({ ...note, color: c })}
                className={`w-5 h-5 rounded-full ${c} border-2 ${note.color === c ? 'border-gray-600' : 'border-transparent'}`}
              />
            ))}
          </div>
          {isExisting && (
            <button
              onClick={() => onDelete(note.id)}
              className="text-red-400 text-sm px-2 py-1"
            >
              🗑
            </button>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 p-4 flex flex-col gap-2">
        <input
          placeholder="Title"
          value={note.title}
          onChange={e => onChange({ ...note, title: e.target.value })}
          className="bg-transparent text-xl font-bold text-gray-800 placeholder-gray-400 outline-none w-full"
        />
        <textarea
          placeholder="Start writing..."
          value={note.content}
          onChange={e => onChange({ ...note, content: e.target.value })}
          className="bg-transparent text-sm text-gray-700 placeholder-gray-400 outline-none flex-1 resize-none w-full leading-relaxed"
          rows={20}
          autoFocus
        />
      </div>
    </div>
  );
}
