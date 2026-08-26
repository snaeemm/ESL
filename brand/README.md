# Brand Kit — MoE Case Study Prototype

Reusable brand assets and rules for anything built off this project going forward: this web app, the 4-slide submission deck, and any future presentation material. Read this before adding a logo, colour, or typeface to a new deliverable — don't reinvent these decisions per-artifact.

This folder is the single source of truth for "what does the official identity actually look like here." `docs/FEDERAL_VISUAL_IDENTITY.md` is the longer decision *record* (why each choice was made, what's official vs. prototype); this folder is the *kit* you actually pull assets and values from.

## Contents

```
brand/
  README.md                                          this file
  assets/
    moe_logo_horizontal_full-colour.png                official MoE logo lockup, transparent background
```

## 1. Logo

**File:** `assets/moe_logo_horizontal_full-colour.png` — 1633×400px, RGBA (transparent background), horizontal lockup: English wordmark ("UNITED ARAB EMIRATES / MINISTRY OF EDUCATION") + UAE federal eagle emblem in gold + Arabic wordmark, left-to-right in that order. Identical file also delivered via an explicit design handoff package (`Ministry of Education branding guidelines.zip` → `design_handoff_sign_language_generator/assets/moe-logo.png`), confirmed byte-identical to the copy already in this kit.

**Provenance note:** sourced from the candidate's own Downloads folder, and re-confirmed as part of a design-handoff brand package (`BRAND_GUIDE.md`), which states this is "the real MOE logo asset" and that no official logo file is published on the public GMO guideline site's own downloads section. Treated as the authoritative asset for this prototype on that basis. **Still not independently verified against an official Ministry-issued download** — reasonable for this internal case-study prototype; confirm before any public/wider use.

**Per the design handoff's explicit build spec:** use the full logo only in page headers/splash; prefer a plain text wordmark ("UAE MINISTRY OF EDUCATION", gold, uppercase, letter-spaced) for any other in-app/repeated placement (nav bars, footers, etc.) rather than the full logo-with-emblem. This kit's rules below are updated accordingly.

**Usage rules (apply these every time, no exceptions):**
- **Clear space:** leave empty space around the logo at minimum equal to the height of the eagle emblem on all sides. Never let text, borders, or other content touch the logo.
- **Minimum size:** never render narrower than ~200px wide (below that the Arabic wordmark stops being legible) — scale down the whole page/layout instead of shrinking just the logo further.
- **No colour changes:** always use the full-colour gold/red/green/white/black version as supplied. Never recolour, invert, apply a filter, or render as a single flat colour.
- **No distortion:** always scale proportionally (`object-fit: contain`, fixed aspect ratio). Never stretch width/height independently.
- **No rotation, no drop shadows, no opacity reduction, no rearranging the wordmark/emblem relative positions.**
- **Always place on a plain, light, uncluttered background** — this file has a transparent background specifically so it can sit on white/near-white surfaces without a visible box; don't place it over photos, patterns, or dark backgrounds without testing contrast first.
- **Never place other logos/marks directly adjacent to it implying co-branding or endorsement** without separately confirming that's appropriate — this is a candidate prototype, not an official Ministry product, so keep the "MoE Case Study Prototype" / "not an officially deployed Ministry service" labelling visible near the logo, not stripped out.

## 2. Colour palette

Primary federal palette — exact hex confirmed by the design handoff, superseding the earlier RGB-only values in `docs/FEDERAL_VISUAL_IDENTITY.md` §3 (which flagged them as unverified live — this handoff resolves that):

| Token | Name | Hex | Typical use |
|---|---|---|---|
| `--federal-white` | White | `#FFFFFF` | Card/surface backgrounds |
| (page bg) | — | `#FAFAFA` | Overall page background (off-white, distinct from card white) |
| `--federal-silver` | Silver (Pantone 877C) | `#C6C6C6` | Dividers, secondary/muted text |
| `--federal-iron` | Iron (Cool Gray) | `#414042` | Primary text, headings, primary UI chrome |
| `--federal-gold` | Gold (Pantone 8960C) | `#B68A35` | Accent/CTA/highlights ONLY — never a large fill |
| (gold tint) | — | `#FBF5EB` | Selected-state background behind gold-accented elements |
| (heading) | — | `#262626` | Large headings (H1), slightly darker than Iron for emphasis |

Border tones used alongside these: `#E5E5E5` (card/section borders), `#DADADA` (input borders). Secondary palette (Sapphire Blue / UAE Red / UAE Black / UAE Green) exists in the official guideline but is **not used in this kit** — pick at most one, only if a status colour is unavoidable, never mixed with the primary palette on the same surface.

Slide decks / documents: use Iron for body text and headings, Gold sparingly for a single emphasis element per slide (a rule line, a key stat, a callout border) — never as a slide background, never for more than one accent purpose per slide.

## 3. Typography

Digital/web: `"Helvetica Neue", Arial, sans-serif` — this is the confirmed web stand-in per the design handoff (Univers Next is not a free web font and is not bundled/licensed in this repo). Do not substitute Inter, Roboto, or other geometric/humanist sans fonts — Helvetica Neue/Arial specifically. See `docs/FEDERAL_VISUAL_IDENTITY.md` §4.

Slide decks: same fallback (Arial, or the presentation tool's closest available match to Helvetica Neue) for the same licensing reason.

Numerals: always Western/Arabic numerals (`45`, not `٤٥`), even in Arabic-language text or slides.

## 4. What NOT to add

Per the official guideline review already done for the web app (`docs/FEDERAL_VISUAL_IDENTITY.md`) — the same rules apply to slides/other materials:
- No official federal pattern (Qasr Al Watan–derived or otherwise) — omit rather than approximate.
- No stock "government AI" imagery — if you need a visual, use a real screenshot/frame of this project's own output (the avatar video, the results dashboard).
- No fabricated/redrawn version of the federal emblem — only the exact logo file in `assets/`, used whole, per the rules in §1.

## 5. Quick-reference for slide decks

1. Title slide: logo top-left or centered per §1's rules, "MoE Case Study Prototype" label visible, Iron text on white/near-white background.
2. Body slides: Iron headings, Gold used for at most one accent element, Silver for divider rules, generous whitespace (this identity is restrained, not dense).
3. Never claim official Ministry endorsement/certification anywhere in the deck — this is a candidate's technical prototype for a case study, state that plainly on the title or closing slide.
