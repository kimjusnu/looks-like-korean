"""facts.py — 윤문 전후 사실 보존 대조.

윤문은 문체만 바꾸고 사실은 그대로 두어야 한다. 이 모듈은 두 원고에서
「바뀌면 안 되는 것」을 뽑아 빠진 것과 새로 생긴 것을 알려 준다.

뽑는 것
-------
number  숫자와 단위: 12% · 1,000명 · 3.5배 · 2026년 (쉼표는 떼고 비교한다)
latin   로마자 낱말: API · GPT-5 · KatFishNet
quote   인용 부호 안의 말: 「…」 · "…" · “…”

새로 생긴 숫자는 윤문 중에 지어낸 사실일 수 있어 특히 위험하다.
한계: 「스무 명」처럼 한글로 쓴 수와 한글 고유명사는 뽑지 못한다.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .findings import Finding

__all__ = ["FACT_KINDS", "FactReport", "extract_facts", "compare_facts"]

FACT_KINDS: tuple[str, ...] = ("number", "latin", "quote")

_KIND_LABEL = {"number": "숫자", "latin": "로마자 낱말", "quote": "인용한 말"}

# 정규식 선택지는 왼쪽부터 맞추므로 긴 단위를 앞에 둔다(「개월」 → 「개」 순서).
_UNIT = (
    r"%|퍼센트|배|조\s?원|억\s?원|만\s?원|천\s?원|원|조|억|만|천|명|건|개월|개|곳|편|회|차|위|등|"
    r"년|월|일|주|시간|시|분(?!기)|초|세|살|자|쪽|"
    r"(?:km|㎞|㎡|kg|GB|MB|TB|m|t)(?![A-Za-z])"
)
_RE_NUMBER = re.compile(rf"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:\s?(?:{_UNIT}))?")
# 단위 없는 한두 자리 정수는 제목·목록 번호일 때가 많아 사실로 세지 않는다.
_RE_BARE_SMALL = re.compile(r"^\d{1,2}$")
_RE_LATIN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9+#.\-]*[A-Za-z0-9+#]")
_RE_QUOTE = re.compile(r"「([^」\n]{1,60})」|\"([^\"\n]{1,60})\"|“([^”\n]{1,60})”")
_RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _norm_number(raw: str) -> str:
    return re.sub(r"[,\s]", "", raw)


def extract_facts(text: str) -> Counter:
    """원고 → Counter[(종류, 값)]."""
    body = _RE_HTML_COMMENT.sub(" ", text)
    numbers = [
        ("number", value)
        for value in (_norm_number(m.group(0)) for m in _RE_NUMBER.finditer(body))
        if not _RE_BARE_SMALL.match(value)
    ]
    latin = [("latin", m.group(0)) for m in _RE_LATIN.finditer(body)]
    quotes = [("quote", next(g for g in m.groups() if g is not None)) for m in _RE_QUOTE.finditer(body)]
    return Counter([*numbers, *latin, *quotes])


def _context(text: str, value: str, width: int = 24) -> str:
    """값이 처음 나오는 자리 앞뒤를 잘라 보여 준다."""
    flat = re.sub(r"\s+", " ", text)
    probe = value if value in flat else value[:1]
    at = flat.find(probe)
    if at < 0:
        return ""
    start, end = max(0, at - width), min(len(flat), at + len(probe) + width)
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


@dataclass(frozen=True)
class FactReport:
    before_total: int
    after_total: int
    missing: tuple[tuple[str, str, int, int], ...]   # (종류, 값, 원문 횟수, 수정문 횟수)
    added: tuple[tuple[str, str, int, int], ...]
    findings: tuple[Finding, ...]

    def header_lines(self) -> list[str]:
        return [
            f"뽑은 사실: 원문 {self.before_total}개 · 수정문 {self.after_total}개",
            f"빠진 것 {len(self.missing)}종 · 새로 생긴 것 {len(self.added)}종",
        ]


def compare_facts(before: str, after: str) -> FactReport:
    a, b = extract_facts(before), extract_facts(after)
    missing = tuple(sorted((k, v, a[(k, v)], b[(k, v)]) for (k, v) in a if a[(k, v)] > b[(k, v)]))
    added = tuple(sorted((k, v, a[(k, v)], b[(k, v)]) for (k, v) in b if b[(k, v)] > a[(k, v)]))
    missing_findings = [
        Finding(
            rule="FACT-MISSING",
            severity="warn",
            message=f"수정문에서 빠진 {_KIND_LABEL[k]}: 「{v}」 (원문 {na}회 → 수정문 {nb}회)",
            suggestion="윤문 중에 지운 것이면 되살립니다. 일부러 뺐다면 그 이유를 적어 둡니다.",
            excerpt=_context(before, v),
        )
        for k, v, na, nb in missing
    ]
    added_findings = [
        Finding(
            rule="FACT-ADDED",
            severity="warn",
            message=f"수정문에 새로 생긴 {_KIND_LABEL[k]}: 「{v}」 (원문 {na}회 → 수정문 {nb}회)",
            suggestion="근거가 있는 사실인지 확인합니다. 근거가 없으면 지웁니다.",
            excerpt=_context(after, v),
        )
        for k, v, na, nb in added
    ]
    return FactReport(
        before_total=sum(a.values()),
        after_total=sum(b.values()),
        missing=missing,
        added=added,
        findings=tuple([*missing_findings, *added_findings]),
    )
