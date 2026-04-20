// SPEC-2026-Q2-002 / AC-4 — Users route refactored to use shared middleware

import { type NextRequest, NextResponse } from "next/server";
import { compose, withAuth, withLogging } from "../middleware";
import { notFound } from "../errors";

const users = [
  { id: "1", name: "Alice", email: "alice@example.com" },
  { id: "2", name: "Bob", email: "bob@example.com" },
];

async function handleGet(_req: NextRequest): Promise<NextResponse> {
  return NextResponse.json({ users });
}

async function handleGetById(
  _req: NextRequest,
  id: string
): Promise<NextResponse> {
  const user = users.find((u) => u.id === id);
  if (!user) return notFound(`User ${id} not found`);
  return NextResponse.json(user);
}

const withMiddleware = compose(withLogging, withAuth);

export const GET = withMiddleware(handleGet);
