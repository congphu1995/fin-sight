"use client";

import { useEffect, useRef } from "react";
import type { MessageDTO } from "@/lib/types";
import { Message } from "./message";
import { Loader2 } from "lucide-react";

interface Props {
  messages: MessageDTO[];
  pending?: { userMessage: string; toolName?: string } | null;
}

export function MessageList({ messages, pending }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  return (
    <div className="flex flex-col gap-4 py-4">
      {messages.map((m) => (
        <Message key={m.id} message={m} />
      ))}
      {pending && (
        <>
          <div className="flex justify-end px-3">
            <div className="max-w-[80%] rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">
              {pending.userMessage}
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>{pending.toolName ? `Running ${pending.toolName}…` : "Thinking…"}</span>
          </div>
        </>
      )}
      <div ref={endRef} />
    </div>
  );
}
