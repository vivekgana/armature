"""SPEC-2026-Q2-002 — Runnable GraphQL prototype (spike deliverable).

This is a proof-of-concept demonstrating how Strawberry would integrate
with the existing FastAPI service. NOT for production use.

Run: uvicorn services.api.graphql_prototype:app --port 4000
Query: POST http://localhost:4000/graphql
  { "query": "{ items { id name } me { email roles } }" }
"""

from __future__ import annotations

from typing import Optional

import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter


@strawberry.type
class Item:
    id: str
    name: str
    price: float


@strawberry.type
class User:
    id: str
    email: str
    roles: list[str]


_ITEMS = [Item(id=str(i), name=f"Item {i}", price=i * 1.5) for i in range(1, 11)]
_CURRENT_USER = User(id="user-1", email="demo@example.com", roles=["admin"])


@strawberry.type
class Query:
    @strawberry.field
    def items(self, limit: int = 10, offset: int = 0) -> list[Item]:
        return _ITEMS[offset : offset + limit]

    @strawberry.field
    def item(self, id: str) -> Optional[Item]:
        return next((i for i in _ITEMS if i.id == id), None)

    @strawberry.field
    def me(self) -> User:
        return _CURRENT_USER


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema)

app = FastAPI(title="GraphQL Gateway Prototype")
app.include_router(graphql_router, prefix="/graphql")
