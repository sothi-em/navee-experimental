import {
  Activity,
  Archive,
  Database,
  Gauge,
  Globe,
  User,
  type LucideIcon,
} from "lucide-react";

interface Card {
  title: string;
  icon: LucideIcon;
  iconClass: string;
  budget?: boolean;
}

const CARDS: Card[] = [
  {
    title: "External Store Memory",
    icon: Database,
    iconClass: "text-datatype-sky",
  },
  {
    title: "Context Budget",
    icon: Gauge,
    iconClass: "text-datatype-amber",
    budget: true,
  },
  {
    title: "Global Skills",
    icon: Globe,
    iconClass: "text-datatype-teal",
  },
  {
    title: "User Facts",
    icon: User,
    iconClass: "text-datatype-purple",
  },
  {
    title: "Compaction History",
    icon: Archive,
    iconClass: "text-datatype-orange",
  },
];

export function MemoryPanel() {
  return (
    <section className="h-full flex flex-col bg-background">
      <div className="h-10 px-4 flex items-center gap-2 border-b border-zinc-200">
        <Activity className="w-4 h-4 text-indigo-500" />
        <span className="text-xs font-medium text-zinc-700">Memory &amp; Metrics</span>
        <div className="flex-1" />
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium text-zinc-600 bg-zinc-50 border border-zinc-200">
          <span className="w-1.5 h-1.5 rounded-full bg-datatype-emerald animate-pulse" />
          live
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 grid grid-cols-2 gap-3 content-start">
        {CARDS.map((card) => (
          <div
            key={card.title}
            className="border border-zinc-200 rounded-lg overflow-hidden bg-white"
          >
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-zinc-200">
              <card.icon className={`w-3.5 h-3.5 ${card.iconClass}`} />
              <span className="text-xs font-medium text-zinc-700">{card.title}</span>
            </div>
            <div className="px-3 py-3 space-y-2">
              {card.budget ? (
                <>
                  <div className="h-1.5 rounded-full bg-zinc-100 flex overflow-hidden">
                    <div className="h-full w-1/4 bg-datatype-indigo" />
                    <div className="h-full w-1/6 bg-datatype-purple" />
                    <div className="h-full w-1/3 bg-datatype-amber" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                      <span className="w-1.5 h-1.5 rounded-full bg-datatype-indigo" />
                      System prompts
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                      <span className="w-1.5 h-1.5 rounded-full bg-datatype-purple" />
                      Compaction
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                      <span className="w-1.5 h-1.5 rounded-full bg-datatype-amber" />
                      Current chat
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="text-xs text-zinc-500">
                    Live data appears here as you converse.
                  </div>
                  <div className="h-2 rounded bg-zinc-100 w-3/4" />
                  <div className="h-2 rounded bg-zinc-100 w-1/2" />
                  <div className="h-2 rounded bg-zinc-100 w-2/3" />
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
