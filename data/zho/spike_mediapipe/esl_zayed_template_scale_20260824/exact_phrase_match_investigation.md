# Exact-phrase bilingual matching — investigation (not implemented)

Question (task brief §7): if a lesson's planned meaning is verbatim identical
to a complete observed ESL Zayed PHRASE/SENTENCE, is a literal
text/normalized-text match fundamentally different from -- and safer than --
the already-rejected embedding-similarity approach (MiniLM sentence
retrieval, Recall@1=0.20, ruled NOT_USEFUL in
`ab_experiment_20260823/FINAL_REPORT.md` §C)?

## Finding: yes, fundamentally different in kind -- but essentially unusable in practice, so not worth wiring in.

**Why it's a different kind of risk.** Embedding similarity is a fuzzy
nearest-neighbor search over a continuous space: it always returns a "closest"
candidate even when nothing truly matches, and the measured failure mode
(Recall@1=0.20, several concretely wrong top-1 hits) came from confidently
wrong nearest neighbors, not from returning nothing. An exact/normalized-text
match (casefold, strip diacritics/punctuation, collapse whitespace) is a
deterministic membership test: it only ever fires when the planned meaning
string is identical (under a narrow, auditable normalization) to one of the
51 known-good ESL Zayed PHRASE/SENTENCE/DIALOGUE strings in the corpus. There
is no similarity threshold to mistune, no "close but wrong" candidate can
ever win, and every accepted match is trivially explainable (show the two
identical strings side by side). In that narrow sense it introduces no new
false-positive risk class beyond what the existing WORD-level exact-match
path already carries.

**Why it doesn't help in practice.** The corpus has only 51
PHRASE/SENTENCE/DIALOGUE items, and they are a fixed set of canned classroom
phrases (greetings, possessive-pronoun drills, a self-introduction template
-- "My name is Zayed", "I'm Deaf", "Your book", etc). Lesson content going
through this pipeline is Falcon/LLM-generated free text tied to arbitrary
curriculum material, not drawn from this canned set. Checked empirically: a
case-folded substring test of all 47 non-empty English PHRASE/SENTENCE
strings against the full text of all 5 dev fixtures (family/school EN+AR,
Emirati D, Cells, Photosynthesis) produced **zero exact matches**. Real
lesson phrasing essentially never reproduces a fixed canned phrase verbatim
-- a single word substitution, different tense, or different word order
(all normal and expected from an LLM) breaks the match completely, since
exact matching by construction has zero fuzzy tolerance.

## Conclusion

Exact-phrase matching is architecturally sound as a future, strictly-gated,
zero-tolerance addition -- categorically safer than embedding similarity
because it cannot produce a "confidently wrong" match. But given the
measured zero-hit rate against real lesson content in this corpus, it would
add a new production authorization surface (PHRASE/SENTENCE candidates
reaching the resolver) for a benefit that has not been observed to exist.
Per the task brief, this is reported as a finding only. It is **not** wired
into `lib/sign_resolver.py` or any live resolver path this session. The
resolver's WORD-only architecture is unchanged.
