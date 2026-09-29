"""eomi.py — 종결어미 레지스터 분류기.

문장을 (1) 마디로 세그먼트팅하고 (2) 각 마디의 종결형을 6범주로 판명한다.
LLM·통계모델 없이 **어미 표면형의 결정론적 문자열 규칙**만 쓴다.

레지스터
--------
polite_formal    합쇼체   …습니다 / …ㅂ니다 / …습니다만
polite_informal  해요체   …해요 / …어요 / …해요요
plain            해라·서술 …한다 / …했다 / (…다 로 끝나는 모든 서술형)
nominal          명사형   …ㅁ · …음 · …임 · …함 · …것 · …지 · …기
question         의문     …습니까 / …ㅂ니까 / …나요 / …는가
none             생략     위 어디에도 해당하지 않는 단문(어미 없음)

판정 순서는 **긴 어미 → 짧은 어미 → 「다」 → 명사형 → 생략** 으로 고정한다.
순서가 의미론적으로 강제된다: 「…습니다」 도 「다」로 끝나므로 polite_formal 이
plain 보다 먼저 판명되어야 한다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

__all__ = [
    "REGISTERS",
    "Sentence",
    "classify_eomi",
    "segment",
    "strip_tail",
    "has_hangul",
]

# ---------------------------------------------------------------------------
# 레지스터 정의
# ---------------------------------------------------------------------------

REGISTERS: tuple[str, ...] = (
    "polite_formal",
    "polite_informal",
    "plain",
    "nominal",
    "question",
    "none",
)

REGISTER_LABEL: dict[str, str] = {
    "polite_formal": "합쇼체(-습니다)",
    "polite_informal": "해요체(-해요)",
    "plain": "해라/서술(-다)",
    "nominal": "명사형(-음·함·것·지·기)",
    "question": "의문(-습니까·나요)",
    "none": "종결생략",
}

# ---------------------------------------------------------------------------
# 어미 표 (긴 것부터)
# ---------------------------------------------------------------------------

_SUFFIX_QUESTION = ("습니까", "ㅂ니까", "나요", "는가", "가냐")

# 「-ㅂ니다」 는 문자열로 못 잡는다. 한글 합성 때문에 표면형이 「합니다」 이 되고
# 「ㅂ」 이 받침으로 소멸한다(§final_consonant). 그래서 받침 규칙으로 따로 판명한다.
_SUFFIX_POLITE_FORMAL = ("습니다만", "습니다")

_SUFFIX_POLITE_INFORMAL = (
    "해요요", "해요", "이에요", "예요", "어요", "아요", "오요", "에요",
    "래요", "라요", "께요", "겠어요", "네요", "거든요", "잖아요", "와요",
    "라고요", "지요", "구요", "군요", "죠", "세요", "까요",
)

_SUFFIX_NOMINAL = ("ㅁ", "음", "임", "함", "것들", "것으로", "것", "지", "기")

# 의문으로 판명할 "약한" 어미. 물음표가 **있을 때만** 성립한다.
# 「~니까」 는 「그러니까」 같은 인과 접속과 「니까?」 같은 의문이 같은 표면형을
# 갖기 때문에 물음표 없이는 판명하지 않는다. (함정 #1)
_SUFFIX_QUESTION_WEAK = ("니까", "까", "나", "가", "지", "래", "잖아")

# 명사형 어미(받침 ㅁ) 또는 「지/기/것」 으로 오탐되는 완결 한자어·부사격.
# 앞 2~3음절이 아래와 같으면 어미로 인정하지 않는다. (함정 #2)
_NOMINAL_BLOCK = frozenset(
    {
        "가지",   # ~가지(이유)
        "까지",   # 끝까지 / 그만큼까지
        "같이",   # 같이
        "마치",   # 마치
        "이미",   # 이미
        "하지",   # 하지(동사 어간)
        "그것", "이것", "저것",   # 지시대명사 — 「것」 을 어미로 오인
        "그거", "이거", "저거",
        "그럼",   # 그러+면 (접속)
        "그림", "이름", "이음",   # 받침 ㅁ 으로 끝나는 고유명사
        "무늬", "조목",
    }
)

# 「~하면 안 된다」 류. 표면형이 명사형(…됨)으로 떨어지는 경우를 제외한다.
# 「안 된다」 는 「다」로 떨어져 자동 plain 이지만, 「안 됨」 은 받침 ㅁ 으로
# 떨어지므로 여기서 막는다. (함정 #3)
_NEGATIVE_NOMINAL = re.compile(r"(?:안|않)\s*(?:됨|함|것|음|움|점)$")

# ---------------------------------------------------------------------------
# 문자 판정
# ---------------------------------------------------------------------------

_HANGUL_SYLLABLE = re.compile(r"[가-힣]")
_HANGUL_ANY = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")
_LATIN = re.compile(r"[A-Za-z]")

_FINAL_CACHE: dict[str, str] = {}


def final_consonant(ch: str) -> str:
    """한글 음절 하나의 **받침 자모**(종성). 받침이 없거나 음절이 아니면 ''.

    이 함수가 있어야만 「합니다」 의 ㅂ 이 보인다. 「합」 은 합성음절이라
    문자열에 「ㅂ」 이 남아 있지 않기 때문이다.

    유니코드 한글 음절 분해는 **알고리즘**이라 `unicodedata.decomposition()` 이
    빈 문자열을 돌려준다(명시적 분해만 담고 있다). 조합표(ㄱㄲㄳㄴ…)를 손으로
    옮겨 적으면 한 칸씩 밀려서 28개/27개 혼동이 난다. NFD 로 실제 풀어
    마지막 자모를 읽는 것이 유일하게 믿을 만한 방법이다.
    """
    if not ch:
        return ""
    cached = _FINAL_CACHE.get(ch)
    if cached is not None:
        return cached
    result = ""
    if "\uac00" <= ch <= "\ud7a3":
        decomposed = unicodedata.normalize("NFD", ch)
        if len(decomposed) == 3:      # 초성 + 중성 + 종성
            result = decomposed[-1]
    _FINAL_CACHE[ch] = result
    return result


def _jong_of(sample: str) -> str:
    """기준 음절(「음」)에서 받침 자모를 뽑는다. 표 오타 방지용."""
    return unicodedata.normalize("NFD", sample)[-1]


# 받침 자모는 U+11A8(ㄱ) ~ U+11C2(ㅎ) 연속 27개다. 호환용 자모(U+3141 등)와는
# **다른 문자**다 — 소스 리터럴 「ㅁ」 과 비교하면 영영 안 맞는다.
# 「다름」 의 받침도 ㅁ 이다(ㄻ 아님). 「-(으)ㄹ」 의 달·살·알 은 받침 ㄹ 이라
# 여기 걸리지 않는다 — ㄹ 가지를 따로 만들 필요가 없었다.
_JONG_M = _jong_of("음")   # ㅁ



# 목록 번호 「가 나 다 라 …」 (국어 순서 근사) + 옛 표기 「거 너 더 …」
_HANGUL_NUMERATORS = frozenset("가나다라마바사아자차카타파하")
_HANGUL_NUMERATORS |= frozenset("거너더러머버서어저처커터퍼허")

_TRAILING_JUNK = ".,!?…。！？、；; \t　\"'”’)]}>」』】〉》*_~"

# 목록 번호로 오탐할 수 있는 토큰의 문자 클래스
_NUM_TOKEN_CH = re.compile(r"[0-9A-Za-z가-힣①-⑳]")

# 마침표 앞뒤에 올 수 있는 마크업 경계
_TOKEN_PRECEDERS = " \t\n>*("


def has_hangul(text: str) -> bool:
    """문자열에 한글(음절 또는 자모)이 있는지."""
    return bool(_HANGUL_ANY.search(text))


def strip_tail(text: str) -> str:
    """문장 끝의 구두점·닫는 괄호·공백을 전부 떼어 낸다."""
    out = unicodedata.normalize("NFC", text).rstrip()
    prev = None
    while out and out != prev:
        prev = out
        out = out.rstrip(_TRAILING_JUNK)
    return out


def _match_suffix(tail: str, table: tuple[str, ...]) -> str | None:
    for suf in table:
        if tail.endswith(suf):
            return suf
    return None


def _ending_key(tail: str, matched: str | None) -> str:
    """문장 끝의 **종결 표기 키**.

    어미가 2음절 이상이면 그 어미 자체를 쓴다(「습니다만」 ≠ 「습니다」).
    1음절 어미(다·음·임·함·것·지·기·ㅁ)는 구분력이 없으므로
    끝의 2음절을 쓴다 — 「했다」 / 「있다」 / 「간다」 를 구분하기 위해.
    「-ㅂ니다」 는 표면형이 「합니다」 로 합성되므로 표기 키도 표면형 그대로
    「합니다」 가 된다. 「습니다」 와 다른 키가 나오므로 반복률 계측에 유용하다.
    """
    if matched and len(matched) >= 2:
        return matched
    compact = tail.replace(" ", "")
    if len(compact) >= 2:
        return compact[-2:]
    return compact or tail


def _nominal_blocked(tail: str) -> bool:
    compact = tail.replace(" ", "")
    for width in (2, 3):
        if compact[-width:] in _NOMINAL_BLOCK:
            return True
    return False


def _brieup(tail: str, verb_tail: str) -> str | None:
    """받침이 붙은 음절 + 「{verb_tail}」 로 이루어진 합쇼/의문 표기형인가.

    「합니다」 「봅니다」 「입니다」 는 「합」+「니다」 로 합성되어 있어서
    원본 문자열에 「ㅂ니다」 라는 문자열이 **존재하지 않는다**. NFD 로 풀어도
    받침 ㅂ 은 자모 U+11B8 로 바뀌어서 여전히 「ㅂ니다」 가 아니다.
    Unicode 음절 분해로 받침을 꺼내는 방법밖에 없다.

    되돌림값은 그 직전 음절(「합니다」 → 「합」). 종결 표기 키로 쓴다.
    """
    if not tail.endswith(verb_tail) or len(tail) <= len(verb_tail):
        return ""
    prev = tail[-(len(verb_tail) + 1)]
    if not final_consonant(prev):
        return ""
    return prev + verb_tail


def _is_final_m(tail: str) -> bool:
    """「-(으)ㅁ」 명사형 종결인가.

    「좋음(좋아+ㅁ)」 「다름(다라+ㅁ)」 「섬(서+ㅁ)」 「점」 「됨」 이 모두
    여기 걸린다. 어미별 나열(음/움/꼼/끔/름)으로는 빠지는 형태가 생긴다.
    받침이 ㄹ 인 「-(으)ㄹ」(달·살·알·나를)은 여기서 통과하지 않는다.
    """
    return bool(tail) and final_consonant(tail[-1]) == _JONG_M


def classify_eomi(sentence: str, terminator: str = "") -> tuple[str, str | None]:
    """문장 하나를 (레지스터, 종결 표기 키) 로 판명한다.

    terminator 는 세그먼트 단계에서 붙은 문장 종결 기호(「.」「?」 등).
    「?」 는 의문 판정에 반드시 쓰이므로 전달해야 한다.
    """
    tail = strip_tail(sentence)
    if not tail or not has_hangul(tail):
        return ("none", None)

    asked = terminator in ("?", "？") or "?" in sentence

    # 1) 의문 — 명시적 의문 어미
    hit = _match_suffix(tail, _SUFFIX_QUESTION)
    if hit:
        return ("question", _ending_key(tail, hit))
    hit = _brieup(tail, "니까")          # 「합니까」 「읍니까」
    if hit:
        return ("question", _ending_key(tail, hit))

    # 2) 의문 — 물음표가 있을 때만 성립하는 약한 어미
    if asked:
        hit = _match_suffix(tail, _SUFFIX_QUESTION_WEAK)
        if hit:
            return ("question", _ending_key(tail, hit))

    # 3) 합쇼체 — 「다」로도 끝나므로 반드시 plain 보다 먼저
    hit = _brieup(tail, "니다")          # 「합니다」 「봅니다」 「입니다」
    if hit:
        return ("polite_formal", hit)
    hit = _match_suffix(tail, _SUFFIX_POLITE_FORMAL)
    if hit:
        return ("polite_formal", _ending_key(tail, hit))

    # 4) 해요체
    hit = _match_suffix(tail, _SUFFIX_POLITE_INFORMAL)
    if hit:
        return ("polite_informal", _ending_key(tail, hit))

    # 5) 해라·서술 — 한글 '다' 로 끝나는 모든 서술형(있다·없다·이다·된다 포함)
    if tail.endswith("다"):
        return ("plain", _ending_key(tail, "다"))

    # 6) 명사형 — 「~하면 안 된다」 류를 먼저 걷어낸다
    if _NEGATIVE_NOMINAL.search(tail):
        return ("plain", _ending_key(tail, "다"))

    if _is_final_m(tail) and not _nominal_blocked(tail):
        return ("nominal", _ending_key(tail, "ㅁ"))

    hit = _match_suffix(tail, _SUFFIX_NOMINAL)
    if hit and not _nominal_blocked(tail):
        return ("nominal", _ending_key(tail, hit))

    return ("none", None)




# ---------------------------------------------------------------------------
# 마크다운 전처리
# ---------------------------------------------------------------------------

_RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RE_FENCE = re.compile(r"^\s{0,3}(?:```|~~~)")
_RE_HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")

# URL · 이메일 · 인라인 코드는 문장 분절 대상이 아니다. 마스킹해서 보호한다.
# 마스킹 자리는 한자 사용 영역(U+E000~U+E001)을 쓴다 — 어떤 가운뎃점도 없다.
_RE_URL = re.compile(
    r"(?:https?://|www\.)[^\s<>()\]]+"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
_RE_INLINE_CODE = re.compile(r"`[^`\n]*`")
_RE_EMPHASIS = re.compile(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1", re.S)

# 표 행 · 가로선 · 그림 전용 줄 · 링크 전용 줄
_RE_TABLE_ROW = re.compile(r"^\s*\|")
_RE_HR = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_RE_IMAGE_ONLY = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
_RE_LINK_ONLY = re.compile(r"^\s*\[[^\]]*\]\([^)]*\)\s*$")
_RE_BARE_URL_LINE = re.compile(r"^\s*(?:https?://|www\.)\S+\s*$")
# 뒤에 공백이 없어도 헤딩으로 본다 — 「#142 제주…」 같은 문서 제목이 흔하다.
_RE_HEADING = re.compile(r"^\s{0,3}#{1,6}[ \t]*")
_RE_QUOTE = re.compile(r"^\s{0,3}>\s?")

# 목록 마커. 한국어 업무문서에서 흔히 쓰이는 ○ □ ※ ⚠ 도 목록으로 본다.
#  · 「1.」 「2)」 「가.」 「I.」 「iv.」 「①.」  — 숫자/라틴은 뒤에 공백이 있어야.
#  · 「-」 「*」 「+」 은 마크다운 규칙대로 뒤에 공백이 있어야. 그래야
#    「**선택기준**」 같은 굵은 글머리표가 목록으로 잡히지 않는다.
_MARKER_ALT = (
    r"(?:(?:\d{1,2}|[A-Za-z]{1,4}|[가-힣]|[①-⑳])[.)](?=[ \t]|\s|$)"
    r"|[-*+](?=[ \t])"
    r"|[•·○◌◎□▪▫※⚠→▶▷◆◇■◼◻])"
)
_RE_LIST_MARKER = re.compile(rf"^[ \t]*{_MARKER_ALT}[ \t]*")

# 마스킹 자리는 한글이 없는 중립 토큰으로 둔다. 읽기 전용 표시이면서
# 어절 수에는 1개로 세인다. (U+E000 사각형은 리포트에豆腐로 보인다)
_MASK_TOKEN = "[link]"


def _mask_spans(line: str) -> str:
    line = _RE_INLINE_CODE.sub(_MASK_TOKEN, line)
    line = _RE_URL.sub(_MASK_TOKEN, line)
    return line


def _is_list_item_line(raw: str) -> bool:
    probe = _RE_QUOTE.sub("", _RE_HEADING.sub("", raw))
    return bool(_RE_LIST_MARKER.match(probe))


def _clean_line(raw: str) -> str:
    """한 줄을 「문장 후보가 들어갈 수 있는 한 줄」로 만든다. 버릴 줄은 ''."""
    if not raw.strip():
        return ""
    if _RE_FENCE.match(raw):
        return ""  # 펜스 시작/끝 줄
    if _RE_TABLE_ROW.match(raw) or _RE_HR.match(raw):
        return ""
    if _RE_IMAGE_ONLY.match(raw) or _RE_LINK_ONLY.match(raw) or _RE_BARE_URL_LINE.match(raw):
        return ""

    line = _RE_HEADING.sub("", raw)
    line = _RE_QUOTE.sub("", line)
    line = _RE_HTML_TAG.sub(" ", line)
    line = _mask_spans(line)
    if _is_list_item_line(raw):
        # 「- ○」 「※ →」 처럼 마커가 겹쳐 있는 줄이 많다. 겹칠 만큼 반복해서 뺀다.
        while _RE_LIST_MARKER.match(line):
            line = _RE_LIST_MARKER.sub("", line, count=1)
    line = _RE_EMPHASIS.sub(r"\2", line)
    line = line.replace("**", "").replace(" ", " ")
    return line.strip()


def extract_blocks(text: str) -> list[str]:
    """원고 → 문단 블록 리스트.

    블록 정의(고정 규칙):
      * 빈 줄로 끊긴 연속 줄 묶음 하나가 문단 하나
      * 목록 마커로 시작하는 줄은 **항상 그 자체로** 새 문단
        (한 항목 = 한 단위 리듬으로 보아야 하기 때문)
    """
    body = _RE_HTML_COMMENT.sub(" ", text)
    # 펜스 코드 블록 제거 — ``` 으로 시작하는 줄부터 다음 ``` 또는 EOF 까지
    kept: list[str] = []
    in_fence = False
    fence_re = ""
    for raw in body.splitlines():
        m = _RE_FENCE.match(raw)
        if m:
            token = m.group(0).strip()[:3]
            if not in_fence:
                in_fence, fence_re = True, token
                continue
            if token == fence_re:
                in_fence = False
                continue
            continue  # 코드 블록 안의 다른 라인
        if in_fence:
            continue
        kept.append(raw)

    blocks: list[str] = []
    buf: list[str] = []
    for raw in kept:
        is_item = _is_list_item_line(raw)
        line = _clean_line(raw)
        if not line:
            if buf:
                blocks.append(" ".join(buf))
                buf = []
            continue
        if is_item:
            if buf:
                blocks.append(" ".join(buf))
                buf = []
            blocks.append(line)
            continue
        buf.append(line)
    if buf:
        blocks.append(" ".join(buf))
    return blocks


# ---------------------------------------------------------------------------
# 문장 세그먼트팅
# ---------------------------------------------------------------------------

_SENTENCE_PUNCT = ".?!。？！…"
_SENTENCE_ABSORB = ".)]}>」』】〉》’\"”…!?！？"

# 닫는 괄호형 문장 끝. 「…시상하지 않을 수 있음」 → 기준 미달… 처럼 한국어
# 평서문에서는 인용 괄호 닫힘이 문장 끝을 알리는 경우가 많다.
# **뒤에 공백(또는 줄 끝)이 올 때만** 경계로 본다 — 「「A」와 「B」가」 는
# 중간이라 걸리지 않는다.
_QUOTE_CLOSE = "」』】"
_RE_QUOTE_CLOSE = re.compile(r"[」』】](?=[ \t]|$)")


def _is_latin(ch: str) -> bool:
    return bool(_LATIN.match(ch))


def _is_hangul_syllable(ch: str) -> bool:
    return bool(_HANGUL_SYLLABLE.match(ch))


def _is_list_numerator(text: str, dot: int) -> bool:
    """dot 앞 토큰이 「목록 번호」인가 판명한다.

    「1.」 「가.」 「나.」 「①.」 「I.」 「iv.」 만 걸어내고,
    「제12조.」 「2026.」 「3.14」 같은 것은 걸러내지 않는다.
    """
    j = dot - 1
    if j < 0 or not _NUM_TOKEN_CH.match(text[j]):
        return False
    k = j
    while k >= 0 and _NUM_TOKEN_CH.match(text[k]):
        k -= 1
    if k >= 0 and text[k] not in _TOKEN_PRECEDERS:
        return False  # 문중 숫자 — 「무료 3.5 만원」 같은 경우
    token = text[k + 1 : j + 1]

    nxt = text[dot + 1] if dot + 1 < len(text) else ""
    if nxt and nxt not in " \t\n":
        return False

    if token.isdigit():
        # 「2026.」 은 연도다. 문장이 숫자 하나로 끝나고 다음이 공백인 경우를
        # 경계로 보면 「기준 연도는 2026」 이 통째로 잘린다. 진짜 문장 끝이라면
        # 「2026이다.」 처럼 「다」 가 뒤에 오므로 여기서 걸리지 않는다.
        return len(token) <= 2 or len(token) == 4
    if token in _HANGUL_NUMERATORS:
        return True
    if len(token) == 1 and token.isascii() and token.isupper():
        return True
    return bool(re.fullmatch(r"[ivxlcIVXLC]{1,4}", token))


def _dot_is_boundary(text: str, dot: int) -> bool:
    prev = text[dot - 1] if dot > 0 else ""
    nxt = text[dot + 1] if dot + 1 < len(text) else ""

    if prev.isdigit() and nxt.isdigit():
        return False                      # 3.14 · 2026.09
    if _is_latin(prev) and _is_latin(nxt):
        return False                      # report.md · example.com
    if _is_latin(nxt) and (prev.isdigit() or _is_hangul_syllable(prev)):
        return False                      # 「…대안검토.md」 같은 파일명
    if _is_list_numerator(text, dot):
        return False                      # 1. · 가. · ①.
    return True


def _split_block(text: str) -> list[tuple[str, str]]:
    """문단 텍스트 → [(마디, 종결기호)]"""
    out: list[tuple[str, str]] = []
    start = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in _SENTENCE_PUNCT:
            if ch == "." and not _dot_is_boundary(text, i):
                i += 1
                continue
        elif not (ch in _QUOTE_CLOSE and _RE_QUOTE_CLOSE.match(text, i)):
            i += 1
            continue
        end = i + 1
        while end < n and text[end] in _SENTENCE_ABSORB:
            end += 1
        piece = text[start:end].strip()
        if piece:
            out.append((piece, ch))
        start = end
        i = end
    rest = text[start:].strip()
    if rest:
        out.append((rest, ""))
    return out


# ---------------------------------------------------------------------------
# 문장 객체
# ---------------------------------------------------------------------------

_TOKEN_CONTENT = re.compile(r"[^\s]")


def count_eojeol(text: str) -> int:
    """어절 수. 글자·숫자가 하나라도 있는 공백 토큰만 센다."""
    return sum(1 for tok in text.split() if _TOKEN_CONTENT.search(tok))


@dataclass(frozen=True)
class Sentence:
    index: int          # 문서 전체 순번
    text: str
    register: str
    ending: str | None  # 종결 표기 키
    terminator: str     # 종결 기호
    paragraph: int      # 문단 번호
    pos: int            # 문단 내 순번(0부터)
    eojeol: int         # 어절 수


def segment(text: str) -> list[Sentence]:
    """원고 → 마디 리스트. 마디 중 한글이 없는 것은 걸러 낸다."""
    out: list[Sentence] = []
    for p_idx, block in enumerate(extract_blocks(text)):
        for s_idx, (piece, term) in enumerate(_split_block(block)):
            if not has_hangul(piece):
                continue
            register, ending = classify_eomi(piece, term)
            out.append(
                Sentence(
                    index=len(out),
                    text=piece,
                    register=register,
                    ending=ending,
                    terminator=term,
                    paragraph=p_idx,
                    pos=s_idx,
                    eojeol=count_eojeol(piece),
                )
            )
    return out
