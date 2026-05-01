import { Badge } from "@/components/ui/badge";
import type { ReportExtraction } from "@/lib/types";
import { formatPrice } from "@/lib/utils";
import { KeyValueGrid, Section } from "./shared";

interface TechnicalExtras {
  period?: string;
  commentary?: string | null;
  index_outlook?: Array<{
    symbol: string;
    direction?: "BULLISH" | "BEARISH" | "SIDEWAYS";
    support?: number[];
    resistance?: number[];
    commentary?: string | null;
  }>;
  top_signals?: Array<{
    ticker: string;
    signal: string;
    entry_price?: number | string;
    stop_loss?: number | string;
    target?: number | string;
  }>;
}

const DIR_CLASS: Record<string, string> = {
  BULLISH: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  SIDEWAYS: "bg-muted text-muted-foreground",
  BEARISH: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30",
};

export function TechnicalExtractionView({ ext }: { ext: ReportExtraction }) {
  const extras = (ext.extras ?? {}) as TechnicalExtras;

  return (
    <div className="space-y-5">
      <KeyValueGrid entries={[{ label: "Period", value: extras.period }]} />

      {extras.index_outlook?.length ? (
        <Section title="Index outlooks">
          <div className="space-y-2">
            {extras.index_outlook.map((o, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium font-mono">{o.symbol}</span>
                  {o.direction && (
                    <Badge variant="outline" className={DIR_CLASS[o.direction]}>
                      {o.direction}
                    </Badge>
                  )}
                </div>
                <div className="mt-1 grid grid-cols-2 gap-x-4 text-xs">
                  <div>
                    <span className="text-muted-foreground">Support: </span>
                    <span className="tabular-nums">{o.support?.join(", ") || "—"}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Resistance: </span>
                    <span className="tabular-nums">{o.resistance?.join(", ") || "—"}</span>
                  </div>
                </div>
                {o.commentary && <div className="mt-1 text-muted-foreground">{o.commentary}</div>}
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {extras.top_signals?.length ? (
        <Section title="Top signals">
          <div className="space-y-2">
            {extras.top_signals.map((s, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="font-mono">
                    {s.ticker}
                  </Badge>
                  <Badge variant="outline">{s.signal}</Badge>
                </div>
                <div className="mt-1 grid grid-cols-3 gap-x-2 text-xs tabular-nums">
                  <div>
                    <span className="text-muted-foreground">Entry: </span>
                    {formatPrice(s.entry_price ?? null, "VND")}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Stop: </span>
                    {formatPrice(s.stop_loss ?? null, "VND")}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Target: </span>
                    {formatPrice(s.target ?? null, "VND")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {extras.commentary && (
        <Section title="Commentary">
          <p className="text-sm text-muted-foreground">{extras.commentary}</p>
        </Section>
      )}
    </div>
  );
}
