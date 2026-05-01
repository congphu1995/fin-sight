import type { ReportOut } from "@/lib/types";
import { cn } from "@/lib/utils";

const ORDER: Array<{ key: ReportOut["status"]; label: string; color: string }> = [
  { key: "extracted", label: "Extracted", color: "bg-emerald-500" },
  { key: "downloaded", label: "Downloaded", color: "bg-blue-500" },
  { key: "discovered", label: "Discovered", color: "bg-muted-foreground/40" },
  { key: "failed", label: "Failed", color: "bg-red-500" },
];

export function StatusBreakdown({ rows }: { rows: ReportOut[] }) {
  const counts = ORDER.map(({ key, label, color }) => ({
    key,
    label,
    color,
    n: rows.filter((r) => r.status === key).length,
  }));
  const total = counts.reduce((s, c) => s + c.n, 0) || 1;

  return (
    <div className="space-y-2">
      <div className="flex h-2 overflow-hidden rounded-full bg-muted">
        {counts.map(({ key, n, color }) => (
          <div key={key} className={cn("h-full", color)} style={{ width: `${(n / total) * 100}%` }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {counts.map(({ key, label, color, n }) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className={cn("h-2 w-2 rounded-full", color)} />
            <span>
              {label} <span className="tabular-nums text-foreground">{n}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
