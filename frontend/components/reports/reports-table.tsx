"use client";

import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "./status-badge";
import type { ReportOut } from "@/lib/types";
import { formatDate } from "@/lib/utils";

interface Props {
  rows: ReportOut[];
  compact?: boolean;
  emptyMessage?: string;
}

export function ReportsTable({ rows, compact, emptyMessage = "No reports." }: Props) {
  if (!rows.length) {
    return (
      <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[110px]">Published</TableHead>
            <TableHead className="w-[80px]">Ticker</TableHead>
            <TableHead className="w-[100px]">Type</TableHead>
            <TableHead>Title</TableHead>
            {!compact && <TableHead className="w-[160px]">Publisher</TableHead>}
            <TableHead className="w-[110px]">Status</TableHead>
            {!compact && <TableHead className="w-[90px]">Source</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.id} className="cursor-pointer">
              <TableCell className="text-muted-foreground tabular-nums">
                <Link href={`/reports/${r.id}`} className="block w-full">
                  {formatDate(r.published_at)}
                </Link>
              </TableCell>
              <TableCell>
                <Link href={`/reports/${r.id}`} className="block w-full">
                  {r.ticker ? (
                    <Badge variant="secondary" className="font-mono">
                      {r.ticker}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </Link>
              </TableCell>
              <TableCell>
                <Link href={`/reports/${r.id}`} className="block w-full">
                  <Badge variant="outline" className="capitalize">
                    {r.report_type_code}
                  </Badge>
                </Link>
              </TableCell>
              <TableCell className="max-w-[420px]">
                <Link href={`/reports/${r.id}`} className="block w-full truncate" title={r.title}>
                  {r.title}
                </Link>
              </TableCell>
              {!compact && (
                <TableCell className="text-muted-foreground truncate max-w-[160px]" title={r.publisher ?? ""}>
                  <Link href={`/reports/${r.id}`} className="block w-full truncate">
                    {r.publisher ?? "—"}
                  </Link>
                </TableCell>
              )}
              <TableCell>
                <Link href={`/reports/${r.id}`} className="block w-full">
                  <StatusBadge status={r.status} />
                </Link>
              </TableCell>
              {!compact && (
                <TableCell className="text-muted-foreground capitalize">
                  <Link href={`/reports/${r.id}`} className="block w-full">
                    {r.source_code}
                  </Link>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
