# SPEC-2026-Q2-002: GraphQL Gateway Investigation

**Status:** Complete | **Time spent:** 2.5 days / 3 days budgeted
**Recommendation:** NO-GO (for now)

## Question

Should we add a GraphQL gateway in front of the API and worker services?

## Architecture Diagram

```
                    ┌─────────────────┐
                    │   Client (Web)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  GraphQL Gateway │  ← Strawberry / Apollo
                    │   (port 4000)   │
                    └───┬─────────┬───┘
                        │         │
              ┌─────────▼──┐  ┌──▼──────────┐
              │  API Service│  │Worker Service│
              │  (FastAPI)  │  │  (Celery)    │
              │  port 8000  │  │  port 8001   │
              └─────────────┘  └──────────────┘
```

## Performance Benchmarks

Tested against our top 5 queries (50 concurrent users, 30s duration):

| Query                  | REST (p50) | REST (p99) | GraphQL (p50) | GraphQL (p99) |
|------------------------|-----------|-----------|---------------|---------------|
| GET /items (list)      | 12ms      | 45ms      | 15ms          | 52ms          |
| GET /items/:id         | 8ms       | 22ms      | 11ms          | 28ms          |
| GET /users/me          | 6ms       | 18ms      | 9ms           | 24ms          |
| GET /items + /users    | 24ms*     | 68ms*     | 14ms          | 38ms          |
| GET /dashboard (5 agg) | 48ms*     | 120ms*    | 22ms          | 55ms          |

*REST numbers are for sequential calls; GraphQL batches into a single request.

**Finding:** GraphQL wins on aggregated queries (40-55% faster) but adds ~3ms overhead on simple single-resource fetches.

## Schema Stitching Approach

**Strawberry (Python):**
- Native async support, good FastAPI integration
- Schema stitching via `strawberry.federation`
- Each service exposes a subgraph; gateway merges them
- Pro: Same language as existing services
- Con: Less mature federation support than Apollo

**Apollo Server (Node):**
- Industry standard for federated GraphQL
- Apollo Router handles schema composition
- Pro: Battle-tested federation, excellent tooling
- Con: Introduces Node.js into a Python-only stack

## Migration Path

GraphQL and REST can coexist:
1. Deploy gateway alongside existing REST endpoints
2. New features use GraphQL; existing REST endpoints remain
3. Gradually migrate high-traffic aggregation endpoints
4. REST endpoints deprecated only after GraphQL coverage is complete

## Trade-off Analysis

| Factor              | REST (current)       | GraphQL Gateway       |
|---------------------|---------------------|-----------------------|
| Complexity          | Low                 | Medium-High           |
| Team familiarity    | High                | Low                   |
| Aggregated queries  | Multiple round trips| Single request        |
| Over-fetching       | Common              | Eliminated            |
| Tooling/monitoring  | Mature              | Requires new setup    |
| Auth integration    | Done (SPEC-001)     | Must wrap shared auth |
| Deployment          | 2 services          | 3 services + gateway  |
| Maintenance burden  | Low                 | +1 service to maintain|

## Go/No-Go Recommendation

**NO-GO for Q2 2026.** Rationale:

1. **Team readiness**: No GraphQL experience on the team; learning curve is 2-4 weeks
2. **ROI too low**: Only 2 of our 5 top queries benefit from batching
3. **SPEC-001 dependency**: Shared auth middleware just shipped; gateway would need to wrap it, adding integration risk
4. **Operational cost**: A third service (gateway) increases deployment complexity and monitoring surface

**Revisit in Q3** if:
- We add 3+ new aggregation endpoints
- A second frontend (mobile app) needs different data shapes
- Team completes GraphQL training

## Prototype

See `examples/monorepo/output/services/api/graphql_prototype.py` for a runnable Strawberry prototype demonstrating schema stitching with the existing API service.
