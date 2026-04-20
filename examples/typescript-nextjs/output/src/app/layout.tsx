// SPEC-2026-Q2-001 / AC-4 — Layout with inline theme script to prevent FOUC

import "./globals.css";
import { ThemeToggle } from "@/components/ThemeToggle";

export const metadata = {
  title: "my-nextjs-app",
  description: "Next.js app with dark mode support",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* AC-4: Inline script prevents flash of unstyled content */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                var stored = localStorage.getItem('theme-preference');
                var theme = stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
                document.documentElement.setAttribute('data-theme', theme);
              })();
            `,
          }}
        />
      </head>
      <body>
        <header style={{ padding: "16px", display: "flex", justifyContent: "flex-end" }}>
          <ThemeToggle />
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
