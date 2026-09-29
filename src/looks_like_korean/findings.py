"""findings.py — 검사 결과(Finding)의 형식과 출력.

check 명령의 모든 검사(말투 일치, 문장 패턴 등)는 Finding 목록을 돌려준다.
출력 형식을 한곳에 모아 두어, 검사를 추가해도 리포트 모양이 바뀌지 않게 한다.

심각도
------
warn    근거가 강하고 오탐이 적은 신호. 고치는 것을 기본으로 한다.
review  정상적인 쓰임도 많은 신호. 다시 읽고 판단한다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

__all__ = ["SEVERITIES", "Finding", "render_findings", "findings_to_dict", "has_warnings"]

SEVERITIES: tuple[str, ...] = ("warn", "review")

_SEVERITY_LABEL = {"warn": "경고", "review": "검토"}


@dataclass(frozen=True)
class Finding:
    rule: str            # 규칙 코드. 예: REG-MIX, REG-DOC
    severity: str        # SEVERITIES 중 하나
    message: str         # 무엇이 문제인지 한 문장
    suggestion: str      # 어떻게 고치는지 한 문장
    sentence_index: int | None = None  # 문서 단위 결과면 None
    paragraph: int | None = None
    excerpt: str = ""    # 해당 문장(또는 일부)
    line: int | None = None  # 원문 줄 번호(말버릇 틀처럼 원문에 돌린 검사)


def has_warnings(findings: Iterable[Finding]) -> bool:
    return any(f.severity == "warn" for f in findings)


def _excerpt(text: str, width: int = 60) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def render_findings(findings: list[Finding], header_lines: list[str], name: str) -> str:
    """사람이 읽는 리포트. 머리말(판정 근거) 다음에 결과를 심각도 순으로 늘어놓는다."""
    warn = [f for f in findings if f.severity == "warn"]
    review = [f for f in findings if f.severity == "review"]
    lines = [f"■ {name}", *header_lines, ""]
    if not findings:
        lines.append("걸린 항목이 없습니다.")
        return "\n".join(lines)
    lines.append(f"경고 {len(warn)}건 · 검토 {len(review)}건")
    for f in [*warn, *review]:
        if f.sentence_index is not None:
            where = f"문장 {f.sentence_index + 1}"
        elif f.line is not None:
            where = f"{f.line}번째 줄"
        else:
            where = "문서 전체"
        lines.append("")
        lines.append(f"[{_SEVERITY_LABEL[f.severity]}] {f.rule} · {where}")
        if f.excerpt:
            lines.append(f"  「{_excerpt(f.excerpt)}」")
        lines.append(f"  문제: {f.message}")
        lines.append(f"  고치기: {f.suggestion}")
    return "\n".join(lines)


def findings_to_dict(findings: list[Finding], meta: dict[str, Any]) -> dict[str, Any]:
    return {
        **meta,
        "counts": {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES},
        "findings": [asdict(f) for f in findings],
    }


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
