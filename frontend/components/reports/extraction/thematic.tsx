import { Badge } from "@/components/ui/badge";
import type { ReportExtraction } from "@/lib/types";
import { BulletList, KeyValueGrid, Section } from "./shared";

interface ThematicExtras {
  topic?: string;
  key_findings?: string[];
  affected_tickers?: Array<{ ticker: string; impact: "POSITIVE" | "NEUTRAL" | "NEGATIVE"; rationale?: string | null }>;
  policy_references?: string[];
}

const IMPACT_CLASS: Record<string, string> = {
  POSITIVE: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  NEUTRAL: "bg-muted text-muted-foreground",
  NEGATIVE: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30",
};

export function ThematicExtractionView({ ext }: { ext: ReportExtraction }) {
  const extras = (ext.extras ?? {}) as ThematicExtras;

  return (
    <div className="space-y-5">
      <KeyValueGrid entries={[{ label: "Topic", value: extras.topic }]} />

      <Section title="Key findings">
        <BulletList items={extras.key_findings ?? []} />
      </Section>

      {extras.affected_tickers?.length ? (
        <Section title="Affected tickers">
          <div className="space-y-2">
            {extras.affected_tickers.map((t, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="font-mono">
                    {t.ticker}
                  </Badge>
                  <Badge variant="outline" className={IMPACT_CLASS[t.impact]}>
                    {t.impact}
                  </Badge>
                </div>
                {t.rationale && <div className="mt-1 text-muted-foreground">{t.rationale}</div>}
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {extras.policy_references?.length ? (
        <Section title="Policy references">
          <BulletList items={extras.policy_references} />
        </Section>
      ) : null}
    </div>
  );
}
