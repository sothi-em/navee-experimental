import { useEffect, useRef, useState } from "react";
import { Panda, ChevronDown, Check, Settings } from "lucide-react";
import type { User } from "../api/client";
import { SettingsModal } from "./SettingsModal";

export function TopBar({
  users,
  currentUserId,
  onSwitchUser,
}: {
  users: User[];
  currentUserId: number | null;
  onSwitchUser: (id: number) => void;
}) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const currentUser = users.find((u) => u.id === currentUserId);

  // Close the dropdown when clicking outside.
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  return (
    <header className="h-[48px] flex items-center justify-between px-4 border-b border-border bg-background flex-shrink-0">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center">
          <Panda className="w-5 h-5 text-green-500" />
        </div>

        {/* User switcher */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            className="flex items-center gap-1 px-2 py-1 rounded-md hover:bg-muted transition-colors"
          >
            <span className="font-semibold text-sm text-foreground">
              {currentUser?.username ?? "…"}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
          </button>

          {menuOpen && (
            <div className="absolute top-full left-0 mt-1 w-44 rounded-md border border-border bg-background shadow-md z-50 py-1">
              {users.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    if (u.id !== currentUserId) onSwitchUser(u.id);
                  }}
                  className="w-full flex items-center justify-between px-3 py-1.5 text-sm text-foreground hover:bg-muted transition-colors"
                >
                  <span className="truncate">
                    {u.username}
                    {u.display_name && (
                      <span className="text-muted-foreground text-xs ml-1.5">{u.display_name}</span>
                    )}
                  </span>
                  {u.id === currentUserId && <Check className="w-3.5 h-3.5 text-indigo-500" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={() => setSettingsOpen(true)}
        className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground"
        aria-label="Settings"
      >
        <Settings className="w-4 h-4" />
      </button>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </header>
  );
}
