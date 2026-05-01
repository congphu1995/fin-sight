import { apiFetch } from "./client";
import type { ReportDetail, ReportOut, ReportsListParams } from "../types";

export function listReports(params: ReportsListParams = {}): Promise<ReportOut[]> {
  return apiFetch<ReportOut[]>("/reports", {
    query: {
      source: params.source,
      type: params.type,
      ticker: params.ticker,
      status: params.status,
      limit: params.limit ?? 20,
      offset: params.offset ?? 0,
    },
  });
}

export function getReport(reportId: string): Promise<ReportDetail> {
  return apiFetch<ReportDetail>(`/reports/${reportId}`);
}

export function reportPdfUrl(reportId: string): string {
  return `/api/v1/reports/${reportId}/pdf`;
}
