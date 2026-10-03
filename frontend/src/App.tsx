import { useEffect, useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { api } from "./api/client";
import { TopBar } from "./components/TopBar";
import { ThreadRail } from "./components/ThreadRail";
import { ChatPanel } from "./components/ChatPanel";
import { MemoryPanel } from "./components/MemoryPanel";

const SESSION_KEY = "navee.sessionId";

export default function App() {
  const [sessionId, setSessionId] = useState<number | null>(null);

  // Bootstrap the chat surface: a default user and a session (persisted in
  // localStorage so the transcript survives page reloads).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let users = await api.listUsers();
      if (users.length === 0) {
        users = [await api.createUser("local")];
      }
      const stored = Number(localStorage.getItem(SESSION_KEY));
      const id = stored > 0 ? stored : (await api.createSession(users[0].id)).id;
      localStorage.setItem(SESSION_KEY, String(id));
      if (!cancelled) setSessionId(id);
    })().catch((e) => console.error("chat bootstrap failed", e));
    return () => {
      cancelled = true;
    };
  }, []);
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <ThreadRail />
        <main className="flex-1 overflow-hidden">
          <PanelGroup direction="horizontal" className="h-full">
            <Panel defaultSize={35} minSize={20} className="h-full">
              {sessionId !== null ? (
                <ChatPanel sessionId={sessionId} />
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
