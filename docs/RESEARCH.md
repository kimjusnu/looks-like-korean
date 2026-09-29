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

## P1 attempt 1 — genre selection and what it does *not* control (2026-09-29)

The P0 log above closed with "collect ≥ 20 machine documents in one genre". This entry
records the genre choice, the evidence for it, and — more importantly — the axes that
the choice leaves uncontrolled. Written **before** the machine corpus was generated, so
the decision cannot be reverse-fitted to the number it produces.

### Genre: `공공서비스제안서` (40 human documents already collected)

**Why this genre.** It is the only human genre in the corpus with more than 20 documents,
and the 40 documents share a submission template rather than merely a broad topic. Template
markers counted across the 40 files:

| marker | documents |
|---|---|
| `기대효과` | 15 |
| `내용` (제안 본문 섹션) | 14 |
| `추진배경 및 목적` | 10 |
| `구분` / `항목` table header | 20 / 13 |
| `협력 방안` | 9 |
| `주요 역할` · `기능 설명` · `단계` | 6 · 6 · 9 |

So this is one document *kind* — a written proposal to a public agency, filling a
competition template, arguing that a public service should be built and changed — not a
bag of documents that happen to contain the word 제안서. That is the same relation the
machine side must be matched on, and it is the relation PLAN.md §2 asks for
("같은 장르·같은 주제").

**Human-side spread, measured (`--genre 공공서비스제안서`, no machine side):**

| quantity | min | median | max |
|---|---|---|---|
| characters | 952 | 3,008 | 16,441 |
| sentences | 12 | 62.5 | 451 |
| distinct registers K | 1 | 3 | 6 |
| `uniformity_index` (mean) | 0.011 | — | 1.000 (mean 0.466) |

Two of the 40 are K=1, 100% 합쇼체 documents; two are ~80–95% `none` documents that are
almost entirely table cells and bullet fragments. The human side is therefore *not*
narrow — it is wide, which is the point: a genre-matched human sample should contain
prose-heavy, table-heavy, 합쇼체-only and fragment-heavy documents alike.

### What is controlled, and what is not

**Controlled** — 문서 종류 (proposal), 문서 목적 (argue for a public service to be
built/changed), 독자 (a public agency / selection panel), 제출 문맥 (a public-service
proposal competition with a sectioned template).

**Not controlled, and I could not control it:**

1. **주제.** 20+ documents per topic do not exist on the human side. The 40 cover at
   least 30 distinct service ideas (키즈카페 대안 · 은둔 청년 · 소상공인 생존 · 장애인
   채용–이동 · 도서관 · 수요응답형 교통 · 시니어 인지훈련 · 귀농귀촌 정착 · 감정 기록 ·
   지역 레이더 · 스마트폰 동작검사 · 지역 상권 활성화 …), 1–2 documents each. So topic
   is left **free on both sides**: every machine document proposes a different service.
   This is a real limit on how far a positive result can be generalised, not a formality.
2. **분량.** Human 952–16,441 chars vs machine 1,000–2,500 (per the P1 brief). Human
   documents were left as they are; the brief forbids normalising them. The overlap region
   is 1,000–2,500 chars, which 22 of the 40 human documents fall inside.
3. **기술 깊이.** A subset of the human documents are engineering-heavy (API, MSA, Redis,
   Next.js, UI flow); others are plain prose with no technology at all. Machine documents
   will be written as a model writes a proposal for this genre, which is technology-aware
   by default. If the metrics lean on that, the log says so.
4. **Extraction artefact.** The human files are hard-wrapped at 53–97 columns (HWP/PDF
   extraction), so a paragraph joins across a wrap and a word split at the wrap point
   becomes two 어절. Machine files are markdown and never wrapped. This inflates human
   어절 counts by roughly 10–15%, near-proportionally. `sentence_len_gini` and
   `sentence_len_logstd` are both invariant to a common multiplicative factor, so H3
   metrics are largely insulated; `max_same_register_run` and `repeat_ngram_rate` are not
   length-normalised at all and are the ones to distrust. Recorded here rather than
   silently patched, because the human side may not be modified.
5. **Proposal count.** The 40 are a *winning-entry* sample (`source_kind=winning_entry`),
   i.e. pre-filtered for quality. Machine drafts are not. If anything this biases the
   comparison in the machine direction being *harder* to separate from — i.e. a positive
   result is not explained by the human side being weak.

**Machine side plan.** Existing proposal-family machine documents (공공데이터제안서 1,
공공서비스기획서 3, 기관제안서 2, 시민제안서 1) were inspected. All 7 are kept at their
existing genre labels and their MANIFEST rows are untouched — they are different document
kinds (기획서 is a competition idea pitch, 기관/시민제안서 has an institution-specific
brief) and re-labelling them into this genre would be relabelling, not collecting. New
documents are written instead.

### P1 attempt 1 — result

24 new machine documents, `genre=공공서비스제안서`, 1,398–1,625 chars each, one distinct
public-service idea per document, no real institution or person named. Full report:
`research-private/P1-MEASUREMENT.md`.

```
python research/measure.py --corpus research-private/corpus --genre 공공서비스제안서
→ 표본: human 40건 / machine 24건

hangul_ratio          AUC 1.000  95% 1.00–1.00
register_switch_rate  AUC 0.931  95% 0.85–0.99
max_same_register_run AUC 0.015
repeat_ngram_rate     AUC 0.040
uniformity_index      AUC 0.056
sentence_len_gini     AUC 0.139
nominal_ratio         AUC 0.147
nominal_position      AUC 0.350
sentence_len_logstd   AUC 0.482
```

**The gate passes, and the pass is not evidence for anything.** Both halves of that sentence
matter, so they are separated here.

### 1. `hangul_ratio` AUC 1.000 is a character-set artifact, and partly my own doing

Per-document script composition, this genre only:

| | Latin chars / 1,000 chars | Han chars | `hangul_ratio` |
|---|---|---|---|
| human (40) | 82.4 | 0.03 | mean 0.873, min 0.606 |
| machine (24) | **0.0** | 0.0 | **1.000 in every document** |

The separation is perfect because the machine side contains literally zero Latin and zero
Han characters, while the human proposals are full of `API` `UI` `MSA` `DB` `LLM` `JSON`
`Next.js` `GitHub Actions` plus `<링크1>`-style mask tokens. The human minimum (0.606) sits
above the machine maximum (1.000 = the ceiling, reached 24/24), so no overlap is possible.

This is exactly the failure mode `metrics.py` warned about when it marked `hangul_ratio`
**neutral**: the name and the hypothesis do not match, and the value separates documents by
script mix, not by authorship. It supports none of H1–H4. It is also **partly a confound I
introduced**: a model writing a proposal in this genre would normally name its own stack
(`API`, `DB`, `알림`), and I wrote the 24 documents in near-pure Hangul. The human side's
token density is a property of the genre; the machine side's absence of it is a property of
my drafting. A re-run with the machine side carrying a comparable density of technical
tokens is the obvious next check, and it has not been done.

### 2. Every rhythm metric came out **reversed**

| hypothesis | predicted direction | measured | AUC |
|---|---|---|---|
| H2 uniformity ↑ = machine | machine > human | machine 0.080 < human 0.466 | **0.056** |
| H2 switch ↑ = human | human > machine | human 0.398 < machine 0.771 | **0.931 (wrong way)** |
| H2 max same-run ↑ = machine | machine > human | — | **0.015** |
| H2 repeat-ngram ↑ = machine | machine > human | — | **0.040** |
| H3 gini ↑ = human | human > machine | human 0.403 > machine 0.323 | 0.139 |
| H3 logstd ↑ = human | — | — | 0.482 (noise) |
| H4 nominal ratio ↑ = human | human > machine | human 0.065 > machine 0.008 | 0.147 |

Note that `measure.py`'s `verdict()` sorts on distance from 0.5 and does not consult the
metric's declared direction, so `register_switch_rate 0.931` is printed as 「게이트 통과」
even though the direction table says it should be *high for humans*. Read with directions
applied, **H2, H3 and H4 are all contradicted in this corpus, H2 most strongly.**

### 3. The most likely cause is document *structure*, not authorship

The human side of this genre is fragment-structured. `생략(none)` is **68.5% of human
sentences** (machine: 32.8%), and the fragments are not truncated prose — they are headings
and table cells that the HWP extraction preserved as text:

```
디지털 기반 국가 사회현안 해결 서비스 ‘아이디어 발굴(프로토타입 개발)’ 수상작 내 용
시스템 종합 구성도
시니어들의 인지프로그램을 위한 AI기반 RAG리포팅 콘텐츠 분석 및 관리 솔루션
① 인지프로그램 구성
```

Human documents average 2.1 sentences per block against the machine side's 1.3, because a
hard-wrapped line that begins with a bullet marker becomes its own block and therefore its
own pseudo-sentence. The `none` mass then dominates the register distribution, which is
precisely what `uniformity_index` and `register_switch_rate` read. The engine is
substantially measuring **prose-vs-template layout**, and a model writing the same brief
writes a sentence per bullet.

Renormalising away the fragments partly rescues H2: among sentences that carry a real
ending, 합쇼체 is 68% on the machine side versus 44% on the human side. So the
「기계 글은 합쇼체로 통일된다」 half of H2 survives; the headline metric, which is dominated
by `none`, reports its opposite. That is a metric-design failure, not a hypothesis failure,
and it is the finding worth carrying into the redesign.

### What this attempt does and does not establish

- It does **not** support H1–H4. No rhythm metric separated in the predicted direction.
- It **does** clear the mechanical gate, via a metric the project had already declared
  unusable for direction. The gate as written in `measure.py` cannot tell that difference;
  per the falsification rule in `PLAN.md` §1, the honest verdict is **지표 재설계**, not 진행.
- Confounds not removed and not removable by argument: 주제 (§ above), 분량 952–16,441 vs
  1,398–1,625, 기술 깊이, the human-side hard-wrap fragmenting described above, and the
  winning-entry-only human sample. `--max-sentences` was **not** added: capping length would
  not remove the `none` mass, which is a fragmentation problem, not a length problem.
