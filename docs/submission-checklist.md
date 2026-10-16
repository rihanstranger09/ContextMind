# Company Brain submission checklist (verify before submitting)

**This is not an official scorecard or a claim of prize eligibility.** The Graph Hacks submission form/rules control. The repository contains an earlier prototype and native recording documented on **2026-10-12**, before the October 15–18, 2026 event. A new video or commits made during the event do **not** make that earlier core implementation new. Ask organizers whether this entry is eligible before describing it as qualifying work; preserve the real Git history. Do not alter dates or claim that all core coding began during the event.

- [x] Public repository with runnable app and MIT license: `rihanstranger09/ContextMind`.
- [x] README with install/run instructions, [data model and Cypher/algorithms](graph-model-and-queries.md), provenance and limitations.
- [x] Native FalkorDB usage verified locally, with fixed Cypher proofs and a download link to a recorded demonstration. **Not** verified against a hosted cloud endpoint.
- [x] Company Brain track stated here and in README. Choose **Company Brain** in the submission form; do not claim a track was submitted automatically.
- [ ] Live public URL: not provisioned or verified. Local setup is complete below; only add a URL after testing it. No localhost URL is a public deployment.
- [ ] Confirm eligibility, submission deadline, any required licenses, video length, links and disclosures with organizers.
- [ ] Personally review the demo, source code, query syntax and architecture; be ready to explain them.
- [ ] Submit the form and video manually. Nothing in this repository submits an entry.

## AI assistant disclosure (adapt to the actual form)

“AI coding assistants in Arena.ai Agent Mode helped implement and test this prototype, write documentation, and produce an AI-narrated demonstration. Human maintainers reviewed the resulting code, data-scope limitations and claims.” **Only use the last sentence after actually reviewing it.** The app itself does not call an LLM: a deterministic intent router invokes graph tools and records its tool steps. Do not describe tool routing as autonomous planning, autonomous actions, or an external MCP agent. See `agents/company_brain.py`, `graph/tools.py`, and `graph/store.py` for the implementation.

## Complete local setup (real native backend)

```sh
# Docker + Compose required. Local-only demo with fictional NovaPay and public GitHub snapshot.
docker compose up --build
# Then in another terminal:
curl http://localhost:8000/api/health
curl 'http://localhost:8000/api/health?workspace=falkordb'
curl 'http://localhost:8000/api/graph/showcase?workspace=falkordb'
curl 'http://localhost:8000/api/graph/company-proof?workspace=novapay'
```

Open `http://localhost:8000/dashboard?workspace=novapay` and `.../dashboard?workspace=falkordb`. In both health checks `graph_mode` must say `falkordb`; both proof responses must set `native_cypher_executed: true`. The local Compose service is not a public deployment. Use a disposable graph prefix, not sensitive company data. The app has no login/tenant ACLs and is not production-ready.

## Honest on-camera sequence

1. Start on the **NovaPay fictional workspace**: ask “Why was Analytics Migration delayed?” Show the decision's ticket, chat, meeting and document evidence; expand **Tools used** and **Why this answer?**.
2. Click **DECISION CYPHER** to show a second fixed native Cypher query (`BASED_ON` + `IMPACTS`). This is a fictional organizational decision, not a public FalkorDB decision.
3. Ask “Who owns Database Cluster?” or “Who knows the most about Payment Service?” The responder score is an explanatory heuristic, not proof of current availability. Reload: saved investigations persist in the graph and remain inspectable in Recent Investigations.
4. Use a **token-protected operator ingest** to add/update a fictional blocker; re-ask the same question. The old answer remains saved, while the new answer sees changed graph data. Never show the token. The watcher for public GitHub is opt-in full refresh, not an automatically running live feed.
5. Switch to the **FalkorDB public GitHub workspace**. Its Decisions tab is hidden because the bounded snapshot has no hand-verified decisions. Click **FALKORDB PROOF** to show the other native Cypher traversal and a real public release source. Ask “Who maintains the Python client?”; read the bounded contributor evidence and limitations. Do not promote contributions to maintainer assignments.
6. Close with the downloadable MP4, repository/PR link and **Company Brain** track name. If there is no verified public deployment, say “local native demo; full setup in README,” not “live cloud deployment.”

See [presenter runbook](presenter-runbook.md) for the recording pipeline. Uploaded video must faithfully depict the running backend, label NovaPay fictional, and must not claim a cloud test that did not happen.
