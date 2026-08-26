# Federal Visual Identity — Decision Record

This document records how the prototype's web UI (`webapp/frontend`) relates to the UAE Government Visual Identity Guidelines for Federal Ministries, and is explicit about what is an **OFFICIAL GUIDELINE REQUIREMENT** versus a **PROTOTYPE UI IMPLEMENTATION DECISION**.

## 1. Official guideline source

`https://vig.gmo.gov.ae/en/guideline/federal-ministries`

**Attempted live re-verification during this build (2026-08-22):** a `WebFetch` request to this URL returned `HTTP 403 Forbidden` — the site appears to block automated/non-browser fetches. **This could not be independently re-confirmed in this session.**

**Update (2026-08-22, same day):** the candidate subsequently supplied a design-handoff package (`Ministry of Education branding guidelines.zip`) containing `BRAND_GUIDE.md` and a high-fidelity HTML mock (`AI Sign Language Generator.html`) for the Create Lesson screen. That package states it was itself sourced from the same GMO guideline page, with exact hex values (not just RGB) and pixel-level spacing/typography specs. The frontend has been rebuilt to match that handoff exactly (see §3/§4 below). **The underlying guideline page itself still could not be independently re-fetched live** — the handoff package is treated as a faithful, higher-fidelity restatement of it, not an independent re-verification. Manually cross-checking the live page before a panel presentation is still worthwhile but no longer the only source behind these values.

## 2. Relevant sections reviewed

Not independently reviewed live (see §1). The build instruction specified: Logo, Logo Usage, Typography, Colours, Website, Photography, Pattern restrictions, Video identity. This record follows that same structure.

## 3. Official colour values used

OFFICIAL GUIDELINE REQUIREMENT (as supplied, not independently re-verified live):

| Name | RGB |
|---|---|
| White | 225, 225, 225 |
| Silver | 198, 198, 198 |
| Iron | 65, 64, 66 |
| Gold | 182, 138, 53 |

PROTOTYPE UI IMPLEMENTATION DECISION: implemented as CSS custom properties in `webapp/frontend/src/theme.css` (`--federal-white`, `--federal-silver`, `--federal-iron`, `--federal-gold`). Only the primary palette is used — no secondary palette was introduced, per the instruction's "do not mix multiple secondary palettes" guidance. Iron is used for primary text and headings; white/near-white for page surfaces; silver for borders/secondary separators; gold is reserved for controlled emphasis only (the prototype badge, focus rings, accent border on the active tab, disclaimer box accent) — never as a large background fill, to keep it a restrained accent rather than a decorative theme colour.

Status indicators (verified/fallback/review/unsupported chips, and PASS/REVIEW_REQUIRED banners) use separate, accessible ok/warn/error tones rather than the federal accent colours — this is a **deliberate deviation**: reusing Gold for both "brand accent" and "warning" would conflate identity with status semantics, and the instruction itself required status to never rely on colour alone (icon + text always accompanies colour, see `StatusChip.tsx`).

## 4. Typography implementation

OFFICIAL GUIDELINE REQUIREMENT (as supplied): Univers / Univers Next for digital/website materials.

PROTOTYPE UI IMPLEMENTATION DECISION: `font-family: "Univers Next", Arial, "Segoe UI", "Noto Sans Arabic", sans-serif;` (see `theme.css` `--font-family`). **Univers Next is not installed/licensed in this environment** — no proprietary font file was downloaded, redistributed, or committed to the repository, per the explicit instruction against pirating/redistributing it. The browser will render the Arial fallback (or the OS default sans-serif) unless the deploying environment legitimately has Univers Next installed. `Noto Sans Arabic` is included ahead of the generic `sans-serif` fallback specifically to keep Arabic-script rendering clean, since Arial's Arabic coverage is inconsistent across platforms — this is a prototype addition beyond the instruction's literal fallback suggestion, made for Arabic-legibility reasons.

## 5. Logo decision

**Updated 2026-08-22 — an official MoE logo asset is now used.** The candidate supplied an official-looking MoE logo file directly (from their own Downloads folder: `united-arab-emirates-ministry-of-education-thumb.png`, 1633×400px RGBA, transparent background). It has been copied into `brand/assets/moe_logo_horizontal_full-colour.png` (the brand kit — see `brand/README.md`) and `webapp/frontend/src/assets/moe_logo.png` (used directly by `App.tsx`).

**Provenance caveat (unchanged from the brand kit's own note, repeated here deliberately):** this specific file's filename convention ("-thumb") suggests it may originate from a third-party logo aggregator rather than an official GMO/MoE download channel, and **has not been independently verified against an official Ministry/GMO source in this session.** Reasonable for this internal candidate prototype; should be swapped for a verified official file before any wider or public use.

**Usage rules applied (see `brand/README.md` §1 for the full list, enforced in code):**
- Placed in a dedicated `.brand-strip` above the main app header (`App.tsx`), never crowded by nav/language-toggle chrome — this IS the clear-space enforcement.
- `object-fit: contain` + fixed `height: 44px` (`.moe-logo` in `theme.css`) — proportional scaling only, no independent width/height stretching.
- Full colour, as supplied — no recolouring, no filters, no opacity reduction.
- No rotation, no drop shadow, no rearrangement of the wordmark/emblem relative positions (rendered as the single supplied image, not decomposed into separate elements).
- Placed on the plain near-white `--surface` background the file's transparency was designed for.
- The "MoE Case Study Prototype" badge and the "not an officially deployed Ministry service" footer line remain visible alongside/near the logo at all times — the logo's presence does not imply official endorsement, and the surrounding disclaimers are deliberately not removed or minimized now that a real logo is present.

Formal deployment would require re-confirming this exact file against an official GMO/MoE asset source (or replacing it with the officially-issued file) before any use beyond this internal case-study prototype.

## 6. Bilingual / RTL implementation

English (`lang="en" dir="ltr"`) and Arabic (`lang="ar" dir="rtl"`) are both implemented, toggled independently from the academic source language (`main.tsx` sets `document.documentElement.lang`/`dir` from a separate `uiLang` state, never from `source_language`). The Arabic translation set is a full parallel dictionary (`i18n.ts`), not a partial/placeholder one. Layout uses CSS logical properties (`margin-inline-*`, `border-inline-start`, `text-align: start`) throughout `theme.css` specifically so RTL is a genuine layout mirror, not just flipped text in an unchanged LTR grid — header order, stage-tracker alignment, and metric-card text alignment all have explicit `[dir="rtl"]` rules where logical properties alone weren't sufficient (see the bottom of `theme.css`).

## 7. Number formatting

Western/keyboard-numeral glyphs (`45`, `85.2%`, `149`) are used in both English and Arabic UI modes — no automatic Arabic-Indic numeral conversion is applied anywhere. All numeric values are rendered directly from the API's JSON numbers via React's default `{value}` interpolation, which never performs locale-based numeral substitution.

## 8. Video-branding decision

**No persistent emblem watermark is added to the generated video anywhere in the pipeline or the web app.** The rendering path (`scripts/spike_render_captioned_lesson.py`, `scripts/spike_cartoon_avatar.py`) is unmodified in this respect. The only on-video text is the existing English/Arabic caption bar, which predates this web-app build and is not a branding element. A restrained text label ("MoE Case Study Prototype") appears only in the surrounding web UI (the badge in the header, and the "not an officially deployed Ministry service" footer line) — never burned into the video itself.

## 9. Pattern decision

**No official or approximated federal pattern (e.g. Qasr Al Watan–derived) is used anywhere in this UI.** No pattern asset exists in `webapp/frontend`. Backgrounds are flat, restrained neutral surfaces per §3.

## 10. Imagery decision

No stock/generated government imagery is used. The generated sign-language avatar video is the primary — and only — visual asset in the Results screen, per the explicit instruction that it should be the main visual asset. No photography was added.

## 11. Accessibility decisions

Semantic HTML landmarks (`<header>`, `<main>`, `<footer>`, `<nav>`); visible focus rings via `:focus-visible` (`theme.css`); status conveyed via icon + text, never colour alone (`StatusChip.tsx`); form fields use associated `<label>` elements; heading hierarchy (`h2`/`h3`) is used consistently per page rather than skipped levels; native `<video controls>` is used for the generated lesson (inherits the browser's own accessible control set rather than a custom player). **No formal accessibility audit/certification has been performed** — this is stated here explicitly per the instruction not to claim certification that hasn't occurred.

## 12. Responsive adaptations

`theme.css` uses `grid-template-columns: repeat(auto-fit/auto-fill, minmax(...))` for the metric cards and history grid, and the header/nav wraps via flexbox `flex-wrap` at narrow widths. No dedicated mobile-first breakpoints were authored beyond this — the prototype's target demonstration context is a desktop panel presentation, not mobile use, so deep responsive work was intentionally out of scope for this build.

## 13. Deliberate deviations (summary)

- Status colours (ok/warn/error) are separate from the federal accent (Gold) — see §3.
- Univers Next is referenced but not bundled (no font file exists in this repo) — see §4.
- `Noto Sans Arabic` added to the font stack ahead of the instruction's literal Arial-only fallback, for Arabic legibility — see §4.
- Live re-verification of the official guideline page was attempted but blocked (HTTP 403) — see §1. **This is the most important open item to close manually before the panel.**
