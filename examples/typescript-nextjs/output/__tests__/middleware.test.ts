// SPEC-2026-Q2-002 / AC-1, AC-2, AC-3 — Middleware unit tests

import { NextRequest } from "next/server";
import { withAuth, withLogging } from "@/app/api/middleware";
import { NextResponse } from "next/server";

const mockHandler = async () => NextResponse.json({ ok: true });

describe("withAuth middleware", () => {
  // AC-1: All API routes use shared validation middleware
  test("rejects request without Authorization header", async () => {
    const req = new NextRequest("http://localhost/api/test");
    const handler = withAuth(mockHandler);
    const res = await handler(req);
    expect(res.status).toBe(401);
  });

  test("passes request with valid Bearer token", async () => {
    const req = new NextRequest("http://localhost/api/test", {
      headers: { Authorization: "Bearer test-token" },
    });
    const handler = withAuth(mockHandler);
    const res = await handler(req);
    expect(res.status).toBe(200);
  });
});

describe("withLogging middleware", () => {
  // AC-3: Request logging captures method, path, status, and duration
  test("logs request details", async () => {
    const consoleSpy = jest.spyOn(console, "log").mockImplementation();
    const req = new NextRequest("http://localhost/api/items");
    const handler = withLogging(mockHandler);
    await handler(req);

    expect(consoleSpy).toHaveBeenCalledTimes(1);
    const logged = JSON.parse(consoleSpy.mock.calls[0][0]);
    expect(logged).toHaveProperty("method", "GET");
    expect(logged).toHaveProperty("path", "/api/items");
    expect(logged).toHaveProperty("status", 200);
    expect(logged).toHaveProperty("duration_ms");

    consoleSpy.mockRestore();
  });
});
