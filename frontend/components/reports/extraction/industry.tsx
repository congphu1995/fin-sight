import { Badge } from "@/components/ui/badge";
import type { ReportExtraction } from "@/lib/types";
import { formatPrice } from "@/lib/utils";
import { BulletList, KeyValueGrid, Section } from "./shared";

interface IndustryExtras {
  industry?: string;
  outlook?: "POSITIVE" | "NEUTRAL" | "NEGATIVE";
  top_picks?: Array<{ ticker: string; recommendation?: string; target_price?: number | string; rationale?: string }>;
  key_drivers?: string[];
  key_risks?: string[];
  key_metrics?: Array<{ name: string; value: number }>;
}

const OUTLOOK_CLASS: Record<string, string> = {
  POSITIVE: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  NEUTRAL: "bg-muted text-muted-foreground",
  NEGATIVE: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30",
};

export function IndustryExtractionView({ ext }: { ext: ReportExtraction }) {
  const extras = (ext.extras ?? {}) as IndustryExtras;

  return (
    <div className="space-y-5">
      <KeyValueGrid
        entries={[
          { label: "Industry", value: extras.industry },
          {
            label: "Outlook",
            value: extras.outlook ? (
              <Badge variant="outline" className={OUTLOOK_CLASS[extras.outlook]}>
                {extras.outlook}
              </Badge>
            ) : null,
          },
        ]}
      />

      {extras.top_picks?.length ? (
        <Section title="Top picks">
          <div className="space-y-2">
            {extras.top_picks.map((p, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="font-mono">
                    {p.ticker}
                  </Badge>
                  {p.recommendation && <Badge>{p.recommendation}</Badge>}
                </div>
                {p.target_price !== undefined && p.target_price !== null && (
                  <div className="mt-1 text-muted-foreground">
                    Target: <span className="font-medium tabular-nums text-foreground">{formatPrice(p.target_price, "VND")}</span>
                  </div>
                )}
                {p.rationale && <div className="mt-1 text-muted-foreground">{p.rationale}</div>}
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      <Section title="Key drivers">
        <BulletList items={extras.key_drivers ?? []} />
      </Section>

      <Section title="Key risks">
        <BulletList items={extras.key_risks ?? []} />
      </Section>
    </div>
  );
}
