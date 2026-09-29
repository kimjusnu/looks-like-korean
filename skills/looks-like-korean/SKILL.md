---
name: looks-like-korean
description: Use when writing or revising Korean text that must not read as AI-written — 자기소개서(self-introductions), 제안서·보고서(proposals/reports), 공문·안내문(official notices), app/web UI copy(버튼·오류·빈 화면·확인 창 문구), and general prose such as blogs or emails. Also use when writing Korean UI strings in code. Triggers include "AI 어투", "AI 티", "사람이 쓴 것처럼", "자소서 다듬어", "문구 자연스럽게", "UX 라이팅". Picks the genre first, applies that genre's register and rules, then verifies with a deterministic checker (no LLM call) and a before/after fact diff.
---

# looks-like-korean

AI가 쓴 티가 나지 않는 한국어를 쓰고 고친다. 핵심은 세 가지다.

1. **장르가 말투를 정한다.** 자기소개서, 제안서, 공문, 화면 문구는 맞는 말투와 규칙이 다르다.
   종결어미를 「다양하게」 바꾸면 더 사람 같아진다는 주장은 근거가 없고, 이 저장소의 첫 버전이 7쌍 모두에서 실패했다.
2. **AI 글의 가장 큰 문제는 어투보다 내용이다.** 누구에게나 붙일 수 있는 문장, 장면과 수치가 없는 문장이 먼저 걸러진다.
3. **윤문은 문체만 바꾼다.** 숫자, 고유명사, 인용한 말은 그대로 둔다. 없는 사실을 지어내지 않는다.

근거는 저장소의 `docs/research/`(공개 자료 75곳 조사)와 `docs/research/measurements.md`(실제 원고 측정)에 있다.

## 검사 엔진 실행

표준 라이브러리만 쓰는 파이썬 패키지다. 이 스킬 폴더의 두 단계 위가 저장소 루트다.

```bash
# 설치 없이 (스킬 폴더 기준 ../../src)
PYTHONPATH="<이 스킬 폴더>/../../src" python -m looks_like_korean check 초안.md --genre self-intro
# 또는 저장소 루트에서 한 번 설치
pip install -e .
```

Windows 콘솔에서 한글이 깨지면 `PYTHONIOENCODING=utf-8`을 붙인다.

## 절차

### 1. 장르를 정한다

| 장르 | `--genre` | 먼저 읽을 규칙 |
|---|---|---|
| 자기소개서 | `self-intro` | `references/self-intro.md` |
| 제안서·보고서·기획서 | `proposal` | `references/proposal.md` |
| 공문·공지·대국민 안내문 | `notice` | `references/notice.md` |
| 앱·웹 화면 문구 | `ui` | `references/ui.md` |
| 블로그·수기·메일·설명문 | `general` | `references/general.md` |

요청에서 장르가 분명하지 않으면 한 번만 묻는다. **해당 규칙 문서를 읽기 전에는 쓰지 않는다.**

### 2. 재료를 확인한다

- **자기소개서:** 문항 원문, 글자 수, 지원 회사·직무의 고유 정보, 본인의 실제 경험(날짜·장소·결정·결과 수치).
  재료가 없으면 무엇이 없는지 묻는다. **확인되지 않은 경험·수치·성과를 지어내지 않는다.**
- **화면 문구:** 서비스가 이미 쓰는 말투(기존 문구에서 「-요.」와 「-니다.」를 세어 많은 쪽), 문구가 놓일 자리(버튼·토스트·확인 창·빈 화면·입력 오류).
  자리를 모르면 먼저 묻는다.
- **제안서·공문:** 서식이 정한 문체와 분량, 숫자의 출처.

### 3. 쓰거나 고친다

- 규칙 문서의 「쓰는 규칙」을 따른다.
- 고칠 때는 **뜻 단위로 다시 쓴다.** 금지어를 동의어로 바꾸는 것으로 끝내지 않는다. AI 어휘는 모델 세대마다 바뀐다.
- 사람이 쓴 초안이 있으면 그 초안에서 출발한다. 처음부터 새로 쓰는 것보다 AI 티가 덜 생긴다.
- 문장 단위의 번역투·상투구를 더 깊이 다듬어야 하면, 설치돼 있는 경우 `humanize-korean` 스킬을 이어서 쓸 수 있다.
  단, 그 뒤에도 아래 4~5단계를 다시 돌린다.

### 4. 기계 검사를 돌린다

```bash
python -m looks_like_korean check 초안.md --genre <장르>
```

- **경고는 모두 고친다.** 고치지 않을 경고가 있으면 그 이유를 보고에 적는다.
- **검토는 다시 읽고 판단한다.** 정상 쓰임도 많은 신호라 모두 고칠 필요는 없다.
- 본인이 장르 기본과 다른 말투를 원하면 `--level formal|informal|plain`으로 기준을 바꾼다.
- 화면 문구는 문구를 한 줄에 하나씩 적은 텍스트 파일을 만들어 검사한다. 빈 줄로 문구를 나누면 서로 다른 문장으로 본다.

### 5. 고쳤다면 사실을 대조한다

```bash
python -m looks_like_korean facts 원문.md 수정문.md --strict
```

- 「빠진 것」은 되살리거나, 일부러 뺀 이유를 적는다.
- 「새로 생긴 것」은 근거를 확인한다. **근거 없이 생긴 숫자는 지운다.**

### 6. 사람이 읽고 판단할 항목을 확인한다

규칙 문서의 체크리스트를 문단마다 확인한다. 기계 검사로는 장면·구체성·논리 연결을 판단할 수 없다.

### 7. 보고한다

- 바꾼 문단마다 고치기 전 → 고친 후와 이유
- `check` 결과(경고·검토 건수)와 `facts` 결과
- 남은 검토 항목과, 본인에게 확인이 필요한 사실

## 하지 않는 것

- 종결어미를 일부러 돌려쓰지 않는다. 장르가 한 가지 말투를 요구하면 끝까지 그 말투가 맞다.
- 문서 전체의 말투를 장르 기준과 다른 쪽으로 일괄 변환하지 않는다.
- AI 탐지기 점수를 맞추려고 문장을 비틀지 않는다. 탐지기는 오판이 많고, 읽는 사람이 보는 것은 구체성이다.
- 인용, 법령 조문, 표, 코드, 고정된 서식 문구는 고치지 않는다.
- 없는 경험·감정·수치로 「사람 냄새」를 만들지 않는다.

## 검사 엔진이 못 하는 것

- 한글로 쓴 수(「스무 명」)와 한글 고유명사의 사실 대조
- 자기소개서·공문·화면 문구의 사람 글 기준선 측정(제안서만 실측, `docs/research/measurements.md`)
- 문맥상 뜻이 맞는지, 장면이 구체적인지 판단(6단계에서 사람이 확인)
