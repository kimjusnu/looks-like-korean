"""looks-like-korean — 결정론적 한국어 리듬 계측 엔진.

LLM 호출 없음 · 네트워크 없음 · 외부 의존성 없음(표준 라이브러리만).
같은 입력 → 항상 같은 출력.

공개 API
--------
analyze(text)            -> Analysis   (문장 분절 + 레지스터 + 지표 일괄 계산)
segment(text)            -> list[Sentence]
classify_eomi(sentence)  -> (레지스터, 종결 표기)
check_register(text, genre, level=None) -> RegisterReport  (장르별 말투 일치 검사)
"""

from __future__ import annotations

from .eomi import REGISTERS, Sentence, classify_eomi, segment
from .findings import Finding
from .genre import GENRES, LEVELS, RegisterReport, check_register
from .metrics import METRIC_KEYS, Analysis, Metric, analyze
from .report import render_compare, render_score, to_json

__version__ = "0.1.0"

__all__ = [
    "REGISTERS",
    "Sentence",
    "classify_eomi",
    "segment",
    "Analysis",
    "Metric",
    "METRIC_KEYS",
    "analyze",
    "render_score",
    "render_compare",
    "to_json",
    "Finding",
    "GENRES",
    "LEVELS",
    "RegisterReport",
    "check_register",
    "__version__",
]
