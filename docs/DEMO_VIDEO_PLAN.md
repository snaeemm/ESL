# Standalone Demo Video Plan

**Status: rebuilt 2026-08-26. `demo/MOE_Website_Walkthrough_Demo.mp4` is 79.2s, 1920x1080, h264, ~1.8MB.**

This replaces a prior build that had ballooned to 167s (2:47) and — the user confirmed — did NOT actually contain a real clip from the current prototype video. This rebuild starts over: every screenshot is a fresh real capture of the currently running app, and the "video plays" shot is a real `ffmpeg`-trimmed clip cut directly from `demo/MOE_Prototype_Lesson_Demo.mp4`, verified byte-for-byte (see "Video-plays shot verification" below). No prior walkthrough content was reused.

## Hero job used

Job `013fbd2aa3f0` ("My Family and My Day at School") — already registered at `outputs/webapp_jobs/013fbd2aa3f0/` from earlier work, no backfilling needed. Its `final_episode.mp4` was confirmed **identical** (md5 `b529fe0d4922e797c8d626b886f88cb0`) to `demo/MOE_Prototype_Lesson_Demo.mp4` before building anything, so the live webapp Results/Sign Plan/Traceability/Demo UI already served the correct, current, hand-jitter-fixed render — no file swap was needed this time.

Real numbers from this job's own `validation.json` / `stage_timings.json` (used verbatim in captions, nothing invented):
- `overall_status: PASS`
- 100% verified lexical sign coverage (22/22 sign units): 86.4% ZHO institutional + 13.6% ESL Zayed supplementary, 0% fingerspelling fallback, 0 unsupported units, 0 review-required
- Requested duration 60s, actual rendered duration 50.92s
- Local model: `hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`, served via Ollama

## How the video was actually built (this session)

1. **Live app check**: confirmed `localhost:5173` (frontend) and `localhost:8000` (backend) were already running — no restart needed.
2. **Real viewport screenshots** (1920x1080, chrome-devtools MCP `navigate_page`/`take_screenshot`/`take_snapshot`/`click`/`fill` — never OS-level capture) of the currently running app:
   - Landing page (`/`), empty
   - Landing page with the job's own real source text (`content/test_g_high_coverage_family.md`, the exact text behind job `013fbd2aa3f0`) pasted in and 60s duration selected
   - Recent Lessons (`/history`) — real job list, unmodified
   - Results page (`/jobs/013fbd2aa3f0/results`) — Lesson tab (video player, duration/model info, coverage cards), Sign Plan tab (VERIFIED SIGN / SUPPLEMENTARY (UNVERIFIED) badges), Traceability tab (per-sign source-sentence table)
   - The `/demo?job=013fbd2aa3f0` one-page case-study view — hero + stage strip, Sign Video evidence row + embedded video, and the Architecture section (AI proposes / verified data authorizes / deterministic validation gates)
3. **Real video clip**: `ffmpeg -i demo/MOE_Prototype_Lesson_Demo.mp4 -t 14 -c copy` → a 14.08s stream-copy (no re-encode) of 0:00–0:14, the FATHER/DOCTOR/MOTHER/TEACHER/SISTER/INTELLIGENT/BROTHER/PATIENT segment. Stream-copy guarantees the trimmed bytes are an exact subset of the source file's own encoded stream — nothing was regenerated or re-rendered.
4. Each screenshot was composited (Python/Pillow) onto a 1920x1080 white canvas with a bottom caption bar: Iron `#414042` body text, Gold `#B68A35` label + rule, Silver unused here (no divider needed), Helvetica as the Univers Next / Helvetica Neue stand-in. A title card and closing card were generated the same way, with the real MOE logo (`webapp/frontend/src/assets/moe_logo.png`) top-left/centered. No gradients, no drop shadows, no emoji.
5. The real video clip was scaled with `force_original_aspect_ratio=decrease` + letterbox-padded to 1920x1080 on white (not black) to match the surrounding frames, with no cropping or alteration of its actual pixel content.
6. All segments (title card, 9 screenshot frames, the real video clip, closing card) were each encoded to fixed-duration 1920x1080/30fps/yuv420p/h264 clips and concatenated with `ffmpeg -f concat` into the final file (`-movflags +faststart`). Hard cuts between shots — no crossfades — for reliability and a crisper pace.

## Video-plays shot verification

Explicit steps taken, not assumed:
1. `md5 demo/MOE_Prototype_Lesson_Demo.mp4` → `b529fe0d4922e797c8d626b886f88cb0`
2. `md5 outputs/webapp_jobs/013fbd2aa3f0/final_episode.mp4` → same `b529fe0d4922e797c8d626b886f88cb0` (already matched — the registered job dir did not need updating)
3. The 14s clip used in the walkthrough was cut with `-c copy` (stream copy, no re-encode) directly from `demo/MOE_Prototype_Lesson_Demo.mp4` on disk — the exact file with the confirmed md5 above, not any other copy.
4. Sanity-checked the assembled walkthrough at the timestamp where the real clip plays (`ffmpeg -ss 30 -i demo/MOE_Website_Walkthrough_Demo.mp4 -frames:v 1 ...`) — the extracted frame shows the avatar mid-sign with the "DOCTOR" / "طبيب" caption, matching the real rendered lesson content, letterboxed on white as expected.

## Shot list (as actually produced)

| # | Approx time | Duration | Shot | Source | Caption |
|---|---|---|---|---|---|
| 1 | 0:00 | 5s | Title card | Generated card | "AI-Powered Sign Language Academic Video Generator - website walkthrough - real running app, real generated lesson" + presenter credit "Shahzeb Naeem" (hyphen, not em-dash; name added per user request) |
| 2 | 0:05 | 5s | Landing page | Real screenshot, `/` | "Landing page — paste or upload verified academic source text" |
| 3 | 0:10 | 6s | Paste + configure | Real screenshot, real pasted text, 60s duration selected | "Real source text pasted, 60s duration and review mode selected" |
| 4 | 0:16 | 5s | Recent Lessons | Real screenshot, `/history` | "Every completed run is saved, with its real coverage numbers" |
| 5 | 0:21 | 5s | Results — video ready | Real screenshot, `/jobs/013fbd2aa3f0/results` | "The generated Arabic Sign Language video, ready to play" |
| 6 | 0:26 | 14.2s | **Real video plays** | Real `-c copy` clip, 0:00–0:14 of `demo/MOE_Prototype_Lesson_Demo.mp4` | (no caption bar — clip's own on-screen sign captions shown, e.g. "DOCTOR" / "طبيب") |
| 7 | 0:40 | 7s | Sign Video coverage stats | Real screenshot, `/demo?job=013fbd2aa3f0` | "86.4% ZHO institutional + 13.6% ESL Zayed supplementary, 0 fallback" |
| 8 | 0:47 | 8s | Sign Plan badges | Real screenshot, Results page Sign Plan tab | "Every sign tagged Verified, Supplementary, or Fingerspelled" |
| 9 | 0:55 | 6s | Traceability table | Real screenshot, Results page Traceability tab | "Every sign traces back to its exact source sentence" |
| 10 | 1:01 | 5s | Case-study view hero | Real screenshot, `/demo?job=013fbd2aa3f0` | "A one-page view assembles the same real pipeline data end to end" |
| 11 | 1:06 | 7s | Architecture section | Real screenshot | "AI proposes, verified data authorizes, deterministic checks gate output" |
| 12 | 1:13 | 6s | Closing card | Generated card | "Local AI only · Falcon-H1-7B via Ollama · Full source code, traceability, and test suite in repository" |

**Total duration: 79.2 seconds** — within the requested 70–100s range, no crossfade padding, no redundant shots (Review tab omitted since this job has 0 review-required items — already communicated honestly via the coverage stats and Sign Plan badges).

## Constraints honored

- Every screenshot is a real chrome-devtools MCP viewport capture of the actually-running app (`localhost:5173`/`:8000`) — never OS-level screen capture, never a mockup.
- The one non-screenshot segment is a real, stream-copied `ffmpeg` trim of the pipeline's own real MP4 output (`demo/MOE_Prototype_Lesson_Demo.mp4`) — verified by md5 match against the registered job's `final_episode.mp4` and by frame-extraction sanity check (see "Video-plays shot verification").
- No caption states anything not directly visible in its shot or independently verifiable from the same job's own JSON artifacts (`validation.json`, `stage_timings.json`).
- No pipeline/backend code or coverage numbers were modified to look better.
- Brand palette exact: white `#FFFFFF` background, Iron `#414042` body text, Gold `#B68A35` accent/label, Helvetica (Helvetica Neue / Univers Next stand-in). No gradients, no drop shadows on the logo, no emoji.

## Live-UI note

While building this, the Results page (`/jobs/013fbd2aa3f0/results`) still displays the job's original staging source path (`/Users/shaz/MOI-Arabic-Sign-Language/outputs/webapp_jobs/_staging_058e62457399/test_g_high_coverage_family.md` — note the typo "MOI" vs. "MOE" in that historical path, an artifact of the machine's directory name at the time the job was originally run, not a new bug). This is disclosed here rather than hidden; it did not appear in any shot's caption.
