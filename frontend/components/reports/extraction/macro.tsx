import { Badge } from "@/components/ui/badge";
import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import type { ReportExtraction } from "@/lib/types";
import { BulletList, KeyValueGrid, Section } from "./shared";

interface Indicator {
  value?: number | null;
  unit?: string | null;
  direction?: "UP" | "DOWN" | "FLAT" | null;
  commentary?: string | null;
}

interface MacroExtras {
  period?: string;
  market_outlook?: "POSITIVE" | "NEUTRAL" | "NEGATIVE";
  gdp_outlook?: Indicator;
  inflation_outlook?: Indicator;
  interest_rate_outlook?: Indicator;
  fx_outlook?: Indicator;
  key_themes?: string[];
  recommended_sectors?: string[];
}

function DirectionIcon({ d }: { d?: string | null }) {
  if (d === "UP") return <ArrowUp className="h-3.5 w-3.5 text-emerald-600" />;
  if (d === "DOWN") return <ArrowDown className="h-3.5 w-3.5 text-red-600" />;
  if (d === "FLAT") return <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />;
  return null;
}

function IndicatorRow({ label, ind }: { label: string; ind?: Indicator }) {
  if (!ind) return null;
  return (
    <div className="rounded-md border p-3 text-sm">
      <div className="flex items-baseline justify-between">
        <span className="font-medium">{label}</span>
        <span className="flex items-center gap-1 tabular-nums">
          <DirectionIcon d={ind.direction} />
          {ind.value !== null && ind.value !== undefined ? ind.value : "—"}
          {ind.unit ? <span className="text-muted-foreground">{ind.unit}</span> : null}
        </span>
      </div>
      {ind.commentary && <div className="mt-1 text-muted-foreground">{ind.commentary}</div>}
    </div>
  );
}

export function MacroExtractionView({ ext }: { ext: ReportExtraction }) {
  const extras = (ext.extras ?? {}) as MacroExtras;

  return (
    <div className="space-y-5">
      <KeyValueGrid
        entries={[
          { label: "Period", value: extras.period },
          { label: "Market outlook", value: extras.market_outlook ? <Badge variant="outline">{extras.market_outlook}</Badge> : null },
        ]}
      />

      <Section title="Indicators">
        <div className="space-y-2">
          <IndicatorRow label="GDP" ind={extras.gdp_outlook} />
          <IndicatorRow label="Inflation" ind={extras.inflation_outlook} />
          <IndicatorRow label="Interest rate" ind={extras.interest_rate_outlook} />
          <IndicatorRow label="FX" ind={extras.fx_outlook} />
        </div>
      </Section>

      <Section title="Key themes">
        <BulletList items={extras.key_themes ?? []} />
      </Section>

      <Section title="Recommended sectors">
        <div className="flex flex-wrap gap-1.5">
          {(extras.recommended_sectors ?? []).map((s, i) => (
            <Badge key={i} variant="secondary">
              {s}
            </Badge>
          ))}
        </div>
      </Section>
    </div>
  );
}
