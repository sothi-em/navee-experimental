import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Check,
  Eye,
  Globe,
  Moon,
  Palette,
  Pencil,
  Plus,
  Sun,
  Trash2,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { api, type Compaction, type Message, type Skill, type User, type UserFact } from "../api/client";
import { cn } from "../utils/cn";
import { applyFontScale, applyTheme, getInitialTheme, getStoredFontScale, FONT_SCALES, type FontScale, type Theme } from "../utils/appearance";

type Section = "users" | "skills" | "appearance";
type DetailTab = "management" | "compactions" | "facts" | "history";
type ClearKind = "compactions" | "facts" | "history";

const SECTIONS: { id: Section; label: string; icon: LucideIcon }[] = [
  { id: "users", label: "Users", icon: Users },
  { id: "skills", label: "Skills", icon: Globe },
  { id: "appearance", label: "Appearance", icon: Palette },
];

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "management", label: "Management" },
  { id: "compactions", label: "Compactions" },
  { id: "facts", label: "Facts" },
  { id: "history", label: "History" },
];

const ROW_BTN =
  "p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground";
const DANGER_BTN =
  "px-2 py-1 text-xs rounded-md bg-destructive text-white hover:bg-destructive/90 disabled:opacity-40";
const GHOST_BTN =
  "px-2 py-1 text-xs rounded-md border border-border text-foreground hover:bg-muted disabled:opacity-40";
const EMPTY = "grid place-items-center h-full text-xs text-muted-foreground";

export function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [section, setSection] = useState<Section>("users");
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [tab, setTab] = useState<DetailTab>("management");
  const [compactions, setCompactions] = useState<Compaction[]>([]);
  const [facts, setFacts] = useState<UserFact[]>([]);
  const [history, setHistory] = useState<Message[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftDisplay, setDraftDisplay] = useState("");
  const [confirmDeleteUserId, setConfirmDeleteUserId] = useState<number | null>(null);
  const [newName, setNewName] = useState("");

  const loadUsers = async () => {
    setUsersLoading(true);
    try {
      setUsers(await api.listUsers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setUsersLoading(false);
    }
  };

  const loadUserData = async (userId: number) => {
    setDataLoading(true);
    try {
      const [c, f, h] = await Promise.all([
        api.listUserCompactions(userId),
        api.listUserFacts(userId),
        api.listUserHistory(userId),
      ]);
      setCompactions(c);
      setFacts(f);
      setHistory(h);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load user data");
    } finally {
      setDataLoading(false);
    }
  };

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  // Reset + load users each time the modal opens.
  useEffect(() => {
    if (!open) return;
    setSection("users");
    setSelectedId(null);
    setTab("management");
    setCompactions([]);
    setFacts([]);
    setHistory([]);
    setEditingId(null);
    setConfirmDeleteUserId(null);
    setNewName("");
    setError(null);
    void loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Load the selected user's data; clear it when deselected.
  useEffect(() => {
    if (selectedId === null) {
      setCompactions([]);
      setFacts([]);
      setHistory([]);
      return;
    }
    setTab("management");
    void loadUserData(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  // Escape closes the modal.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const selected = users.find((u) => u.id === selectedId) ?? null;
  // The first (lowest-id) user is the protected default: no edit/delete.
  const defaultId = users.length > 0 ? users[0].id : null;

  const startEdit = (u: User) => {
    setEditingId(u.id);
    setDraftName(u.username);
    setDraftDisplay(u.display_name ?? "");
    setConfirmDeleteUserId(null);
  };

  const commitEdit = () =>
    run(async () => {
      if (editingId === null || !draftName.trim()) return;
      await api.updateUser(editingId, draftName.trim(), draftDisplay.trim() || null);
      setEditingId(null);
      await loadUsers();
    });

  const removeUser = (id: number) =>
    run(async () => {
      await api.deleteUser(id);
      setConfirmDeleteUserId(null);
      if (selectedId === id) setSelectedId(null);
      await loadUsers();
    });

  const addUser = () =>
    run(async () => {
      const name = newName.trim();
      if (!name) return;
      await api.createUser(name);
      setNewName("");
      await loadUsers();
    });

  const deleteCompaction = (id: number) =>
    run(async () => {
      if (selectedId === null) return;
      await api.deleteUserCompaction(selectedId, id);
      await loadUserData(selectedId);
    });

  const deleteFact = (id: number) =>
    run(async () => {
      if (selectedId === null) return;
      await api.deleteUserFact(selectedId, id);
      await loadUserData(selectedId);
    });

  const clearData = (kind: ClearKind) =>
    run(async () => {
      if (selectedId === null) return;
      if (kind === "compactions") await api.clearUserCompactions(selectedId);
      else if (kind === "facts") await api.clearUserFacts(selectedId);
      else await api.clearUserHistory(selectedId);
      await loadUserData(selectedId);
    });

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center"
      onMouseDown={onClose}
    >
      <div
        className="w-[720px] h-[480px] bg-background rounded-lg shadow-xl flex overflow-hidden"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Left rail */}
        <div className="w-44 shrink-0 border-r border-border flex flex-col p-2 gap-1">
          <div className="flex items-center justify-between px-2 py-1.5">
            <span className="text-xs font-semibold text-foreground">Settings</span>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close settings"
              className={ROW_BTN}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => {
                setSection(s.id);
                setSelectedId(null);
              }}
              className={cn(
                "flex items-center gap-2 px-2 py-1.5 rounded-md text-xs transition-colors",
                section === s.id
                  ? "bg-indigo-50 text-indigo-600 font-medium dark:bg-indigo-500/15 dark:text-indigo-300"
                  : "text-foreground hover:bg-muted"
              )}
            >
              <s.icon className="w-3.5 h-3.5" />
              {s.label}
            </button>
          ))}
        </div>

        {/* Right content */}
        <div className="flex-1 min-w-0 flex flex-col">
          {section === "skills" ? (
            <SkillsSection busy={busy} error={error} setError={setError} run={run} />
          ) : section === "appearance" ? (
            <AppearanceSection />
          ) : selected ? (
            <>
              <div className="h-10 px-4 flex items-center gap-2 border-b border-border">
                <button
                  type="button"
                  onClick={() => setSelectedId(null)}
                  aria-label="Back to users"
                  className={ROW_BTN}
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                </button>
                <span className="text-xs font-medium text-foreground">{selected.username}</span>
                {selected.display_name && (
                  <span className="text-3xs text-muted-foreground">{selected.display_name}</span>
                )}
              </div>
              <div className="flex gap-1 px-4 pt-2 border-b border-border">
                {DETAIL_TABS.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTab(t.id)}
                    className={cn(
                      "px-2.5 py-1.5 text-xs rounded-t-md border-b-2 transition-colors",
                      tab === t.id
                        ? "border-indigo-500 text-indigo-600 font-medium dark:text-indigo-300"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="flex-1 overflow-y-auto">
                {error && (
                  <div className="mx-4 mt-2 px-2 py-1 text-3xs text-destructive bg-destructive/10 rounded-md">
                    {error}
                  </div>
                )}
                {dataLoading ? (
                  <div className={EMPTY}>Loading…</div>
                ) : (
                  <>
                    {tab === "management" && (
                      <ManagementTab
                        compactionCount={compactions.length}
                        factCount={facts.length}
                        historyCount={history.length}
                        onClear={clearData}
                        busy={busy}
                      />
                    )}
                    {tab === "compactions" && (
                      <CompactionsTab items={compactions} onDelete={deleteCompaction} busy={busy} />
                    )}
                    {tab === "facts" && <FactsTab items={facts} onDelete={deleteFact} busy={busy} />}
                    {tab === "history" && <HistoryTab items={history} />}
                  </>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="h-10 px-4 flex items-center justify-between border-b border-border">
                <span className="text-xs font-medium text-foreground">Users</span>
                <div className="flex items-center gap-1.5">
                  <input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void addUser();
                    }}
                    placeholder="username"
                    className="w-32 px-2 py-1 text-xs border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                  <button
                    type="button"
                    onClick={addUser}
                    disabled={!newName.trim() || busy}
                    className="flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-40 transition-colors"
                  >
                    <Plus className="w-3 h-3" />
                    Add
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto">
                {error && (
                  <div className="mx-4 mt-2 px-2 py-1 text-3xs text-destructive bg-destructive/10 rounded-md">
                    {error}
                  </div>
                )}
                {usersLoading ? (
                  <div className={EMPTY}>Loading…</div>
                ) : users.length === 0 ? (
                  <div className={EMPTY}>No users yet.</div>
                ) : (
                  users.map((u) => {
                    const isDefault = u.id === defaultId;
                    if (editingId === u.id) {
                      return (
                        <div
                          key={u.id}
                          className="flex items-center gap-2 px-4 py-2 border-b border-border"
                        >
                          <div className="w-6 h-6 rounded-full bg-muted grid place-items-center text-2xs font-medium text-muted-foreground">
                            {u.username.slice(0, 1).toUpperCase()}
                          </div>
                          <input
                            value={draftName}
                            onChange={(e) => setDraftName(e.target.value)}
                            className="flex-1 px-2 py-1 text-xs border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400"
                            autoFocus
                          />
                          <input
                            value={draftDisplay}
                            onChange={(e) => setDraftDisplay(e.target.value)}
                            placeholder="display name"
                            className="w-40 px-2 py-1 text-xs border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400"
                          />
                          <button
                            type="button"
                            onClick={commitEdit}
                            disabled={busy}
                            aria-label="Save"
                            className={ROW_BTN}
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            aria-label="Cancel"
                            className={ROW_BTN}
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      );
                    }
                    if (confirmDeleteUserId === u.id) {
                      return (
                        <div
                          key={u.id}
                          className="flex items-center gap-2 px-4 py-2 border-b border-border"
                        >
                          <div className="flex-1">
                            <div className="text-xs font-medium text-foreground">{u.username}</div>
                            <div className="text-3xs text-muted-foreground">
                              Delete this user and all their data?
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeUser(u.id)}
                            disabled={busy}
                            className={DANGER_BTN}
                          >
                            Delete
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteUserId(null)}
                            className={GHOST_BTN}
                          >
                            Cancel
                          </button>
                        </div>
                      );
                    }
                    return (
                      <div
                        key={u.id}
                        className="flex items-center gap-2 px-4 py-2 border-b border-border hover:bg-muted cursor-pointer"
                        onClick={() => setSelectedId(u.id)}
                      >
                        <div className="w-6 h-6 rounded-full bg-muted grid place-items-center text-2xs font-medium text-muted-foreground">
                          {u.username.slice(0, 1).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium text-foreground truncate">
                            {u.username}
                            {isDefault && (
                              <span className="ml-1.5 text-2xs font-normal text-muted-foreground">
                                default
                              </span>
                            )}
                          </div>
                          {u.display_name && (
                            <div className="text-3xs text-muted-foreground truncate">
                              {u.display_name}
                            </div>
                          )}
                        </div>
                        {!isDefault && (
                          <>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                startEdit(u);
                              }}
                              aria-label="Edit user"
                              className={ROW_BTN}
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setConfirmDeleteUserId(u.id);
                              }}
                              aria-label="Delete user"
                              className={ROW_BTN}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Detail tab subcomponents ---------------------------------------------

function ManagementTab({
  compactionCount,
  factCount,
  historyCount,
  onClear,
  busy,
}: {
  compactionCount: number;
  factCount: number;
  historyCount: number;
  onClear: (kind: ClearKind) => void;
  busy: boolean;
}) {
  const [confirm, setConfirm] = useState<ClearKind | null>(null);
  const rows: { kind: ClearKind; label: string; count: number; noun: string }[] = [
    { kind: "compactions", label: "Compactions", count: compactionCount, noun: "compactions" },
    { kind: "facts", label: "Facts", count: factCount, noun: "facts" },
    { kind: "history", label: "History", count: historyCount, noun: "messages" },
  ];
  return (
    <div className="p-4 space-y-2">
      <p className="text-3xs text-muted-foreground">
        Clear all of this user&apos;s data in a category. This cannot be undone.
      </p>
      {rows.map((r) => (
        <div
          key={r.kind}
          className="flex items-center gap-2 px-3 py-2 border border-border rounded-md"
        >
          <div className="flex-1">
            <div className="text-xs font-medium text-foreground">{r.label}</div>
            <div className="text-3xs text-muted-foreground">
              {r.count} {r.noun}
            </div>
          </div>
          {confirm === r.kind ? (
            <>
              <span className="text-3xs text-muted-foreground">
                Clear all {r.count} {r.noun}?
              </span>
              <button
                type="button"
                onClick={() => {
                  onClear(r.kind);
                  setConfirm(null);
                }}
                disabled={busy}
                className={DANGER_BTN}
              >
                Clear
              </button>
              <button type="button" onClick={() => setConfirm(null)} className={GHOST_BTN}>
                Cancel
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setConfirm(r.kind)}
              disabled={r.count === 0 || busy}
              className={GHOST_BTN}
            >
              Clear
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function CompactionsTab({
  items,
  onDelete,
  busy,
}: {
  items: Compaction[];
  onDelete: (id: number) => void;
  busy: boolean;
}) {
  const [viewingId, setViewingId] = useState<number | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  if (items.length === 0) {
    return <div className={EMPTY}>No compactions yet.</div>;
  }
  return (
    <div className="divide-y divide-border">
      {items.map((c) => {
        if (confirmId === c.id) {
          return (
            <div key={c.id} className="flex items-center gap-2 px-4 py-2">
              <div className="flex-1 text-xs text-foreground">Delete this compaction?</div>
              <button
                type="button"
                onClick={() => onDelete(c.id)}
                disabled={busy}
                className={DANGER_BTN}
              >
                Delete
              </button>
              <button type="button" onClick={() => setConfirmId(null)} className={GHOST_BTN}>
                Cancel
              </button>
            </div>
          );
        }
        const viewing = viewingId === c.id;
        return (
          <div key={c.id} className="px-4 py-2">
            <div className="flex items-start gap-2">
              <div className="flex-1 min-w-0">
                <p className={cn("text-xs text-foreground", !viewing && "truncate")}>{c.summary}</p>
                {viewing ? (
                  <div className="mt-1 text-3xs text-muted-foreground">
                    {c.messages_compacted} messages · {c.tokens_before ?? "?"}→
                    {c.tokens_after ?? "?"} tokens · session #{c.session_id} · {c.created_at}
                  </div>
                ) : (
                  <div className="mt-0.5 text-3xs text-muted-foreground">{c.created_at}</div>
                )}
              </div>
              {viewing ? (
                <button
                  type="button"
                  onClick={() => setViewingId(null)}
                  aria-label="Close"
                  className={ROW_BTN}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setViewingId(c.id)}
                    aria-label="View compaction"
                    className={ROW_BTN}
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmId(c.id)}
                    aria-label="Delete compaction"
                    className={ROW_BTN}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FactsTab({
  items,
  onDelete,
  busy,
}: {
  items: UserFact[];
  onDelete: (id: number) => void;
  busy: boolean;
}) {
  const [viewingId, setViewingId] = useState<number | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  if (items.length === 0) {
    return <div className={EMPTY}>No facts yet.</div>;
  }
  return (
    <div className="divide-y divide-border">
      {items.map((f) => {
        if (confirmId === f.id) {
          return (
            <div key={f.id} className="flex items-center gap-2 px-4 py-2">
              <div className="flex-1 text-xs text-foreground">Delete this fact?</div>
              <button
                type="button"
                onClick={() => onDelete(f.id)}
                disabled={busy}
                className={DANGER_BTN}
              >
                Delete
              </button>
              <button type="button" onClick={() => setConfirmId(null)} className={GHOST_BTN}>
                Cancel
              </button>
            </div>
          );
        }
        const viewing = viewingId === f.id;
        return (
          <div key={f.id} className="px-4 py-2">
            <div className="flex items-start gap-2">
              <div className="flex-1 min-w-0">
                <p className={cn("text-xs text-foreground", !viewing && "truncate")}>{f.fact}</p>
                <div className="mt-0.5 text-3xs text-muted-foreground">{f.created_at}</div>
              </div>
              {viewing ? (
                <button
                  type="button"
                  onClick={() => setViewingId(null)}
                  aria-label="Close"
                  className={ROW_BTN}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setViewingId(f.id)}
                    aria-label="View fact"
                    className={ROW_BTN}
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmId(f.id)}
                    aria-label="Delete fact"
                    className={ROW_BTN}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function HistoryTab({ items }: { items: Message[] }) {
  if (items.length === 0) {
    return <div className={EMPTY}>No history yet.</div>;
  }
  return (
    <div className="px-4 py-3 space-y-3">
      {items.map((m) => (
        <div key={m.id} className="flex flex-col">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-3xs font-medium",
                m.role === "user" ? "text-indigo-600 dark:text-indigo-400" : "text-muted-foreground"
              )}
            >
              {m.role}
            </span>
            <span className="text-2xs text-muted-foreground">{m.created_at}</span>
          </div>
          <p className="text-xs text-foreground whitespace-pre-wrap break-words">{m.content}</p>
        </div>
      ))}
    </div>
  );
}

function SkillsSection({
  busy,
  error,
  setError,
  run,
}: {
  busy: boolean;
  error: string | null;
  setError: (e: string | null) => void;
  run: (fn: () => Promise<void>) => void;
}) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewingId, setViewingId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftContent, setDraftContent] = useState("");
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [confirmClearAll, setConfirmClearAll] = useState(false);

  const loadSkills = async () => {
    setLoading(true);
    setError(null);
    try {
      setSkills(await api.listSkills());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  };

  // The section unmounts when switching away, so mount = fresh load.
  useEffect(() => {
    void loadSkills();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startEdit = (s: Skill) => {
    setEditingId(s.id);
    setDraftName(s.name);
    setDraftDescription(s.description);
    setDraftContent(s.content);
    setViewingId(null);
    setConfirmId(null);
  };

  const commitEdit = () =>
    run(async () => {
      if (editingId === null || !draftName.trim()) return;
      await api.updateSkill(
        editingId,
        draftName.trim(),
        draftDescription.trim(),
        draftContent
      );
      setEditingId(null);
      await loadSkills();
    });

  const removeSkill = (id: number) =>
    run(async () => {
      await api.deleteSkill(id);
      setConfirmId(null);
      await loadSkills();
    });

  const clearAll = () =>
    run(async () => {
      await api.clearSkills();
      setConfirmClearAll(false);
      setSkills([]);
    });

  return (
    <>
      <div className="h-10 px-4 flex items-center justify-between border-b border-border">
        <span className="text-xs font-medium text-foreground">Global skills</span>
        {skills.length > 0 &&
          (confirmClearAll ? (
            <div className="flex items-center gap-1.5">
              <span className="text-3xs text-muted-foreground">
                Delete all {skills.length} skills?
              </span>
              <button type="button" onClick={clearAll} disabled={busy} className={DANGER_BTN}>
                Clear all
              </button>
              <button
                type="button"
                onClick={() => setConfirmClearAll(false)}
                className={GHOST_BTN}
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmClearAll(true)}
              disabled={busy}
              className={GHOST_BTN}
            >
              Clear all
            </button>
          ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="mx-4 mt-2 px-2 py-1 text-3xs text-destructive bg-destructive/10 rounded-md">
            {error}
          </div>
        )}
        {loading ? (
          <div className={EMPTY}>Loading…</div>
        ) : skills.length === 0 ? (
          <div className={EMPTY}>No skills yet.</div>
        ) : (
          <div className="divide-y divide-border">
            {skills.map((s) => {
              if (confirmId === s.id) {
                return (
                  <div key={s.id} className="flex items-center gap-2 px-4 py-2">
                    <div className="flex-1 text-xs text-foreground">
                      Delete skill "{s.name}"?
                    </div>
                    <button
                      type="button"
                      onClick={() => removeSkill(s.id)}
                      disabled={busy}
                      className={DANGER_BTN}
                    >
                      Delete
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmId(null)}
                      className={GHOST_BTN}
                    >
                      Cancel
                    </button>
                  </div>
                );
              }
              if (editingId === s.id) {
                return (
                  <div key={s.id} className="px-4 py-2 space-y-1.5">
                    <div className="flex gap-1.5">
                      <div className="flex-1">
                        <label
                          htmlFor="skill-name"
                          className="block text-3xs text-muted-foreground mb-0.5"
                        >
                          Name
                        </label>
                        <input
                          id="skill-name"
                          value={draftName}
                          onChange={(e) => setDraftName(e.target.value)}
                          placeholder="name"
                          className="w-full px-2 py-1 text-xs border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400"
                          autoFocus
                        />
                      </div>
                      <div className="flex-1">
                        <label
                          htmlFor="skill-description"
                          className="block text-3xs text-muted-foreground mb-0.5"
                        >
                          Description
                        </label>
                        <input
                          id="skill-description"
                          value={draftDescription}
                          onChange={(e) => setDraftDescription(e.target.value)}
                          placeholder="description"
                          className="w-full px-2 py-1 text-xs border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400"
                        />
                      </div>
                    </div>
                    <label
                      htmlFor="skill-content"
                      className="block text-3xs text-muted-foreground mb-0.5"
                    >
                      Content
                    </label>
                    <textarea
                      id="skill-content"
                      value={draftContent}
                      onChange={(e) => setDraftContent(e.target.value)}
                      placeholder="skill content"
                      rows={6}
                      className="w-full px-2 py-1 text-xs font-mono border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-400 resize-y"
                    />
                    <div className="flex justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className={GHOST_BTN}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={commitEdit}
                        disabled={busy || !draftName.trim()}
                        className="px-2 py-1 text-xs rounded-md bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-40"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                );
              }
              const viewing = viewingId === s.id;
              return (
                <div key={s.id} className="px-4 py-2">
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-foreground truncate">{s.name}</p>
                      <p className="text-3xs text-muted-foreground truncate">
                        {s.description || "—"}
                      </p>
                      {viewing && (
                        <pre className="mt-1.5 text-3xs text-foreground whitespace-pre-wrap break-words bg-muted rounded-md p-2 max-h-40 overflow-y-auto">
                          {s.content}
                        </pre>
                      )}
                      <div className="mt-0.5 text-3xs text-muted-foreground">{s.created_at}</div>
                    </div>
                    {viewing ? (
                      <button
                        type="button"
                        onClick={() => setViewingId(null)}
                        aria-label="Close"
                        className={ROW_BTN}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => setViewingId(s.id)}
                          aria-label="View skill"
                          className={ROW_BTN}
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => startEdit(s)}
                          aria-label="Edit skill"
                          className={ROW_BTN}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmId(s.id)}
                          aria-label="Delete skill"
                          className={ROW_BTN}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}

function AppearanceSection() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [fontScale, setFontScale] = useState<FontScale>(getStoredFontScale);

  const pickTheme = (t: Theme) => {
    setTheme(t);
    applyTheme(t);
    localStorage.setItem("navee.theme", t);
  };

  const pickFontScale = (s: FontScale) => {
    setFontScale(s);
    applyFontScale(s);
    localStorage.setItem("navee.fontScale", s);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="h-10 px-4 flex items-center border-b border-border">
        <span className="text-xs font-medium text-foreground">Appearance</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div>
          <div className="text-xs text-foreground mb-2">Font size</div>
          <div className="flex gap-1.5">
            {FONT_SCALES.map((fs) => (
              <button
                key={fs.id}
                type="button"
                onClick={() => pickFontScale(fs.id)}
                className={`flex-1 px-2 py-1.5 text-xs rounded-md border transition-colors ${
                  fontScale === fs.id
                    ? "bg-indigo-500 text-white border-indigo-500"
                    : "border-border text-muted-foreground hover:bg-muted"
                }`}
              >
                {fs.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs text-foreground mb-2">Theme</div>
          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={() => pickTheme("light")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border transition-colors ${
                theme === "light"
                  ? "bg-indigo-500 text-white border-indigo-500"
                  : "border-border text-muted-foreground hover:bg-muted"
              }`}
            >
              <Sun className="w-3.5 h-3.5" />
              Light
            </button>
            <button
              type="button"
              onClick={() => pickTheme("dark")}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border transition-colors ${
                theme === "dark"
                  ? "bg-indigo-500 text-white border-indigo-500"
                  : "border-border text-muted-foreground hover:bg-muted"
              }`}
            >
              <Moon className="w-3.5 h-3.5" />
              Dark
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
