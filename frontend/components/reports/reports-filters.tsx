"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type { ReportStatus, ReportTypeCode } from "@/lib/types";

export interface ReportsFilterValue {
  ticker: string;
  type: ReportTypeCode | "all";
  status: ReportStatus | "all";
}

const TYPES: Array<{ value: ReportTypeCode | "all"; label: string }> = [
  { value: "all", label: "All types" },
  { value: "company", label: "Company" },
  { value: "industry", label: "Industry" },
  { value: "macro", label: "Macro" },
  { value: "technical", label: "Technical" },
  { value: "thematic", label: "Thematic" },
  { value: "generic", label: "Generic" },
];

const STATUSES: Array<{ value: ReportStatus | "all"; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "extracted", label: "Extracted" },
  { value: "downloaded", label: "Downloaded" },
  { value: "discovered", label: "Discovered" },
  { value: "failed", label: "Failed" },
];

interface Props {
  value: ReportsFilterValue;
  onChange: (next: ReportsFilterValue) => void;
}

export function ReportsFilters({ value, onChange }: Props) {
  const reset = () => onChange({ ticker: "", type: "all", status: "all" });
  const dirty = value.ticker !== "" || value.type !== "all" || value.status !== "all";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        placeholder="Ticker (e.g. HPG)"
        value={value.ticker}
        onChange={(e) => onChange({ ...value, ticker: e.target.value.toUpperCase() })}
        className="w-[180px]"
      />
      <Select value={value.type} onValueChange={(v) => onChange({ ...value, type: v as ReportTypeCode | "all" })}>
        <SelectTrigger className="w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {TYPES.map((t) => (
            <SelectItem key={t.value} value={t.value}>
              {t.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={value.status} onValueChange={(v) => onChange({ ...value, status: v as ReportStatus | "all" })}>
        <SelectTrigger className="w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STATUSES.map((s) => (
            <SelectItem key={s.value} value={s.value}>
              {s.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {dirty && (
        <Button variant="ghost" size="sm" onClick={reset}>
          Clear
        </Button>
      )}
    </div>
  );
}
