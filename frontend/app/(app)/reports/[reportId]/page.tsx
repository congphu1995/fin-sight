"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { getReport } from "@/lib/api/reports";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/reports/status-badge";
import { PdfViewer } from "@/components/reports/pdf-viewer";
import { ExtractionView } from "@/components/reports/extraction";
import { cn, formatDate, formatPrice, formatRelative } from "@/lib/utils";

interface PageProps {
  params: Promise<{ reportId: string }>;
}

export default function ReportDetailPage({ params }: PageProps) {
  const { reportId } = use(params);
  const query = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => getReport(reportId),
  });

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-7xl space-y-4">
        <Skeleton className="h-8 w-1/2" />
        <div className="grid gap-4 md:grid-cols-5">
          <Skeleton className="md:col-span-3 h-[600px]" />
          <Skeleton className="md:col-span-2 h-[600px]" />
        </div>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-7xl">
        <Link
          href="/reports"
          className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "mb-4")}
        >
          <ArrowLeft className="mr-1.5 h-4 w-4" /> Back
        </Link>
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          Report not found.
        </div>
      </div>
    );
  }

  const { report, latest_extraction } = query.data;

  return (
    <div className="mx-auto max-w-7xl space-y-4">
      <Link href="/reports" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
        <ArrowLeft className="mr-1.5 h-4 w-4" /> Back to reports
      </Link>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          {report.ticker && (
            <Badge variant="secondary" className="font-mono text-base">
              {report.ticker}
            </Badge>
          )}
          <Badge variant="outline" className="capitalize">
            {report.report_type_code}
          </Badge>
          <StatusBadge status={report.status} />
          <span className="text-sm text-muted-foreground capitalize">{report.source_code}</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">{report.title}</h1>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span>{report.publisher ?? "Unknown publisher"}</span>
          <span>·</span>
          <span>Published {formatDate(report.published_at)}</span>
          {report.extracted_at && (
            <>
              <span>·</span>
              <span>Extracted {formatRelative(report.extracted_at)}</span>
            </>
          )}
          {report.detail_url && (
            <a
              href={report.detail_url}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "ml-auto h-7")}
            >
              <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
              Source
            </a>
          )}
        </div>
      </div>

      <Separator />

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <PdfViewer reportId={report.id} hasPdf={!!report.pdf_url} externalUrl={report.detail_url} />
        </div>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Extraction</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {!latest_extraction ? (
              <p className="text-sm text-muted-foreground">Not yet extracted.</p>
            ) : (
              <>
                {latest_extraction.summary && (
                  <p className="text-sm leading-relaxed">{latest_extraction.summary}</p>
                )}
                {(latest_extraction.recommendation || latest_extraction.target_price) && (
                  <div className="flex flex-wrap items-center gap-4 rounded-md border bg-muted/40 p-3 text-sm">
                    {latest_extraction.recommendation && (
                      <div>
                        <div className="text-xs text-muted-foreground">Recommendation</div>
                        <Badge className="mt-0.5">{latest_extraction.recommendation}</Badge>
                      </div>
                    )}
                    {latest_extraction.target_price && (
                      <div>
                        <div className="text-xs text-muted-foreground">Target</div>
                        <div className="font-medium tabular-nums">
                          {formatPrice(latest_extraction.target_price, latest_extraction.target_currency)}
                        </div>
                      </div>
                    )}
                    {latest_extraction.horizon && (
                      <div>
                        <div className="text-xs text-muted-foreground">Horizon</div>
                        <div className="font-medium">{latest_extraction.horizon}</div>
                      </div>
                    )}
                  </div>
                )}
                <Separator />
                <ExtractionView typeCode={report.report_type_code} ext={latest_extraction} />
                <p className="pt-2 text-xs text-muted-foreground">
                  Model: <span className="font-mono">{latest_extraction.model}</span> · Prompt {latest_extraction.prompt_version}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
