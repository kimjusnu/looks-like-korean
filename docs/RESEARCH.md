# Research log

Everything this project believes, and how it decided to believe it. Numbers move;
the procedure below is the asset.

## The question

Can a Korean text be separated into *written by a Korean person* and *written by a model*
using only the distribution of its sentence endings and sentence lengths?

## The hypothesis

- **H1** — the signal is in the ending distribution, not the vocabulary.
- **H2** — a machine keeps one register for the whole document; a human crosses 2–4.
  Headline metric: `uniformity_index = 1 − normalised entropy(register distribution)`.
- **H3** — humans mix extremes (a 3-word sentence beside a 40-word one); machines stay
  near-normal. → `sentence_len_gini` on the log-length distribution.
- **H4** — nominal endings (`~함`, `~가능`, `~지`) appear in human prose as an
  unintentional beat, and in machine prose only as a formal closing. → `nominal_ratio`.

## P0 — gate: build a genre-matched labelled corpus

**Falsification rule.** If no metric reaches **AUC ≥ 0.75** on a genre-matched corpus, H1
is rejected and the metric list is redesigned. Building the engine before measuring is the
mistake we are trying not to repeat.

### What we have

347 documents, 579,061 characters human / 42,040 characters machine.

| side | genres | docs |
|---|---|---|
| human | 참여 의견 221 · 공고문 64 · 공공서비스제안서 40 · 기업공모제안서 4 | 329 |
| machine | 14 unrelated genres, 1–3 docs each (poster copy, video scripts, 자기소개지원서) | 18 |

### What we measured

Genre intersection: **zero**. `research/measure.py` therefore refuses to emit an AUC.

For the record, here is the number a first pass produced before the guard existed, because
numbers like this get quoted later without their caveats:

```
uniformity_index      AUC 0.700   human 0.616 > machine 0.397   ← opposite of H2
register_switch_rate  AUC 0.308                                  ← opposite of H2
sentence_len_gini     AUC 0.367                                  ← opposite of H3
sentence_len_logstd   AUC 0.352                                  ← opposite of H3
nominal_ratio         AUC 0.268                                  ← opposite of H4
max_same_register_run AUC 0.476   (inconclusive)
repeat_ngram_rate     AUC 0.373   (inconclusive)
hangul_ratio          AUC 0.815   (reported without a direction)
```

**This is not a refutation.** It is a comparison between citizen comments and agency
notices on one side, and poster copy and video scripts on the other. Register differences
between document types dominate completely. With 18 machine documents, the confidence
interval swallows the point estimate.

The **direction table in `src/looks_like_korean/metrics.py` was deliberately left
uncorrected.** Flipping it to match an untrustworthy number would be the exact error this
log exists to prevent. The directions remain labelled as hypotheses in the source.

## P1 — next

1. Collect ≥ 20 machine documents in **one** genre, matched to ≥ 20 human documents in that
   same genre. 제안서 is the first candidate: 40 human documents already collected.
2. Re-run with `--genre`. Only a value that survives a single-genre comparison counts.
3. If the single-genre AUC still contradicts H2, the honest move is to abandon H2 and
   report that — not to re-define `uniformity_index` until it agrees.

## Why the engine refuses to answer

`research/measure.py` gates on sample size and genre overlap. A metric library that cannot
tell you your evidence is insufficient is a toy. It is also the only reason the 0.700 above
is labelled worthless instead of becoming the project's headline.

## Korean text pitfalls found while building the classifier

1. **`ㅂ니다` does not exist in the string.** `합니다` is `합` + `니다`, so a `ㅂ니다`
   substring match never fires, and NFD decomposition does not help because the 받침 becomes
   a standalone jamo. `unicodedata.decomposition()` returns an empty string for Hangul
   (algorithmic, not compatibility). Read the last jamo in NFD form instead. Missing this
   silently demoted every ordinary 합쇼체 sentence to `plain` and killed the headline metric.
2. **`-(으)ㅁ` nominal endings collide with Sino-Korean and loanwords.** A 받침-based rule
   pulls in `야함`(夜勤) `부담` `상금` `0점` `제점`(點) `그램` `랫/platform`. An explicit
   ending list misses forms; the 받침 rule needs a blocklist. Residual error is unavoidable.
3. **`-니까` is both causal and interrogative**, and `-ㅂ니다` is written identically for
   합쇼체 and 해라체-derived forms (`있습니다` vs `읽습니다` vs `알립니다`, which is both
   `알리+ㄴ다` and `알리+ㅂ니다`). Surface form alone cannot decide; the interrogative case
   is separable only by punctuation.

## Corpus policy

The working corpus contains real citizens' participation comments and public agency
notices. It is **not** in this repository and must never be. Published examples
(`eval/examples.json`) are entirely self-authored — that restriction is what keeps this
publishable, and contributors must preserve it.
