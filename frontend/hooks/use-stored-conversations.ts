import { useSyncExternalStore } from "react";
import type { StoredConversation } from "@/lib/storage/conversations";

const STORAGE_KEY = "fin-sight:conversations:v1";
const STORAGE_EVENT = "fin-sight:conversations:changed";

// useSyncExternalStore requires getSnapshot to return a stable reference when
// the underlying state hasn't changed. Parse localStorage once per write and
// memoise the filtered views so React doesn't loop.

let allCache: { raw: string | null; parsed: StoredConversation[] } = {
  raw: null,
  parsed: [],
};
const filteredCache = new Map<
  string | "__all__",
  { source: StoredConversation[]; result: StoredConversation[] }
>();
const byIdCache = new Map<string, { source: StoredConversation[]; result: StoredConversation | undefined }>();

function readAll(): StoredConversation[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === allCache.raw) return allCache.parsed;
  let parsed: StoredConversation[] = [];
  if (raw) {
    try {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) parsed = arr as StoredConversation[];
    } catch {
      parsed = [];
    }
  }
  parsed.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  allCache = { raw, parsed };
  return parsed;
}

function readFiltered(agentKey?: string): StoredConversation[] {
  const all = readAll();
  const key = agentKey ?? "__all__";
  const cached = filteredCache.get(key);
  if (cached && cached.source === all) return cached.result;
  const result = agentKey ? all.filter((c) => c.agentKey === agentKey) : all;
  filteredCache.set(key, { source: all, result });
  return result;
}

function readById(conversationId: string): StoredConversation | undefined {
  const all = readAll();
  const cached = byIdCache.get(conversationId);
  if (cached && cached.source === all) return cached.result;
  const result = all.find((c) => c.id === conversationId);
  byIdCache.set(conversationId, { source: all, result });
  return result;
}

const EMPTY: StoredConversation[] = [];

function subscribe(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", callback);
  window.addEventListener(STORAGE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(STORAGE_EVENT, callback);
  };
}

export function useStoredConversations(agentKey?: string): StoredConversation[] {
  return useSyncExternalStore(
    subscribe,
    () => readFiltered(agentKey),
    () => EMPTY,
  );
}

export function useStoredConversation(conversationId: string): StoredConversation | undefined {
  return useSyncExternalStore(
    subscribe,
    () => readById(conversationId),
    () => undefined,
  );
}
