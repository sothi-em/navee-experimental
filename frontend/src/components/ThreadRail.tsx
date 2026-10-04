import { useState } from "react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import type { Session } from "../api/client";
import { cn } from "../utils/cn";

interface ThreadRailProps {
  sessions: Session[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => void;
  onRename: (id: number, title: string) => void;
  onDelete: (id: number) => void;
}

const ROW_BTN =
  "p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground";

function formatWhen(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  const opts: Intl.DateTimeFormatOptions =
    d.getFullYear() === now.getFullYear()
      ? { month: "short", day: "numeric" }
      : { month: "short", day: "numeric", year: "numeric" };
  return d.toLocaleDateString([], opts);
}

export function ThreadRail({
  sessions,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: ThreadRailProps) {
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const startEdit = (s: Session) => {
    setEditing(s.id);
    setDraft(s.title ?? "");
  };

  const commitEdit = () => {
    if (editing === null) return;
    const title = draft.trim();
    if (title) onRename(editing, title);
    setEditing(null);
  };

  return (
    <aside className="w-[280px] shrink-0 flex flex-col border-r border-border bg-background">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground">Conversations</h2>
        <button
          type="button"
          onClick={onCreate}
          className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground"
          aria-label="New conversation"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <div className="px-3 py-2 text-xs text-muted-foreground">No conversations yet.</div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={cn(
              "w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center gap-2 cursor-pointer",
              s.id === activeId
                ? "bg-muted text-foreground"
                : "text-foreground hover:bg-muted"
            )}
          >
            <div className="flex-1 min-w-0">
              {confirmDelete === s.id ? (
                <div className="text-xs font-medium text-destructive truncate">
                  Delete this conversation?
                </div>
              ) : editing === s.id ? (
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={commitEdit}
                  onClick={(e) => e.stopPropagation()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit();
                    if (e.key === "Escape") setEditing(null);
                  }}
                  className="w-full px-1 rounded border border-indigo-500 bg-background text-sm text-foreground focus:outline-none"
                />
              ) : (
                <>
                  <div className="truncate">{s.title || "New conversation"}</div>
                  <div className="text-2xs text-muted-foreground">{formatWhen(s.created_at)}</div>
                </>
              )}
            </div>

            <div className="flex items-center gap-0.5 shrink-0">
              {confirmDelete === s.id ? (
                <>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDelete(null);
                      onDelete(s.id);
                    }}
                    className={ROW_BTN}
                    aria-label="Confirm delete"
                  >
                    <Check className="w-3.5 h-3.5 text-destructive" />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDelete(null);
                    }}
                    className={ROW_BTN}
                    aria-label="Cancel delete"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </>
              ) : editing === s.id ? (
                <>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      commitEdit();
                    }}
                    className={ROW_BTN}
                    aria-label="Save name"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditing(null);
                    }}
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
                    onClick={(e) => {
                      e.stopPropagation();
                      startEdit(s);
                    }}
                    className={ROW_BTN}
                    aria-label="Rename conversation"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDelete(s.id);
                    }}
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
    </aside>
  );
}
