import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCents(value: number | null | undefined) {
  if (value === null || value === undefined) return "Unknown";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value / 100);
}

export function formatPercent(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "Unknown";
  const numeric = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 }).format(numeric);
}

export function yyyyMm(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function confidenceTone(confidence?: string) {
  switch (confidence) {
    case "verified":
    case "high":
      return "success";
    case "medium":
      return "neutral";
    case "low":
      return "warning";
    default:
      return "danger";
  }
}
