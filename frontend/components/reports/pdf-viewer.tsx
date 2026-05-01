"use client";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Download, ExternalLink } from "lucide-react";

interface Props {
  reportId: string;
  hasPdf: boolean;
  externalUrl?: string | null;
}

export function PdfViewer({ reportId, hasPdf, externalUrl }: Props) {
  if (!hasPdf) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center gap-3 rounded-md border border-dashed p-8 text-center">
        <p className="text-sm text-muted-foreground">No PDF stored for this report.</p>
        {externalUrl && (
          <a
            href={externalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            <ExternalLink className="mr-1.5 h-4 w-4" />
            View on source
          </a>
        )}
      </div>
    );
  }

  // Open parameters: collapse the thumbnail sidebar by default and fit to width.
  // Honoured by both Chromium's built-in viewer and PDF.js.
  const src = `/api/v1/reports/${reportId}/pdf#pagemode=none&navpanes=0&view=FitH`;

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">PDF preview</span>
        <a
          href={src}
          target="_blank"
          rel="noopener noreferrer"
          download
          className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
        >
          <Download className="mr-1.5 h-4 w-4" />
          Download
        </a>
      </div>
      <iframe
        src={src}
        className="h-[calc(100vh-220px)] min-h-[500px] w-full rounded-md border bg-muted"
        title="Report PDF"
      />
    </div>
  );
}
