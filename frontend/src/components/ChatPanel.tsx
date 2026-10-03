import ReactMarkdown from "react-markdown";
import { Bot, Send } from "lucide-react";

const STUB_REPLY = `Stub reply — the live agent lands in the next pass.

- **Memory** is organized into stores
- \`context budget\` tracks token usage`;

export function ChatPanel() {
  return (
    <section className="h-full flex flex-col bg-background">
      <div className="h-10 px-4 flex items-center gap-2 border-b border-zinc-200">
        <Bot className="w-4 h-4 text-indigo-500" />
        <span className="text-xs font-medium text-zinc-700">Agent</span>
        <span className="w-1.5 h-1.5 rounded-full bg-datatype-emerald" />
        <span className="text-[10px] text-zinc-400">online</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <div>
          <div className="text-[10px] text-zinc-400 text-right">you</div>
          <div className="ml-auto w-fit max-w-[80%] px-3 py-2 rounded-lg bg-indigo-500 text-white text-sm">
            How is memory organized?
          </div>
        </div>
        <div>
          <div className="text-[10px] text-zinc-400">agent</div>
          <div className="prose prose-sm max-w-none text-zinc-800">
            <ReactMarkdown>{STUB_REPLY}</ReactMarkdown>
          </div>
        </div>
      </div>

      <div className="p-3 border-t border-zinc-200">
        <div className="flex gap-2">
          <input
            placeholder="Message the agent…"
            className="flex-1 px-3 py-2 rounded-md border border-zinc-200 bg-zinc-50 text-sm text-zinc-800 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="button"
            disabled
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
