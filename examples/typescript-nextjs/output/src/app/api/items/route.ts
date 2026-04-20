// SPEC-2026-Q2-002 / AC-4 — Items route refactored to use shared middleware

import { type NextRequest, NextResponse } from "next/server";
import { compose, withLogging } from "../middleware";

const items = Array.from({ length: 50 }, (_, i) => ({
  id: String(i + 1),
  name: `Item ${i + 1}`,
  price: Math.round(Math.random() * 10000) / 100,
}));

async function handleGet(req: NextRequest): Promise<NextResponse> {
  const { searchParams } = req.nextUrl;
  const page = Math.max(1, Number(searchParams.get("page") ?? 1));
  const limit = Math.min(100, Math.max(1, Number(searchParams.get("limit") ?? 10)));
  const offset = (page - 1) * limit;

  return NextResponse.json({
    items: items.slice(offset, offset + limit),
    page,
    limit,
    total: items.length,
  });
}

const withMiddleware = compose(withLogging);

export const GET = withMiddleware(handleGet);
