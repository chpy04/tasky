// src/utils/formatters.ts

/**
 * Convert a vault folder path to a display name.
 * E.g. "Experiences/electric_racing" → "Electric Racing"
 *      "electric_racing"             → "Electric Racing"
 */
export function formatExperienceName(folderPath: string): string {
  const segment = folderPath.split("/").pop() ?? folderPath;
  return segment
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Format an ISO datetime string to a short display date like "Mar 16".
 * Returns null if dueDateStr is null.
 */
export function formatDueDate(dueDateStr: string | null): string | null {
  if (!dueDateStr) return null;
  const d = new Date(dueDateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/**
 * Returns true if the due date is within 3 days from now (and not past).
 */
export function isDueSoon(dueDateStr: string | null): boolean {
  if (!dueDateStr) return false;
  const due = new Date(dueDateStr);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays >= 0 && diffDays <= 3;
}

/**
 * Returns true if the due date is in the past.
 */
export function isOverdue(dueDateStr: string | null): boolean {
  if (!dueDateStr) return false;
  const due = new Date(dueDateStr);
  return due.getTime() < Date.now();
}

/**
 * Returns true if the given ISO datetime string is today (local timezone).
 */
export function isToday(dateStr: string): boolean {
  const d = new Date(dateStr);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

/**
 * Returns true if the given ISO datetime string is within the last N days.
 */
export function isWithinLastDays(dateStr: string, days: number): boolean {
  const d = new Date(dateStr);
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return d >= cutoff;
}
