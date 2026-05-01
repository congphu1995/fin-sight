"use client";

import { use, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getConversation, sendMessage } from "@/lib/api/agent";
import { friendlyMessage } from "@/lib/api/client";
import { MessageList } from "@/components/chat/message-list";
import { Composer } from "@/components/chat/composer";
import { Skeleton } from "@/components/ui/skeleton";
import { updateConversationTitle } from "@/lib/storage/conversations";
import { useStoredConversation } from "@/hooks/use-stored-conversations";
import type { ConversationDetail, MessageDTO } from "@/lib/types";

interface PageProps {
  params: Promise<{ conversationId: string }>;
}

export default function ChatThreadPage({ params }: PageProps) {
  const { conversationId } = use(params);
  const qc = useQueryClient();
  const [pending, setPending] = useState<{ userMessage: string; toolName?: string } | null>(null);

  // Backend route requires agent_key in the URL — recover it from localStorage,
  // falling back to "qa" for bookmarked links until Phase 2's list endpoint exists.
  const stored = useStoredConversation(conversationId);
  const agentKey = stored?.agentKey ?? "qa";

  const detail = useQuery({
    queryKey: ["conversation", conversationId, agentKey],
    queryFn: () => getConversation(agentKey, conversationId),
  });

  const sendMut = useMutation({
    mutationFn: async (text: string) => {
      setPending({ userMessage: text });
      return sendMessage(agentKey, conversationId, text);
    },
    onSuccess: (data, text) => {
      qc.setQueryData<ConversationDetail | undefined>(["conversation", conversationId, agentKey], (prev) => {
        if (!prev) return prev;
        const seen = new Set(prev.messages.map((m) => m.id));
        const merged = [...prev.messages];
        for (const m of data.messages) {
          if (!seen.has(m.id)) merged.push(m);
        }
        return { ...prev, messages: merged };
      });
      // Use the first user message as a friendly title.
      if (detail.data && detail.data.messages.length === 0) {
        const title = text.length > 60 ? `${text.slice(0, 60)}…` : text;
        updateConversationTitle(conversationId, title);
      }
      setPending(null);
    },
    onError: (err) => {
      setPending(null);
      toast.error(friendlyMessage(err));
    },
  });

  if (detail.isLoading) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    );
  }

  if (detail.isError || !detail.data) {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-sm text-muted-foreground">
        Conversation not found.
      </div>
    );
  }

  const messages: MessageDTO[] = detail.data.messages;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-4 py-2">
        <h2 className="text-sm font-medium">{detail.data.conversation.title ?? "Conversation"}</h2>
        <p className="text-xs text-muted-foreground">
          Agent <span className="font-mono">{agentKey}</span>
        </p>
      </div>
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !pending ? (
          <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
            Send the first message to start.
          </div>
        ) : (
          <MessageList messages={messages} pending={pending} />
        )}
      </div>
      <Composer disabled={sendMut.isPending} onSend={(t) => sendMut.mutate(t)} />
    </div>
  );
}
