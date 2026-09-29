# looks-like-korean

**Deterministic Korean prose measurement. No LLM call, no dependencies.**

A Korean sentence is not "AI-sounding" because of vocabulary. It is sounding mechanical
because every sentence ends the same way. This project measures that, and it refuses to
guess.

```bash
pip install looks-like-korean
looks-like-korean score draft.md
looks-like-korean compare before.md after.md
```

```
# uniformity_index  0.813   ← 1.000 = one sentence-ending register for the whole document
# max_same_register_run  14
# sentence_len_gini  0.284
```

> **한국어**: 한국어 문장이 AI처럼 느껴지는 이유는 어휘가 아니라 **종결어미가 한 가지로
> 통일되어 있기 때문**입니다. 이 도구는 그것을 측정합니다. 추측하지 않습니다.

---

## Status: v0 — the engine works, the hypothesis is not yet proven

This is the important paragraph. Read it before trusting any number.

We built the measurement engine. We then tried to use it to answer the question it was
built for, and **the measurement failed** — not the hypothesis, the measurement design.

| | |
|---|---|
| Engine | 9 metrics, deterministic, 68/68 tests green |
| Corpus | 347 Korean documents, human-labelled and machine-labelled |
| Result | **Not measurable.** The two groups share zero genres |

The corpus holds 221 citizen participation comments and 75 agency notices on the human
side; 18 AI drafts across 14 unrelated genres (poster copy, video scripts) on the machine
side. Running a metric across those compares *register differences between document
types*, not human-versus-machine. A first pass reported `uniformity_index` at AUC 0.700 —
that number is meaningless, and it appeared to **contradict** our own hypothesis, which
is exactly the shape of a result that tempts you into believing it.

So the harness refuses to produce the number:

```
$ python research/measure.py --corpus <dir>

## 측정 불가

- ⛔ 장르 교집합 0 — 비교 대상이 같은 문종이 아니다

**AUC 을 내지 않는다.** 두 그룹이 같은 조건에서 나오지 않았으므로
어숫값을 넣어도 장르 차이 또는 표본 오차를 재는 것이 된다.
```

A metric library that cannot tell you your evidence is insufficient is a toy. This one
can. The P0 gate is written down in [`docs/RESEARCH.md`](docs/RESEARCH.md) and the next
step is building a genre-matched corpus, not shipping a claim.

---

## Three pairs

Full set of 9 in [`docs/DEMO.md`](docs/DEMO.md), machine-readable in
[`eval/examples.json`](eval/examples.json). All self-authored.

| | before (machine-flavoured) | after (human-flavoured) |
|---|---|---|
| **기념`** | 회의 시간이 변경되어 **안내드립니다**. 이번 주 목요일 회의는 오후 3시에서 오전 11시로 **앞당겨집니다**. 장소는 3층 소회의실로 **변경되었습니다**. … 안내해 주셔서 감사합니다. | 회의 시간이 갑자기 앞당겨져서 먼저 공지해 **둡니다**. 이번 주 목요일 건만 11시로 당겼고, 나머지 주는 **그대로예요**. … 시간이 안 되는 분만 **있나요?** 네, 그럼 이대로 **갑니다**. |
| | `~습니다` ×6 · uniformity **1.000** | `~습니다` ×4 / `~해요` ×2 / `~나요` ×1 · uniformity **0.130** |

| | before | after |
|---|---|---|
| **제안서**<br>ex-03 | 아파트 단지 앞 보행로 개선 방안을 제안드립니다. 현재 해당 구간은 포장 파손이 심하고 야간 조도가 부족한 상황입니다. … 아무리 조명을 개선하더라도 포장 파손이 계속되면 효과가 제한적이라는 점에 유의할 필요가 있습니다. 관리사무소 검토 후 반영해 주시면 감사하겠습니다. | 단지 앞 보행로 좀 봐 주시겠어요? 저녁에 내려갈 때마다 어두워서 불안한데, 가로등 하나가 안 들어와요. 포장도 벌써 몇 군데가 들떠서 비 오는 날이면 다 틀어져 버려요. **제일 급한 건 조명이고 포장은 그다음이다.** |
| | uniformity **1.000** | uniformity **0.125** |

| | before | after |
|---|---|---|
| **에세이**<br>ex-06 | 이러한 반복은 무의식적으로 안정감을 부여하는 효과를 낳습니다. **그러나** 이 안정이라는 감각은 정체와 구분하기 어렵습니다. **다만** 이 문제를 개인의 성품으로만 설명하는 태도에는 한계가 있습니다. **결국에는** … | 6분이면 알람 하나로 충분한데 어느새 10분이 되더라. 이게 일상이 되면 별생각을 안 하게 되는 것이 문제임. 솔직히 나는 반씩이라고 생각한다. **이게 정말 개인의 문제일까?** |
| | uniformity **1.000** | uniformity **0.077** |

The point is not "mix in some 해요체 and throw in a question". The point is subtler:

- **ex-01** — the machine announces first and thanks you last. The human states the outcome, drops a question mid-way, and closes on a decision.
- **ex-03** — 「아무리 ~하더라도」 and 「~것에 유의할 필요가 있습니다」 are cushions for postponing a verdict. The human one ends on a judgement. Not naming the obvious is *more* courteous in a Korean proposal.
- **ex-06** — four connective adverbs (「이러한」 「그러나」 「다만」 「결국에는」) organise the logic and kill the rhythm. Dropping them and letting 「~되더라」 「~문제가 아님」 carry the feeling is what a Korean writer actually does. The irregular joints are what stay in memory.

That is rhythm. No vocabulary blacklist reaches it.

---

## The nine metrics

| metric | what it measures |
|---|---|
| `uniformity_index` | `1 − normalised entropy` of the sentence-ending register distribution. **The headline metric.** 1.000 = the whole document uses one register |
| `max_same_register_run` | longest run of identical register, in sentences |
| `register_switch_rate` | how often the register changes inside a 3-sentence window |
| `sentence_len_gini` | inequality of sentence lengths |
| `sentence_len_logstd` | spread of log sentence length |
| `nominal_ratio` / `nominal_position` | nominal endings (`~함`, `~지`, `~기`) and where they land |
| `hangul_ratio` | non-Hangul character share (reported, **no direction assumed**) |
| `repeat_ngram_rate` | repeated sentence-ending n-grams |

`analysis.value('uniformity_index')` and `analysis.uniformity_index` both work.

### Direction is a hypothesis, not a fact

Every metric carries an assumed direction (higher = more machine-like, or the reverse).
Those directions come from a written hypothesis, they are **not** confirmed, and the one
measurement we attempted pointed the other way for 7 of 9. Read
[`docs/RESEARCH.md`](docs/RESEARCH.md) before you quote a direction.

---

## What this is not

* **Not a scrubber.** There is excellent work for that: [`im-not-ai`](https://github.com/epoko77-ai/im-not-ai) (MIT, 5.7k stars) detects translationese, mechanical parallelism and 85 sub-patterns, then edits surgically. Do not rebuild that. This project measures the layer scrubbers cannot reach.
* **Not a prompt.** If a judgement can be made by a model reading the text, it belongs in a model. Everything here is a function of the text and nothing else.
* **Not Korean-plus-three-languages.** Korean only. A name that over-promises is worse than a narrow promise.

---

## Why Korean needs its own metrics

The existing Korean-humanizer's own docs cite *KatFish* and *post-editese* — English-derived
metrics applied to Korean. No public benchmark exists that measures Korean text by its
own distribution. That is the gap: **we do not actually know what a Korean human's
sentence-ending distribution looks like.** Finding out is the project.

## Install

```bash
pip install -e .          # from source, stdlib only, Python ≥ 3.10
python -m unittest discover -s tests
```

## Contribute

Most useful, in order:

1. **A genre-matched labelled corpus.** One genre, both labels, ≥ 20 documents each. This unblocks the entire project.
2. Real Korean documents you are allowed to publish, with their label.
3. Corpus disagreement — cases where a metric and a human reader disagree. The misfires are the interesting part.

Do not open a pull request that reorders the direction table to match a number we could
not trust. See the P0 gate in `docs/RESEARCH.md`.

## License

MIT. See [LICENSE](LICENSE).
