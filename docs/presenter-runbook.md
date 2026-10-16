# Company Brain · native FalkorDB presentation runbook

[Download the current narrated, captioned 2:20 MP4](../presentation/ContextMind-FalkorDB-demo.mp4). It was filmed against a **local native FalkorDB module**, not an unverified cloud deployment. NovaPay is a **fictional** company; the FalkorDB workspace is a **bounded GitHub snapshot**. The narration uses a user-selected Indian English masculine AI voice. The video has not been published or submitted automatically. Do not show credentials or claim that source timestamps imply live data.

## Safe local setup and recording

1. Install `requirements.txt`, `npm ci --prefix tests/browser`, Playwright's video encoder (`tests/browser/node_modules/.bin/playwright install ffmpeg`), and provide ffmpeg for the render stage (`FFMPEG=/path/to/ffmpeg` if not on PATH). Docker Compose can start an isolated native database + app: `docker compose up --build`. For the recording-only ingest, use an **operator token** on an isolated test instance, not a production secret. Both workspaces must return `healthy`, `graph_mode: falkordb` from `/api/health?workspace=novapay` and `?workspace=falkordb`.
2. Start a **fresh, disposable graph prefix** for every take. The guard checks `/api/graph/company-proof?workspace=novapay` and `/api/graph/showcase?workspace=falkordb` for nonempty native query results before filming. If JSON storage is active it refuses to record.
3. With the isolated app running and the operator token in **local environment variables only**, run `BASE_URL=http://127.0.0.1:8000 VIDEO_INGEST_TOKEN="$INGEST_TOKEN" CHROMIUM_BUNDLED_LIBS=1 npm run record:company --prefix tests/browser`. The recorder sends normalized fictional ticket writes through the token-protected API; the token never appears in the browser, video, logs, repo, or README. It saves raw WebM and scene timing JSON under ignored `deliverables/`.
4. Supply ten same-speaker narration clips (`01-intro.mp3` through `10-close.mp3` in `deliverables/company-narration/`, names in `render-company-brain.py`). Render with `python tests/browser/render-company-brain.py`. The renderer checks scene timing and clip lengths, burns in captions, and exports a high-bitrate H.264/AAC MP4 and an SRT sidecar under ignored `deliverables/`. Review every claim and caption before copying the final MP4 into `presentation/` for a persistent download.

## Recorded sequence (~2 minutes 20 seconds)

| Moment | Actual footage | Honest claim |
|---|---|---|
| 0:00 | NovaPay dashboard (native storage label) | Scattered fictional docs, tickets, chats and decisions can be connected. |
| 0:08 | **Graph model** modal | Typed node and relationship schema, explicitly fictional. |
| 0:17 | **Decision Cypher** proof | Fixed native `BASED_ON` + `IMPACTS` query links a fictional decision to ticket/chat/meeting/RFC. |
| 0:32 | Ask why migration was delayed | Deterministic tool routing, linked evidence paths and source cards; not autonomous planning. |
| 0:50 | Ask who owns database | Recorded ownership and expert evidence, not verified real-time availability. |
| 1:03 | Reload and open recent investigation | Saved answer, tool steps and graph trace persist across page reloads. |
| 1:13–1:37 | Authenticated fictional ticket ingest → re-ask → resolve → re-ask | Graph data changes; older answer remains saved; latest active blockers change. Not a live GitHub sync. |
| 1:38 | Public FalkorDB proof | Separate graph, second fixed native Cypher query and real GitHub release citation. |
| 1:52 | Ask about Python client maintainers | Bounded public activity evidence; no maintainer assignment inferred. The public Decisions tab is hidden. |
| 2:08 | End card | Company Brain track; GitHub repo and complete local setup. Explicitly **no verified cloud deployment**. |

## Integrity / submission reminder

The graph proof endpoints do not accept user-supplied Cypher or graph names. JSON mode is labeled **CYPHER NOT EXECUTED**. The UI shows *actual* tool calls, not hidden chain-of-thought. No MCP interface, LLM tool caller, graph-algorithm package or live public deployment is claimed. Timings are not benchmarks. [Graph model/queries](graph-model-and-queries.md) and [submission checklist](submission-checklist.md) explain scope.

**Eligibility is unresolved:** this repo documents a prototype and native video recorded before the October 15–18, 2026 event. New changes/video do not retroactively make its core implementation new. Confirm with organizers before submitting, disclose AI assistance accurately, and do not alter commit dates. Do not use this MP4 as evidence of a hosted cloud test.
