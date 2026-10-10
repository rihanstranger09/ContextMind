# ContextMind

[![Railway ready](https://img.shields.io/badge/Railway-ready_to_deploy-0B0D47?style=flat&logo=railway)](#railway-deployment)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Good questions. Connected answers.** An evidence-first company-brain MVP for FalkorDB · Graph Hacks Track 03.

ContextMind connects a fictional fintech company’s people, teams, projects, systems, documents, tickets, chats, incidents, meetings, and decisions. Ask what breaks when a service fails, who can help, or why a migration was delayed. Inspect the actual relationships behind each claim.

## Demo and submission status

- **Quick-test guide:** [`/demo.html`](frontend/demo.html), served by the running app.
- **Dashboard:** `/dashboard` (also available at `/`).
- **Health:** `/api/health` checks that the graph can read the seeded Database Cluster. Returns HTTP 200 with `status: healthy`, `version: 1.0.0-mvp`, actual `graph_mode`, and `sample_data: NovaPay`; HTTP 503 if the graph read fails. Existing `backend` and `company` fields remain compatible with the dashboard.
- **Repository:** [rihanstranger09/ContextMind](https://github.com/rihanstranger09/ContextMind), verified public.
- **License:** [MIT](LICENSE).
- **Public deployment:** not yet provisioned or verified. The badge above indicates configuration readiness, **not** a successful deployment. No placeholder URL is presented as live.

The dashboard’s **Demo guide** link opens instructions for testing chat, graph interactions, source cards, and evidence traces. The guide shows the current host URL, probes health, and links all five demo questions into the dashboard input. Questions are not sent until the user submits them.

## Railway deployment

1. In Railway, create a project from this GitHub repository. Select branch **`arena/10eeec69-contextmind`**, which contains this implementation. No changes have been made to `main`.
2. Railway can use the included `Dockerfile` and `railway.json`. The container listens on `0.0.0.0:$PORT` (8000 locally); `/api/health` is the deployment health check.
3. For a quick **fictional-data-only** demo, set `GRAPH_BACKEND=demo`. Leave `INGEST_TOKEN` unset to disable ingestion. Keep one instance/worker. Without a persistent volume, runtime demo updates and answer traces are lost on redeployment; for persistence, mount a volume at `/app/.runtime`.
4. For FalkorDB mode, provision a reachable FalkorDB service separately and set `GRAPH_BACKEND=falkordb`, `FALKOR_HOST`, `FALKOR_PORT`, and `FALKOR_GRAPH`. Railway does not deploy the local Compose stack automatically. This adapter assumes a trusted private network without database password/TLS configuration; do not expose the database port publicly.
5. Generate a public domain in Railway’s networking settings. Open `/demo.html`, confirm health, and submit each suggested question. Check chat facts, graph nodes, source excerpts, and the expandable trace.
6. Add the **real, verified URL** to this README, and only then change the badge to “Deployed on Railway” linked to that URL.

Public hosting may incur charges. This prototype has no authentication or rate limits, and answering questions persists traces. Use only the fictional dataset and limit public demo exposure; do not treat the demo as production-ready.

### Final submission checklist

- [ ] Confirm the implementation branch is pushed to GitHub and selected for deployment.
- [ ] Deploy the app and test the public URL (including `/demo.html` and `/api/health`).
- [ ] Add the verified public deployment link to this README and update the badge.
- [x] Demo instructions visible from the dashboard.
- [x] Automated API coverage for all five suggested questions, graphs, sources, and traces.
- [ ] Manually verify those workflows in a browser on the public deployment.
- [x] Health endpoint reports readiness and actual graph mode.
- [x] Repository visibility verified public.
- [x] MIT license included.

## Quick start

### FalkorDB deployment

Requires Docker with Compose:

```sh
docker compose up --build
```

Open **http://localhost:8000**. Compose starts FalkorDB, waits for its health check, and starts the API and frontend. The initial graph is automatically seeded on first startup. FalkorDB data is stored in a named volume; the database port is not published externally.

The graph indicator in the sidebar reports the actual backend. FalkorDB failures do **not** silently fall back to demo storage.

### Local preview without Docker

Python 3.11+:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
GRAPH_BACKEND=demo uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Demo mode is explicitly labeled. It uses the same graph tools with a local JSON adapter, persists updates and traces to ignored `.runtime/demo.json`, and needs no credentials or external services. Delete that file to reset demo data. The `.env.example` documents configuration; local shell variables must be exported (the app does not automatically load `.env`).

To connect locally to an existing FalkorDB instance, set `GRAPH_BACKEND=falkordb`, `FALKOR_HOST`, `FALKOR_PORT`, and optionally `FALKOR_GRAPH` (default `contextmind`).

## Demo in two minutes

1. Ask **“What is at risk if the Database Cluster is unavailable, who should respond, and what previous decisions are relevant?”**
2. Inspect the multi-hop project dependencies and scored experts. Click **Path** beside a claim to see its stored relationships.
3. Open a source card to read its excerpt and timestamp. All `novapay.example` source URLs are deliberately fictional and shown as text, not working external links.
4. Ask **“Why was Analytics Migration delayed?”** to follow the decision to DB-212, chat, planning notes, and the RFC.
5. Ask **“Which critical systems have no active owner?”** to find missing Redis ownership/documentation.
6. Use the source library, click graph nodes, change graph focus, and zoom. `Ctrl / Cmd K` focuses the question input.

More supported questions:

- Who owns API Gateway?
- Who knows the most about Payment Service?
- What tickets block the Q4 launch?
- Find docs about Database Cluster.

Entity IDs are stable and discoverable at `/api/entities`; for example the database is `sys_database` and the migration decision is `decision_delay`.

## Architecture

```text
Vanilla HTML/CSS/JS dashboard
        │ same-origin REST
        ▼
FastAPI → deterministic intent/entity router
        → allowlisted graph tools
        → bounded graph traversals
        → facts + source excerpts + relationship traces
        → persisted AgentDecision / USED_EVIDENCE
        ▼
FalkorDB: typed entities and typed relationships
```

- **`graph/store.py`**: parameterized FalkorDB storage plus an explicit JSON demo adapter. Entities have `:Entity` and their domain label (`:System`, `:Person`, etc.). Edges use native domain relationship types (`DEPENDS_ON`, `USES`, etc.). Node payloads preserve source metadata; `id`, `name`, `updated_at`, and `kind` are also directly queryable properties.
- **`graph/tools.py`**: entity resolution, direct/team-lead ownership, expert ranking, reverse dependency traversal, decision evidence, blockers, knowledge gaps, and evidence retrieval. Impact analysis includes directly used systems and indirect dependencies up to five hops, with cycle protection. Visualization neighborhoods are capped at 70 nodes and depth 3.
- **`agents/company_brain.py`**: routes supported questions, assembles only relevant facts/evidence, exposes auditable retrieval paths, and stores the answer trace. Unknown entities produce an explicit insufficient-context response.
- **`app/main.py`**: validated HTTP API, write token checks, static frontend.
- **`data/sample_company.json`**: fictional NovaPay company graph; regenerate with `python data/generate.py`.

**No LLM is wired in yet.** Answer synthesis is deterministic and supported intents are keyword-based. The frontend shows evidence paths, not hidden chain-of-thought. This makes the demo reproducible and avoids fabricated company facts. The tools operate through FalkorDB reads in database mode; the graph is not merely a visualization layer. An LLM integration should receive only these bounded facts, excerpts, and paths, never the entire graph or permission to execute arbitrary Cypher.

### Expertise scoring

Recorded direct/project work = 3; document authorship = 2; resolved incident = 4; direct ownership or owning-team lead = 5. Unique evidence paths contribute once; multiple distinct dependency paths may contribute. Scores are explanatory heuristics, **not probabilities**. Recorded availability/on-call status is displayed but must be confirmed before escalation. Recency weighting is not yet implemented.

## API

Interactive OpenAPI documentation: **`/docs`**.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Backend and demo-data status |
| GET | `/api/entities?q=&type=` | Entity search (bounded to 100) |
| GET | `/api/entities/{id}` | Entity or saved answer trace |
| POST | `/api/chat` | `{ "question": "Who owns API Gateway?" }` |
| POST | `/api/impact` | `{ "system_id": "sys_database" }` |
| GET | `/api/experts/{id}` | Ranked experts with paths |
| GET | `/api/decisions/{id}/trace` | Decision relationships |
| GET | `/api/graph/subgraph?entity_id=sys_database&depth=2` | Bounded graph neighborhood |
| GET | `/api/risks` | Critical systems missing ownership/docs |
| POST | `/api/ingest/documents`, `/tickets`, `/messages` | Token-protected source upsert |

### Live update example

Compose defaults to `local-demo-token` **for local demonstration only**. Set `INGEST_TOKEN` to a strong secret for anything else. In local Python mode, ingestion is disabled unless the variable is configured. Do not expose this prototype to untrusted users.

```sh
curl -X POST http://localhost:8000/api/ingest/tickets \
  -H 'Authorization: Bearer local-demo-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "ticket_replication",
    "name": "DB-212 · Replication lag exceeds threshold",
    "content": "Replication validation passed. Migration can resume.",
    "status": "RESOLVED",
    "priority": "CRITICAL",
    "updated_at": "2026-10-10T12:00:00Z",
    "about_id": "sys_database",
    "project_id": "project_analytics",
    "assignee_id": "person_carol"
  }'
```

Ask about Analytics Migration blockers again; DB-212 no longer appears as an open blocker. The historical delay decision remains, correctly, in the graph. Upserts use stable IDs, record hashes and sync timestamps, reject older updates and type collisions, and do not duplicate existing edges. Replacing established relationship metadata is rejected rather than silently leaving stale edges. Re-ask/reselect a node to refresh the UI; there is no push sync or background connector.

## Verification

```sh
pytest -q
node --check frontend/app.js
```

Tests cover alias resolution, direct/multi-hop impact, indirect expertise, citations/decision traces, missing context, gaps, idempotent persistence, blocker resolution, and API/write validation. They use the JSON test adapter. Docker/FalkorDB integration must be verified separately in a Docker-capable environment.

## Scope and limitations

This is a runnable hackathon foundation, **not a production knowledge/security platform**:

- Real Slack/Jira/Notion/GitHub connectors, extraction pipelines, scheduled synchronization, and deletion reconciliation are not implemented. Ingestion accepts normalized manual records.
- No authentication, per-user ACLs, tenant isolation, rate limits, or audit retention policy. `user_id` is not an authorization boundary. Use only fictional/sanitized data.
- Bounded entity matching uses IDs/names/aliases, not vector search or an ambiguity-confirmation dialogue. It selects the longest known name; broad unknown queries return insufficient context.
- Missing-owner detection reflects absence of recorded ownership, not a verified lack of a real-world owner. No employee-active-state checks yet.
- Source cards mark records older than 90 days. Staleness does not automatically invalidate a source. No stale-doc risk scoring yet.
- Expert scores do not model current workload or recent activity. No automated paging or work assignment.
- Graph tools issue parameterized adjacency queries and traverse in Python. This MVP is not optimized for large graphs; entity search is bounded to 100 results, adjacency reads to 300, and trace pagination is not implemented.
- Cross-record FalkorDB writes are not transactional; concurrent ingestion conflict control and migrations remain future work. Run one API worker for the JSON demo backend.
- The UI is an interactive SVG explorer with focus and zoom, not a force-directed editor. No live ingestion UI or video asset is included.

**FalkorDB is the company graph, evidence store, and answer-trace memory in database mode. Every supported factual answer is built from graph relationships that can be inspected.**
