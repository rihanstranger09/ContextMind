# Proposed Company Brain narration + captions (v4 draft)

**Draft only — not yet recorded, timed, or rendered.** Target approximately **2:00**, subject to a fresh take and measured voice-clip durations. Each quoted line below is both the proposed spoken line **and its exact subtitle text**; break longer lines into two sequential subtitle cues without changing the words. Do not label this the current video. Record on a fresh, disposable native FalkorDB graph; the public workspace remains a separate bounded GitHub snapshot.

| Target | Picture / action | Proposed voiceover = on-screen caption |
|---|---|---|
| 0:00–0:06 | NovaPay dashboard; local native backend visible. | “ContextMind connects scattered company evidence to answers you can inspect.” |
| 0:06–0:14 | Open node-and-edge graph-model diagram. | “NovaPay is fictional. People, systems, tickets, and decisions are typed nodes and relationships.” |
| 0:14–0:26 | Open native decision-provenance proof. **Show all four BASED_ON records, one per row**, and the readable parameterized Cypher query. | “This fixed Cypher query runs on local FalkorDB. Four sources support the migration-delay record and its impacted project.” |
| 0:26–0:39 | Ask “Why was Analytics Migration delayed?” Expand **Tools used**, then one evidence path and a source card. | “A deterministic router matches the question, selects a bounded decision tool, and records each call, source, and graph path.” |
| 0:39–0:45 | Ask “Who owns Database Cluster?” Hold on the ownership answer. **No idle availability caption.** | “Platform Engineering owns the cluster in this graph. That is not a live on-call roster.” |
| 0:45–1:04 | Ask **“What breaks if the Database Cluster goes down?”** Open the impact tool and the `Payments v2 Launch` Path. Give the two-hop path enough screen space to read. | “What breaks if the cluster goes down? The impact tool follows dependencies. Payments v2 Launch reaches Database Cluster through API Gateway. Open Path to inspect both edges.” |
| 1:04–1:14 | Ask shortest path from Alice Johnson to Database Cluster; show ordered drawing and recorded tool steps. | “A bounded shortest-path search connects Alice through the gateway. Its tool call and evidence path are saved.” |
| 1:14–1:21 | Reload and open a saved investigation. | “After reload, the investigation, selected tools, and evidence trace remain in FalkorDB.” |
| 1:21–1:24 | Ask project blockers; no recording-only ticket yet. | “First, VID-42 is absent.” |
| 1:24–1:27 | A small truthful **“Operator API: add fictional VID-42 ✓”** overlay *after* an HTTP 200 ingest response; never show URL credentials, Authorization header, or token. | “An authorized operator adds a fictional blocker.” |
| 1:27–1:31 | Re-ask; show the **OPEN** VID-42 result. | “Re-asking reads the changed graph: VID-42 is open.” |
| 1:31–1:34 | **“Operator API: resolve VID-42 ✓”** overlay after HTTP 200. | “The operator resolves that ticket.” |
| 1:34–1:37 | Re-ask; VID-42 no longer appears among **active** blockers. | “Resolved: no longer an active blocker.” |
| 1:37–1:45 | Switch to separate public workspace; open native org → Python client → releases Cypher proof. **Remove the second public contributor question** from this cut. | “The same engine, now on a bounded public GitHub snapshot. Another native Cypher query reaches releases.” |
| 1:45–1:53 | Return to the tool trace / architecture card, not an idle screen. | “No LLM is wired in. A future model could phrase cited facts, but tool access stays bounded.” |
| 1:53–2:00 | Closing card, shortened from ~12 to ~7 seconds. Card text: **“Two native Cypher proofs + bounded graph-algorithm tools”**; show full repo URL, local setup, Company Brain track, and “Cloud deployment not verified.” | “ContextMind, Company Brain. See the repository for the model, queries, code, and local setup.” |

## Cut and claim notes

- The **impact** question replaces the *second* public-data question. On the seeded fictional graph it invokes `resolve_entity`, `analyze_system_impact`, and `get_evidence_sources`: Payments v2 Launch → `USES` → API Gateway → `DEPENDS_ON` → Database Cluster. This is a recorded multi-hop path, not an inferred production outage prediction. The impact result includes other direct and indirect paths; choose and open this one on screen.
- Keep the shortest-path shot as an **application-side BFS over FalkorDB-backed adjacency**, with four-hop and 70-node limits. It is **not** a native FalkorDB algorithm-library invocation. The router is deterministic pattern/keyword matching, **not** an LLM selecting tools or planning autonomously. The LLM sentence describes a *possible future integration*, not code that exists.
- The proposed freshness block occupies **16 seconds (1:21–1:37)** rather than the current roughly **25 seconds**. Replace long holds on similar screens with the two verified operator-action overlays and quick before/open/resolved answer shots. If the insert or resolution request fails, **stop recording**; never show a success overlay for a failed write. The dashboard does not currently expose an operator write button.
- Remove the old availability subtitle at 0:57–1:02; do not transplant it onto an idle ownership screen. The ownership line above is about the **visible ownership answer**, not a human availability demonstration.
- For one-source-per-row proof results, style the four evidence items as a vertical list rather than a wrapping flex row. That is a suggested production change, **not** already implemented by this draft.
- Re-time from the **new measured recording timeline**, leave short gaps only where the image changes, and check spoken words against final captions by listening. This document is a script, **not** a claim that the existing video or voice clips match it.
- Do not claim rule-8 eligibility from a new cut: the core repository predates the event; verify eligibility directly with organizers. The draft does not establish a hosted deployment. Put the clickable repo URL in any eventual video description and submission form as well as on the card.
