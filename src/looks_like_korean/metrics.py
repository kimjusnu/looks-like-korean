"""metrics.py — 지표 계산.

모든 지표는 `Metric` 을 돌려준다. `Metric.value` 가 float 이고 `Metric.detail`
에 근거 숫자를 그대로 실어 둔다(디버깅 가능). 같은 입력 → 같은 출력.

============================================================================
지표별 방향 표의 근거
============================================================================
방향(human / machine / neutral)은 **가정**이 아니라 아래 가설에서 온다.
research-private/PLAN.md 가 이 저장소의 근거 문서다.

* H2 「기계 글은 종결 레지스터가 문서 전체에서 하나로 통일된다(합쇼체 100% 등).
   사람은 2~4개 레지스터를 교차한다.」 → uniformity_index ↑ = 기계.
* H2 의 연장 + E-2 계열(동일 어미의 기계적 반복) → max_same_register_run ↑ = 기계,
  repeat_ngram_rate ↑ = 기계.
* H2 「사람은 2~4개 레지스터를 교차한다」 → register_switch_rate ↑ = 사람.
* H3 「사람은 극단 길이가 섞인다(3어절 단문 + 40어절 장문). 기계는 준정규에 가깝다.
   → 문장 길이 로그분포의 Gini 계수」 → sentence_len_gini ↑ = 사람.
  로그 표준편차는 같은 가정(H3)에서 나온다. 준정규 → 분산이 작고 극단치가
  적으므로 logstd 도 작다.
* H4 「명사형 종결이 사람 글엔 비의도적 박자로 나타난다」 → nominal_ratio ↑ = 사람.
  단 **위치**(nominal_position)에는 방향이 없다. H4 는 비율만 말한다.
  「기계 글엔 형식적 결론 구간에만 나타난다」 는 위치 가설이긴 하지만
  계측 결과로 뒷받침되기 전까지 방향 표시는 하지 않는다.
* hangul_ratio 는 **방향 표시에 부적합**하다. 「한글이 아닌 문자 비중」 라는
  설명과 이름이 서로 다르고, 어느 쪽이 사람 쪽인지 가설이 없다.
  → neutral. 대신 한자 비율과 영문 비율을 성분으로 따로 뽑아 근거에 넣는다.

가설이 없는 지표에는 방향을 붙이지 않는다. 근거 없는 방향 표시는 금지.

============================================================================
2026-09-28 실측 — 위 방향표는 아직 확인되지 않았다
============================================================================
아래는 위 표를 근거로 하라는 지시에 따라 H2~H4 를 **가설로만** 옮긴 것이다.
같은 날 저장소의 `research-private/corpus/` (human 329 / machine 18 문서) 를
읽기 전용으로 돌려 확인한 결과, 9개 중 **7개가 역전**했다.

    uniformity_index      AUC 0.700  human 0.616 > machine 0.397   ← H2 반대
    register_switch_rate  AUC 0.308  human 0.291 < machine 0.460   ← H2 반대
    sentence_len_gini     AUC 0.367                              ← H3 반대
    sentence_len_logstd   AUC 0.352                              ← H3 반대
    nominal_ratio         AUC 0.268                              ← H4 반대
    max_same_register_run AUC 0.476   (무판정)
    repeat_ngram_rate     AUC 0.373   (무판정)
    hangul_ratio          AUC 0.815                              (중립이라 미사용)

**이 실측으로 방향표를 고치지 않았다.** 방향표는 가설이고, 가설 검증과
지표 목록 재설계는 PLAN.md §1 의 반증 절차에 따른 P0 결정이다. 다만
「방향 열」 을 정정 사실처럼 읽으면 안 된다는 뜻이므로 여기에 남긴다.

다만 이 수치를 **반증으로 읽어서는 안 된다.** 코퍼스가 장르 대칭이 아니다.
human 329건의 대부분은 참여 의견 221건과 공고문 75건(=불릿 나열)이고,
machine 은 18건뿐이며 장르가 다르다(카드뉴스 대본·광고 영상 대본·포스터 카피).
PLAN.md §2 가 요구한 「같은 장르·같은 주제」 대조가 아니며, 18건에 대한 AUC
는 표본 오차 안에 있다. 결론이 아니라 **측정 설계가 먼저**다.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .eomi import REGISTERS, Sentence, has_hangul, segment

__all__ = ["Metric", "Analysis", "analyze", "METRIC_KEYS"]


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    value: float
    unit: str
    direction: str          # "human" | "machine" | "neutral"
    n: int                  # 이 값을 계산한 표본 수
    detail: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 통계 도구
# ---------------------------------------------------------------------------

def _gini(values: Iterable[float]) -> float:
    """Gini 계수. 값이 하나뿐이거나 전부 0 이면 0.0."""
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return 0.0
    total = math.fsum(xs)
    if total <= 0.0:
        return 0.0
    weighted = math.fsum((i + 1) * x for i, x in enumerate(xs))
    return (2.0 * weighted) / (n * total) - (n + 1.0) / n


def _pstdev(values: Iterable[float]) -> float:
    """모표준편차(분모 n). 표본이 2개 미만이면 0.0."""
    xs = [float(v) for v in values]
    n = len(xs)
    if n < 2:
        return 0.0
    mean = math.fsum(xs) / n
    return math.sqrt(math.fsum((x - mean) ** 2 for x in xs) / n)


# ---------------------------------------------------------------------------
# 지표
# ---------------------------------------------------------------------------

def uniformity_index(sentences: list[Sentence]) -> Metric:
    """단일화 지수 = 1 − 정규화 엔트로피(종결 레지스터 분포).  ← 헤드라인

    정규화 분모는 **문서에 실제로 나타난 레지스터 수 K** 다.
      * K = 1  → 엔트로피 0 → 1.0 (전부 한 레지스터)
      * K = 4 가 균등 → 엔트로피 ln4 → 0.0 (등장한 레지스터가 완전히 고르게 섞임)
    고정 분모 ln6 을 쓰면 「4레지스터 균등」 이 0.226 이 남아 0 근처라는
    기대와 어긋나고, K=1 일 때 0으로 나누기가 생긴다. 관측 K 로 잡는다.
    """
    counts = {r: 0 for r in REGISTERS}
    for s in sentences:
        counts[s.register] += 1
    total = sum(counts.values())
    present = {r: c for r, c in counts.items() if c > 0}
    if total == 0:
        return Metric("uniformity_index", "단일화 지수", 0.0, "0–1", "machine", 0,
                      {"k": 0, "distribution": {}})
    k = len(present)
    if k <= 1:
        return Metric("uniformity_index", "단일화 지수", 1.0, "0–1", "machine", total,
                      {"k": k, "distribution": present, "note": "레지스터 1종"})
    entropy = -math.fsum(
        (c / total) * math.log(c / total) for c in present.values()
    )
    value = 1.0 - entropy / math.log(k)
    return Metric("uniformity_index", "단일화 지수", value, "0–1", "machine", total,
                  {"k": k, "entropy": entropy, "max_entropy": math.log(k),
                   "distribution": dict(sorted(present.items()))})


def max_same_register_run(sentences: list[Sentence]) -> Metric:
    """동일 레지스터가 최대로 연속되는 문장 수."""
    best = 0
    run = 0
    prev: str | None = None
    where = -1
    for s in sentences:
        if s.register == prev:
            run += 1
        else:
            run, prev = 1, s.register
        if run > best:
            best, where = run, s.index
    return Metric("max_same_register_run", "최대 동일 레지스터 연속", float(best), "문장",
                  "machine", len(sentences), {"at_sentence": where, "end_register": prev})


def register_switch_rate(sentences: list[Sentence]) -> Metric:
    """연속 3문장 창 안에서 레지스터 전환이 일어나는 창의 비율."""
    n = len(sentences)
    if n < 3:
        return Metric("register_switch_rate", "레지스터 전환율(3창)", 0.0, "0–1",
                      "human", n, {"windows": 0, "note": "문장 3개 미만 — 측정 불가"})
    windows = n - 2
    switched = 0
    for i in range(windows):
        trio = sentences[i : i + 3]
        if len({s.register for s in trio}) > 1:
            switched += 1
    switches = sum(
        1 for i in range(n - 1) if sentences[i].register != sentences[i + 1].register
    )
    return Metric("register_switch_rate", "레지스터 전환율(3창)", switched / windows,
                  "0–1", "human", windows,
                  {"windows": windows, "switched": switched, "total_switches": switches})


def sentence_len_gini(sentences: list[Sentence]) -> Metric:
    """어절 수 분포의 Gini 계수."""
    lens = [float(s.eojeol) for s in sentences]
    return Metric("sentence_len_gini", "문장길이 Gini", _gini(lens), "0–1", "human",
                  len(lens), {"min": min(lens) if lens else 0,
                               "max": max(lens) if lens else 0,
                               "mean": (sum(lens) / len(lens)) if lens else 0.0})


def sentence_len_logstd(sentences: list[Sentence]) -> Metric:
    """문장 길이(어절 수) 로그의 모표준편차."""
    logs = [math.log(s.eojeol) for s in sentences if s.eojeol > 0]
    return Metric("sentence_len_logstd", "문장길이 log 표준편차", _pstdev(logs), "ln 어절",
                  "human", len(logs), {"min_log": min(logs) if logs else 0.0,
                                       "max_log": max(logs) if logs else 0.0})


_NOMINAL_BINS = ("0–20%", "20–40%", "40–60%", "60–80%", "80–100%")


def nominal_ratio(sentences: list[Sentence]) -> Metric:
    """명사형 종결 비율."""
    total = len(sentences)
    hits = [s for s in sentences if s.register == "nominal"]
    return Metric("nominal_ratio", "명사형 종결 비율",
                  (len(hits) / total) if total else 0.0, "0–1", "human", total,
                  {"hits": len(hits), "endings": sorted(
                      {s.ending for s in hits if s.ending})})


def nominal_position(sentences: list[Sentence]) -> Metric:
    """명사형 종결의 문단 내 상대 위치. 값 = 평균 위치, detail 에 히스토그램.

    위치 = (문단 내 순번) / (문단 문장 수 − 1). 0 = 문단 맨 앞, 1 = 맨 뒤.
    문장이 하나뿐인 문단은 0.0 으로 본다(앞이면서 뒤다).
    """
    sizes: dict[int, int] = {}
    for s in sentences:
        sizes[s.paragraph] = sizes.get(s.paragraph, 0) + 1

    positions: list[float] = []
    hist = {b: 0 for b in _NOMINAL_BINS}
    for s in sentences:
        if s.register != "nominal":
            continue
        n = sizes[s.paragraph]
        rel = 0.0 if n <= 1 else s.pos / (n - 1)
        rel = min(1.0, max(0.0, rel))
        positions.append(rel)
        b = min(4, int(rel * 5))
        hist[_NOMINAL_BINS[b]] += 1

    value = (sum(positions) / len(positions)) if positions else 0.0
    return Metric("nominal_position", "명사형 위치(문단 내)", value, "0–1", "neutral",
                  len(positions), {"histogram": hist, "positions": positions[:40]})


_LATIN_CH = re.compile(r"[A-Za-z]")
_HAN_CH = re.compile(r"[一-鿿㐀-䶿]")


def hangul_ratio(text: str) -> Metric:
    """한글 음절 비중(한글·한자·영문 문자만 분모에 넣는다).

    설명서의 「한글이 아닌 문자 비중」 과 이름이 엇갈리므로 **두 값을 모두** 낸다.
      * hangul_ratio      = 한글 / (한글 + 한자 + 영문)
      * nonhangul_ratio   = 1 − hangul_ratio   (설명서의 그 지표)
    방향 표시는 neutral — 어느 쪽이 사람 쪽인지 가설이 없다.
    """
    hangul = len(re.findall(r"[가-힣]", text))
    han = len(_HAN_CH.findall(text))
    latin = len(_LATIN_CH.findall(text))
    denom = hangul + han + latin
    value = (hangul / denom) if denom else 0.0
    return Metric("hangul_ratio", "한글 문자 비중", value, "0–1", "neutral", denom,
                  {"hangul": hangul, "han": han, "latin": latin,
                   "nonhangul_ratio": 1.0 - value,
                   "han_ratio": (han / denom) if denom else 0.0,
                   "latin_ratio": (latin / denom) if denom else 0.0})


def repeat_ngram_rate(sentences: list[Sentence], n: int = 4) -> Metric:
    """동일 종결 표기가 4연속 출현(4-gram)하는 비율.

    종결 표기 키 = eomi 의 `ending` (「합니다만」 ≠ 「합니다」,
    「했다」 ≠ 「있다」 처럼 어미별로 갈린다).
    어미가 없는 「생략」 마디는 '∅' 키를 쓴다 — 어미 없는 줄이 길게 이어지는 것
    자체가 하나의 리듬(불릿 나열)이므로 지표에서 빼면 안 된다.
    """
    keys = [s.ending if s.ending else "∅" for s in sentences]
    if len(keys) < n:
        return Metric("repeat_ngram_rate", f"종결 {n}-gram 반복률", 0.0, "0–1", "machine",
                      0, {"windows": 0, "note": f"문장 {n}개 미만 — 측정 불가"})
    windows = [tuple(keys[i : i + n]) for i in range(len(keys) - n + 1)]
    seen: dict[tuple[str, ...], int] = {}
    for w in windows:
        seen[w] = seen.get(w, 0) + 1
    repeated = sum(c for c in seen.values() if c > 1)
    top = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    return Metric("repeat_ngram_rate", f"종결 {n}-gram 반복률",
                  repeated / len(windows), "0–1", "machine", len(windows),
                  {"windows": len(windows), "repeated": repeated,
                   "distinct": len(seen),
                   "top": ["+".join(k) + f"×{c}" for k, c in top]})


# ---------------------------------------------------------------------------
# 집계
# ---------------------------------------------------------------------------

@dataclass
class Analysis:
    text: str
    sentences: list[Sentence]
    metrics: dict[str, Metric]
    skipped_non_hangul: int
    register_counts: dict[str, int]

    @property
    def n_sentences(self) -> int:
        return len(self.sentences)

    def metric(self, key: str) -> Metric:
        return self.metrics[key]

    def value(self, key: str) -> float:
        return self.metrics[key].value

    def __getattr__(self, name: str) -> float:
        # `analyze(text).uniformity_index` 를 지원한다. 지표명이라 Python 명명 규약에는
        # 맞지 않지만, 사용자에게는 이 형태가 가장 자연스럽다.
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.__dict__["metrics"][name].value
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__} has no metric {name!r}; "
                f"available: {', '.join(sorted(self.__dict__['metrics']))}"
            ) from None

    def __dir__(self) -> list[str]:
        return [*super().__dir__(), *sorted(self.metrics)]


METRIC_FUNCS: tuple[Callable[[list[Sentence], str], Metric], ...] = (
    lambda s, _t: uniformity_index(s),
    lambda s, _t: max_same_register_run(s),
    lambda s, _t: register_switch_rate(s),
    lambda s, _t: sentence_len_gini(s),
    lambda s, _t: sentence_len_logstd(s),
    lambda s, _t: nominal_ratio(s),
    lambda s, _t: nominal_position(s),
    lambda s, _t: hangul_ratio(_t),
    lambda s, _t: repeat_ngram_rate(s),
)

# 리포트 출력 순서 = 고정. 표가 흔들리지 않게 한다.
METRIC_KEYS: tuple[str, ...] = (
    "uniformity_index",
    "max_same_register_run",
    "register_switch_rate",
    "sentence_len_gini",
    "sentence_len_logstd",
    "nominal_ratio",
    "nominal_position",
    "hangul_ratio",
    "repeat_ngram_rate",
)


def analyze(text: str) -> Analysis:
    """원고 → 전 지표. 결정론적(같은 입력 → 같은 출력)."""
    sentences = segment(text)
    skipped = sum(1 for line in text.splitlines() if line.strip() and not has_hangul(line))
    counts = {r: 0 for r in REGISTERS}
    for s in sentences:
        counts[s.register] += 1

    metrics = {m.key: m for m in (f(sentences, text) for f in METRIC_FUNCS)}
    return Analysis(
        text=text,
        sentences=sentences,
        metrics=metrics,
        skipped_non_hangul=skipped,
        register_counts=counts,
    )

