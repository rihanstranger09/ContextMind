# Real-browser testing checklist

These tests use Playwright to click/type/navigate in headless Chromium against the **real running API**, without mocked API responses or disabling browser web security. They cover both workspaces, the sidebar workspace links, header selector, chat, Send and Enter submission, SVG graph, source dialogs, expanded/path traces, every dashboard suggestion, all ten demo-guide links, and a mobile-size viewport. The public revenue question is expected to return insufficient context.

## Run

Requires Node.js 22.17+ and Python app dependencies. On Linux, the pinned Chromium package contains the browser binary, so a separate browser download is not required.

```sh
# Terminal 1 (repository root; fictional/public snapshot data only)
GRAPH_BACKEND=demo .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2
npm ci --prefix tests/browser
npm test --prefix tests/browser
```

On a minimal Linux image without NSS/NSPR libraries, opt into the packaged libraries:

```sh
CHROMIUM_BUNDLED_LIBS=1 npm test --prefix tests/browser
```

To use an installed compatible Chromium binary or a different app URL:

```sh
BROWSER_EXECUTABLE=/path/to/chromium BASE_URL=http://127.0.0.1:8000 npm test --prefix tests/browser
```

The default tested origin is `http://127.0.0.1:8000`. All browser API requests must stay on that page origin. `BASE_URL` allows testing another accessible deployment, but **the suite submits questions**, which persist NovaPay answer traces; do not run against sensitive production data. The browser uses `--no-sandbox` for container compatibility and must only visit a trusted test application. CORS/web security remains enabled.

Reports and desktop/mobile screenshots go to ignored `.runtime/browser-results/`. The process exits nonzero on any failed assertion, HTTP error, network failure, uncaught page exception, or red browser-console message. A failed run may stop before later checklist items. This is not a visual-regression, accessibility, native-FalkorDB, or cross-browser test suite.
