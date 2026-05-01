"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { listReports } from "@/lib/api/reports";
import { listAgents } from "@/lib/api/agent";
import { StatCard } from "@/components/dashboard/stat-card";
import { StatusBreakdown } from "@/components/dashboard/status-breakdown";
import { ReportsTable } from "@/components/reports/reports-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCompact } from "@/lib/utils";

export default function DashboardPage() {
  const recent = useQuery({
    queryKey: ["reports", "recent-window"],
    queryFn: () => listReports({ limit: 200 }),
  });
  const agents = useQuery({
    queryKey: ["agents"],
    queryFn: () => listAgents(),
  });

  const rows = useMemo(() => recent.data ?? [], [recent.data]);
  const total = rows.length;
  const lastWeekExtracted = useMemo(() => {
    // eslint-disable-next-line react-hooks/purity -- "rows extracted in last 7 days" is intentionally relative to render time; refresh cadence comes from the query's refetch.
    const cutoff = Date.now() - 7 * 24 * 3600 * 1000;
    return rows.filter(
      (r) => r.status === "extracted" && r.extracted_at && Date.parse(r.extracted_at) >= cutoff,
    ).length;
  }, [rows]);
  const recentExtracted = rows.filter((r) => r.status === "extracted").slice(0, 5);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Overview of the research pipeline.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {recent.isLoading ? (
          <>
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </>
        ) : (
          <>
            <StatCard label="Reports tracked" value={formatCompact(total)} hint="Most recent 200 in window" />
            <StatCard label="Extracted (7d)" value={formatCompact(lastWeekExtracted)} hint="Status = extracted" />
            <StatCard
              label="Pipeline"
              value={
                <div className="pt-1">
                  <StatusBreakdown rows={rows} />
                </div>
              }
            />
            <StatCard
              label="Agents"
              value={agents.isLoading ? "—" : formatCompact(agents.data?.agents.length ?? 0)}
              hint={agents.data?.agents.map((a) => a.key).join(", ")}
            />
          </>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent extractions</CardTitle>
        </CardHeader>
        <CardContent>
          {recent.isLoading ? (
            <Skeleton className="h-40" />
          ) : (
            <ReportsTable rows={recentExtracted} compact emptyMessage="No extracted reports yet." />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent conversations</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Available once a list-conversations endpoint is added (Phase 2).
        </CardContent>
      </Card>
    </div>
  );
}
