import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNow, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined, fmt = "MMM d, yyyy"): string {
  if (!value) return "—";
  try {
    return format(parseISO(value), fmt);
  } catch {
    return value;
  }
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return formatDistanceToNow(parseISO(value), { addSuffix: true });
  } catch {
    return value;
  }
}

const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
export function formatCompact(n: number): string {
  return compact.format(n);
}

export function formatPrice(value: string | number | null | undefined, currency: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(num)) return "—";
  const cur = currency ?? "VND";
  if (cur === "VND") return `${num.toLocaleString("en-US")} VND`;
  return `${num.toLocaleString("en-US")} ${cur}`;
}
