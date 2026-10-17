# Company Brain v4 recording runbook (draft assets, not a released video)

Track: **Company Brain**. This storyboard is for a **local native FalkorDB** capture. The existing MP4 in `presentation/` is an earlier v3 fallback; never label a JSON rehearsal or silent draft as the finished native v4 video. The script and caption text are [verbatim](../docs/company-brain-v4-script.md). The public workspace is a bounded GitHub snapshot; NovaPay is fictional. The app has a deterministic router, **no LLM**, and application-side BFS over stored adjacency.

## Clean, isolated native setup

Prerequisites: Docker Engine/Desktop with Compose, Python 3.11+, Node.js 22+, ffmpeg and ffprobe. Follow [README local setup](../README.md#falkordb-deployment-local-not-public-hosting) first. Docker maps the database **only to host loopback** on port 6380 for disposable local seeding; the app stays on port 8000. Nothing here provisions a public URL.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm ci --prefix tests/browser
docker compose up --build -d
# In the local shell only, generate a private operator credential; never print it.
export INGEST_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')"
# Seed a fresh, random, isolated native graph prefix. Do not reuse an existing name.
GRAPH_BACKEND=falkordb FALKOR_HOST=127.0.0.1 FALKOR_PORT=6380 python scripts/seed_demo_graph.py
set -a; . .runtime/recording-graph.env; set +a
# Recreate the app so it reads the new graph prefix and the private operator variable.
docker compose up -d --force-recreate app
# Both endpoints must say graph_mode=falkordb; both proofs must say native_cypher_executed=true.
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS 'http://127.0.0.1:8000/api/health?workspace=falkordb'
```

**Caution:** `docker compose up` before exporting the operator variable starts with writes disabled, as intended. After export, Compose passes the private environment value to the app; never print Compose config or include its environment in screenshots/logs. The graph seed file contains a generated graph *name only*, not a credential. A previous graph must never be overwritten. A new graph prefix is required for each rehearsal/check and final take: the checker and recorder both write a fictional ticket. Do not point them at a production service.

## Preflight and exact click path

Run the guarded browser state checker on a *separate disposable graph* before filming. It requires `VIDEO_INGEST_TOKEN` in the process environment and refuses JSON mode by default. Its output is an ignored sanitized summary; a failed request must stop the take. Then seed another fresh graph for the actual recording.

```sh
export VIDEO_INGEST_TOKEN="$INGEST_TOKEN"
BASE_URL=http://127.0.0.1:8000 CHROMIUM_BUNDLED_LIBS=1 node scripts/check_video_states.cjs
# Create a NEW graph using the setup/seed sequence above, then:
BASE_URL=http://127.0.0.1:8000 CHROMIUM_BUNDLED_LIBS=1 \
  PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/ms-playwright" node scripts/record_v4.cjs
```

If Playwright's video encoder is missing, install it by running `tests/browser/node_modules/.bin/playwright install ffmpeg`. Never display a terminal with request headers, shell history, environment values or the private operator credential. The recorder uses Playwright's API request context in memory, never a visible command. It injects into the **opt-in** dashboard panel only after each successful API response, passing only its status and response object; the panel itself strictly allowlists ticket ID, OPEN/RESOLVED status, timestamp and graph counts. In all other dashboard URLs it does not exist. No raw response, request headers or credential enter the page.

| Target time | Exact on-screen action |
|---|---|
| 0:00–0:06 | Open `/dashboard?workspace=novapay&demo_evidence=1`. Confirm native backend and **NovaPay · Fictional company dataset**. |
| 0:06–0:14 | Click **GRAPH MODEL**; show nodes/relationships. |
| 0:14–0:26 | Close model; click **DECISION CYPHER**; verify native-executed badge and **four separate BASED_ON rows**. |
| 0:26–0:39 | Close proof; ask **Why was Analytics Migration delayed?** Expand **Tools used** and **Why this answer?**; inspect source/path. |
| 0:39–0:45 | Ask **Who owns Database Cluster?** Hold on recorded team/lead answer, not an on-call claim. |
| 0:45–1:04 | Ask **What breaks if the Database Cluster goes down?** Click the `Payments v2 Launch` path. Show `USES` → API Gateway → `DEPENDS_ON` → Database Cluster in the path dialog. |
| 1:04–1:14 | Close path; ask **What is the shortest path from Alice Johnson to Database Cluster?** Show ordered path drawing and **Tools used**. |
| 1:14–1:21 | Reload; open first **Recent investigations** row and verify saved tool/evidence trace. |
| 1:21–1:24 | Close history; ask **What tickets block Analytics Migration?**; verify VID-42 absent. |
| 1:24–1:27 | API inserts fictional VID-42; **only on HTTP 2xx** display server response-derived receipt beside dashboard (OPEN, ticket ID, timestamp, counts). |
| 1:27–1:31 | Ask same blockers question; verify VID-42 OPEN appears. |
| 1:31–1:34 | API resolves same ticket; **only on HTTP 2xx** display second response-derived receipt (RESOLVED, counts). |
| 1:34–1:37 | Re-ask blockers; verify VID-42 absent from *active* blockers. |
| 1:37–1:45 | Switch to **FalkorDB · public GitHub snapshot**; click **FALKORDB PROOF**. Confirm separate native org → Python client → releases traversal. |
| 1:45–1:53 | Open `/architecture.html`; diagram Question → deterministic router → bounded graph tools → FalkorDB → cited answer + saved trace. Optional LLM not connected. |
| 1:53–2:00 | Open `/present.html`; only track, short repo URL, local README setup, unverified deployment note. |

The recording script writes `deliverables/native-company-v4.webm` and its *measured* timeline only when all native checks pass. `RECORD_ALLOW_DEMO=1` is a **JSON rehearsal only** and writes to ignored `.runtime/company-v4/demo-rehearsal-v4.webm`, not the native output. A success screenshot from a failed request is forbidden. Review key frames and narration pacing after every take.

## Narration, captions and export

The [draft SRT](../presentation/ContextMind-v4-draft.srt) is generated **verbatim** from the sixteen quoted script lines. It is not synchronized to recorded speech yet. Generate it with `python scripts/generate_v4_captions.py`; use `--timings .runtime/v4-measured-cues.json` to supply reviewed per-cue `[start,end]` seconds after listening to the final same-voice narration. Keep every word identical to the voiceover. Supply a continuous, reviewed `deliverables/v4-voiceover.wav` (AI narration is disclosed). No video is considered complete if this audio is missing.

For a real, verified native take only (using installed ffmpeg):

```sh
ffmpeg -y -i deliverables/native-company-v4.webm -i deliverables/v4-voiceover.wav \
  -vf "subtitles=presentation/ContextMind-v4-draft.srt:force_style='FontName=DejaVu Sans,FontSize=19,PrimaryColour=&H00FFFFFF,BackColour=&H90000000,BorderStyle=3,Alignment=2,MarginV=16'" \
  -map 0:v:0 -map 1:a:0 -t 120 -c:v libx264 -preset medium \
  -b:v 2500k -minrate 2200k -maxrate 3000k -bufsize 5000k -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart deliverables/ContextMind-v4-candidate.mp4
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,width,height,bit_rate \
  -of json deliverables/ContextMind-v4-candidate.mp4
ffmpeg -hide_banner -i deliverables/ContextMind-v4-candidate.mp4 \
  -vf 'blackdetect=d=0.04:pix_th=0.10' -an -f null - 2>&1 | grep black_start
```

**Release gate:** confirm 1440×900 or 1920×1080, H.264 video rate ≥2 Mbps, AAC stream, duration ≤130 s, no black frames at either end, no credential-bearing frame, accurate subtitle/audio correspondence and all checks in the script. `ffprobe` output must show a real audio stream; silent generated audio is not acceptable. Only then copy the candidate into `presentation/` and link that specific file. Do not replace the existing v3 fallback with an unverified v4 cut.

## Clickable description / submission link

ContextMind · Company Brain. Fictional NovaPay on local native FalkorDB, plus a bounded public GitHub snapshot. Deterministic router; no LLM; app-side graph traversals over FalkorDB-backed adjacency. **Repository and complete local setup:** https://github.com/rihanstranger09/ContextMind . Cloud deployment not verified. Confirm event eligibility and author review before submitting.
