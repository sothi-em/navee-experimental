import { useEffect, useState } from "react";
import {
  Activity,
  Archive,
  Database,
  Gauge,
  Globe,
  User,
  type LucideIcon,
} from "lucide-react";
import {
  api,
  type ContextBudgetStats,
  type MemoryStats,
} from "../api/client";

interface Card {
  title: string;
  icon: LucideIcon;
  iconClass: string;
}

const CARDS: Card[] = [
  { title: "External Store Memory", icon: Database, iconClass: "text-datatype-sky" },
  { title: "Context Budget", icon: Gauge, iconClass: "text-datatype-amber" },
  { title: "Global Skills", icon: Globe, iconClass: "text-datatype-teal" },
  { title: "User Facts", icon: User, iconClass: "text-datatype-purple" },
  { title: "Compaction History", icon: Archive, iconClass: "text-datatype-orange" },
];

const BUDGET_SEGMENTS = [
  { key: "system_prompt", label: "System prompts", color: "bg-datatype-indigo" },
  { key: "compaction", label: "Compaction", color: "bg-datatype-purple" },
  { key: "current_chat", label: "Current chat", color: "bg-datatype-amber" },
  { key: "user_facts", label: "User facts", color: "bg-datatype-teal" },
  { key: "skills", label: "Skills", color: "bg-datatype-fuchsia" },
] as const;

function truncate(s: string, n = 64): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground tabular-nums">{value}</span>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="text-xs text-muted-foreground">{text}</div>;
}

function Skeleton() {
  return (
    <>
      <div className="h-2 rounded bg-muted w-3/4" />
      <div className="h-2 rounded bg-muted w-1/2" />
      <div className="h-2 rounded bg-muted w-2/3" />
    </>
  );
}

function BudgetSkeleton() {
  return (
    <>
      <div className="h-1.5 rounded-full bg-muted flex overflow-hidden">
        <div className="h-full w-1/4 bg-datatype-indigo" />
        <div className="h-full w-1/6 bg-datatype-purple" />
        <div className="h-full w-1/3 bg-datatype-amber" />
      </div>
      <div className="space-y-1">
        {BUDGET_SEGMENTS.slice(0, 3).map((s) => (
          <div key={s.key} className="flex items-center gap-1.5 text-3xs text-muted-foreground">
            <span className={`w-1.5 h-1.5 rounded-full ${s.color}`} />
            {s.label}
          </div>
        ))}
      </div>
    </>
  );
}

function BudgetBody({ b }: { b: ContextBudgetStats }) {
  const used =
    b.system_prompt + b.compaction + b.current_chat + b.user_facts + b.skills;
  const pct = (v: number) => (b.total > 0 ? (v / b.total) * 100 : 0);
  return (
    <>
      <div className="text-xs font-medium text-foreground tabular-nums">
        {used} / {b.total} tokens
      </div>
      <div className="h-1.5 rounded-full bg-muted flex overflow-hidden">
        {BUDGET_SEGMENTS.map((s) => {
          const v = b[s.key];
          if (v <= 0) return null;
          return (
            <div
              key={s.key}
              className={s.color}
              style={{ width: `${Math.max(pct(v), 0.75)}%` }}
            />
          );
        })}
      </div>
      <div className="space-y-1">
        {BUDGET_SEGMENTS.map((s) => (
          <div key={s.key} className="flex items-center gap-1.5 text-3xs text-muted-foreground">
            <span className={`w-1.5 h-1.5 rounded-full ${s.color}`} />
            <span className="flex-1">{s.label}</span>
            <span className="tabular-nums">{b[s.key]}</span>
          </div>
        ))}
      </div>
    </>
  );
}

export function MemoryPanel({
  userId,
  sessionId,
  tick,
}: {
  userId: number | null;
  sessionId: number | null;
  tick: number;
}) {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (userId === null) return;
    let cancelled = false;
    api
      .memoryStats(userId, sessionId)
      .then((s) => {
        if (!cancelled) {
          setStats(s);
          setError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setStats(null);
          setError(e instanceof Error ? e.message : String(e));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [userId, sessionId, tick]);

  const body = (title: string) => {
    if (error !== null)
      return <div className="text-xs text-datatype-red dark:text-red-400">Failed to load: {error}</div>;
    if (stats === null) return title === "Context Budget" ? <BudgetSkeleton /> : <Skeleton />;

    switch (title) {
      case "External Store Memory": {
        const e = stats.external_store;
        return (
          <>
            <div className="flex items-center gap-1.5 text-xs text-foreground">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  e.vector_recall ? "bg-datatype-emerald" : "bg-datatype-amber"
                }`}
              />
              Vector recall {e.vector_recall ? "healthy" : "degraded"}
            </div>
            <StatRow label="Durable transcript" value={`${e.messages_total} messages`} />
            <StatRow label="This session" value={`${e.messages_session} messages`} />
            <StatRow label="Sessions" value={String(e.sessions_total)} />
          </>
        );
      }
      case "Context Budget":
        return <BudgetBody b={stats.context_budget} />;
      case "Global Skills":
        if (stats.skills.length === 0) return <Empty text="No skills yet." />;
        return (
          <>
            <StatRow label="Skills" value={String(stats.skills.length)} />
            {[...stats.skills]
              .reverse()
              .slice(0, 5)
              .map((s) => (
                <div key={s.id} className="text-xs">
                  <div className="font-medium text-foreground truncate">{s.name}</div>
                  {s.description && (
                    <div className="text-muted-foreground truncate">{truncate(s.description)}</div>
                  )}
                </div>
              ))}
          </>
        );
      case "User Facts":
        if (stats.user_facts.length === 0) return <Empty text="No facts yet." />;
        return (
          <>
            <StatRow label="Facts" value={String(stats.user_facts.length)} />
            {[...stats.user_facts]
              .reverse()
              .slice(0, 5)
              .map((f) => (
                <div key={f.id} className="text-xs text-foreground truncate">
                  {truncate(f.fact)}
                </div>
              ))}
          </>
        );
      case "Compaction History":
        if (stats.compactions.length === 0) return <Empty text="No compactions yet." />;
        return (
          <>
            <StatRow label="Compactions" value={String(stats.compactions.length)} />
            {[...stats.compactions]
              .reverse()
              .slice(0, 3)
              .map((c) => (
                <div key={c.id} className="text-xs">
                  <div className="text-foreground">
                    {c.tokens_before !== null && c.tokens_after !== null
                      ? `${c.tokens_before} → ${c.tokens_after} tokens`
                      : `${c.messages_compacted} messages`}
                  </div>
                  <div className="text-muted-foreground">
                    {c.created_at ? new Date(c.created_at).toLocaleString() : ""}
                  </div>
                </div>
              ))}
          </>
        );
      default:
        return null;
    }
  };

  return (
    <section className="h-full flex flex-col bg-background">
      <div className="h-10 px-4 flex items-center gap-2 border-b border-border">
        <Activity className="w-4 h-4 text-indigo-500" />
        <span className="text-sm font-medium text-foreground">Memory &amp; Metrics</span>
        <div className="flex-1" />
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium text-foreground bg-muted border border-border">
          <span className="w-1.5 h-1.5 rounded-full bg-datatype-emerald animate-pulse" />
          live
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 grid grid-cols-2 gap-3 content-start">
        {CARDS.map((card) => (
          <div
            key={card.title}
            className="border border-border rounded-lg overflow-hidden bg-background"
          >
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border">
              <card.icon className={`w-3.5 h-3.5 ${card.iconClass}`} />
              <span className="text-sm font-medium text-foreground">{card.title}</span>
            </div>
            <div className="px-3 py-3 space-y-2">{body(card.title)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
