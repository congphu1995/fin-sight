import { MessageSquare } from "lucide-react";

export default function ChatEmptyPage() {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="max-w-sm space-y-3 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <MessageSquare className="h-5 w-5 text-muted-foreground" />
        </div>
        <h2 className="text-lg font-medium">Ask the agent something</h2>
        <p className="text-sm text-muted-foreground">
          Pick an agent on the left and start a new conversation. The QA agent can search reports,
          fetch metrics, and read individual PDFs.
        </p>
      </div>
    </div>
  );
}
