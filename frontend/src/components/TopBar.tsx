import { useState } from "react";
import { Bot, Settings } from "lucide-react";

const SETTINGS_ITEMS = [
  "Profile",
  "Appearance",
  "Notifications",
  "Model",
  "Data & Privacy",
] as const;

export function TopBar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="h-[48px] flex items-center justify-between px-4 border-b border-zinc-200 bg-white flex-shrink-0">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-indigo-500 flex items-center justify-center">
          <Bot className="w-4 h-4 text-white" />
        </div>
        <span className="font-semibold text-sm text-zinc-800">Navee</span>
      </div>

      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="p-1.5 rounded-md hover:bg-zinc-100 transition-colors text-zinc-500"
          aria-label="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
        {open && (
          <div className="absolute right-0 top-full mt-1 w-44 rounded-md border border-zinc-200 bg-white shadow-md py-1 z-50">
            {SETTINGS_ITEMS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setOpen(false)}
                className="w-full text-left px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50 transition-colors"
              >
                {item}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
