# Native FalkorDB presentation runbook

A **narrated, captioned local take** is available as [a downloadable MP4](../presentation/ContextMind-FalkorDB-demo.mp4); it was recorded against a native local FalkorDB module, **not** a cloud instance or a published deployment. Raw footage, narration clips and intermediates are kept out of Git under ignored `deliverables/`. Use a native database in the final video: the public GitHub dataset and the storage engine are separate things. Never call the JSON preview “running on FalkorDB.” Do not display `.env.txt`, passwords, connection strings, cloud consoles, or private graphs on camera.

## Rehearsal (local, no cloud credentials)

1. Install the app dependencies: `pip install -r requirements.txt`.
2. Start an isolated FalkorDB service: `docker compose up --build`. This starts the app at `http://localhost:8000` and a local FalkorDB instance on a private Compose network, **not** a hosted/cloud instance. The app seeds two separate graphs on first boot: fictional NovaPay and the public FalkorDB snapshot. If Docker is unavailable, point `GRAPH_BACKEND=falkordb` at another isolated FalkorDB instance using the documented variables; do not substitute the JSON adapter.
3. Visit `/demo.html?workspace=falkordb` and verify the readiness line says **READY FOR NATIVE RECORDING**. Open `/api/health?workspace=falkordb`: `graph_mode` must be `falkordb` and status `healthy`. Open `/api/graph/showcase?workspace=falkordb`: `native_cypher_executed` must be `true` and `paths` nonempty. If not, stop and fix the environment rather than editing the video to conceal it.
4. For a cloud-based shoot, inject `FALKOR_HOST`, `FALKOR_PORT`, `FALKOR_USERNAME`, `FALKOR_PASSWORD`, `FALKOR_SSL=true`, `GRAPH_BACKEND=falkordb` and a **dedicated graph prefix** into the deployment's secret variables; alternatively use `FALKOR_URL=rediss://...`. Never show that URL on screen. See README's cloud setup. Startup seeds empty graphs; do not connect this public demo to a sensitive production database.
5. Optional native integration validation: `FALKOR_INTEGRATION=1 pytest -q tests/test_falkordb_integration.py` against a **disposable** database. This test deletes its own uniquely named graph. Do not run on a restricted production account. The fixed read-only showcase endpoint itself does not modify data.
6. To capture native browser footage, run `npm ci --prefix tests/browser`, `tests/browser/node_modules/.bin/playwright install ffmpeg` (Playwright's video encoder), then `CHROMIUM_BUNDLED_LIBS=1 npm run record --prefix tests/browser` while the native app is running. Output is ignored by Git at `deliverables/native-falkordb-showcase.webm`. The script **refuses** JSON mode or an empty native proof; it does not show credentials or cloud settings. It holds each shot long enough for narration (about 95 seconds).
7. Supply five narration clips under `deliverables/narration/` named `01-intro.mp3`, `02-proof.mp3`, `03-question.mp3`, `04-trace.mp3`, `05-boundary.mp3`. The current take uses user-selected **Indian English masculine AI narration**; clips are generated outside the repository and not committed. With ffmpeg installed (`FFMPEG=/path/to/ffmpeg` if not on PATH), run `python tests/browser/render-showcase.py`. The renderer checks that clip durations fit their shots, mixes audio, burns in readable captions, and writes `deliverables/contextmind-falkordb-presenting-video.mp4` plus a separate `.srt` file. Review sync, captions, attribution and hackathon rules before publishing; the generated MP4 is not automatically submitted.

## Recorded shot list (about 1 minute 35 seconds)

| Time | Screen | Narration focus |
|---|---|---|
| 0:00–0:16 | Public demo guide and dashboard sidebar | Public GitHub snapshot; native FalkorDB backend, not a JSON mock. |
| 0:16–0:39 | Click **FALKORDB PROOF**; hold on native status, Cypher, counts, path/source | Fixed parameterized Cypher traversal, graph counts and provenance links. |
| 0:39–0:57 | Ask “How do I use FalkorDB with LangChain?” | Bounded, source-backed answer, not an invented connection. |
| 0:57–1:14 | Open source and expand “Why this answer?” | Show attributed GitHub artifact and relationship evidence trace. |
| 1:14–1:35 | Ask “What is FalkorDB annual revenue?” | Refuse unsupported financial claims; snapshot, not live data or LLM synthesis. |

Show the green **NATIVE FALKORDB · CYPHER EXECUTED** badge only with `GRAPH_BACKEND=falkordb`. In JSON mode it explicitly says **CYPHER NOT EXECUTED**. Timings on the panel measure this server-side proof request only; do not call them a benchmark or claim a speedup. The graph counts are graph storage counts, not the number of visible SVG nodes. The public workspace is a bounded snapshot from GitHub; do not imply verified maintainer status, live updates, or private company access. NovaPay is fictional.

## Why this matters / checks

- The showcased multi-hop query is allowlisted and parameterized on the server; the client cannot submit arbitrary Cypher. Graph names and credentials are never sent to the browser.
- Two workspace graphs are isolated by name; the proof targets only the public graph.
- Unit tests ensure JSON mode never claims execution; the opt-in integration test executes the fixed query on a real FalkorDB service. Browser tests click the proof button and validate the native/preview label.
- Video eligibility: this repository had a prototype and earlier recording **before** the October 15–18, 2026 event. Confirm hackathon rules/eligibility with organizers; recording a new video or adding features during the event does not retroactively make earlier work new.
