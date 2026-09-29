# looks_like_korean

**AI가 쓴 티가 나지 않는 한국어를 쓰게 돕는 Claude Code 스킬과 검사 엔진.**
자기소개서, 제안서, 공문, 앱 화면 문구를 장르에 맞는 말투로 쓰고, 고친 뒤에는 사실이 바뀌지 않았는지 확인한다.

> Genre-first Korean writing skill for Claude Code, with a deterministic checker (standard library only, no LLM call).

## 무엇을 하나

1. **장르가 말투를 정한다.** 자기소개서는 합쇼체 서술문, 제안서는 개조식과 한 가지 종결 체계,
   대국민 안내는 명령형 명사 종결 없이, 화면 문구는 서비스 전체에서 한 가지 말투로 쓴다.
   장르 기준에서 벗어난 문장을 찾아낸다.
2. **근거가 있는 AI 문체 신호만 잡는다.** 공개 자료 75곳(논문 25편, 국립국어원·행정 지침, 기업 UX 라이팅 가이드)을
   조사하고, 실제 원고와 사람이 쓴 문서로 오탐을 재서 남긴 규칙만 쓴다.
3. **윤문 전후 사실을 대조한다.** 숫자·로마자 낱말·인용한 말이 빠지거나 새로 생기면 알린다.
   새로 생긴 숫자는 윤문 중에 지어낸 사실일 수 있다.

## 설치

**스킬로 쓰기 (Claude Code)**

```bash
git clone https://github.com/kimjusnu/looks_like_korean.git
# 스킬 폴더를 Claude Code 사용자 스킬 위치에 연결한다 (macOS·Linux 예시)
ln -s "$(pwd)/looks_like_korean/skills/looks-like-korean" ~/.claude/skills/looks-like-korean
```

Windows에서는 `skills\looks-like-korean` 폴더를 `%USERPROFILE%\.claude\skills\` 아래로 복사하거나 연결한다.
스킬은 검사 엔진을 `스킬 폴더/../../src`에서 찾으므로 저장소 전체를 받아 둔다.

**검사 엔진만 쓰기**

```bash
pip install git+https://github.com/kimjusnu/looks_like_korean.git
looks-like-korean check 초안.md --genre self-intro
```

설치 없이 저장소에서 바로 돌리려면 `PYTHONPATH=src python -m looks_like_korean ...`.
Windows 콘솔에서 한글이 깨지면 `PYTHONIOENCODING=utf-8`을 붙인다.

## 사용

```bash
# 장르 기준 검사: 경고는 고치고, 검토는 다시 읽고 판단한다
looks-like-korean check 초안.md --genre self-intro
looks-like-korean check 문구.txt --genre ui --strict      # 경고가 있으면 종료 코드 1

# 윤문 전후 사실 대조
looks-like-korean facts 원문.md 수정문.md --strict

# 기계 판독용 출력
looks-like-korean check 초안.md --genre proposal --json
```

출력 예 (제목 한 줄과 본문 세 문장으로 된 `초안.md`):

```
■ 초안.md
장르: 자기소개서 · 기준 말투: 합쇼체(-습니다) (장르 고정)
문장 끝 높임 등급: 합쇼체(-습니다) 2 · 해요체(-어요) 1 · 해라체(-다) 0

경고 1건 · 검토 0건

[경고] REG-MIX · 문장 4
  「그때 처음으로 보람을 느꼈어요.」
  문제: 자기소개서에는 해요체(-어요)를 쓰지 않습니다.
  고치기: 문장 끝을 「-습니다」「-습니까」로 맞춥니다. 내용은 바꾸지 않습니다.
```

문장 번호는 제목을 포함해 센다.

### 장르

| `--genre` | 장르 | 말투 기준 | 쓰기 규칙 |
|---|---|---|---|
| `self-intro` | 자기소개서 | 합쇼체 고정, 명사형 종결 경고 | [self-intro.md](skills/looks-like-korean/references/self-intro.md) |
| `proposal` | 제안서·보고서 | 합쇼체·해라체 중 본문 다수결, 개조식 허용 | [proposal.md](skills/looks-like-korean/references/proposal.md) |
| `notice` | 공문·안내문 | 합쇼체·해요체 중 다수결, 명령형 명사 종결 경고 | [notice.md](skills/looks-like-korean/references/notice.md) |
| `ui` | 화면 문구 | 해요체·합쇼체 중 다수결, 한 서비스 한 말투 | [ui.md](skills/looks-like-korean/references/ui.md) |
| `general` | 일반 글 | 본문 다수결 | [general.md](skills/looks-like-korean/references/general.md) |

`--level formal|informal|plain`으로 기준 말투를 직접 지정할 수 있다.

### 규칙

| 등급 | 규칙 | 근거 |
|---|---|---|
| 경고 | 장르와 다른 높임 등급이 섞임 (`REG-MIX`, `REG-DOC`) | 국립국어원 공공언어 지침, UX 가이드 15곳 합의 |
| 경고 | 자기소개서·공문 서술문의 명사형 종결 (`REG-NOM`) | 국립국어원 보도자료·공문 지침 |
| 경고 | 본문 줄표 `—` (`PAT-DASH`) | 문장 부호 규정. 실측 AI 초안이 사람 글의 약 10배 |
| 경고 | 접속부사 뒤 쉼표 「따라서,」 (`PAT-CONJ-COMMA`) | 한글 맞춤법 문장 부호 원칙 |
| 경고 | 「단순한 X를 넘어」 (`PAT-FRAME`) | KCI 초록 40만 건 분석, 추세 대비 약 61배 |
| 경고 | 이중 피동 「되어지다」 (`PAT-DOUBLE-PASSIVE`) | 국립국어원 |
| 경고 | 자기소개서 자기 평가 마무리 (`PAT-SELF-EVAL`) | 자기소개서 오류 분석 연구, 결론부 오류 1위 |
| 경고 | 원인 없는 화면 오류 문구 (`PAT-UI-GENERIC-ERROR`) | UX 가이드 10곳 합의 |
| 검토 | 번역 투, 상투 틀, 과장 수식, 100자 넘는 문장, 화면 문구의 사과·느낌표·과한 요청·기계식 문구·감탄사, 이모지 | 정상 쓰임도 많아 글쓴이가 판단 |

규칙 코드와 정규식은 [`patterns.py`](src/looks_like_korean/patterns.py)·[`genre.py`](src/looks_like_korean/genre.py)에,
조사 근거는 [`docs/research/`](docs/research/)에 있다.

## 측정한 것

[`docs/research/measurements.md`](docs/research/measurements.md)에 원고 없이 수치만 남긴다.

- 실제 공모 제안서 59편(5,273문장): 말투 섞임 경고를 첫 구현 79건에서 8건으로 줄였고, 8건 중 6건이 맞게 잡은 것이었다.
- 사람이 쓴 공공·학술 문서 7편을 기준선으로 비교: 줄표는 AI 초안이 약 10배 많아 경고로 둔다.
  반대로 **연결어미 뒤 쉼표**는 학생 논술문 연구에서 가장 강한 AI 신호였지만, 격식 문서에서는 사람도
  21.5%를 찍어 AI 초안(19.3%)과 차이가 없었다. 그래서 경고에서 뺐다.

## 처음 버전에서 배운 것

v0.1.0은 「종결어미를 다양하게 바꾸면 더 사람 같아진다」고 보고 리듬 지표를 만들었다.
직접 만든 예문 7쌍에서 어미를 다양하게 바꾼 쪽이 **모두 더 나빴다.** 업무 메모에 없던 대화가 생기고,
자기소개서가 반말로 끝나고, 공문에 해요체 질문이 섞였다. 지표는 움직였지만 글은 나빠졌다.

실패의 원인은 장르와 독자에 맞지 않는 말투였다. 그래서 방향을 뒤집어, 이제는 **장르 기준에서 벗어난 문장**을 찾는다.
리듬 지표(`score`, `compare` 명령)는 기록용으로 남아 있지만 품질 지표가 아니다.
당시 기록은 [`docs/RESEARCH.md`](docs/RESEARCH.md)와 [`eval/counterexamples.json`](eval/counterexamples.json)에 있다.

## 하지 않는 것

- **AI 탐지기가 아니다.** 사람이 썼는지 판정하지 않는다. 탐지기 점수를 맞추려는 용도로 쓰지 않는다.
- **문장을 대신 고치지 않는다.** 엔진은 검사만 한다. 고치는 일은 스킬 절차를 따르는 Claude나 사람이 한다.
- **문장 단위 윤문 전문 도구가 아니다.** 번역투·상투구를 깊게 다듬으려면
  [`im-not-ai`](https://github.com/epoko77-ai/im-not-ai)(MIT)를 함께 쓴다. 이 저장소는 그 도구가 다루지 않는
  장르·말투, 자기소개서 내용, 화면 문구를 맡는다.

## 한계

- 한글로 쓴 수(「스무 명」)와 한글 고유명사는 사실 대조에서 뽑지 못한다.
- 자기소개서·공문·화면 문구는 아직 사람 글 기준선으로 오탐을 재지 않았다.
- 장면이 구체적인지, 논리가 맞는지는 판단하지 못한다. 스킬 절차의 체크리스트로 사람이 확인한다.

## 개발

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

표준 라이브러리만 쓴다. 네트워크와 모델 호출이 없어서 같은 입력에는 항상 같은 결과가 나온다.
브랜치·PR 규칙은 [`docs/BRANCHING.md`](docs/BRANCHING.md)와 [`CLAUDE.md`](CLAUDE.md).
공개 예문은 모두 직접 지은 것만 쓴다. 실제 사람의 글은 올리지 않는다.

MIT. [LICENSE](LICENSE)
