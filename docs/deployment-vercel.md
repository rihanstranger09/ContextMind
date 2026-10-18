# ContextMind on Vercel with hosted FalkorDB

ContextMind deploys to Vercel as its own project — **separate** from the
Next.js `company-brain` project — using Vercel's FastAPI preset. The existing
`app/main.py` exports the FastAPI `app`, so the whole service (API + bundled
frontend) runs as one Fluid-compute function. `vercel.json` only tunes that
function: 300 s duration (first-hit graph seeding), the frontend and the two
seed snapshots bundled via `includeFiles`, and tests/presentation media
excluded. `.python-version` pins Python 3.12. There are no rewrites and no
`api/` shim to keep in sync.

```text
Browser ──HTTPS──▶ Vercel project "contextmind" (app/main.py, FastAPI)
                       │  Redis protocol (TLS when the provider requires it)
                       ▼
                   Hosted FalkorDB (same instance as company-brain)
                     ├─ contextmind_vercel                  (NovaPay fictional)
                     └─ contextmind_vercel_public_falkordb  (public snapshot)
```

The two graphs above are the **distinct ContextMind graphs**. They are not
shared with `company-brain`, with local development (`contextmind*`), with CI
test graphs, or with disposable recording graphs (`contextmind_recording_*`).
Application startup seeds each graph from the committed snapshots **only if
that graph is empty**, so redeploys never wipe saved investigations.

## Status (2026-10-18)

| Step | State |
|---|---|
| Deployment code + config in this PR | Done |
| Local native verification (FalkorDB 4.16.3, distinct local graph) | **PASS** — verifier green on health + both proofs; JSON mode correctly FAILs |
| Test suite | 105 passed + native integration test passed locally (1 skipped without a database) |
| Separate Vercel project `contextmind` | Created; linked to `rihanstranger09/ContextMind` |
| Non-secret env (`GRAPH_BACKEND`, `FALKOR_GRAPH`, `LLM_PROVIDER`) | Set on the project |
| Hosted FalkorDB credentials | **Pending — owner adds them privately in Vercel (below). Never paste them in chat, issues, PRs or recordings.** |
| Hosted `/api/health` + both native-Cypher proofs verified | **Pending** the credentials above |
| Revised 1× native demo video | **Pending** — record only after hosted verification passes (gate below) |

Until the hosted verification row passes, no Vercel URL from this project may
be described as a verified native deployment. Health fails closed meanwhile:
the dashboard serves, but `/api/health` returns HTTP 503 with
`graph_mode: "unavailable"`, `graph_ready: false` (and
`graph_configured: "falkordb"` showing what was requested). Endpoint details
are never echoed.

## Environment variables

Set under Vercel → Project `contextmind` → Settings → Environment Variables.
Changing variables requires a redeploy to take effect.

### Already set by project setup (plain, non-secret values)

| Name | Value | Why |
|---|---|---|
| `GRAPH_BACKEND` | `falkordb` | Native mode. Never `demo` on a public URL — the verifier fails JSON mode. |
| `FALKOR_GRAPH` | `contextmind_vercel` | Distinct graph prefix on the hosted instance (see diagram). |
| `LLM_PROVIDER` | `disabled` | Deterministic router, labeled as such in health/UI. The live OpenAI agent is opt-in below. |

### Owner adds privately (Sensitive; targets: Production + Preview)

Copy these from the **FalkorDB provider console** for the same hosted
instance that `company-brain` uses. They intentionally cannot be copied
project-to-project by an assistant without exposing the values, so re-enter
them from the provider. Use the Redis-protocol endpoint, not a web URL.

| Name | Value |
|---|---|
| `FALKORDB_HOST` | Hosted FalkorDB hostname |
| `FALKORDB_PORT` | Hosted port (provider supplies it; code defaults to 6379 only if unset) |
| `FALKORDB_PASSWORD` | Instance password |
| `FALKORDB_USERNAME` | **Only if** the provider issued a username |
| `FALKORDB_SSL` | `true` **only if** the endpoint requires TLS (a `rediss://` connection string means it does). Certificate and hostname verification stay on. |

Alternative: replace all five with a single sensitive
`FALKOR_URL=rediss://<user>:<password>@<host>:<port>` and leave every
individual `FALKOR_*`/`FALKORDB_*` connection variable unset — the code
rejects mixing a URL with non-blank individual settings instead of guessing.
The `FALKOR_HOST` / `FALKOR_PORT` / `FALKOR_USERNAME` / `FALKOR_PASSWORD` /
`FALKOR_SSL` spellings are also accepted and take precedence over
`FALKORDB_*`. Blank values count as unset everywhere.

### Optional, later

- **Live agent:** `LLM_PROVIDER=openai`, `OPENAI_API_KEY` (Sensitive),
  `MODEL_NAME`. Only after a real provider call is verified end to end may
  the deployment be presented as using the live tool-calling agent; until
  then it stays `disabled`/deterministic. Without a key the chat endpoint
  returns 503 rather than silently substituting the deterministic router.
- **Operator writes:** leave `INGEST_TOKEN` **unset** in Production.
  Writes are disabled without it. It exists only for a controlled,
  preview-scoped recording window (gate below) and must be removed after.

## Seed the distinct hosted graphs (optional but recommended)

First request against an empty graph auto-seeds it, which can make one cold
start slow. To pre-seed from a local checkout instead, put the same
connection values in a local ignored `.env` (never commit it), then:

```sh
GRAPH_BACKEND=falkordb FALKOR_GRAPH=contextmind_vercel python -m backend.seed
# novapay: native FalkorDB ready; {'nodes': ..., 'relationships': ...}
# falkordb: native FalkorDB ready; {'nodes': 332, 'relationships': 378}
```

This prints counts only. It is idempotent for an already-seeded graph.

## Verify before claiming anything

After the credentials are in and the project has been redeployed:

```sh
python scripts/verify_deployment.py https://<production-host>
```

The verifier (standard library only; sends no secrets) requires **all** of:

1. `GET /api/health?workspace=novapay` → 200, `status: healthy`,
   `graph_mode: falkordb`, `graph_ready: true`.
2. `GET /api/health?workspace=falkordb` → same.
3. `GET /api/graph/company-proof?workspace=novapay` →
   `native_cypher_executed: true`, exactly 4 `BASED_ON` evidence rows.
4. `GET /api/graph/showcase?workspace=falkordb` →
   `native_cypher_executed: true`, ≥332 entities, ≥378 relationships,
   3 org → Python-client → release paths.
5. `GET /dashboard` → 200.

It retries for a few minutes while a cold deployment seeds. Exit code 0 and
a final `PASS` line are the release evidence — save the output with the
date. Anything else (JSON mode, 503 `unavailable`, partial seed) exits 1.

Troubleshooting, in order: a Vercel login page instead of the app →
Deployment Protection is still covering this URL (see Exposure notes).
503 with `graph_mode: unavailable` → credentials
missing/wrong, a required username or `FALKORDB_SSL=true` not set, or no
redeploy after the last env change. `graph_mode: demo` → `GRAPH_BACKEND`
did not reach the deployment. Only the first request slow → initial seeding;
pre-seed (above) or let the verifier retries finish.

## Recording gate for the revised 1× native demo video

Do **not** record until every box passes, in order:

1. This PR is merged and the **Production** deployment is READY.
2. `scripts/verify_deployment.py` prints PASS against the production URL;
   keep that output next to the recording notes.
3. Record against a deployment of that same verified build, using a fresh
   disposable recording graph — preview-scoped `FALKOR_GRAPH` such as
   `contextmind_recording_<random>` plus a preview-only `INGEST_TOKEN` —
   following `scripts/record_runbook.md`. Never write the fictional VID-42
   ticket into the production `contextmind_vercel` graph, never show the
   Vercel/FalkorDB consoles, tokens, hostnames or shell history, and remove
   the preview token/graph variables when filming ends.
4. Re-run the verifier after recording to confirm production is untouched.

Until then the 1× native video remains **pending**; the existing repository
videos keep their existing (local-native, pre-deployment) labels.

## Exposure notes

This remains a fictional/snapshot-data prototype with no authentication,
rate limits or per-user permissions. Answered questions persist as traces
in the hosted graphs by design. Keep `INGEST_TOKEN` unset publicly, watch
function/database usage on the free tiers, and pause the Vercel project
when the demo window closes. Deployment Protection on preview URLs is
fine; the production alias must be publicly reachable for judges.
