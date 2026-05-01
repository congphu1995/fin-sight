import { Badge } from "@/components/ui/badge";
import type { ReportStatus } from "@/lib/types";

const VARIANT: Record<ReportStatus, { label: string; className: string }> = {
  extracted: { label: "Extracted", className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30" },
  downloaded: { label: "Downloaded", className: "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30" },
  discovered: { label: "Discovered", className: "bg-muted text-muted-foreground" },
  duplicate: { label: "Duplicate", className: "bg-muted text-muted-foreground" },
  failed: { label: "Failed", className: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30" },
};

export function StatusBadge({ status }: { status: ReportStatus }) {
  const v = VARIANT[status] ?? VARIANT.discovered;
  return (
    <Badge variant="outline" className={v.className}>
      {v.label}
    </Badge>
  );
}
