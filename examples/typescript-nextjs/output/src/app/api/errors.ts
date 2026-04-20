// SPEC-2026-Q2-002 / AC-2 — Consistent error response schema

import { NextResponse } from "next/server";

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export function errorResponse(
  status: number,
  code: string,
  message: string,
  details?: Record<string, unknown>
): NextResponse<ErrorResponse> {
  return NextResponse.json(
    { error: { code, message, ...(details ? { details } : {}) } },
    { status }
  );
}

export function badRequest(message: string, details?: Record<string, unknown>) {
  return errorResponse(400, "BAD_REQUEST", message, details);
}

export function unauthorized(message = "Unauthorized") {
  return errorResponse(401, "UNAUTHORIZED", message);
}

export function notFound(message = "Not found") {
  return errorResponse(404, "NOT_FOUND", message);
}

export function internalError(message = "Internal server error") {
  return errorResponse(500, "INTERNAL_ERROR", message);
}
