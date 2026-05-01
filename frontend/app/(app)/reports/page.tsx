"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { listReports } from "@/lib/api/reports";
import { ReportsTable } from "@/components/reports/reports-table";
import { ReportsFilters, type ReportsFilterValue } from "@/components/reports/reports-filters";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReportsListParams } from "@/lib/types";

const PAGE_SIZE = 20;

export default function ReportsPage() {
  const [filters, setFilters] = useState<ReportsFilterValue>({ ticker: "", type: "all", status: "all" });
  const [page, setPage] = useState(1);

  const params: ReportsListParams = {
    ticker: filters.ticker || undefined,
    type: filters.type === "all" ? undefined : filters.type,
    status: filters.status === "all" ? undefined : filters.status,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };

  const query = useQuery({
    queryKey: ["reports", params],
    queryFn: () => listReports(params),
    placeholderData: (prev) => prev,
  });

  const rows = query.data ?? [];
  // We don't have a total count from the API yet — assume there's a next page
  // whenever the current page came back full.
  const hasPrev = page > 1;
  const hasNext = rows.length === PAGE_SIZE;
  const startIndex = (page - 1) * PAGE_SIZE + (rows.length ? 1 : 0);
  const endIndex = (page - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground">Browse downloaded reports and their extractions.</p>
      </div>

      <ReportsFilters
        value={filters}
        onChange={(next) => {
          setFilters(next);
          setPage(1);
        }}
      />

      {query.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      ) : query.isError ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          Failed to load reports. Is the backend running on the port configured in <code>.env.local</code>?
        </div>
      ) : (
        <>
          <ReportsTable rows={rows} emptyMessage="No reports match these filters." />
          {(hasPrev || hasNext || rows.length > 0) && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span className="tabular-nums">
                {rows.length > 0
                  ? `${startIndex.toLocaleString()}–${endIndex.toLocaleString()}`
                  : "No results"}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasPrev || query.isFetching}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="mr-1 h-3.5 w-3.5" />
                  Previous
                </Button>
                <span className="px-2 tabular-nums text-foreground">Page {page}</span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasNext || query.isFetching}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                  <ChevronRight className="ml-1 h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
