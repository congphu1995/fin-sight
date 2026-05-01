"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { listAgents, createConversation } from "@/lib/api/agent";
import { forgetConversation, rememberConversation } from "@/lib/storage/conversations";
import { useStoredConversations } from "@/hooks/use-stored-conversations";
import { cn, formatRelative } from "@/lib/utils";
import { toast } from "sonner";
import { friendlyMessage } from "@/lib/api/client";

export function ConversationList() {
  const router = useRouter();
  const params = useParams<{ conversationId?: string }>();
  const activeId = params?.conversationId;
  const qc = useQueryClient();

  const [agentKey, setAgentKey] = useState<string>("qa");
  const items = useStoredConversations(agentKey);

  const agents = useQuery({
    queryKey: ["agents"],
    queryFn: () => listAgents(),
  });

  const createMut = useMutation({
    mutationFn: () => createConversation(agentKey),
    onSuccess: (data) => {
      rememberConversation({
        id: data.id,
        agentKey: data.agent_key,
        title: "New conversation",
        createdAt: new Date().toISOString(),
      });
      qc.invalidateQueries({ queryKey: ["conversation", data.id] });
      router.push(`/chat/${data.id}`);
    },
    onError: (err) => toast.error(friendlyMessage(err)),
  });

  function remove(id: string) {
    forgetConversation(id);
    if (activeId === id) router.push("/chat");
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col gap-2 border-r bg-sidebar/40 p-3">
      <div className="space-y-2">
        <Select value={agentKey} onValueChange={(v) => v && setAgentKey(v)}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(agents.data?.agents ?? []).map((a) => (
              <SelectItem key={a.key} value={a.key}>
                <span className="font-mono text-xs">{a.key}</span> · {a.description}
              </SelectItem>
            ))}
            {!agents.data && <SelectItem value="qa">qa</SelectItem>}
          </SelectContent>
        </Select>
        <Button
          onClick={() => createMut.mutate()}
          disabled={createMut.isPending}
          className="w-full"
          size="sm"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          New conversation
        </Button>
      </div>

      <ScrollArea className="flex-1 -mx-1 px-1">
        {items.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">
            No conversations yet. Start one above.
          </p>
        ) : (
          <ul className="space-y-1">
            {items.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/chat/${c.id}`}
                  className={cn(
                    "group flex items-start gap-2 rounded-md px-2 py-2 text-sm hover:bg-sidebar-accent",
                    activeId === c.id && "bg-sidebar-accent",
                  )}
                >
                  <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate">{c.title}</div>
                    <div className="text-xs text-muted-foreground">{formatRelative(c.createdAt)}</div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      remove(c.id);
                    }}
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                    aria-label="Forget conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                  </button>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>

      <p className="text-[10px] leading-tight text-muted-foreground">
        Conversations stored locally until a list endpoint is added (Phase 2).
      </p>
    </aside>
  );
}
