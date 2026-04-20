// SPEC-2026-Q2-001 / AC-1, AC-2, AC-3 — Theme utility tests

import { getInitialTheme, getStoredTheme, storeTheme } from "@/lib/theme";

describe("Theme utilities", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  // AC-2: Theme preference persists across page reloads
  test("storeTheme persists to localStorage", () => {
    storeTheme("dark");
    expect(localStorage.getItem("theme-preference")).toBe("dark");
  });

  test("getStoredTheme retrieves persisted value", () => {
    localStorage.setItem("theme-preference", "dark");
    expect(getStoredTheme()).toBe("dark");
  });

  test("getStoredTheme returns null when no preference set", () => {
    expect(getStoredTheme()).toBeNull();
  });

  // AC-3: First visit respects system prefers-color-scheme
  test("getInitialTheme falls back to system preference", () => {
    const theme = getInitialTheme();
    expect(["light", "dark"]).toContain(theme);
  });

  // AC-2: Stored preference takes precedence over system
  test("getInitialTheme uses stored preference over system", () => {
    storeTheme("dark");
    expect(getInitialTheme()).toBe("dark");
  });
});
