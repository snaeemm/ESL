# UAE Ministry of Education — Brand Guide (for prototyping)

Source: UAE Government Media Office Visual Identity Guidelines, Federal Ministries (vig.gmo.gov.ae/en/guideline/federal-ministries).

## Colors
Primary palette (use these, don't invent new colors):
- White #FFFFFF
- Silver (Pantone 877C) — rgb(198,198,198) / #C6C6C6
- Iron (Cool Gray) — rgb(65,64,66) / #414042
- Gold (Pantone 8960C) — rgb(182,138,53) / #B68A35

Secondary (pick ONE palette, never mix with primary in the same design):
- Sapphire Blue, UAE Red, UAE Black, UAE Green — use sparingly for accents/highlights/buttons only.

For a digital prototype: white background, Iron for body text, Gold for accents/CTAs/highlights, Silver for dividers/secondary text.

## Typography
- **Univers (Univers Next)** — primary typeface for digital, web, publications, reports, advertising. Use this for the prototype's UI/body/headings.
- **Cronos Pro** (Latin) + **GE Alma** (Arabic) — formal pairing, used in logo wordmarks and official stationery only (not general UI).
- Fallback: Arial if Univers/Cronos/GE Alma unavailable.
- Numerals: always Arabic (Western) numerals, even in Arabic text.
- For web builds, substitute Univers with a close web-safe/Google Font (e.g. "Helvetica Now", "Inter", or system sans) since Univers isn't a free web font.

## Logo
- Real MOE logo asset available at `assets/moe-logo.png` (primary winged lockup, gold wordmark) — use this, not a placeholder, going forward. Full official 146-page PDF guideline also in `uploads/1_Guidelines Ministry_EN_2024_S_compressed_compressed.pdf` for deeper reference (stationery specs, PPT/presentation rules, initiatives branding, etc).
- Primary "winged" logo: UAE emblem centered, Arabic wordmark right, English wordmark left (country name line 1, ministry name line 2).
- On white/light backgrounds: full-colour logo.
- On dark backgrounds: white single-colour logo.
- Minimum clear space: generous margin on all sides (~4x a text unit).
- **Do not**: recolor, add shadows/gradients, stretch, rotate, change composition, or use the federal emblem alone (emblem-only use is restricted to President/PM).
- Digital header placement: top-left corner, with ample clear margin around it.
- Websites: logo top-left in header; simple header / content / footer structure.
- Social/app UI: prefer the **wordmark** (text-based, no emblem) over the full logo inside app screens; the full vertical logo is fine on a splash screen only.
- No custom placeholder logo — leave an `image-slot` or clearly labeled placeholder for the real MOE logo asset; do not fabricate an emblem graphic.

## Photography / imagery
Natural light, genuine (not staged) moments, authentic representation of UAE community, culturally respectful (appropriate dress). Avoid stock-photo feel, heavy manipulation, or exaggerated effects.

## Pattern
An ornamental geometric pattern (inspired by Qasr Al Watan) exists as a decorative edge/crop element in gold/iron/white — optional, used on covers/collateral, never combined with the logo on the same surface, and never as a background behind UI text.

## Tone / principles (advertising & comms)
Modern, elegant, objective/accurate, inclusive, empathetic. Clean, harmonious layouts — avoid clutter.

## Additional rules (from FAQ / Flag / Visuals pages)
- Only school uniforms may carry the full logo; other staff uniforms use the wordmark only.
- Never co-brand the official letterhead — no other logos, ever.
- Social media posts: one logo max, wordmark only (never the full logo with emblem).
- Government schools are exempt from outdoor flagpoles (they use in-yard flagpoles).
- No official MOE logo file is published on the public guideline site (Visuals/Downloads are empty of ministry-specific assets) — real asset is at `assets/moe-logo.png` instead (see Logo section above).

## Build spec for Claude Code — implement exactly as follows
- **Logo file**: `assets/moe-logo.png`. Use full-colour primary logo top-left on every page header, min width ~160-220px, ample clear space (don't crowd it). Never recolor/stretch/rotate it. Do not use it inside app screens beyond header/splash — prefer a plain text wordmark ("UAE MINISTRY OF EDUCATION", gold, all caps, letter-spaced) for in-app chrome, nav bars, or repeated small placements.
- **Colors (hex, exact)**: background `#FFFFFF`; body text `#414042` (Iron); accent/CTA/links/highlights `#B68A35` (Gold) — use sparingly, not as a wall of color; dividers/secondary/muted text `#C6C6C6` (Silver). Do not introduce other colors. If a secondary accent is unavoidable (e.g. success/error states), pick ONE of Sapphire Blue / UAE Red / UAE Green and use it only for that narrow purpose.
- **Typography**: font stack `"Helvetica Neue", Arial, sans-serif` (stand-in for Univers Next — do not use Inter/Roboto/Fraunces). Headings bold/semibold, Iron color. Numerals always Western/Arabic numerals.
- **Layout defaults**: header = logo top-left, white bg, simple nav; generous whitespace/margins; no gradients, no drop shadows on the logo, no emoji, no rounded-card-with-left-border-accent clichés.
- **Buttons/CTAs**: gold fill or gold outline, white or Iron text, simple flat style, no glow/gradient.
- **Imagery**: use neutral placeholders (image-slot) for people/culture photography — natural light, authentic, no stock-photo gloss — until real photos are supplied.
- **Reference**: full 146-page official guideline at `uploads/1_Guidelines Ministry_EN_2024_S_compressed_compressed.pdf` for anything beyond this scope (stationery, print, signage, events) — not needed for a typical web/app prototype.

This file (`CLAUDE.md`) is the single source of truth — hand the project to Claude Code as-is; it reads this automatically.
