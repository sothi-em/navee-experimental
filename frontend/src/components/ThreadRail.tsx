import { useState } from "react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { cn } from "../utils/cn";

interface Thread {
  title: string;
  timestamp: string;
}

const INITIAL_THREADS: Thread[] = [
  { title: "Memory architecture", timestamp: "2h ago" },
  { title: "Vector recall tuning", timestamp: "yesterday" },
  { title: "Onboarding", timestamp: "3d ago" },
];

const ROW_BTN =
  "p-1 rounded hover:bg-zinc-200 transition-colors text-zinc-400 hover:text-zinc-600";

export function ThreadRail() {
  const [threads, setThreads] = useState(INITIAL_THREADS);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const startEdit = (i: number) => {
    setEditing(i);
    setDraft(threads[i].title);
  };

  const commitEdit = () => {
    if (editing === null) return;
    const title = draft.trim();
    setThreads((ts) =>
      ts.map((t, i) => (i === editing ? { ...t, title: title || t.title } : t))
    );
    setEditing(null);
  };

  const removeThread = (i: number) =>
    setThreads((ts) => ts.filter((_, j) => j !== i));

  return (
    <aside className="w-[280px] shrink-0 flex flex-col border-r border-zinc-200 bg-white">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200">
        <h2 className="text-sm font-semibold text-zinc-800">Conversations</h2>
        <button
          type="button"
          className="p-1.5 rounded-md hover:bg-zinc-100 transition-colors text-zinc-500"
          aria-label="New conversation"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {threads.map((thread, i) => (
          <div
            key={i}
            className={cn(
              "w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center gap-2",
              i === 0
                ? "bg-zinc-100 text-zinc-800"
                : "text-zinc-600 hover:bg-zinc-50"
            )}
          >
            <div className="flex-1 min-w-0">
              {editing === i ? (
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={commitEdit}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit();
                    if (e.key === "Escape") setEditing(null);
                  }}
                  className="w-full px-1 rounded border border-indigo-500 bg-white text-sm text-zinc-800 focus:outline-none"
                />
              ) : (
                <div className="truncate">{thread.title}</div>
              )}
              <div className="text-[10px] text-zinc-400">{thread.timestamp}</div>
            </div>

            <div className="flex items-center gap-0.5 shrink-0">
              {editing === i ? (
                <>
                  <button
                    type="button"
                    onClick={commitEdit}
                    className={ROW_BTN}
                    aria-label="Save name"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditing(null)}
                    className={ROW_BTN}
                    aria-label="Cancel rename"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => startEdit(i)}
                    className={ROW_BTN}
                    aria-label="Rename conversation"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(i)}
                    className={ROW_BTN}
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {confirmDelete !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-72 rounded-lg border border-zinc-200 bg-white shadow-lg p-4">
            <h3 className="text-sm font-semibold text-zinc-800">
              Delete conversation?
            </h3>
            <p className="mt-1 text-xs text-zinc-500">
              “{threads[confirmDelete].title}” will be removed. This cannot be
              undone.
            </p>
            <div className="mt-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(null)}
                className="px-3 py-1.5 rounded-md text-xs font-medium border border-zinc-200 text-zinc-600 hover:bg-zinc-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  removeThread(confirmDelete);
                  setConfirmDelete(null);
                }}
                className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
