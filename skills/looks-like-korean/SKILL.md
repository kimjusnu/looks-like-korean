---
name: looks-like-korean
description: Use when writing or revising Korean prose that must not read as machine-written - proposals, reports, self-introductions, essays, memos. Declares sentence-ending rhythm targets BEFORE writing, then measures the result with a deterministic engine and regenerates only the off-target paragraphs. No LLM-based detection.
---

# looks-like-korean

## What this is for

A Korean text reads as machine-written when every sentence ends the same way. Vocabulary
editing does not fix that, and no amount of prompt instruction reliably prevents it. So the
rhythm is decided **before** the prose, and checked **after** it.

## The one claim this skill makes

> The register of your sentence endings should vary, and you should be able to measure by how
> much.

That claim holds regardless of whether the engine's human-versus-machine hypothesis holds.
That hypothesis is **still unproven** — see `docs/RESEARCH.md`. Do not use this skill to
claim a text is human-written. Use it to keep a text from being register-uniform.

## Procedure

### 1. Fix the target before writing (2 minutes, before any prose)

For the document, decide and write down:

- **Length** and section count.
- **Ending register budget** — not "use 해요체". Explicitly: e.g. `~습니다` 4, `~해요` 2,
  명사형 1, 의문 1, across 8 sentences. The point is to plan the *distribution*, not a style.
- **Longest run of one register you will tolerate** — 4. Not "no more than a few".
- **Two places a sentence will be allowed to be very short** (under 5 words) and one place
  that will be allowed to be very long (over 30). Extremes are what a reader feels without
  noticing.

If the document is 3 sentences, skip this step. The machinery is not worth it.

### 2. Draft normally

Write the document. Do not think about the metrics while writing; that produces text that
scores well and reads like nothing.

### 3. Measure

```bash
python -m looks_like_korean score draft.md
```

Read `uniformity_index` first. Then `max_same_register_run`, then `sentence_len_gini`.

These are **your own targets**, not reference values. The comparison that means something:

```bash
python -m looks_like_korean compare original.md revised.md
```

If `uniformity_index` in the revision is not meaningfully lower, the revision did not change
the rhythm — it changed words.

### 4. Regenerate off-target paragraphs only

For any paragraph above target, rewrite **that paragraph** with the concrete change named:

- one sentence switched to a different register — not a swap for its own sake, but because
  the paragraph has been ending the same way for three sentences
- one very short sentence placed where the paragraph has been running at one length
- one nominal ending (`~함`, `~지`, `~기`) where the paragraph is closing a thought instead
  of stating a verdict
- one connective adverb (「그러나」 「또한」 「결국」) deleted, the two halves joined directly

Do not touch paragraphs that already meet the target. Rhythm variety across a document
requires some paragraphs to be uniform.

### 5. Report the diff, not just the new text

Output the before/after of every changed paragraph, with the reason for that paragraph's
change. A revision whose rhythm moved but whose numbers are not shown cannot be checked.

## Hard rules

- **Facts do not change.** Numbers, proper nouns, conditions, and direct quotations are
  identical before and after. This is first, and it is not negotiable. Rhythm edits that
  alter a figure are a bug.
- **Length within ±3%** unless the change was requested.
- **Do not convert the register globally.** A bulk `~습니다` → `~해요` pass is the failure
  mode this whole project exists to prevent.
- **Genre register is a rule, not a suggestion.** An official notice should not suddenly
  become conversational. If the document's genre demands one register throughout, that is
  the correct target, and `uniformity_index` near 1.0 is the right answer for it. Say so
  instead of fighting the metric.

## When not to use this

- Under ~10 sentences. Not enough text for the metric to mean anything.
- Direct quotation, references, code, tables, legal citations, and formulae — measure the
  prose around them, never the citations.
- A document that must not be edited at all, such as an official form whose wording is fixed.
  In that case the register is not yours to choose. Leave it alone.

## Files

- `src/looks_like_korean/` — the engine (standard library only)
- `docs/RESEARCH.md` — what is known, what is not, and the Korean classifier pitfalls
- `eval/examples.json` — self-authored before/after pairs to imitate the *shape* of a change
