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

export interface ToolEvent {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
}

export interface StreamCallbacks {
  /** Fired once the response is established — the user message is persisted
   *  and the session title (first message) is set by then. */
  onStart?: () => void;
  onDelta?: (content: string) => void;
  /** Fired when a tool call begins (before it runs). */
  onToolStart?: (tool: ToolEvent) => void;
  /** Fired when a tool call completes; `result` is set. */
  onTool?: (tool: ToolEvent) => void;
  onError?: (message: string) => void;
  onDone?: (messageId: number | null) => void;
}

export class StreamError extends Error {
  status: number;
  constructor(status: number) {
    super(`Stream request failed: ${status}`);
    this.status = status;
  }
}

// POST-based SSE: EventSource only supports GET, so we read the fetch body
// stream and parse `event:`/`data:` frames (sse-starlette emits CRLF).
export async function streamMessage(
  sessionId: number,
  content: string,
  cb: StreamCallbacks
): Promise<void> {
  const res = await fetch(`/api/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok || !res.body) {
    throw new StreamError(res.status);
  }
  cb.onStart?.();
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    buf = buf.replace(/\r\n/g, "\n");
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      if (frame.trim()) handleFrame(frame, cb);
    }
  }
}

function handleFrame(frame: string, cb: StreamCallbacks): void {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
    // comment lines (": ping") and anything else are ignored
  }
  if (dataLines.length === 0) return;
  let data: {
    type?: string;
    content?: string;
    id?: string;
    name?: string;
    arguments?: Record<string, unknown>;
    result?: string;
    message?: string;
    message_id?: number | null;
  };
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    return;
  }
  switch (event) {
    case "delta":
      if (data.content) cb.onDelta?.(data.content);
      break;
    case "tool_start":
      if (data.name) cb.onToolStart?.({ id: data.id ?? "", name: data.name, arguments: data.arguments ?? {} });
      break;
    case "tool":
      if (data.name)
        cb.onTool?.({ id: data.id ?? "", name: data.name, arguments: data.arguments ?? {}, result: data.result ?? "" });
      break;
    case "error":
      cb.onError?.(data.message ?? "unknown error");
      break;
    case "done":
      cb.onDone?.(data.message_id ?? null);
      break;
  }
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
  listSessions: (userId: number) =>
    request<Session[]>(`/api/chat/sessions?user_id=${userId}`),
  renameSession: (id: number, title: string) =>
    request<Session>(`/api/chat/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteSession: (id: number) =>
    request<{ deleted: boolean }>(`/api/chat/sessions/${id}`, { method: "DELETE" }),
  listMessages: (sessionId: number) =>
    request<Message[]>(`/api/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: number, role: string, content: string) =>
    request<Message[]>(`/api/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ role, content }),
    }),
};
