// SPEC-2026-Q2-002 / AC-1, AC-3 — Composable API middleware

import { type NextRequest, NextResponse } from "next/server";
import { internalError, badRequest, unauthorized } from "./errors";

type Handler = (req: NextRequest) => Promise<NextResponse> | NextResponse;
type Middleware = (handler: Handler) => Handler;

// AC-1: Shared validation middleware
export function withValidation(
  schema: { parse: (data: unknown) => unknown }
): Middleware {
  return (handler: Handler) => async (req: NextRequest) => {
    try {
      const body = await req.json();
      schema.parse(body);
    } catch {
      return badRequest("Validation failed");
    }
    return handler(req);
  };
}

// AC-1: Auth middleware
export function withAuth(handler: Handler): Handler {
  return async (req: NextRequest) => {
    const authHeader = req.headers.get("authorization");
    if (!authHeader?.startsWith("Bearer ")) {
      return unauthorized();
    }
    return handler(req);
  };
}

// AC-3: Request logging middleware captures method, path, status, duration
export function withLogging(handler: Handler): Handler {
  return async (req: NextRequest) => {
    const start = Date.now();
    const response = await handler(req);
    const duration = Date.now() - start;
    console.log(
      JSON.stringify({
        method: req.method,
        path: req.nextUrl.pathname,
        status: response.status,
        duration_ms: duration,
        timestamp: new Date().toISOString(),
      })
    );
    return response;
  };
}

// Compose multiple middlewares left-to-right
export function compose(...middlewares: Middleware[]): Middleware {
  return (handler: Handler) =>
    middlewares.reduceRight((h, mw) => mw(h), handler);
}
