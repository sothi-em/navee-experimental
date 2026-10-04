import { useState } from "react";
import { Bot, Settings } from "lucide-react";
import { SettingsModal } from "./SettingsModal";

export function TopBar() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <header className="h-[48px] flex items-center justify-between px-4 border-b border-zinc-200 bg-white flex-shrink-0">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-indigo-500 flex items-center justify-center">
          <Bot className="w-4 h-4 text-white" />
        </div>
        <span className="font-semibold text-sm text-zinc-800">Navee</span>
      </div>

      <button
        type="button"
        onClick={() => setSettingsOpen(true)}
        className="p-1.5 rounded-md hover:bg-zinc-100 transition-colors text-zinc-500"
        aria-label="Settings"
      >
        <Settings className="w-4 h-4" />
      </button>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </header>
  );
}
