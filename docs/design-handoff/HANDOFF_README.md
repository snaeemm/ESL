# Handoff: AI-Powered Sign Language Academic Video Generator

## Overview
A form-based prototype screen for a MoE tool that turns academic text into sign-language educational videos. User pastes/uploads source content, sets duration/review options, and generates a lesson.

## About the Design Files
The bundled file (`AI Sign Language Generator.html`) is a **design reference built in HTML** — it shows intended look, layout and copy, not production code to copy directly. Recreate this UI in the target codebase's existing framework/design system (React, Vue, etc.), or pick the most suitable framework if none exists yet.

## Fidelity
**High-fidelity.** Colors, typography, spacing and copy are final; recreate pixel-close using the codebase's own component library where possible.

## Brand system
This is a UAE Ministry of Education product — see `CLAUDE.md` (bundled) for the full brand spec (colors, type, logo rules). Key tokens also listed below.

## Screens / Views

### Screen: Create Lesson (single view)
**Purpose:** User submits academic source text/file and generation settings to produce a sign-language video lesson.

**Layout:**
- Full-width page, `#FAFAFA` background.
- **Header bar** (white, `1px solid #E5E5E5` bottom border, `20px 48px` padding): flex row, space-between. Left: MoE logo image, `64px` height. Right: pill badge "MoE Case Study Prototype" — `1.5px solid #B68A35` border, gold text, `999px` border-radius, `8px 18px` padding.
- **Title band** (white, same bottom border, `40px 48px` padding): flex row, space-between, wraps on narrow widths.
  - Left: H1 "AI-Powered Sign Language Academic Video Generator" (30px/700/#262626), subtext below (15px/#6b6b6d, max-width 640px, line-height 1.6).
  - Right: nav cluster — "Create Lesson" link (14px/700/#B68A35), "Recent Lessons" link (14px/600/#9a9a9c), language toggle (EN/ع segmented control, dark active pill).
- **Form card**: centered, `max-width:900px`, white bg, `1px solid #E5E5E5`, `14px` radius, `36px` padding, subtle shadow (`0 1px 3px rgba(0,0,0,0.04)`).
  - Tab row (2 buttons, `12px` gap): "Paste academic content" (active: dark filled `#414042`), "Upload academic source (.txt, .md)" (inactive: outlined).
  - Textarea, full width, `220px` min-height, `10px` radius, `1px solid #DADADA`, placeholder "Paste verified academic source text here…".
  - "Source language" label (13px/700) + select dropdown, full width, default "Auto-detect".
  - "Lesson duration" label + button row: 30s / 45s (selected — gold border `#B68A35`, gold text, `#FBF5EB` fill) / 60s / "Custom (seconds)" input (flex:1).
  - Helper text below (12.5px/#9a9a9c): pipeline duration note.
  - "Signing target" label + static text: "Arabic Sign Language — UAE/ZHO verified sign assets".
  - "Review mode" label + 2 radio rows: STRICT (selected — gold border + `#FBF5EB` fill) and PROTOTYPE (default outline). Each row is a full-width clickable label, `12px 14px` padding, `10px` radius.
  - Primary button "Generate Lesson": full width, `16px` padding, `10px` radius, solid gold `#B68A35` fill, white bold text, no border.
- Footnote below card, centered, `12.5px/#9a9a9c`: data/privacy disclaimer about local inference and the public UAE ZHO sign-language dictionary.

## Interactions & Behavior
- Tab switch toggles Paste vs Upload input mode (upload tab should reveal a file picker in place of the textarea).
- Duration buttons and review-mode radios are single-select, gold highlight on selection.
- "Generate Lesson" button should be disabled/grey until required fields (source text, duration) are filled, then active gold.
- Language toggle (EN/ع) switches app locale/direction (RTL for Arabic) — not implemented in the static mock.
- No animations/transitions specified beyond standard hover/focus states (add subtle `background`/`border-color` transitions, ~150ms ease, on interactive elements per platform convention).

## State Management
- `sourceMode`: 'paste' | 'upload'
- `sourceText`: string / `sourceFile`: File
- `sourceLanguage`: string (default 'auto')
- `duration`: 30 | 45 | 60 | custom number (default 45)
- `reviewMode`: 'strict' | 'prototype' (default 'strict')
- `locale`: 'en' | 'ar'
- Generation submit triggers an async pipeline call (not modeled here) — needs loading/progress and error states to be designed next.

## Design Tokens
- Colors: White `#FFFFFF`, page bg `#FAFAFA`, border `#E5E5E5` / `#DADADA`, Iron (text) `#414042`, muted text `#6b6b6d` / `#9a9a9c`, Gold (accent/CTA) `#B68A35`, gold tint bg `#FBF5EB`, heading dark `#262626`.
- Typography: font stack `"Helvetica Neue", Arial, sans-serif` (stand-in for Univers Next). Sizes: H1 30px/700, section labels 13px/700, body 14-15px, helper/footnote 12.5px.
- Radius: cards/inputs 10px, header card 14px, pill badges 999px.
- Shadow: `0 1px 3px rgba(0,0,0,0.04)` on the form card only.
- Spacing: page padding 48px horizontal; card internal gaps ~26px between form sections; button/tab gaps 10-12px.

## Assets
- MoE logo: `assets/moe-logo.png` (bundled) — official UAE Ministry of Education winged lockup, gold wordmark. Never recolor/stretch.

## Files
- `AI Sign Language Generator.html` — the full-fidelity mock (source of truth for this screen).
- `BRAND_GUIDE.md` — full MoE brand guide (colors, type, logo rules, do's/don'ts). Rename to `CLAUDE.md` at the target repo root so Claude Code picks it up automatically.
- `assets/moe-logo.png` — logo asset.
