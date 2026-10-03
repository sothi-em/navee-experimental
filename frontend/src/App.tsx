import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { TopBar } from "./components/TopBar";
import { ThreadRail } from "./components/ThreadRail";
import { ChatPanel } from "./components/ChatPanel";
import { MemoryPanel } from "./components/MemoryPanel";

export default function App() {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <ThreadRail />
        <main className="flex-1 overflow-hidden">
          <PanelGroup direction="horizontal" className="h-full">
            <Panel defaultSize={35} minSize={20} className="h-full">
              <ChatPanel />
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
