// Phase 1 fallback for the chat sidebar — backend has no GET /conversations
// endpoint yet, so we remember conversation ids per-browser. Phase 2 swaps
// this for a real query against the backend.

const KEY = "fin-sight:conversations:v1";

export interface StoredConversation {
  id: string;
  agentKey: string;
  title: string;
  createdAt: string;
}

function read(): StoredConversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as StoredConversation[]) : [];
  } catch {
    return [];
  }
}

function write(value: StoredConversation[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(value));
  // Notify same-tab subscribers — the native `storage` event only fires
  // across tabs, not within the tab that wrote the change.
  window.dispatchEvent(new Event("fin-sight:conversations:changed"));
}

export function listStoredConversations(agentKey?: string): StoredConversation[] {
  const all = read().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  return agentKey ? all.filter((c) => c.agentKey === agentKey) : all;
}

export function rememberConversation(c: StoredConversation): void {
  const all = read().filter((existing) => existing.id !== c.id);
  all.unshift(c);
  write(all.slice(0, 50));
}

export function updateConversationTitle(id: string, title: string): void {
  const all = read().map((c) => (c.id === id ? { ...c, title } : c));
  write(all);
}

export function forgetConversation(id: string): void {
  write(read().filter((c) => c.id !== id));
}
