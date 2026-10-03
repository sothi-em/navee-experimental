import { useEffect, useState } from "react";
import { api, Message, Session, User } from "./api/client";

export default function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshUsers() {
    try {
      setUsers(await api.listUsers());
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    refreshUsers();
  }, []);

  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    try {
      await api.createUser(username.trim());
      setUsername("");
      await refreshUsers();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleCreateSession(user: User) {
    setError(null);
    try {
      const s = await api.createSession(user.id, `Session — ${user.username}`);
      setSession(s);
      setMessages([]);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!session || !input.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const msgs = await api.sendMessage(session.id, "user", input.trim());
      setMessages(msgs);
      setInput("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4">
        <h1 className="text-xl font-semibold">Navee — long-form agent chat lab</h1>
        <p className="text-sm text-slate-400">
          Experimental dashboard for LLM agent chat, recall, and learned state.
        </p>
      </header>

      <main className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-3">
        <section className="lg:col-span-1">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Users
          </h2>
          <form onSubmit={handleCreateUser} className="mb-4 flex gap-2">
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="username"
              className="flex-1 rounded bg-slate-900 px-3 py-2 text-sm outline-none ring-1 ring-slate-800 focus:ring-slate-600"
            />
            <button className="rounded bg-slate-700 px-3 py-2 text-sm hover:bg-slate-600">
              Add
            </button>
          </form>
          <ul className="space-y-2">
            {users.map((u) => (
              <li
                key={u.id}
                className="flex items-center justify-between rounded bg-slate-900 px-3 py-2 ring-1 ring-slate-800"
              >
                <span>
                  <span className="font-medium">{u.username}</span>
                  <span className="ml-2 text-xs text-slate-500">#{u.id}</span>
                </span>
                <button
                  onClick={() => handleCreateSession(u)}
                  className="rounded bg-indigo-600 px-2 py-1 text-xs hover:bg-indigo-500"
                >
                  New session
                </button>
              </li>
            ))}
            {users.length === 0 && (
              <li className="text-sm text-slate-500">No users yet. Add one above.</li>
            )}
          </ul>
        </section>

        <section className="lg:col-span-2">
          <div className="flex h-[70vh] flex-col rounded bg-slate-900 ring-1 ring-slate-800">
            <div className="border-b border-slate-800 px-4 py-3 text-sm">
              {session ? (
                <span>Session #{session.id}</span>
              ) : (
                <span className="text-slate-500">
                  Select a user and start a new session to chat.
                </span>
              )}
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`max-w-[80%] rounded px-3 py-2 text-sm ${
                    m.role === "user" ? "ml-auto bg-indigo-600" : "bg-slate-800"
                  }`}
                >
                  <div className="mb-1 text-xs uppercase opacity-60">{m.role}</div>
                  {m.content}
                </div>
              ))}
              {messages.length === 0 && session && (
                <div className="text-sm text-slate-500">Say something to begin.</div>
              )}
            </div>
            <form onSubmit={handleSend} className="flex gap-2 border-t border-slate-800 p-3">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={!session || busy}
                placeholder={session ? "Type a message…" : "No active session"}
                className="flex-1 rounded bg-slate-950 px-3 py-2 text-sm outline-none ring-1 ring-slate-800 focus:ring-slate-600 disabled:opacity-50"
              />
              <button
                disabled={!session || busy}
                className="rounded bg-indigo-600 px-4 py-2 text-sm hover:bg-indigo-500 disabled:opacity-50"
              >
                {busy ? "…" : "Send"}
              </button>
            </form>
          </div>
          {error && (
            <div className="mt-3 rounded bg-red-950 px-3 py-2 text-sm text-red-300 ring-1 ring-red-900">
              {error}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
