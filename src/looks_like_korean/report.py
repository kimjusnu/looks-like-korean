"""report.py — 출력 포맷. 관보 스타일(정렬 표 · 소수 3자리 · 단위 표기).

사람용 텍스트 리포트와 기계용 JSON 두 갈래만 낸다.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Iterable

from .eomi import REGISTER_LABEL, REGISTERS
from .metrics import METRIC_KEYS, Analysis, Metric

__all__ = ["render_score", "render_compare", "to_json", "analysis_to_dict"]

_DECIMALS = 3

# 방향 표기. 근거는 metrics.py 모듈 docstring 에 있다.
_DIRECTION_MARK = {
    "human": "사람 ↑",
    "machine": "기계 ↑",
    "neutral": "중립",
}


# ---------------------------------------------------------------------------
# 동아리아 폭을 고려한 표 정렬
# ---------------------------------------------------------------------------

def _width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, width: int, align: str = "<") -> str:
    gap = max(0, width - _width(text))
    if align == ">":
        return " " * gap + text
    if align == "^":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def _truncate(text: str, width: int) -> str:
    if _width(text) <= width:
        return text
    out = ""
    for ch in text:
        if _width(out + ch) > width - 1:
            return out + "…"
        out += ch
    return out


def _rule(width: int, ch: str = "─") -> str:
    return ch * width


def _fmt_value(metric: Metric) -> str:
    if metric.key == "max_same_register_run":
        return f"{metric.value:.0f}"
    return f"{metric.value:.{_DECIMALS}f}"


def _fmt_delta(value: float) -> str:
    return f"{value:+.{_DECIMALS}f}"


# ---------------------------------------------------------------------------
# 근거 요약 (detail → 한 줄)
# ---------------------------------------------------------------------------

def _evidence(metric: Metric) -> str:
    d = metric.detail
    if not d:
        return ""
    if metric.key == "uniformity_index":
        dist = d.get("distribution", {})
        body = " · ".join(
            f"{REGISTER_LABEL.get(k, k)} {v}" for k, v in dist.items()
        )
        return f"레지스터 {d.get('k', 0)}종 — {body}"
    if metric.key == "max_same_register_run":
        return f"끝 레지스터 {REGISTER_LABEL.get(d.get('end_register') or '', '—')} · 시작 문장 #{d.get('at_sentence', 0)}"
    if metric.key == "register_switch_rate":
        return f"창 {d.get('windows', 0)}개 중 {d.get('switched', 0)}개 전환"
    if metric.key == "sentence_len_gini":
        return f"어절 최솟값 {d.get('min', 0):.0f} · 최댓값 {d.get('max', 0):.0f} · 평균 {d.get('mean', 0):.1f}"
    if metric.key == "sentence_len_logstd":
        return f"ln 범위 {d.get('min_log', 0):.2f} ~ {d.get('max_log', 0):.2f}"
    if metric.key == "nominal_ratio":
        ends = d.get("endings", [])
        tail = " · " + " ".join(ends[:6]) if ends else ""
        return f"{d.get('hits', 0)}문장 / {metric.n}문장{tail}"
    if metric.key == "nominal_position":
        hist = d.get("histogram", {})
        body = " ".join(f"{k}:{v}" for k, v in hist.items())
        return body or "명사형 종결 없음"
    if metric.key == "hangul_ratio":
        return (f"한글 {d.get('hangul', 0)} · 한자 {d.get('han', 0)} · 영문 {d.get('latin', 0)}"
                f" (한글이 아님 {d.get('nonhangul_ratio', 0):.{_DECIMALS}f})")
    if metric.key == "repeat_ngram_rate":
        top = d.get("top", [])
        return "상위 " + " · ".join(top) if top else "표본 없음"
    return ""


def _header(name: str, analysis: Analysis) -> list[str]:
    return [
        f"■ {name}",
        f"  마디 {analysis.n_sentences}개 분석"
        f" · 한글 없는 줄 {analysis.skipped_non_hangul}개 제외"
        f" · 문자 {len(analysis.text):,}자",
        "",
    ]


def _distribution_line(analysis: Analysis) -> list[str]:
    total = max(1, sum(analysis.register_counts.values()))
    label_w = max(_width(REGISTER_LABEL[r]) for r in REGISTERS)
    parts = []
    for r in REGISTERS:
        c = analysis.register_counts[r]
        bar = "█" * round(40 * c / total)
        parts.append(f"  {_pad(REGISTER_LABEL[r], label_w)}{_pad(str(c), 5, '>')}  {_pad(bar, 40)}")
    return ["종결 레지스터 분포", *parts, ""]


def _metric_table(analyses: Iterable[Analysis], labels: Iterable[str]) -> list[str]:
    analyses = list(analyses)
    labels = list(labels)

    head = ["지표", *labels, "단위", "방향"]
    key_w = max(_width("지표"), max(_width(k) for k in METRIC_KEYS))
    val_ws = [
        max(_width(head[i + 1]), max(_width(_fmt_value(a.metrics[k]))
                                     for a in analyses for k in METRIC_KEYS))
        for i in range(len(analyses))
    ]
    unit_w = max(_width("단위"), max(_width(analyses[0].metrics[k].unit) for k in METRIC_KEYS))
    dir_w = max(_width("방향"), max(_width(_DIRECTION_MARK[analyses[0].metrics[k].direction])
                                    for k in METRIC_KEYS))
    widths = [key_w, *val_ws, unit_w, dir_w]
    total_width = sum(widths) + 2 * (len(widths) - 1)

    out = [
        "  ".join(
            [
                _pad(head[0], widths[0]),
                *[_pad(head[i + 1], widths[i + 1], ">") for i in range(len(analyses))],
                _pad(head[-2], widths[-2], ">"),
                _pad(head[-1], widths[-1], ">"),
            ]
        ).rstrip(),
        _rule(total_width),
    ]
    for key in METRIC_KEYS:
        first = analyses[0].metrics[key]
        cells = [_pad(key, widths[0])]
        for i, a in enumerate(analyses):
            cells.append(_pad(_fmt_value(a.metrics[key]), widths[i + 1], ">"))
        cells.append(_pad(first.unit, widths[-2], ">"))
        cells.append(_pad(_DIRECTION_MARK[first.direction], widths[-1], ">"))
        out.append("  ".join(cells).rstrip())
    out.append(_rule(total_width))
    return out


def _evidence_table(analyses: Iterable[Analysis]) -> list[str]:
    analyses = list(analyses)
    w_key = max(_width(k) for k in METRIC_KEYS)
    out = ["", "근거"]
    for key in METRIC_KEYS:
        out.append(f"  {_pad(key, w_key)}  {_truncate(_evidence(analyses[0].metrics[key]), 96)}")
    return out


# ---------------------------------------------------------------------------
# 공개 렌더러
# ---------------------------------------------------------------------------

def render_score(analysis: Analysis, name: str = "입력") -> str:
    lines = [
        "looks-like-korean · 한국어 리듬 계측",
        "",
        *_header(name, analysis),
        *_distribution_line(analysis),
        *_metric_table([analysis], ["값"]),
        *_evidence_table([analysis]),
        "",
        "※ 방향 열은 '값이 어느 쪽인지'를 뜻한다. 중립은 가설이 없어 방향을 붙이지 않은 지표다.",
    ]
    return "\n".join(lines)


def render_compare(a: Analysis, b: Analysis, name_a: str, name_b: str) -> str:
    lines = [
        "looks-like-korean · 두 원고 비교",
        "",
        *_header(name_a, a),
        *_header(name_b, b),
    ]
    lines += _metric_table([a, b], ["원문", "수정문"])

    key_w = max(_width(k) for k in METRIC_KEYS)
    rows = [f"  {_pad('지표', key_w)}  {_pad('사람 쪽', 26, '^')}  {'Δ':>9}"]
    for key in METRIC_KEYS:
        ma, mb = a.metrics[key], b.metrics[key]
        delta = mb.value - ma.value
        if ma.direction == "neutral":
            verdict = "–  (가설 없음)"
        elif delta == 0.0:
            verdict = "동일"
        elif (delta > 0.0) == (ma.direction == "human"):
            verdict = name_b
        else:
            verdict = name_a
        rows.append(
            f"  {_pad(key, key_w)}  {_pad(verdict, 26, '^')}  {_fmt_delta(delta):>9}"
        )
    lines += ["", "판정", _rule(max(_width(r) for r in rows)), *rows]
    lines += [
        "",
        "※ Δ = 수정문 − 원문. 「사람 쪽」 열은 그 지표에서 사람에 가까운 쪽을 가리킨다.",
        "  방향의 근거는 looks_like_korean/metrics.py 모듈 주석에 있다.",
    ]
    return "\n".join(lines)


def analysis_to_dict(analysis: Analysis, name: str = "입력") -> dict[str, Any]:
    return {
        "name": name,
        "n_sentences": analysis.n_sentences,
        "skipped_non_hangul_lines": analysis.skipped_non_hangul,
        "n_chars": len(analysis.text),
        "register_counts": dict(analysis.register_counts),
        "register_labels": dict(REGISTER_LABEL),
        "metrics": {
            key: {
                "key": m.key,
                "label": m.label,
                "value": round(m.value, _DECIMALS),
                "unit": m.unit,
                "direction": m.direction,
                "n": m.n,
                "detail": m.detail,
            }
            for key, m in ((k, analysis.metrics[k]) for k in METRIC_KEYS)
        },
        "sentences": [
            {
                "i": s.index,
                "register": s.register,
                "ending": s.ending,
                "eojeol": s.eojeol,
                "paragraph": s.paragraph,
                "pos": s.pos,
                "text": s.text,
            }
            for s in analysis.sentences
        ],
    }


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
