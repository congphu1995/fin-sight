import { apiFetch } from "./client";
import type {
  AgentsList,
  ConversationDetail,
  CreateConversationResponse,
  SendMessageResponse,
} from "../types";

export function listAgents(): Promise<AgentsList> {
  return apiFetch<AgentsList>("/agent/agents");
}

export function createConversation(agentKey: string): Promise<CreateConversationResponse> {
  return apiFetch<CreateConversationResponse>(`/agent/${agentKey}/conversations`, {
    method: "POST",
  });
}

export function getConversation(
  agentKey: string,
  conversationId: string,
): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(
    `/agent/${agentKey}/conversations/${conversationId}`,
  );
}

export function sendMessage(
  agentKey: string,
  conversationId: string,
  message: string,
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(
    `/agent/${agentKey}/conversations/${conversationId}/messages`,
    { method: "POST", body: { message } },
  );
}
