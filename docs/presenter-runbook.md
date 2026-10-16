# Native FalkorDB presentation runbook

This is a **recording plan**, not a claim that a new video has already been recorded. Use a native database in the final video: the public GitHub dataset and the storage engine are separate things. Never call the JSON preview “running on FalkorDB.” Do not display `.env.txt`, passwords, connection strings, cloud consoles, or private graphs on camera.

## Rehearsal (local, no cloud credentials)

1. Install the app dependencies: `pip install -r requirements.txt`.
2. Start an isolated FalkorDB service: `docker compose up --build`. This starts the app at `http://localhost:8000` and a local FalkorDB instance on a private Compose network, **not** a hosted/cloud instance. The app seeds two separate graphs on first boot: fictional NovaPay and the public FalkorDB snapshot. If Docker is unavailable, point `GRAPH_BACKEND=falkordb` at another isolated FalkorDB instance using the documented variables; do not substitute the JSON adapter.
3. Visit `/demo.html?workspace=falkordb` and verify the readiness line says **READY FOR NATIVE RECORDING**. Open `/api/health?workspace=falkordb`: `graph_mode` must be `falkordb` and status `healthy`. Open `/api/graph/showcase?workspace=falkordb`: `native_cypher_executed` must be `true` and `paths` nonempty. If not, stop and fix the environment rather than editing the video to conceal it.
4. For a cloud-based shoot, inject `FALKOR_HOST`, `FALKOR_PORT`, `FALKOR_USERNAME`, `FALKOR_PASSWORD`, `FALKOR_SSL=true`, `GRAPH_BACKEND=falkordb` and a **dedicated graph prefix** into the deployment's secret variables; alternatively use `FALKOR_URL=rediss://...`. Never show that URL on screen. See README's cloud setup. Startup seeds empty graphs; do not connect this public demo to a sensitive production database.
5. Optional native integration validation: `FALKOR_INTEGRATION=1 pytest -q tests/test_falkordb_integration.py` against a **disposable** database. This test deletes its own uniquely named graph. Do not run on a restricted production account. The fixed read-only showcase endpoint itself does not modify data.
6. To capture a silent browser take, run `npm ci --prefix tests/browser`, `tests/browser/node_modules/.bin/playwright install ffmpeg` (Playwright's video encoder), then `CHROMIUM_BUNDLED_LIBS=1 npm run record --prefix tests/browser` while the native app is running. Output is ignored by Git at `deliverables/native-falkordb-showcase.webm`. The script **refuses** JSON mode or an empty native proof; it does not show credentials or cloud settings. Edit in narration/captions before submission. This is a screen recording aid, not a finished submission video.

## Shot list (about 1 minute 45 seconds)

| Time | Screen | Suggested narration (say only after verifying) |
|---|---|---|
| 0:00–0:20 | Public demo guide and dashboard sidebar | “ContextMind is a company-brain demo with a public FalkorDB GitHub snapshot. Here the backend status says FalkorDB storage, not JSON demo mode.” |
| 0:20–0:55 | Click **FALKORDB PROOF**; hold on native status, Cypher, counts, path/source | “This is a fixed parameterized Cypher traversal executed against FalkorDB. It follows the organization through its Python client to recorded releases. The counts and these paths came from this running graph, and each release links back to GitHub.” |
| 0:55–1:25 | Ask “How do I use FalkorDB with LangChain?”; open source and trace | “A question returns attributed evidence and an inspectable relationship trace. The graph is used for retrieval, not just a visual decoration. This answer is drawn from a bounded public snapshot.” |
| 1:25–1:45 | Ask “What is FalkorDB annual revenue?” | “When the snapshot lacks evidence, the system says so instead of inventing a financial claim. This is not a live crawl or an LLM-generated answer.” |

Show the green **NATIVE FALKORDB · CYPHER EXECUTED** badge only with `GRAPH_BACKEND=falkordb`. In JSON mode it explicitly says **CYPHER NOT EXECUTED**. Timings on the panel measure this server-side proof request only; do not call them a benchmark or claim a speedup. The graph counts are graph storage counts, not the number of visible SVG nodes. The public workspace is a bounded snapshot from GitHub; do not imply verified maintainer status, live updates, or private company access. NovaPay is fictional.

## Why this matters / checks

- The showcased multi-hop query is allowlisted and parameterized on the server; the client cannot submit arbitrary Cypher. Graph names and credentials are never sent to the browser.
- Two workspace graphs are isolated by name; the proof targets only the public graph.
- Unit tests ensure JSON mode never claims execution; the opt-in integration test executes the fixed query on a real FalkorDB service. Browser tests click the proof button and validate the native/preview label.
- Video eligibility: this repository had a prototype and earlier recording **before** the October 15–18, 2026 event. Confirm hackathon rules/eligibility with organizers; recording a new video or adding features during the event does not retroactively make earlier work new.
