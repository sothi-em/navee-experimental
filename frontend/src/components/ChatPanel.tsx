import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Loader2, Send, Wrench } from "lucide-react";
import { api, streamMessage, StreamError, type ToolEvent } from "../api/client";

interface ChatMsg {
  id: number | null; // backend id; null while the turn is in flight
  role: "user" | "assistant";
  content: string;
  tools?: ToolState[];
  error?: string;
  streaming?: boolean;
}

interface ToolState extends ToolEvent {
  status: "running" | "ok" | "error";
}

function ToolPill({ tool }: { tool: ToolState }) {
  const [open, setOpen] = useState(false);
  const args = Object.keys(tool.arguments);
  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs text-zinc-500 hover:bg-zinc-100 transition-colors"
      >
        {tool.status === "running" && <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />}
        {tool.status !== "running" && (
          <Wrench className={`w-3 h-3 ${tool.status === "ok" ? "text-emerald-600" : "text-red-600"}`} />
        )}
        {tool.name}
      </button>
      {open && (
        <div className="mt-1.5 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2">
          {args.length > 0 && (
            <pre className="text-[10px] leading-4 text-zinc-500 overflow-x-auto">
              {JSON.stringify(tool.arguments)}
            </pre>
          )}
          {tool.result !== undefined && (
            <pre className="mt-1 text-[11px] leading-4 text-zinc-700 overflow-x-auto whitespace-pre-wrap">
              {tool.result}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export function ChatPanel({
  sessionId,
  onUserMessageSent,
}: {
  sessionId: number;
  onUserMessageSent?: () => void;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Load the persisted transcript when the session changes.
  useEffect(() => {
    let cancelled = false;
    api
      .listMessages(sessionId)
      .then((rows) => {
        if (!cancelled) {
          setMessages(
            rows.map((m) => ({ id: m.id, role: m.role as "user" | "assistant", content: m.content }))
          );
        }
      })
      .catch((e) => console.error("listMessages failed", e));
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Keep the newest content in view.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const patchLastAssistant = (patch: (m: ChatMsg) => ChatMsg) =>
    setMessages((ms) => {
      const i = ms.length - 1;
      if (i < 0 || ms[i].role !== "assistant") return ms;
      const next = [...ms];
      next[i] = patch(next[i]);
      return next;
    });

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setStreaming(true);
    setMessages((ms) => [
      ...ms,
      { id: null, role: "user", content: text },
      { id: null, role: "assistant", content: "", streaming: true },
    ]);
    try {
      await streamMessage(sessionId, text, {
        onStart: onUserMessageSent,
        onDelta: (c) => patchLastAssistant((m) => ({ ...m, content: m.content + c })),
        onToolStart: (t) =>
          patchLastAssistant((m) => ({
            ...m,
            tools: [...(m.tools ?? []), { ...t, status: "running" as const }],
          })),
        onTool: (t) =>
          patchLastAssistant((m) => {
            const status: ToolState["status"] = t.result?.startsWith("error:") ? "error" : "ok";
            const tools = m.tools ?? [];
            return {
              ...m,
              tools: tools.some((x) => x.id === t.id)
                ? tools.map((x) => (x.id === t.id ? { ...x, ...t, status } : x))
                : [...tools, { ...t, status }],
            };
          }),
        onError: (msg) => patchLastAssistant((m) => ({ ...m, error: msg })),
        onDone: (id) => patchLastAssistant((m) => ({ ...m, id })),
      });
    } catch (e) {
      const msg =
        e instanceof StreamError
          ? e.status === 404
            ? "Session not found — the backend store may have been reset."
            : `Stream request failed: ${e.status}`
          : e instanceof Error
            ? e.message
            : String(e);
      patchLastAssistant((m) => ({ ...m, error: msg }));
    } finally {
      patchLastAssistant((m) => ({ ...m, streaming: false }));
      setStreaming(false);
    }
  };

  return (
    <section className="h-full flex flex-col bg-background">
      <div className="h-10 px-4 flex items-center gap-2 border-b border-zinc-200">
        <Bot className="w-4 h-4 text-indigo-500" />
        <span className="text-xs font-medium text-zinc-700">Agent</span>
        <span className="w-1.5 h-1.5 rounded-full bg-datatype-emerald" />
        <span className="text-[10px] text-zinc-400">online</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-xs text-zinc-400 text-center pt-8">
            Start a conversation — the agent streams its reply and tool activity here.
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={m.id ?? `u-${i}`}>
              <div className="text-[10px] text-zinc-400 text-right">you</div>
              <div className="ml-auto w-fit max-w-[80%] px-3 py-2 rounded-lg bg-indigo-500 text-white text-sm">
                {m.content}
              </div>
            </div>
          ) : (
            <div key={m.id ?? `a-${i}`}>
              <div className="text-[10px] text-zinc-400">agent</div>
              {m.tools?.map((t, j) => (
                <ToolPill key={t.id || j} tool={t} />
              ))}
              {m.content && (
                <div className="prose prose-sm max-w-none text-zinc-800">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                  {m.streaming && (
                    <span className="inline-block w-2 h-4 ml-0.5 bg-indigo-400 align-text-bottom animate-pulse" />
                  )}
                </div>
              )}
              {m.streaming && !m.content && m.tools === undefined && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs text-zinc-500">
                  <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />
                  thinking
                </span>
              )}
              {m.error && (
                <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md px-2 py-1 mt-1">
                  {m.error}
                </div>
              )}
            </div>
          )
        )}
        <div ref={endRef} />
      </div>

      <div className="p-3 border-t border-zinc-200">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Message the agent…"
            disabled={streaming}
            className="flex-1 px-3 py-2 rounded-md border border-zinc-200 bg-zinc-50 text-sm text-zinc-800 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={send}
            disabled={streaming || input.trim() === ""}
            className="px-3 rounded-md bg-indigo-500 text-white hover:bg-indigo-600 transition-colors disabled:opacity-50"
            aria-label="Send"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </section>
  );
}
