# UI testing checklist — 2026-10-12

**Result: PASS** in real headless Chromium 153.0.8010.0 against the running FastAPI server at `http://127.0.0.1:8000`, with `GRAPH_BACKEND=demo`. Both NovaPay and FalkorDB public-snapshot workspaces were exercised. This is a browser test, not a DOM simulation.

| Requested check | Result | Evidence |
|---|---|---|
| Backend starts without errors | Pass | Server startup completed; both workspace health endpoints returned HTTP 200 and `healthy` |
| Frontend loads without 404s | Pass | Zero HTTP 4xx/5xx responses across tested dashboard/demo page loads and requests |
| Org switcher buttons are clickable | Pass | Both sidebar workspace links navigated successfully; header selector changed workspace |
| Chat input can be focused and typed in | Pass | Click-to-focus, active-element assertion, sequential keyboard entry, and input-value assertion |
| Send button submits query | Pass | Actual click sent POST `/api/chat` with the expected question and workspace; HTTP 200 |
| Graph renders | Pass | Visible SVG nodes and edges asserted; desktop/mobile screenshots captured |
| Answer, sources, and trace display | Pass | Answer facts, source dialogs, expanded trace list, and clickable path evidence inspected |
| Demo questions are clickable | Pass | All eight dashboard suggestions and all ten demo-guide links exercised; public revenue negative control refused as expected |
| Browser console has no red errors | Pass | Zero console errors and zero uncaught page exceptions |
| CORS does not block API calls | Pass | 139 observed same-origin API requests, zero failed requests; browser web security enabled |

Additional checks: Enter-to-submit; a 390 × 844 mobile viewport for switching, chat, and graph; actual public source hyperlinks in source dialogs.

## Reproduce

See [`tests/browser/README.md`](../tests/browser/README.md). The test is `tests/browser/checklist.cjs`; it produces a JSON result and screenshots under ignored `.runtime/browser-results/`.

The Python regression suite also passed: **55 passed, 1 skipped**. The skipped test requires a real FalkorDB service. One dependency deprecation warning is emitted by the FastAPI/Starlette test-client stack; it is not a browser-console error.

## Boundaries

These results apply to the local app and demo-storage backend, not to an untested Railway URL, the external Arena proxy, other browser engines, production security, or native FalkorDB database operations. CORS is unnecessary for this app's relative same-origin API URLs; this check does not claim that arbitrary third-party origins are allowed. No production CORS policy was relaxed.

## Later native-backend verification

During video preparation on the same date, the app was also tested against an actual local FalkorDB 4.16.3 instance. The full Python run passed all 56 tests, and all 22 browser checks passed at port 8001. See [native recording validation](native-recording-validation.md) for the environment, fixes, and limitations. This later run does not retroactively change the demo-storage scope of the original checklist above.
