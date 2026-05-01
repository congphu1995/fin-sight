// Mirrors of backend Pydantic schemas. Keep aligned with:
//   app/reports/schemas.py
//   app/agent/schemas.py
// If drift becomes painful, swap to openapi-typescript code generation.

export type ReportStatus =
  | "discovered"
  | "downloaded"
  | "extracted"
  | "duplicate"
  | "failed";

export type ReportTypeCode =
  | "company"
  | "industry"
  | "macro"
  | "technical"
  | "thematic"
  | "generic";

export interface ReportOut {
  id: string;
  source_code: string;
  report_type_code: string;
  external_id: string;
  ticker: string | null;
  title: string;
  publisher: string | null;
  published_at: string | null;
  detail_url: string | null;
  pdf_url: string | null;
  status: ReportStatus;
  discovered_at: string;
  downloaded_at: string | null;
  extracted_at: string | null;
}

export interface ReportExtraction {
  id: string;
  report_id: string;
  model: string;
  prompt_version: string;
  extracted_at: string;
  summary: string | null;
  recommendation: string | null;
  target_price: string | number | null;
  target_currency: string | null;
  horizon: string | null;
  extras: Record<string, unknown>;
}

export interface ReportDetail {
  report: ReportOut;
  latest_extraction: ReportExtraction | null;
}

export interface AgentInfo {
  key: string;
  description: string;
  tool_names: string[];
}

export interface AgentsList {
  agents: AgentInfo[];
}

export type MessageRole = "user" | "assistant" | "tool";

export interface MessageDTO {
  id: string;
  role: MessageRole;
  content: string | null;
  tool_call_id: string | null;
  tool_name: string | null;
  tool_args: Record<string, unknown> | null;
  tool_result: Record<string, unknown> | null;
  step: number;
  created_at: string;
}

export interface ConversationDTO {
  id: string;
  agent_key: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  conversation: ConversationDTO;
  messages: MessageDTO[];
}

export interface CreateConversationResponse {
  id: string;
  agent_key: string;
}

export interface SendMessageResponse {
  messages: MessageDTO[];
}

export interface ReportsListParams {
  source?: string;
  type?: ReportTypeCode;
  ticker?: string;
  status?: ReportStatus;
  limit?: number;
  offset?: number;
}
