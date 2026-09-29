"""patterns.py — 문장 패턴 검사.

근거가 있는 표현 패턴을 정규식으로 찾는다. 규칙마다 근거 노트의 항목을 적어 둔다.
  A = docs/research/academic.md · P = public-language.md · U = ux-writing.md

심각도는 근거 강도와 정상 쓰임의 빈도로 정한다.
  warn    근거가 강하고, 고쳐서 손해 보는 경우가 드물다
  review  정상 쓰임도 많다. 다시 읽고 글쓴이가 판단한다

번역 투는 「AI 티」가 아니라 품질 규칙이다(A C3). 그래서 review 로만 둔다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .eomi import Sentence, segment
from .findings import Finding
from .genre import GENRES, is_quoted

__all__ = ["PatternRule", "RULES", "check_patterns", "connective_comma_rate"]

ALL_GENRES = frozenset(GENRES)


@dataclass(frozen=True)
class PatternRule:
    code: str
    severity: str
    regex: re.Pattern
    message: str
    suggestion: str
    genres: frozenset = ALL_GENRES
    prose_only: bool = False       # 목록 항목에는 적용하지 않는다


def _rule(code, severity, pattern, message, suggestion, genres=ALL_GENRES, prose_only=False):
    return PatternRule(code, severity, re.compile(pattern), message, suggestion, frozenset(genres), prose_only)


_UI = {"ui"}
_WRITING = {"self-intro", "proposal", "general"}

RULES: tuple[PatternRule, ...] = (
    # A F2 · P P12 — 한글 맞춤법상 접속부사 뒤에는 쉼표를 쓰지 않는 것이 자연스럽다
    _rule(
        "PAT-CONJ-COMMA", "warn",
        r"^(?:그러나|그리고|따라서|또한|하지만|그런데|즉|특히|이에|나아가|더불어|아울러|반면|결국|게다가|한편|그래서),",
        "문장 첫 접속부사 뒤에 쉼표를 찍었습니다.",
        "쉼표를 지웁니다. 접속부사가 없어도 뜻이 통하면 부사째 지웁니다.",
    ),
    # A F4 — 「단순한 X를 넘어」는 KCI 초록에서 추세 대비 약 61배 늘었다
    _rule(
        "PAT-FRAME", "warn",
        r"단순(?:한|히)\s*\S+(?:\s\S+)?\s*(?:을|를)?\s*넘어",
        "「단순한 X를 넘어」 틀입니다.",
        "틀을 지우고 실제로 하는 일(Y)만 구체적으로 씁니다.",
    ),
    # A F13 · P P34 — 줄표는 부제 표시에만 쓴다. 숫자 사이 붙임표(2024–2025)는 제외
    _rule(
        "PAT-DASH", "warn",
        r"[—―]|(?<!\d)\s–\s(?!\d)",
        "본문에 줄표(—)를 썼습니다.",
        "쉼표·괄호로 바꾸거나 문장을 둘로 나눕니다.",
    ),
    # P P09 — 이중 피동
    _rule(
        "PAT-DOUBLE-PASSIVE", "warn",
        r"(?:되어|보여|잊혀|쓰여|읽혀|불려|찢겨)(?:지|져|졌)",
        "이중 피동입니다(「되어지다」「보여지다」).",
        "「되다」「보이다」처럼 피동을 한 번만 씁니다. 가능하면 주어를 살려 능동으로 씁니다.",
    ),
    # P 3장 — 자기소개서를 자기 평가로 마무리하면 근거 없이 결론만 남는다
    _rule(
        "PAT-SELF-EVAL", "warn",
        r"(?:적합한|적임자|필요한\s?인재|준비된\s?인재|최고의\s?인재)[^.!?]{0,25}(?:생각합니다|확신합니다|자신합니다|믿습니다)"
        r"|인재가\s?되겠습니다",
        "근거 없이 자기 평가로 마무리했습니다.",
        "평가 대신, 그렇게 말할 수 있는 장면이나 수치를 한 문장으로 씁니다.",
        genres={"self-intro"},
    ),
    # U 원칙 3 — 오류 메시지는 상황·이유·해결 방법을 담는다(10곳 합의)
    _rule(
        "PAT-UI-GENERIC-ERROR", "warn",
        r"^(?:알 수 없는\s)?(?:오류|에러|문제)가\s?(?:발생했습니다|발생했어요|생겼어요|생겼습니다)[.!]?$",
        "원인과 해결 방법이 없는 오류 문구입니다.",
        "무슨 일이 있었는지, 사용자가 무엇을 하면 되는지를 씁니다. 예: 「인터넷 연결이 끊겼어요. 연결되면 다시 시도해 주세요.」",
        genres=_UI,
    ),
    # P 2-1 · A F14 — 번역 투. 품질 규칙이라 review
    _rule(
        "PAT-TRANS", "review",
        r"에\s?대(?:해|하여|한)|(?:을|를)\s?통(?:해|하여|한)|에\s?의(?:해|하여|한)\s|에\s?있어(?:서)?\s|(?:을|를)\s?(?:가지|갖)고\s?있",
        "번역 투 표현입니다(「에 대해」「을 통해」「에 의해」「에 있어서」「가지고 있다」).",
        "대부분 조사 하나나 더 짧은 동사로 바꿀 수 있습니다. 예: 「회의를 통해 정했다」 → 「회의에서 정했다」.",
    ),
    # A F4 — 격을 세우려고 끼우는 상투 틀
    _rule(
        "PAT-CLICHE", "review",
        r"이러한\s(?:결과|점)(?:은|는)|시사(?:한다|합니다|하는 바|점을 제공)|할\s때입니다|해야\s할\s때다|에서\s\S+(?:으로|로)의\s전환",
        "뜻보다 격을 세우는 상투 틀입니다.",
        "틀을 빼고 말하려는 내용만 남깁니다.",
        genres=_WRITING | {"notice"},
    ),
    # P P20 — 과장 수식
    _rule(
        "PAT-HYPE", "review",
        r"혁신적|획기적|극대화|독보적|압도적|최고의|탁월한|완벽한|무궁무진",
        "근거 없는 과장 수식입니다.",
        "수식어 대신 비교 대상과 수치를 씁니다.",
        genres=_WRITING | _UI,
    ),
    # P 2-3 — 한 문장에 한 정보. 한국 공공 글 권장은 평균 60자·3줄 이하
    _rule(
        "PAT-LONG", "review",
        r"^.{100,}$",
        "100자가 넘는 문장입니다.",
        "정보가 둘 이상이면 문장을 나눕니다.",
        genres=_WRITING | {"notice"},
        prose_only=True,
    ),
    # U 원칙 11 — 오류에서 사과·감탄을 빼고 「부탁드립니다」를 남발하지 않는다
    _rule(
        "PAT-UI-SORRY", "review",
        r"죄송합니다|죄송해요|불편을\s?드려",
        "화면 문구에 사과를 넣었습니다.",
        "서비스 잘못이 분명할 때만 사과하고, 나머지는 해결 방법을 바로 씁니다.",
        genres=_UI,
    ),
    _rule(
        "PAT-UI-PLEASE", "review",
        r"부탁드립니다|부탁드려요|바랍니다",
        "요청을 과하게 높였습니다.",
        "요청은 「~해 주세요」로 씁니다.",
        genres=_UI,
    ),
    # U 원칙 12 — 느낌표는 아끼고 오류·경고에는 쓰지 않는다
    _rule(
        "PAT-UI-EXCLAIM", "review",
        r"!",
        "느낌표를 썼습니다.",
        "축하처럼 감정이 분명한 순간이 아니면 마침표로 바꿉니다.",
        genres=_UI,
    ),
    # U 원칙 13 · A F13 — 이모지는 정보가 될 때만
    _rule(
        "PAT-EMOJI", "review",
        r"[\U0001F300-\U0001FAFF]",
        "이모지를 썼습니다.",
        "정보를 더하지 않는 이모지는 지웁니다.",
        genres=_WRITING | _UI,
    ),
)

# A F1 — 연결어미 뒤 쉼표. 학생 논술문 기준 AI 19.8% · 사람 4.1%.
# 그러나 사람이 쓴 공공·학술 문서 7편은 21.5%로 AI 초안(19.3%)과 차이가 없었다
# (docs/research/measurements.md). 격식 문서에서는 변별하지 못하므로
# 논술문에 가까운 장르에만, 검토 등급으로만 알린다.
_COMMA_GENRES = frozenset({"self-intro", "general"})
_CONNECTIVE = r"(?:고|며|면서|는데|은데|지만|어서|아서|해서|므로|도록|으면|면)"
_RE_CONNECTIVE_ANY = re.compile(rf"[가-힣]{_CONNECTIVE}(?=[ ,])")
_RE_CONNECTIVE_COMMA = re.compile(rf"[가-힣]{_CONNECTIVE},")
# 「고」「면」으로 끝나지만 어미가 아닌 명사. 명사 나열의 쉼표를 어미 쉼표로 세지 않게 한다.
_NOUN_LOOKALIKE = re.compile(r"(?:최고|참고|광고|재고|사고|신고|보고서|측면|전면|표면|이면|단면|반면|국면|장면|화면)[,\s]")
_COMMA_RATE_WARN = 0.12
_COMMA_MIN_COUNT = 3


def connective_comma_rate(sentences: list[Sentence]) -> tuple[int, int]:
    """(쉼표가 붙은 연결어미 수, 전체 연결어미 수)."""
    with_comma = total = 0
    for s in sentences:
        text = _NOUN_LOOKALIKE.sub(" ", s.text)
        total += len(_RE_CONNECTIVE_ANY.findall(text))
        with_comma += len(_RE_CONNECTIVE_COMMA.findall(text))
    return with_comma, total


def _comma_findings(sentences: list[Sentence]) -> list[Finding]:
    with_comma, total = connective_comma_rate(sentences)
    if with_comma < _COMMA_MIN_COUNT or total == 0 or with_comma / total < _COMMA_RATE_WARN:
        return []
    rate = with_comma / total
    doc = Finding(
        rule="PAT-COMMA-RATE",
        severity="review",
        message=(
            f"연결어미 {total}개 중 {with_comma}개({rate:.0%}) 뒤에 쉼표를 찍었습니다. "
            "학생 논술문 연구에서 사람은 약 4%, AI는 약 20%였습니다."
        ),
        suggestion="아래 표시한 쉼표를 지웁니다. 지우고 문장이 헷갈리면 쉼표 대신 문장을 둘로 나눕니다.",
    )
    each = [
        Finding(
            rule="PAT-COMMA",
            severity="review",
            message="연결어미 뒤에 쉼표를 찍었습니다.",
            suggestion="쉼표를 지우거나 문장을 나눕니다.",
            sentence_index=s.index,
            paragraph=s.paragraph,
            excerpt=s.text,
        )
        for s in sentences
        if _RE_CONNECTIVE_COMMA.search(_NOUN_LOOKALIKE.sub(" ", s.text))
    ]
    return [doc, *each]


def _rule_findings(sentences: list[Sentence], genre: str) -> list[Finding]:
    rules = [r for r in RULES if genre in r.genres]
    return [
        Finding(
            rule=r.code,
            severity=r.severity,
            message=r.message,
            suggestion=r.suggestion,
            sentence_index=s.index,
            paragraph=s.paragraph,
            excerpt=s.text,
        )
        for s in sentences
        for r in rules
        if not (r.prose_only and s.kind != "prose") and r.regex.search(s.text)
    ]


def check_patterns(text: str, genre: str = "general") -> list[Finding]:
    """문장 패턴 검사. 제목과 인용문으로 끝나는 문장은 검사하지 않는다."""
    if genre not in GENRES:
        raise ValueError(f"알 수 없는 장르: {genre} (가능: {', '.join(GENRES)})")
    sentences = [s for s in segment(text) if s.kind != "heading" and not is_quoted(s)]
    comma = _comma_findings(sentences) if genre in _COMMA_GENRES else []
    return [*comma, *_rule_findings(sentences, genre)]
