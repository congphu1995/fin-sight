import type { ReportExtraction } from "@/lib/types";
import { BulletList, Section } from "./shared";

interface GenericExtras {
  key_findings?: string[];
}

export function GenericExtractionView({ ext }: { ext: ReportExtraction }) {
  const extras = (ext.extras ?? {}) as GenericExtras;

  return (
    <Section title="Key findings">
      <BulletList items={extras.key_findings ?? []} />
    </Section>
  );
}
