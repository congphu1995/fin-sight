"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

interface Props {
  disabled?: boolean;
  onSend: (text: string) => void;
}

export function Composer({ disabled, onSend }: Props) {
  const [text, setText] = useState("");

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="flex items-end gap-2 border-t bg-background p-3">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask the agent…  (⌘/Ctrl + Enter to send)"
        rows={2}
        className="min-h-[60px] flex-1 resize-none"
        disabled={disabled}
        maxLength={8000}
      />
      <Button type="submit" disabled={disabled || !text.trim()} size="icon">
        <Send className="h-4 w-4" />
      </Button>
    </form>
  );
}
