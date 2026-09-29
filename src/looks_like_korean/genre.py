"""genre.py — 장르별 말투(높임 등급) 일치 검사.

v0.1.0 은 「종결어미가 다양할수록 사람 같다」고 보았고, 7쌍 모두에서 틀렸다.
어미를 다양하게 바꾼 글은 장르에 맞지 않는 말투가 섞여 오히려 나빠졌다.
이 모듈은 방향을 뒤집는다. **장르가 정한 말투에서 벗어난 문장**을 찾는다.

근거: docs/research/public-language.md 4장, docs/research/ux-writing.md 4장.

높임 등급
---------
formal    합쇼체  -습니다 / -습니까
informal  해요체  -어요 / -나요
plain     해라체  -다 / -는가

명사형(-음·-함)과 종결 생략은 높임 등급이 없다. 개조식 목록에서는 정상이고,
본문에서는 장르에 따라 따로 판단한다.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, replace

from .eomi import Sentence, classify_eomi, segment, strip_tail
from .findings import Finding

__all__ = [
    "LEVELS",
    "LEVEL_LABEL",
    "GenreProfile",
    "GENRES",
    "RegisterReport",
    "is_nominal",
    "is_quoted",
    "speech_level",
    "check_register",
]

LEVELS: tuple[str, ...] = ("formal", "informal", "plain")

LEVEL_LABEL: dict[str, str] = {
    "formal": "합쇼체(-습니다)",
    "informal": "해요체(-어요)",
    "plain": "해라체(-다)",
}

_LEVEL_HINT: dict[str, str] = {
    "formal": "「-습니다」「-습니까」",
    "informal": "「-어요」「-나요」",
    "plain": "「-다」「-는가」",
}

# 문서 단위로 한 번에 알리는 기준. 고정 말투와 다른 문장이 이 비율을 넘으면
# 문장마다 경고하지 않고 「문서 전체가 다른 말투」로 묶는다.
_DOC_LEVEL_RATIO = 0.5
_DOC_LEVEL_MIN = 3

# 본문 문장 중 명사형 비율이 이 값 이상이면 개조식 문서로 보고 REG-NOM 을 내지 않는다.
# 공모 제안서는 목록 기호 없이 줄마다 「~함」「~음」으로 끝내는 경우가 많다.
_BULLET_STYLE_RATIO = 0.5

# 「~하지 않음」「안 됨」. eomi 분류기는 이것을 plain 으로 두지만(지표 호환),
# 말투 검사에서는 높임 등급이 없는 명사형 종결로 본다.
_NEGATIVE_NOMINAL_TAIL = re.compile(r"(?:안|않)\s*(?:됨|함|것|음|움|점)$")

# 「다」로 끝나지만 어미가 아니라 명사인 낱말. eomi 는 이것을 plain 으로 본다.
_NOUN_ENDING_DA = ("최다", "과다", "바다")

# 명사형 검사에서 뺄 줄: 개조식 기호로 시작하는 항목, 그림·표 설명, 「이름: 값」 서식 칸.
# 표 칸 안에서 여러 항목이 한 줄로 이어 붙은 경우처럼 eomi 가 목록으로 못 가른 것을 받친다.
_BULLET_START = re.compile(r"^\s*(?:[◦❍○●◎□■※▸▶•·]|ㅇ\s|[-–]\s|[〔\[(（]?(?:그림|표|사진)\s?\d)")
_FIELD_LABEL = re.compile(r"^[^\s:：]{1,12}(?:\s[^\s:：]{1,12})?\s?[:：]\s")

_OPEN_QUOTES = ("「", "『", "“", "‘")
_CLOSE_QUOTES = ("」", "』", "”", "’")
_QUOTE_TAIL = re.compile(r"[」』”’\"'][\s.!?)\]]*$")

# 문장 끝에 붙은 이모지. 떼지 않으면 「발생했습니다 😢」의 높임 등급을 못 읽는다.
_TRAILING_EMOJI = re.compile(r"[\s\U0001F300-\U0001FAFF\u2600-\u27BF]+$")


@dataclass(frozen=True)
class GenreProfile:
    key: str
    label: str
    levels: tuple[str, ...]        # 본문에 허용하는 높임 등급. 하나면 고정, 여럿이면 다수결로 하나를 고른다
    default_level: str             # 다수결을 할 문장이 없을 때 쓰는 기준
    nominal_in_prose: str | None   # 본문(목록·제목 제외)의 명사형 종결: None 허용 / "warn" / "review"
    basis: str                     # 근거 한 줄


GENRES: dict[str, GenreProfile] = {
    profile.key: profile
    for profile in (
        GenreProfile(
            key="self-intro",
            label="자기소개서",
            levels=("formal",),
            default_level="formal",
            nominal_in_prose="warn",
            basis="채용 문서 관행과 공개 지침의 예문이 모두 합쇼체 서술문이다(명시 규정은 없음)",
        ),
        GenreProfile(
            key="proposal",
            label="제안서·보고서",
            levels=("formal", "plain"),
            default_level="formal",
            nominal_in_prose="review",
            basis="개조식 목록은 명사형을 허용하고, 서술 문단은 한 가지 종결 체계로 쓴다",
        ),
        GenreProfile(
            key="notice",
            label="공문·안내문",
            levels=("formal", "informal"),
            default_level="formal",
            nominal_in_prose="warn",
            basis="대국민 안내는 하십시오체나 해요체로 쓰고, 명사형 종결(「~할 것」「~바람」)은 권위적이라 피한다",
        ),
        GenreProfile(
            key="ui",
            label="화면 문구",
            levels=("informal", "formal"),
            default_level="informal",
            nominal_in_prose="review",
            basis="한 서비스 안에서는 말투를 하나로 통일한다. 오류 메시지도 예외가 아니다",
        ),
        GenreProfile(
            key="general",
            label="일반 글",
            levels=("formal", "informal", "plain"),
            default_level="formal",
            nominal_in_prose=None,
            basis="한 글 안에서 높임 등급을 섞지 않는다",
        ),
    )
}


@dataclass(frozen=True)
class RegisterReport:
    genre: GenreProfile
    target_level: str
    target_reason: str
    level_counts: dict[str, int]
    findings: tuple[Finding, ...]
    bullet_style: bool = False     # 본문 절반 이상이 명사형이면 개조식 문서로 본다

    def header_lines(self) -> list[str]:
        counts = " · ".join(f"{LEVEL_LABEL[k]} {self.level_counts.get(k, 0)}" for k in LEVELS)
        lines = [
            f"장르: {self.genre.label} · 기준 말투: {LEVEL_LABEL[self.target_level]} ({self.target_reason})",
            f"문장 끝 높임 등급: {counts}",
        ]
        if self.bullet_style:
            lines.append("본문 절반 이상이 명사형이라 개조식 문서로 보고, 명사형 종결은 검사하지 않았습니다.")
        return lines


def is_quoted(sentence: Sentence) -> bool:
    """문장 끝이 인용 부호 안에 있는가. 인용한 말의 말투는 글쓴이의 말투가 아니다."""
    text = sentence.text
    if _QUOTE_TAIL.search(text):
        return True
    unclosed = any(text.count(o) > text.count(c) for o, c in zip(_OPEN_QUOTES, _CLOSE_QUOTES))
    return unclosed or text.count('"') % 2 == 1


def is_nominal(sentence: Sentence) -> bool:
    """명사형 종결인가. 「~하지 않음」 같은 부정 명사형과 「최다」 같은 명사 끝도 포함한다."""
    if sentence.register == "nominal":
        return True
    if sentence.register != "plain":
        return False
    tail = strip_tail(sentence.text)
    return bool(_NEGATIVE_NOMINAL_TAIL.search(tail)) or tail.endswith(_NOUN_ENDING_DA)


def _is_item_like(sentence: Sentence) -> bool:
    """목록 기호·그림 설명·서식 칸처럼 서술문이 아닌 줄인가."""
    return bool(_BULLET_START.match(sentence.text) or _FIELD_LABEL.match(sentence.text))


def _without_trailing_emoji(sentence: Sentence) -> Sentence:
    """문장 끝 이모지를 떼고 다시 분류한 새 Sentence. 이모지가 없으면 그대로 돌려준다."""
    stripped = _TRAILING_EMOJI.sub("", sentence.text)
    if stripped == sentence.text or not stripped:
        return sentence
    register, ending = classify_eomi(stripped, sentence.terminator)
    return replace(sentence, text=stripped, register=register, ending=ending)


def _is_exempt_request(sentence: Sentence, profile: GenreProfile) -> bool:
    """화면 문구의 「~해 주세요」. 요청은 서비스 말투와 상관없이 이렇게 쓴다(ux-writing.md 4-2)."""
    return profile.key == "ui" and strip_tail(sentence.text).endswith("주세요")


def speech_level(sentence: Sentence) -> str | None:
    """문장의 높임 등급. 명사형·종결 생략·인용문은 None."""
    if is_quoted(sentence) or is_nominal(sentence):
        return None
    register = sentence.register
    if register == "polite_formal":
        return "formal"
    if register == "polite_informal":
        return "informal"
    if register == "plain":
        return "plain"
    if register == "question":
        tail = strip_tail(sentence.text)
        if tail.endswith("니까"):
            return "formal"
        if tail.endswith("요"):
            return "informal"
        return "plain"
    return None


def _choose_target(profile: GenreProfile, counts: Counter, forced: str | None) -> tuple[str, str]:
    if forced is not None:
        return forced, "직접 지정"
    if len(profile.levels) == 1:
        return profile.levels[0], "장르 고정"
    candidates = [(counts.get(level, 0), -profile.levels.index(level), level) for level in profile.levels]
    best_count, _, best = max(candidates)
    if best_count == 0:
        return profile.default_level, "본문 문장 없음 · 장르 기본값"
    return best, "본문 다수결"


def _level_finding(s: Sentence, level: str, target: str, profile: GenreProfile) -> Finding:
    if level in profile.levels:
        message = f"{LEVEL_LABEL[target]}로 쓴 글에 {LEVEL_LABEL[level]} 문장이 섞였습니다."
    else:
        message = f"{profile.label}에는 {LEVEL_LABEL[level]}를 쓰지 않습니다."
    return Finding(
        rule="REG-MIX",
        severity="warn",
        message=message,
        suggestion=f"문장 끝을 {_LEVEL_HINT[target]}로 맞춥니다. 내용은 바꾸지 않습니다.",
        sentence_index=s.index,
        paragraph=s.paragraph,
        excerpt=s.text,
    )


def _nominal_finding(s: Sentence, profile: GenreProfile, target: str) -> Finding:
    return Finding(
        rule="REG-NOM",
        severity=profile.nominal_in_prose or "review",
        message=f"{profile.label}의 서술 문단이 명사형으로 끝났습니다.",
        suggestion=(
            f"개조식 목록이면 앞에 목록 기호를 붙이고, 서술문이면 {_LEVEL_HINT[target]}로 끝맺습니다."
        ),
        sentence_index=s.index,
        paragraph=s.paragraph,
        excerpt=s.text,
    )


def check_register(text: str, genre: str = "general", level: str | None = None) -> RegisterReport:
    """원고의 말투가 장르 기준과 맞는지 검사한다.

    genre  GENRES 의 키
    level  기준 말투를 직접 지정할 때 LEVELS 중 하나
    """
    if genre not in GENRES:
        raise ValueError(f"알 수 없는 장르: {genre} (가능: {', '.join(GENRES)})")
    if level is not None and level not in LEVELS:
        raise ValueError(f"알 수 없는 말투: {level} (가능: {', '.join(LEVELS)})")
    profile = GENRES[genre]
    sentences = [_without_trailing_emoji(s) for s in segment(text) if s.kind != "heading"]
    leveled = [(s, speech_level(s)) for s in sentences if not _is_exempt_request(s, profile)]
    leveled = [(s, lv) for s, lv in leveled if lv is not None]
    counts = Counter(lv for _, lv in leveled)
    target, reason = _choose_target(profile, counts, level)

    off = [(s, lv) for s, lv in leveled if lv != target]
    doc_level = (
        reason in ("장르 고정", "직접 지정")
        and len(leveled) >= _DOC_LEVEL_MIN
        and len(off) / len(leveled) > _DOC_LEVEL_RATIO
    )
    if doc_level:
        dominant = counts.most_common(1)[0][0]
        level_findings = [
            Finding(
                rule="REG-DOC",
                severity="warn",
                message=(
                    f"문장 {len(leveled)}개 중 {len(off)}개가 기준({LEVEL_LABEL[target]})과 다르고, "
                    f"대부분 {LEVEL_LABEL[dominant]}입니다."
                ),
                suggestion=(
                    f"의도한 말투라면 --level {dominant} 로 기준을 바꿉니다. "
                    f"아니라면 문서 전체를 {_LEVEL_HINT[target]}로 맞춥니다."
                ),
            )
        ]
    else:
        level_findings = [_level_finding(s, lv, target, profile) for s, lv in off]

    prose = [s for s in sentences if s.kind == "prose" and not is_quoted(s) and not _is_item_like(s)]
    prose_nominal = [s for s in prose if is_nominal(s)]
    # 개조식 예외는 명사형을 「검토」로만 보는 장르에 한정한다.
    # 자기소개서·공문처럼 명사형 종결 자체가 문제인 장르에는 적용하지 않는다.
    bullet_style = (
        profile.nominal_in_prose == "review"
        and bool(prose)
        and len(prose_nominal) / len(prose) >= _BULLET_STYLE_RATIO
    )
    nominal_findings = []
    if profile.nominal_in_prose is not None and not bullet_style:
        nominal_findings = [_nominal_finding(s, profile, target) for s in prose_nominal]

    findings = sorted(
        [*level_findings, *nominal_findings],
        key=lambda f: (-1 if f.sentence_index is None else f.sentence_index, f.rule),
    )
    return RegisterReport(
        genre=profile,
        target_level=target,
        target_reason=reason,
        level_counts=dict(counts),
        findings=tuple(findings),
        bullet_style=bullet_style,
    )
