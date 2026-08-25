# Security & Hygiene Audit — feature/bilingual-zho-resolution

Read-only audit. Repo: /Users/shaz/MOI-Arabic-Sign-Language, date 2026-08-25.

## 1. Test run

`uv run pytest tests/ -q` → **77 passed** in 4.61s, no failures, no skips reported. Ran in well under the 120s budget.

## 2. Stack audit

**Frontend** — `/Users/shaz/MOI-Arabic-Sign-Language/webapp/frontend/package.json`:
- React 19.2.8 + react-dom 19.2.8, react-router-dom 7.18.2
- Build tooling: Vite 8.2.0, TypeScript ~6.0.2, oxlint (lint), @vitejs/plugin-react
- No state-management/UI-kit deps beyond React itself.

**Backend / Python** — `/Users/shaz/MOI-Arabic-Sign-Language/pyproject.toml`:
- `requires-python = "==3.11.*"` (no separate `.python-version` file found)
- Core deps: `requests` (talks to local Ollama HTTP server), `mediapipe==0.10.14` (pinned — newer 1.0.1 crashes natively per comment), `opencv-python`, `numpy`, `Pillow`, `arabic-reshaper`, `python-bidi`
- Optional `[benchmark]`: scikit-learn, rouge-score, nltk
- Optional `[webapp]`: fastapi, uvicorn, python-multipart
- Optional `[vocab-embedding-experiment]`: sentence-transformers (pulls in torch; explicitly NOT used by default — default retrieval is lexical/token-overlap in `lib/vocab_retrieval.py`)
- Dev group: pytest>=9.1.1
- External non-pip deps noted in comments: Ollama (local, model `hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`), ffmpeg, uv itself.
- pyproject.toml explicitly states: "No API keys/secrets are required by run_pipeline.py or anything under lib/ (all inference is local)."

## 3. Security / secrets audit

**Secret-shaped grep hits** — none are real credentials. All hits are either:
- Documentation describing that no secrets exist / how `.env` (hf_token) is handled (README.md:156,199; CHECKPOINT.md:27; REPO_TECHNICAL_AUDIT.md:77,142,357,365-366,477,531)
- Code identifiers containing "token" in the NLP sense (tokenize/tokens — `lib/vocab_retrieval.py`, `lib/sign_resolver.py`, `lib/sign_plan.py`, `lib/episode_builder.py`, `benchmarks/llm_grounding/*.py`, `tests/test_sign_plan_arabic_hints.py`, `tests/test_resolver_regressions.py`) — not credentials.
- `brand/README.md:37` — "Token" as in design-system color token, unrelated.
- `webapp/backend/app/main.py:7` — comment asserting `.env`/secrets are never returned by any endpoint.

No `sk-`, `Bearer `, `OPENAI`, or `ANTHROPIC_API_KEY` string literals found anywhere. **No actual secret values found in tracked files.**

Note: search results also picked up a stale `.claude/worktrees/agent-a3731017e37e9bf81/` copy of the repo containing the same docs — same conclusion applies, not a separate finding.

**Committed .env file**: `git ls-files | grep -i env` → **no output**. No `.env` is tracked by git. `.gitignore` explicitly excludes `.env` (see §4). Docs (README/CHECKPOINT/REPO_TECHNICAL_AUDIT) describe an untracked local `.env` holding one Hugging Face token (`hf_token`), stated as unrelated to and unused by this repo's own scripts.

**Outbound network calls**:
- `lib/vocab_embedding.py:42` — `requests.post(OLLAMA_EMBED_URL, ...)` → **local inference** (local Ollama server)
- `lib/episode_builder.py:134` — `requests.post(...)` → local Ollama call (STRUCTURE stage), **local inference**
- `lib/understand.py:52` — `requests.post(...)` → local Ollama call (UNDERSTAND stage), **local inference**
- `webapp/frontend/src/api.ts` — multiple `fetch(...)` calls to `/api/...` relative paths → **local dev server** (backend FastAPI running alongside the Vite frontend), not external.
- Not exercised by this grep but documented in README.md:156 and coverage_report.md: `scripts/zho_download.py` / `lib/clip_prep.py` (ESL Zayed via yt-dlp) make **external network calls** to the public ZHO government dictionary site / Vimeo CDN and to source video hosts for ESL Zayed clips — these are one-time data-acquisition scripts, not part of the core AI inference path, and are documented as such.

**Verdict**: core AI inference (UNDERSTAND/STRUCTURE/embedding) is local-only (Ollama over HTTP to localhost). The only external network calls are one-time content-acquisition scripts (ZHO dictionary download, ESL Zayed clip download), not part of the runtime inference path.

**Absolute `/Users/shaz/` paths committed in tracked files** (`git grep -n "/Users/shaz"`):
- `REPO_TECHNICAL_AUDIT.md:3` — `Repo: \`/Users/shaz/MOI-Arabic-Sign-Language\` — ...`
- `REPO_TECHNICAL_AUDIT.md:40` — directory tree listing starting with `/Users/shaz/MOI-Arabic-Sign-Language/`
- `scripts/test/vrm-poc/extract_landmarks.py:19` — `ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"`
- `scripts/zho_download.py:17` — `ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"`
- `scripts/zho_index.py:100` — `out_path = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/catalog.json"`

(Also present, but inside a nested worktree copy at `.claude/worktrees/agent-a3731017e37e9bf81/REPO_TECHNICAL_AUDIT.md` — same underlying findings, not a distinct file to fix separately if that worktree is discarded.)

**These 3 scripts (`extract_landmarks.py`, `zho_download.py`, `zho_index.py`) and 2 docs (`REPO_TECHNICAL_AUDIT.md`) hard-code the author's absolute local path and should be flagged for parameterization/removal before external submission** — not fixed here per audit scope.

## 4. Repo hygiene

`.gitignore` (`/Users/shaz/MOI-Arabic-Sign-Language/.gitignore`) — covers:
```
.env
.venv/, .venv_live2d/, __pycache__/, *.pyc
.DS_Store
node_modules/, scripts/test/vrm-poc/output/
*.task, yolo11n-pose.pt
data/zho/clips/
data/zho/thumbs/
data/zho/spike_mediapipe/*.mp4
data/zho/spike_mediapipe/trimmed/
data/zho/spike_mediapipe/lesson/*  (with explicit un-ignore for lesson_captioned_xfade.mp4)
data/zho/spike_mediapipe/rigged/, sentence/, paragraph/, normalized/
data/zho/spike_mediapipe/avatar_parts/*.png|*.jpeg
scratch/*.html
outputs/*/  (with !outputs/.gitkeep)
webapp/outputs/
data/zho/spike_mediapipe/norm_cache/
data/zho/spike_mediapipe/trim_cache.json   <-- NOTE: this file is currently modified (M) per git status, meaning it IS tracked despite being gitignored (was added before the ignore rule, or force-added)
data/zho/catalog_embeddings.json, catalog_embeddings_*.npz
data/zho/spike_mediapipe/esl_zayed_caption_pilot_v2_20260823/{videos,frames,ocr_frames,scale_frames,__pycache__}/
data/zho/spike_mediapipe/esl_zayed_raw/  (raw yt-dlp downloads, explicitly commented "never committed — licensing + repo-size")
```
Note: `data/zho/spike_mediapipe/esl_zayed_clips/` itself (the trimmed per-word segments) is **NOT** in `.gitignore` — it is meant to be committed as "provenance evidence" per the comment above `esl_zayed_raw/`. This explains why the 23 untracked `.mp4`s under `esl_zayed_clips/` show as untracked-but-not-ignored in `git status` rather than being filtered out.

**Disk usage** (`du -sh`):
- `data/zho/clips` — 37M
- `data/zho/spike_mediapipe` — 159M
- `outputs/` — 685M

**Tracked count** (`git ls-files data/zho/clips outputs/ | wc -l`) → **0**. Neither `data/zho/clips` nor `outputs/` has any files tracked by git — all of that disk usage is untracked/gitignored local working-tree bulk, not part of the committed repo.

**Top tracked files by size** (`git ls-files -s` → `du -k`, top entries, in KB):
```
10524  scripts/test/vrm-poc/assets/VRM1_Constraint_Twist_Sample.vrm
 2220  data/zho/spike_mediapipe/lesson/lesson_captioned_xfade.mp4
 1320  scripts/test/trying-avatarIwant/emirati_avatar_mesh_master.svg
  992  scripts/test/trying-avatarIwant/avatar_clean_reference.png
  908  data/zho/catalog.json
  776  data/zho/spike_mediapipe/esl_zayed_clips/ESL_ZAYED_0016_sleepy.mp4
  640  data/zho/spike_mediapipe/esl_zayed_clips/final_mixed_zho_esl_zayed_proof_20260823.mp4
  604  scripts/test/trying-avatarIwant/avatar_retarget_out.mp4
  604  data/zho/spike_mediapipe/ab_experiment_20260823/case_cells_20260823.json
  592  scripts/test/vrm-poc/assets/alif_landmarks.json
  544  benchmarks/alyah/results/alyah_checkpoint.jsonl
  256  scripts/test/trying-avatarIwant/frame55.png
  236  scripts/test/trying-avatarIwant/frame5.png
  216  data/zho/spike_mediapipe/ab_experiment_20260823/case_arabic_family_school_20260823.json
  208  data/zho/spike_mediapipe/esl_zayed_full_93video_corpus_20260823.json
```
Largest tracked artifact is a ~10.3MB VRM avatar sample asset (`scripts/test/vrm-poc/assets/VRM1_Constraint_Twist_Sample.vrm`), followed by two already-committed `.mp4`s (a baseline lesson video, ~2.2MB, and an ESL Zayed clip + proof video already tracked under `esl_zayed_clips/`, ~776KB/~640KB). None of these are runaway/unbounded — nothing in the tens-of-MB+ range is currently tracked.

**Untracked ESL Zayed clips** (23 `.mp4` files under `data/zho/spike_mediapipe/esl_zayed_clips/` per `git status`): `.gitignore` has **no rule** matching `esl_zayed_clips/` itself, so these would NOT be excluded if `git add`-ed — they would need to be either (a) intentionally added as provenance evidence (matching the two already-tracked files in that same folder), or (b) explicitly gitignored, per submission policy that raw ESL Zayed source clips should not ship in the final package. As-is they are simply untracked working-tree files; no accidental-commit risk exists unless someone runs a broad `git add -A`.

## 5. Data source / quality story

**`data/zho/coverage_report.md`** — key figures:
- Full ZHO dictionary indexed: **1,143 entries across 21 categories**.
- Episode 1 term coverage: **1/24 direct match (4%)** — 23/24 terms have zero direct ZHO coverage and route through fingerspelling, matching the brief's own prediction that ZHO is general-vocabulary, not science-domain.
- Signer identity finding: 3 distinct signers found by visual inspection — Signer A (female, Alphabets only, 35 entries/3.1%), Signer B (male, 19/21 categories, 1,062 entries/92.9% — the de facto primary presenter), Signer C (male, Sports only, 46 entries/4.0%).
- Recommendation: use Signer A only (full fingerspelling, including "inside" despite a direct Signer-B match) to satisfy a "presenter never visibly changes" consistency rule.
- One technical blocker found and routed around: per-word detail pages blocked by an edge WAF rule; a documented JSON search-API workaround was used for 100% of indexing/download instead.
- Usage rights note (§8): "usage terms should be formally verified with ZHO before any deployment beyond this prototype/demo context."

**`data/zho/catalog_validation_report.json`** — key figures:
- `total_rows: 1143`, `en_records: 1143`, `ar_records: 1137`, `bilingual_joins_both_labels: 1137`, `en_only: 6`, `missing_ar_labels: 6`, `missing_video_asset: 0`, `missing_thumbnail: 0`.
- No duplicate stable IDs (healthy) and no rows missing video assets.
- 6 entries have no official ZHO Arabic label — "preserved as missing, per instruction, rather than machine-translated or fabricated."
- Extensive `duplicate_english_labels` list (source-data duplicates, e.g. "naphew": 2, "cap": 3, "citizenship paper": 3, plus many numeral labels appearing twice) and `duplicate_arabic_labels_ambiguous_join` (e.g. Mother/Father/Sister all share Arabic title "باب الأسرة"; "Second Wife"/"Second Wife-"; various numeral pairs) — explicitly documented as **source data anomalies from ZHO itself**, not introduced or hidden by the pipeline's join logic. Report states the resolver still resolves each entry correctly by stable id + video, but an exact-Arabic-text lookup alone would be genuinely ambiguous — a disclosed limitation, not silently guessed around.

**ESL Zayed clip count cross-reference**:
- `ls data/zho/spike_mediapipe/esl_zayed_clips | wc -l` → **23** (matches the untracked-file count noted in git status; consistent with 2 of those being already-tracked provenance files plus this directory listing count reflecting current disk state at the time of this audit — the git-status "23 untracked" figure and this directory-listing figure agree).
- `data/zho/esl_zayed_supplementary_catalog.json` → **244 entries** (each with a `supplementary_id` like `ESL_ZAYED_0001` and `verification_status: "SUPPLEMENTARY_UNVERIFIED"` on every entry checked).

**Provenance/licensing reasoning found**:
- `.gitignore` comments (see §4) state ESL Zayed raw videos/frames are "never committed (licensing + repo-size)" and that only the small trimmed per-word segments under `esl_zayed_clips/` are committed "as provenance evidence."
- Every entry in `esl_zayed_supplementary_catalog.json` is explicitly tagged `verification_status: "SUPPLEMENTARY_UNVERIFIED"` — i.e., the catalog itself encodes that this source is supplementary/unverified rather than institutional-grade, consistent with ZHO being the primary, officially-sourced (government) dictionary and ESL Zayed being an auxiliary, not-yet-verified source layered on top.
- No standalone licensing/provenance narrative doc was found beyond these inline markers (no dedicated `docs/*.md` on ESL Zayed provenance turned up by the grep); the reasoning lives in the `.gitignore` comments and the catalog's own `verification_status` field.
