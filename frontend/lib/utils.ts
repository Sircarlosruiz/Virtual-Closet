import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isValidUuid(value: string | null | undefined): boolean {
  return typeof value === "string" && UUID_RE.test(value);
}

/** API may return Decimal as string; normalizes for display. */
export function formatPrice(price: number | string): string {
  const value = typeof price === "number" ? price : Number.parseFloat(price);
  return Number.isFinite(value) ? value.toFixed(2) : "0.00";
}
