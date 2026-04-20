// SPEC-2026-Q2-001 / AC-1, AC-2, AC-3, AC-4 — Dark mode toggle component

"use client";

import { useCallback, useEffect, useState } from "react";
import { type Theme, applyTheme, getInitialTheme, storeTheme } from "@/lib/theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const initial = getInitialTheme();
    setTheme(initial);
    applyTheme(initial);
    setMounted(true);
  }, []);

  const toggle = useCallback(() => {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    storeTheme(next);
    applyTheme(next);
  }, [theme]);

  // AC-4: Prevent flash of unstyled content by rendering nothing until mounted
  if (!mounted) return null;

  return (
    <button
      onClick={toggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle();
        }
      }}
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      role="switch"
      aria-checked={theme === "dark"}
      tabIndex={0}
      style={{
        background: "var(--toggle-bg)",
        color: "var(--toggle-fg)",
        border: "1px solid var(--border-color)",
        borderRadius: "8px",
        padding: "8px 16px",
        cursor: "pointer",
        fontSize: "14px",
      }}
    >
      {theme === "light" ? "Dark Mode" : "Light Mode"}
    </button>
  );
}
