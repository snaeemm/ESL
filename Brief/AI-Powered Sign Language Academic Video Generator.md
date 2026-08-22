# AI-Powered Sign Language Academic Video Generator
## Technical Brief for Implementation (Claude Code / Cowork)

**Owner:** Shahzeb Naeem
**Context:** MoE AI Center of Excellence candidate case study. Prototype + 4 slides + source code + README, due in 2 weeks. Panel will ask "explain and defend" — every design choice below must be defensible, not just functional.

---

## 0. Non-negotiable constraints (from the brief)

- Core inference (understanding, transformation, sign generation) must run on **local models only**. No external generative AI APIs for these stages.
- Every fact/term in the output episode must be **traceable to the approved source material**. No fabricated content.
- Uncertain/unsupported segments must be **flagged, not hidden or guessed**.
- Prototype = one complete short episode ("Episode 1: Cells," Grade 6 Science Ch.3), fully traceable, in Arabic Sign Language.

---

## 1. Architecture decision: deterministic sign output, not generative video

**Decision:** The final "Sign Video" stage is NOT AI-generated video. It is deterministic clip selection + assembly from a real, official sign-language video source.

**Why (state this explicitly on the architecture slide):**
- Full source traceability (a hard requirement) is very difficult to guarantee for generative video output, but trivial to guarantee for a lookup-based system — every clip in the output has a direct receipt back to (a) the source text and (b) an official government dictionary entry.
- Confidence-based flagging (shown in the brief's own mockup) requires a bounded vocabulary with a real notion of "not found" — a generative model doesn't naturally have this.
- The "LOCAL AI MODELS ONLY" requirement is scoped to *understanding, transformation, and sign generation as AI-eligible stages* — it does not mandate the final rendering be neural.

**Pipeline (fixed order, no autonomous branching — deliberately NOT using a general agent framework like Google's ADK; see Section 6):**

```
Source (verified curriculum text)
   -> Understand (local LLM: concept extraction, grounded only in source)
   -> Structure (deterministic: ordered script of concepts/terms)
   -> Generate (deterministic: glossary lookup -> fingerspell fallback -> flag)
   -> Validate (human-in-the-loop review queue for flagged/low-confidence terms)
   -> Sign Video (deterministic: clip trimming, crossfade, assembly)
```

---

## 2. Video source — Step 1, do this FIRST, before any backend/frontend scaffolding

**Primary source:** Zayed Higher Organization (ZHO) UAE Sign Language Dictionary
https://www.za.gov.ae/en/Sign-Language-Dictionary/UAE-Sign-Language-Categories

Categories available: Alphabets, Numbers, Official Documents, Landmarks and Locations, Ministries Departments, Clothing and Toiletries, Popular Cuisines, Family, Common Verbs, Attributes and Situations, Directions and Locations, Colors, Household Items, Professions and Jobs, Education, Measurement Units, Health, Environment, Animals, Plants, Sports.

**Secondary source to evaluate for access:** UAEU thesis dataset — "Interactive Emirate Sign Language E-Dictionary Based on Deep Learning" (Ahmed Abdelhadi Abdelhadi, UAEU ScholarWorks, thesis #1022). 127 signs + 50 sentences, 708 clips, performed by only 4 Emirati signers, reviewed by UAE Community Development Authority. Fewer signers = better consistency. Check `scholarworks.uaeu.ac.ae/all_theses/1022` for access terms; likely requires a request rather than bulk public download — evaluate but do not block on it.

**Task for Claude Code (run this first, report back before continuing):**
1. Enumerate all ZHO categories and index every available word + its video URL.
2. Download clips relevant to the Episode 1 term list (Section 3) plus the full Alphabets set (needed for fingerspelling fallback).
3. **Tag each clip with signer identity** (cluster by visual similarity if no metadata) — we need to know, per term, whether it's available from a single consistent signer.
4. Produce a coverage report: which needed terms are directly available, from which signer(s), and which have zero coverage (these become fingerspell/flag cases).
5. Flag technical blockers immediately (e.g., JS-rendered video players resisting scripted download, rate limits, missing clips) so we can adjust scope on day 1–2, not day 10.

**Signer consistency requirement:** Prefer a single primary signer across the episode. If coverage from one signer is too sparse for the needed terms, fingerspell the gaps rather than switching to a different visible presenter mid-episode — the presenter should never visibly change person-to-person.

**Note on usage rights:** ZHO is an official Abu Dhabi government educational resource. Flag in the README that usage terms should be formally verified before any deployment beyond this prototype/demo context — don't skip this, it's a legitimate line item MoE will respect, not a weakness to hide.

---

## 3. Episode 1 term list ("Cells," Grade 6 Science Ch.3)

*[To be finalized against actual chapter content — placeholder core list below, refine once source text is available]*

cell, membrane, nucleus, mitochondria, cytoplasm, organelle, function, protect, energy, wall, plant, animal, structure, small, inside, contain, produce, living, organism, body, part, example, difference, compare

Cross-check this list against the ZHO coverage report (Section 2, task 4). Expect several scientific terms (mitochondria, organelle, cytoplasm) to have zero direct coverage — this is expected and is exactly what exercises the fingerspelling/flagging fallback logic.

---

## 4. LLM selection — benchmark, don't assert

**Candidates (all local-deployable on M1 Pro via Ollama/MLX, quantized):**
- **Jais** (Inception/G42/MBZUAI, UAE-built) — primary candidate. Strong Gulf-Arabic coverage, sovereign-deployment narrative fit.
- **Falcon** (TII, Abu Dhabi) — secondary UAE-sovereign candidate.
- **Qwen3** — strong general instruction-following control group.

**Task for the demo:** the LLM only performs concept extraction + structuring — output a structured JSON script (ordered list of {concept, key_terms, source_span}) grounded strictly in the provided source text. It does NOT touch the video glossary directly (see Section 1 — that's a separate deterministic stage, to preserve traceability).

**Benchmark methodology (reuse the thesis's own evaluation approach — this is a strong, citable continuity point):**
Score each candidate's structured output against the verified source text using the same metrics used in prior published research (cosine similarity, ROUGE, Jaccard, BLEU) to measure faithfulness/grounding. Report actual numbers. The model with the best grounding-faithfulness score is the one used in the live demo. Write this comparison up as a small appendix table for the slides/README — "we benchmarked, we didn't assume" is a materially stronger answer under panel questioning.

**Demo vs. production distinction (state explicitly):**
- Demo: real local Ollama call, live, on the selected model.
- Production reasoning (for slide/README): off-the-shelf instruct models are sufficient for MVP-scale extraction; production-scale accuracy across all grades/subjects likely needs domain adaptation (e.g., LoRA fine-tuning on verified MoE curriculum text specifically for extraction-faithfulness), which should be scoped as a Phase 2 item, not attempted in the prototype.

---

## 5. Human-in-the-loop / validation stage

Any term that is: (a) not found in the glossary, (b) only found via fingerspelling, or (c) below a coverage/confidence threshold → routed to a review queue in the UI, mirroring the case study's own mockup ("mitochondria — low confidence, teacher review suggested"). This is a visible, working feature in the demo, not just a claim.

---

## 6. Explicitly rejected approaches (state these as deliberate decisions, not gaps)

- **No agentic orchestration framework** (e.g., Google's ADK or similar multi-agent kits). The pipeline is fixed-order and auditable by design; a general agent framework introduces autonomous branching that would need to be justified away, and the case study's traceability requirement is best served by an explicit, simple, self-owned pipeline (FastAPI stages), not a general orchestrator.
- **No neural sign-video generation for the prototype.** See Section 1. Explicitly note this as the production/Phase 2 direction, citing prior published research (IEEE TCSS 2026, sign-language deepfake generation and validation) as relevant prior art — but note the real blocker: no large-scale licensed/consented Emirati/Arabic Sign Language video corpus currently exists at the scale needed (unlike How2Sign for ASL), so this is a data-availability problem, not a modeling problem, and should be framed that way.

---

## 7. Known limitations to state explicitly (in README + slides — do not hide these)

- ZHO (and the UAEU dataset) are general-vocabulary lexical resources, not domain-specialized (science terminology) and not complete lexicons — coverage gaps are expected and are handled by the fallback chain, not a failure of the system.
- Word-by-word concatenation is not linguistically equivalent to fluent, grammatically correct ArSL (no spatial grammar, classifiers, or non-manual markers). Production deployment would need an ArSL linguistics/interpreter consultant, or longer-term, a learned sign-production model trained on a proper ArSL corpus once one exists.
- M1 Pro is a prototyping environment; production requires GPU-backed inference infrastructure, sized for concurrent MoE users.
- Video usage rights for ZHO content should be formally verified before any deployment beyond this demo.

---

## 8. Stack

- **Backend:** FastAPI. Modules: `source_ingest`, `understand` (LLM call), `structure`, `generate` (glossary lookup + fingerspell fallback + flagging), `validate` (review queue), `assemble` (clip trim/crossfade/render).
- **Frontend:** React + Tailwind. MoE-themed (colors/typography to match Ministry of Education branding — source from official MoE brand guidelines if available, otherwise UAE government visual conventions: greens/golds, clean Arabic-first typography, RTL support).
- **LLM runtime:** Ollama, local.
- **Video assembly:** ffmpeg for trim/crossfade/concatenation.

---

## 9. Build order

1. ZHO (+ UAEU dataset evaluation) indexing/download + coverage report — **do this first, alone, before scaffolding anything else.**
2. LLM benchmark script (Jais vs Falcon vs Qwen3, grounding-faithfulness scoring).
3. Backend pipeline (all stages, using real data from step 1).
4. Frontend (MoE-themed, includes review-flag UI).
5. End-to-end run producing one real Episode 1 output video.
6. README + slides, written from what was actually built.

---

## 10. Deliverables checklist

- [ ] Working prototype (end-to-end, one real output episode)
- [ ] Max 4 slides: problem / architecture (with the "deterministic not generative" decision explained) / decisions (LLM benchmark results, fallback chain, rejected approaches) / production path (data-corpus gap, thesis as Phase 2 prior art)
- [ ] Source code (clean repo)
- [ ] Short README (how to run, stack, assumptions, limitations — Section 7 above goes here near-verbatim)