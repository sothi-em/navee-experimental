// Typed client for the Navee backend. Uses relative /api URLs, which the Vite
// dev server proxies to FastAPI (see vite.config.ts).

export interface User {
  id: number;
  username: string;
  display_name: string | null;
  created_at: string | null;
}

export interface Session {
  id: number;
  user_id: number;
  title: string | null;
  created_at: string | null;
}

export interface Message {
  id: number;
  session_id: number;
  role: string;
  content: string;
  created_at: string | null;
}

export interface Health {
  status: string;
  llm_base_url: string;
  llm_model: string;
  vector_recall: boolean;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  listUsers: () => request<User[]>("/api/users"),
  createUser: (username: string, displayName?: string) =>
    request<User>("/api/users", {
      method: "POST",
      body: JSON.stringify({ username, display_name: displayName }),
    }),
  createSession: (userId: number, title?: string) =>
    request<Session>("/api/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, title }),
    }),
  listMessages: (sessionId: number) =>
    request<Message[]>(`/api/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: number, role: string, content: string) =>
    request<Message[]>(`/api/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ role, content }),
    }),
};
