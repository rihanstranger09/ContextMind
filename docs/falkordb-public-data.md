# FalkorDB public brain: shipped scope and evidence contract

ContextMind now has two **separate** workspaces:

- **NovaPay**: fictional sandbox and original ownership/impact/decision demo.
- **FalkorDB**: a real, bounded public GitHub snapshot, with real URLs. It is **not** private company knowledge or a continuously live feed.

The workspace selector is visible in the dashboard header. Open `/dashboard?workspace=falkordb` or the public walkthrough at `/demo.html?workspace=falkordb`. Storage mode is independent: either workspace can use JSON demo storage or the actual FalkorDB database adapter. In database mode, the public graph is `${FALKOR_GRAPH}_public_falkordb`; NovaPay keeps `${FALKOR_GRAPH}`.

## What was collected

The checked-in `data/falkordb/snapshot.json` contains a timestamped capture of real GitHub REST responses, normalized to selected fields. It is **not** populated from the proposed sample records, version numbers, licensing rationale, or alleged maintainers in the integration plan.

| Collection | Snapshot scope |
|---|---|
| Public repository inventory | 149 repositories returned by the FalkorDB org public repository API; forks explicitly labeled |
| Detailed repositories | Core FalkorDB, falkordb-py, node-falkordb, JFalkorDB, falkordb-go, GraphRAG-SDK, langchain-falkordb, FalkorDB-MCPServer, QueryWeaver, docs |
| Documents | 11 README/CODEOWNERS records; 18 documentation source files from `FalkorDB/docs` |
| Releases | 36 published Version records; at most five per detailed repository |
| Issues / PRs | 91 Ticket records; at most ten recently updated in the last 730 days per detailed repository |
| Contributors | 19 unique public users from at most five contributors per detailed repository; only public login/profile URL and per-repository activity counts |
| Documentation topics | Six Integration nodes plus a Cypher Skill, explicitly marked as derived/inferred classification |
| Total | 332 nodes, 378 edges |

Counts describe this committed snapshot, not the current size of the organization. `/api/coverage?workspace=falkordb` exposes the shipped manifest and runtime organization collection time. Each source card carries its own timestamp, URL, collection method, source system, hash, and inference label. Code/document URLs are pinned to the observed default-branch commit. Issues, contributor pages, and repository URLs are live pages; the stored values describe the capture time, not guaranteed current values.

## What is **not** collected or implemented

- No direct website crawl, robots.txt/sitemap crawler, partner-site crawl, or docs website watcher. Documentation came from the **public GitHub docs repository**, not scraped pages. This environment only permits selected network hosts.
- No YouTube, GitHub Discussions, Discord, X, Reddit, or LinkedIn collection. GitHub Discussions would require GraphQL, not the proposed REST endpoint.
- No private org/team data, private repos, DMs, email fields, commit email addresses, or internal roadmap/financial data. Email-like text in selected public bodies is redacted.
- No hand-verified Decision, BreakingChange, Benchmark, competitor-comparison or version-compatibility records. The schema accepts these types, but source text is **not** automatically promoted to such facts. Merely saying “breaking” in release notes is not sufficient extraction.
- No automatic person-level maintainer assignment. CODEOWNERS may contain path-specific rules; those are preserved as documents, not generalized to repository-wide responsibility. An issue reporter is not assigned as the issue's assignee.
- No LLM synthesis, vector search, automatic contribution-quality assessment, personal performance ranking, or availability claims.
- No outbound maintainer message was posted. [`maintainer-outreach.md`](maintainer-outreach.md) is a draft, not consent. No community bot has been authorized.
- No demo video/blog publication or external deployment has been created by this integration.

Absence means **not present in the collected snapshot**, not “data not public.” The application intentionally does not assert that financial details or other uncollected facts cannot be found elsewhere.

## Provenance and graph behavior

Public nodes and edges contain `source_url`, `source_system`, `method`, `collected_at`, `content_hash`, `visibility`, and `inferred`. Hashes are SHA-256 over canonical JSON of the stored record excluding `content_hash` and `collected_at`. They are checked before replay. They verify snapshot integrity, **not external truth**. Metadata collection timestamps are not cryptographic evidence of source authenticity.

`Organization → OWNS → Repository` comes from the org's public repository inventory. `Person → CONTRIBUTES_TO → Repository` comes from the contributor API and includes the count scope. `Document/Guide → ABOUT → Repository`, `Repository → VERSION → Version`, and `Ticket → IN_REPO → Repository` connect actual artifacts. Documentation-topic classification adds `Guide → DOCUMENTS → Integration/Skill` with an explicit inferred reason; this does **not** claim partner endorsement or supported-version compatibility.

Every returned factual entry references at least one source ID and actual graph path. Excerpts remain attributed quotations, not tested instructions. Source text is escaped in the browser, never executed or treated as instructions. Publisher-authored comparisons are not independent measurements.

Public queries do not persist copied answer text or user questions, reducing personal-data duplication. NovaPay's original answer-trace persistence is unchanged. Public traces are returned to the client and can be inspected, but are not currently an audit-history store.

### Freshness

- Repository stale badge: `pushed_at` older than 90 days. A push is **not** a commit-frequency or support guarantee.
- Guide/document badge: captured repository commit date older than 180 days. This is explicitly labeled as a **repository commit**, not a verified file-modification date.
- Open ticket badge: `updated_at` older than 30 days; other artifact badges use 90 days.
- Source cards show capture time separately. The app does not infer “active maintainer” from any of these signals.

## Reproduce or refresh

Run from the repository root after installing `requirements.txt`.

```sh
# Optional collection: public GitHub only. Uses authenticated gh if installed,
# otherwise GITHUB_TOKEN from your environment. Never put credentials in chat or Git.
python -m connectors.collect --org falkordb --source github

# Offline replay: no collection credentials required.
# Defaults to JSON demo unless GRAPH_BACKEND=falkordb is exported.
python data/seed.py --org falkordb

# Start the dashboard after replay (JSON changes require restart).
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Collection follows public repo discovery rather than guessing repository names. It makes at most one API request per second, paginates repository inventory up to an explicit safety cap, bounds artifact collections, stops on HTTP/auth/rate-limit errors, and only atomically publishes a fully validated output file. It does not retry aggressively or silently publish partial results. Endpoint lists and sample limits are explicit in `connectors/github.py`. A full refresh uses roughly a hundred-plus API requests; monitor your rate allowance before enabling repeated collection.

```sh
# Opt-in refresh against an already configured FalkorDB backend:
GRAPH_BACKEND=falkordb python -m connectors.github_watcher --interval 900
# One refresh:
GRAPH_BACKEND=falkordb python -m connectors.github_watcher --once
```

This is a **bounded full-refresh loop**, not incremental commits/webhooks/ETag synchronization. It sleeps 900 seconds after finishing a pass. It is **not automatically running** with the web app or Docker Compose. Keep one collector/replay operator per graph. In database mode, new queries see updated graph reads; the browser refreshes on re-ask/reselect, not via push events. The JSON backend cannot safely live-share multiple writer processes, so the watcher refuses JSON mode.

Snapshot publication is atomic at the file level. Replay validates first and reconciles current snapshot nodes and edges, respecting Person suppression, but **multi-query FalkorDB replay is not transactional**. Pause public serving during replay if partial read visibility is unacceptable. A mid-replay DB outage requires rerunning the validated snapshot. Sources falling outside the bounded window disappear from the serving snapshot; that is not interpreted as upstream deletion.

## Person removal

Only an operator with `INGEST_TOKEN` can delete a Person. Both workspace and ID are explicit:

```sh
curl -X DELETE 'http://localhost:8000/api/people/PERSON_ID?workspace=falkordb' \
  -H "Authorization: Bearer $INGEST_TOKEN"
```

Use a real ID obtained from `/api/entities?workspace=falkordb&type=Person`, not the placeholder above. The operation deletes the Person node, its incident graph edges, and generated traces; it records a hash suppression tombstone so snapshot replay cannot restore that ID. Suppression persists in the JSON runtime file or in FalkorDB. Back up runtime suppression when migrating storage; deleting runtime data/volumes can otherwise discard suppression.

For the checked-in/exported snapshot, the operator can also run:

```sh
python -m connectors.forget PERSON_ID --snapshot data/falkordb/snapshot.json
```

This scrubs the Person entity and edges, and records suppression in that snapshot. Future collection **to the same output file** preserves it. A different output path is a separate data copy and needs the same removal review. Runtime tombstones still block reintroduction to that serving graph.

**This is not a complete legal erasure guarantee.** Review free-text mentions in documents/issues, other snapshot copies, caches, Git history, and upstream sources separately. The endpoint does not rewrite Git history or delete another platform's content. Do not promise a person that all references were erased merely because the entity endpoint succeeded.

## Evaluation and test scope

`data/falkordb/eval.jsonl` contains 25 offline regression questions: builders, contributors, operators, and six missing-evidence controls. `tests/test_eval_falkordb.py` verifies supported intents, source URL families, claim citation coverage, and that every trace edge exists in the stored graph. The set does not pretend to be an independent benchmark or expert assessment of all source claims.

```sh
pytest -q
# With an actual FalkorDB listening at configured host/port:
FALKOR_INTEGRATION=1 pytest -q tests/test_falkordb_integration.py
```

GitHub Actions defines offline and real-FalkorDB-service jobs. Local offline tests do not validate native Cypher execution; the integration test is skipped unless explicitly enabled. The <2-second answer target is a deployment performance goal, not a claimed native-database benchmark.

## Dataset attribution

The normalized snapshot contains public third-party excerpts and metadata with source URLs for attribution. Those materials retain their original copyrights and applicable repository/document licenses; the ContextMind MIT software license does not relicense third-party content. Preserve provenance and review upstream reuse requirements before redistributing beyond this demo.
