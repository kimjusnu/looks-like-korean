# Contributing

## The one thing that would help most

**A genre-matched labelled corpus.** One genre, both labels, at least 20 documents each.
Without it, nothing in `docs/RESEARCH.md` moves past "not measurable". The human side of
the 제안서 genre is already collected; the machine side is missing.

## Rules

**Never publish real people's text.** The working corpus contains citizens' participation
comments and agency notices. `eval/examples.json` is self-authored, and any example you add
must be too. If you cannot publish it, contribute the measurement, not the document.

**Do not reorder the direction table to fit a number.** The assumed direction of each metric
(`metrics.py`, top of file) is a hypothesis. Flipping it because a measurement you do not
trust agrees with you is the failure mode this project was built to avoid. Write it in
`docs/RESEARCH.md` instead, with the caveats attached.

**A metric needs a falsifier, not just a name.** New metric proposals must state what result
would make you delete it. "uniformity_index" is only trustworthy if someone can measure the
case where it fails.

**Determinism is a feature.** Standard library only. No network. No model calls. If your
contribution needs an LLM to run, it is a different project — say so in the issue instead
of merging it here.

## Running things

```bash
python -m unittest discover -s tests
python -m looks_like_korean score <file.md>
python research/measure.py --corpus <dir> --report docs/MEASUREMENT.md
```

Windows users: set `PYTHONPATH=src` when running from source.

## Adding an example pair

Append to `eval/examples.json`, then check it actually moved the metric:

```bash
set PYTHONPATH=src
python -c "import json,io; from looks_like_korean.metrics import analyze; \
d=json.load(io.open('eval/examples.json',encoding='utf-8')); \
[print(e['id'], round(analyze(e['before']).uniformity_index,3), \
        round(analyze(e['after']).uniformity_index,3)) for e in d['examples']]"
```

`after` should sit lower than `before`. If it does not, either the rewrite is not doing
what you think, or the metric does not capture what you think it captures. Both are worth
an issue. Populate `register_mix_*` from the classifier's actual output, not from
intention — they are used to catch exactly that mismatch.

## 한국어

규칙 요약은 [`docs/RESEARCH.md`](docs/RESEARCH.md) 끝에 있다. **판정은 사람이 한다.**
계측값이 사람의 읽힘과 어긋난 사례가 이 프로젝트에서 가장 값진 데이터다.
