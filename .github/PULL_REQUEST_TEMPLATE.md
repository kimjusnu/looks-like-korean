<!--
이 저장소의 검토 기준은 「코드가 동작하는가」 가 아니라 「측정이 신뢰할 만한가」 다.
PR 설명란은 코드가 아니라 근거를 설명하는 칸이다.
-->

## 무엇을 고쳤는가 (한 줄)

<!-- 한 문장. 지표를 추가했으면 지표 이름, 버그였으면 무엇이 잘못 세어졌는지. -->

## 왜 — 계측값이 어떻게 바뀌었는가 (숫자로)

<!--
설명만 하지 말고 수치를 붙인다. 「더 자연스러워 보인다」 는 근거가 아니다.

python -m looks_like_korean compare before.md after.md

예시 형식:
  uniformity_index  before 1.000 → after 0.125
  문서 9쌍 중 uniformity_index 이 내려간 쌍 9/9 (이전 7/9)
  실행 환경: Python 3.12 / Windows 11 / commit abc1234
-->

| 지표 | 이전 | 이후 |
|---|---|---|
| | | |

- 표본: <!-- 몇 건, 어느 장르인지. -->
- 실행 환경: <!-- Python 버전 / OS / 커밋. -->

## 재현 방법

```bash
# 그대로 복사해 실행되게 쓴다
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m looks_like_korean compare before.md after.md
```

## 체크리스트

- [ ] **사실 불변** — `eval/examples.json` 예문을 손댔다면, `kept_facts` 에 적힌 수치·고유명사·조건이 수정 전후 원고에 **문자 그대로** 들어 있다. 의역으로 바꾸지 않았다.
- [ ] **분량 ±3%** — 수정 전후 원고의 분량 차이가 ±3% 안이다. (리듬이 아니라 길이를 바꾼 결과를 지표 차이로 보고하지 않는다)
- [ ] **테스트 통과** — `python -m unittest discover -s tests` 가 초록색이다.
- [ ] **테스트 결과 붙임** — 아래 칸에 실제 출력 붙였다. 「통과함」 으로만 쓰지 않는다.
- [ ] **결정론 유지** — 같은 입력 → 같은 출력. 표준 라이브러리 외 의존성, 네트워크 호출, 모델 호출을 추가하지 않았다.
- [ ] **방향표(가설) 수정이 포함됐다면** — `src/looks_like_korean/metrics.py` 의 방향을 바꿨다면, `docs/RESEARCH.md` 에 **반증 조건과 함께** 근거를 적었다. 코드만 바꾸고 문서를 안 바꾸는 PR 은 받지 않는다.
- [ ] **예문은 자체 작성** — 실전 제출물·기관 공고문·실제 일반인의 참여 의견을 한 글자도 인용·복제·의역하지 않았다.

```
$ PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m unittest discover -s tests
<여기에 붙여넣기>
```

## 이 저장소에서 받지 않는 PR

**근거 없는 측정값에 맞춰 지표 방향표를 뒤집는 PR 은 받지 않습니다.**
그래서 하고 싶다면 `docs/RESEARCH.md` 에 **반증 조건과 함께** 기록하십시오.
가설을 뒤집는 것은 잘못이 아니고, 뒤집은 근거를 남기지 않는 것이 잘못입니다.
`docs/RESEARCH.md` 「The hypothesis」 절의 H1~H4 와 `research/measure.py` 의
표본·장르 게이트(장르 교집합 0 이면 AUC 을 내지 않는다)를 함께 읽어 주십시오.

리뷰어는 **수치 하나를 믿지 않습니다.** 표본 크기, 장르 대칭, 표본 오차,
재현 가능성을 먼저 봅니다. 수치가 좋아 보이는 것보다 그 수치가 **무엇을 재는
것인지**가 중요합니다.
