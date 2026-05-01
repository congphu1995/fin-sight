import { Badge } from "@/components/ui/badge";
import type { ReportExtraction } from "@/lib/types";
import { formatPrice } from "@/lib/utils";
import { BulletList, KeyValueGrid, Section } from "./shared";

interface CompanyExtras {
  current_price?: number | string;
  analyst?: string[];
  key_drivers?: string[];
  key_risks?: string[];
  financial_highlights?: Array<{ name: string; value: number }>;
}

export function CompanyExtractionView({ ext }: { ext: ReportExtraction }) {
  const extras = (ext.extras ?? {}) as CompanyExtras;

  return (
    <div className="space-y-5">
      <KeyValueGrid
        entries={[
          { label: "Recommendation", value: ext.recommendation ? <Badge>{ext.recommendation}</Badge> : null },
          { label: "Target price", value: formatPrice(ext.target_price, ext.target_currency) },
          { label: "Current price", value: formatPrice(extras.current_price ?? null, ext.target_currency) },
          { label: "Horizon", value: ext.horizon },
          { label: "Analyst", value: extras.analyst?.join(", ") || "—" },
        ]}
      />

      <Section title="Key drivers">
        <BulletList items={extras.key_drivers ?? []} />
      </Section>

      <Section title="Key risks">
        <BulletList items={extras.key_risks ?? []} />
      </Section>

      {extras.financial_highlights?.length ? (
        <Section title="Financial highlights">
          <ul className="space-y-1 text-sm">
            {extras.financial_highlights.map((m, i) => (
              <li key={i} className="flex items-baseline justify-between gap-4">
                <span className="text-muted-foreground">{m.name}</span>
                <span className="font-medium tabular-nums">{m.value.toLocaleString("en-US")}</span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
    </div>
  );
}
