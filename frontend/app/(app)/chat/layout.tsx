import { ConversationList } from "@/components/chat/conversation-list";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-[calc(100vh-3rem)] gap-0 -m-6">
      <ConversationList />
      <div className="flex flex-1 flex-col min-w-0">{children}</div>
    </div>
  );
}
