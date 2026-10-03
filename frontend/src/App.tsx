import { useEffect, useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { api, type Session } from "./api/client";
import { TopBar } from "./components/TopBar";
import { ThreadRail } from "./components/ThreadRail";
import { ChatPanel } from "./components/ChatPanel";
import { MemoryPanel } from "./components/MemoryPanel";

const SESSION_KEY = "navee.sessionId";

export default function App() {
  const [userId, setUserId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);

  // Bootstrap the chat surface: a default user, the user's backend sessions,
  // and an active session (last-used persisted in localStorage; falls back to
  // the newest existing session — never auto-created, so no phantom threads).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let users = await api.listUsers();
      if (users.length === 0) {
        users = [await api.createUser("local")];
      }
      const uid = users[0].id;
      const list = await api.listSessions(uid);
      const stored = Number(localStorage.getItem(SESSION_KEY));
      const active = list.some((s) => s.id === stored) ? stored : (list[0]?.id ?? null);
      if (active !== null) localStorage.setItem(SESSION_KEY, String(active));
      else localStorage.removeItem(SESSION_KEY);
      if (!cancelled) {
        setUserId(uid);
        setSessions(list);
        setSessionId(active);
      }
    })().catch((e) => console.error("chat bootstrap failed", e));
    return () => {
      cancelled = true;
    };
  }, []);

  const selectSession = (id: number) => {
    setSessionId(id);
    localStorage.setItem(SESSION_KEY, String(id));
  };

  const createConversation = async () => {
    if (userId === null) return;
    try {
      const s = await api.createSession(userId);
      setSessions((ss) => [s, ...ss]);
      selectSession(s.id);
    } catch (e) {
      console.error("createSession failed", e);
    }
  };

  const refreshSessions = async () => {
    if (userId === null) return;
    try {
      setSessions(await api.listSessions(userId));
    } catch (e) {
      console.error("listSessions failed", e);
    }
  };

  // The backend titles a session from its first user message; pick up the
  // new title as soon as the stream is established.
  const handleUserMessageSent = () => {
    if (sessionId !== null && sessions.some((s) => s.id === sessionId && !s.title)) {
      void refreshSessions();
    }
  };

  const renameConversation = async (id: number, title: string) => {
    try {
      const s = await api.renameSession(id, title);
      setSessions((ss) => ss.map((t) => (t.id === id ? s : t)));
    } catch (e) {
      console.error("renameSession failed", e);
    }
  };

  const deleteConversation = async (id: number) => {
    try {
      await api.deleteSession(id);
      const next = sessions.filter((t) => t.id !== id);
      setSessions(next);
      if (sessionId === id) {
        if (next.length > 0) selectSession(next[0].id);
        else setSessionId(null);
      }
    } catch (e) {
      console.error("deleteSession failed", e);
    }
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <ThreadRail
          sessions={sessions}
          activeId={sessionId}
          onSelect={selectSession}
          onCreate={createConversation}
          onRename={renameConversation}
          onDelete={deleteConversation}
        />
        <main className="flex-1 overflow-hidden">
          <PanelGroup direction="horizontal" className="h-full">
            <Panel defaultSize={35} minSize={20} className="h-full">
              {sessionId !== null ? (
                <ChatPanel sessionId={sessionId} onUserMessageSent={handleUserMessageSent} />
              ) : userId !== null ? (
                <div className="h-full grid place-items-center">
                  <button
                    type="button"
                    onClick={createConversation}
                    className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-50 transition-colors"
                  >
                    Start a conversation
                  </button>
                </div>
              ) : (
                <div className="h-full grid place-items-center text-sm text-zinc-400">
                  Loading…
                </div>
              )}
            </Panel>
            <PanelResizeHandle className="w-1 bg-zinc-200 hover:bg-indigo-500/50 transition-colors cursor-col-resize" />
            <Panel defaultSize={65} minSize={25} className="h-full">
              <MemoryPanel />
            </Panel>
          </PanelGroup>
        </main>
      </div>
    </div>
  );
}
