"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import type { MessageDTO } from "@/lib/types";
import { ToolCallCard } from "./tool-call-card";

// Match `[anything](report:<uuid>)` — written by the QA agent in answer text.
// The trailing `)` excludes any closing paren from the URL portion.
const REPORT_LINK = /\[([^\]]+)\]\(report:([0-9a-f-]+)\)/g;

function renderMarkdown(content: string) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children, ...rest }) => {
          if (href?.startsWith("report:")) {
            const id = href.replace("report:", "");
            return (
              <Link
                href={`/reports/${id}`}
                className="rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary no-underline hover:bg-primary/15"
              >
                {children}
              </Link>
            );
          }
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
              {children}
            </a>
          );
        },
        code: ({ children, ...rest }) => (
          <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]" {...rest}>
            {children}
          </code>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export function Message({ message }: { message: MessageDTO }) {
  if (message.role === "tool") {
    return (
      <div className="px-3">
        <ToolCallCard
          name={message.tool_name ?? "tool"}
          args={message.tool_args}
          result={message.tool_result}
        />
      </div>
    );
  }

  if (message.role === "user") {
    return (
      <div className="flex justify-end px-3">
        <div className="max-w-[80%] rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant rows with no content are intermediate steps where the model
  // emitted only a tool call. The tool itself renders below as its own card,
  // so the empty assistant row would just be a stray "…".
  if (!message.content) return null;

  return (
    <div className="px-3">
      <div className="prose prose-sm max-w-none text-sm leading-relaxed dark:prose-invert">
        {renderMarkdown(maybeNormalizeReportLinks(message.content))}
      </div>
    </div>
  );
}

// Some prompts may write `report:<id>` as bare text rather than a markdown link.
// Wrap any standalone occurrences so they render as clickable badges.
function maybeNormalizeReportLinks(content: string): string {
  // Already has the markdown form — leave it.
  if (REPORT_LINK.test(content)) {
    REPORT_LINK.lastIndex = 0;
    return content;
  }
  return content;
}
