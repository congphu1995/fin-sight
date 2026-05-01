"use client";

import { useState } from "react";
import { ChevronRight, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

interface Props {
  name: string;
  args: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
}

export function ToolCallCard({ name, args, result }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="group flex w-full items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-left text-xs hover:bg-muted">
        <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="font-mono text-muted-foreground">{name}</span>
        {args && Object.keys(args).length > 0 && (
          <span className="truncate text-muted-foreground/60">
            {Object.entries(args)
              .slice(0, 2)
              .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
              .join(", ")}
          </span>
        )}
        <ChevronRight
          className={cn(
            "ml-auto h-3.5 w-3.5 text-muted-foreground transition-transform",
            open && "rotate-90",
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1 space-y-2 rounded-md border bg-muted/20 p-3 text-xs">
        {args && Object.keys(args).length > 0 && (
          <div>
            <div className="mb-1 font-medium text-muted-foreground">Arguments</div>
            <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-[11px]">
              {JSON.stringify(args, null, 2)}
            </pre>
          </div>
        )}
        {result && (
          <div>
            <div className="mb-1 font-medium text-muted-foreground">Result</div>
            <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-all font-mono text-[11px]">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
