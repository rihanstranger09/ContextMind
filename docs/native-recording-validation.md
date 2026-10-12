# Native FalkorDB recording validation — 2026-10-12

The prototype video was recorded against a **real FalkorDB 4.16.3 module** on a local Redis 8.2.3 process, using the optional `falkordb-bin==1.4.1` Python wheel. The FastAPI instance used `GRAPH_BACKEND=falkordb`, graph prefix `contextmind_video`, and port 8001. Port 8000's JSON preview remained separate.

This is a local development/test instance, not a production deployment. Persistence was disabled for the recording database; it was populated from the repository's checked-in snapshots. No live third-party sync was running. Narration is AI-generated. The video uses real app footage and captured panels with edited holds so evidence can be read; no answers or graph relationships were fabricated for the recording.

## Checks

- `FALKOR_INTEGRATION=1 .venv/bin/pytest -q`: **56 passed**, with one dependency deprecation warning.
- `BASE_URL=http://127.0.0.1:8001 CHROMIUM_BUNDLED_LIBS=1 npm test --prefix tests/browser`: equivalent browser script passed **22 checks** against the native backend, covering both workspaces.
- Both workspace health endpoints returned `healthy` with `graph_mode: falkordb`.
- API/database reads, repeat startup, snapshot replay, privacy suppression, and query graph traces were exercised.

This validates the packaged FalkorDB **4.16.3** instance, not the separate Docker/CI image version or an external deployment.

## Fixes exposed by running the native backend

1. Replaced a non-existent `contains(...)` function with Cypher's `CONTAINS` operator.
2. Handled the specific “already indexed” response on repeat startup without suppressing unrelated database errors.
3. Made public evidence path selection deterministic, preferring document-to-repository links over organization publication links. Database edge-return order is not guaranteed.

The native integration test now checks reopening an existing graph and inclusion of the resolved repository in the returned answer subgraph.

## Video deliverables

The video, captions, and transcript are exported to `deliverables/`, ignored by Git to keep generated media out of the source repository. Runtime databases, intermediate media, and browser recordings remain under ignored `.runtime/`.

## Eligibility reminder

The official Graph Hacks page states that the submission and main FalkorDB implementation must be new work completed during the October 15–18, 2026 event. This prototype and recording were prepared before that window. Confirm eligibility with the organizers; producing a submission-style video does not establish eligibility.

Official page: https://www.wemakedevs.org/hackathons/falkordb
