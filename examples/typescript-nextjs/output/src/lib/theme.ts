// SPEC-2026-Q2-001 / AC-1, AC-2, AC-3 — Theme management utilities

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme-preference";

export function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return null;
}

export function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function getInitialTheme(): Theme {
  return getStoredTheme() ?? getSystemTheme();
}

export function storeTheme(theme: Theme): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, theme);
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}
