"""measure.py — 라벨 코퍼스로 지표 분리도(AUC)를 재는 재현 하네스.

    python research/measure.py --corpus research-private/corpus
    python research/measure.py --corpus <DIR> --report docs/MEASUREMENT.md

왜 공개 저장소에 있는가
----------------------
이 도구의 결과가 「한국어 리듬 지표가 사람/기계를 갈라내는가」 라는 질문의
유일한 근거다. 근거를 남겨야 남이 검토할 수 있다. 없으면 marketing 이 된다.

가드가 있는 이유
--------------
AUC 는 두 그룹이 **같은 조건**에서 나왔을 때만 의미를 갖는다. 장르가 다르면
장르 차이를 재는 것이고, 표본이 한쪽에 몰리면 표본 오차다. 그래서 이 스크립트는
측정 조건이 깨졌을 때 숫자를 내지 않고 **측정 불가를 명시한다**.
숫자가 나오는 것보다 숫자가 나오지 않는 것이 정직한 결과다.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from looks_like_korean.metrics import analyze  # noqa: E402

# AUC 0.5 는 무작위. 0.70 미만이면 「약한 분리」, 0.75 이상이면 계획서의 진행 게이트.
AUC_NOISE = 0.50
AUC_WEAK = 0.70
AUC_GATE = 0.75


@dataclass
class Doc:
    path: Path
    label: str
    genre: str
    chars: int
    values: dict[str, float]


def load_manifest(corpus: Path) -> list[dict]:
    path = corpus / "MANIFEST.tsv"
    if not path.exists():
        raise SystemExit(f"매니페스트가 없다: {path}")
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def load_docs(corpus: Path, manifest: list[dict], min_chars: int) -> list[Doc]:
    docs: list[Doc] = []
    for row in manifest:
        label, genre = row.get("label", ""), row.get("genre", "")
        try:
            chars = int(row.get("chars") or 0)
        except ValueError:
            chars = 0
        path = corpus / row["file"]
        if not path.exists() or chars < min_chars:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        result = analyze(text)
        if not result.sentences:
            continue
        docs.append(
            Doc(
                path=path,
                label=label,
                genre=genre,
                chars=len(text),
                values={k: m.value for k, m in result.metrics.items()},
            )
        )
    return docs


def auc(machine: list[float], human: list[float]) -> float:
    """Mann-Whitney U 기반 AUC. machine 쪽 값이 클 때 1 에 가까워진다."""
    if not machine or not human:
        return AUC_NOISE
    pairs = [(v, 0) for v in machine] + [(v, 1) for v in human]
    pairs.sort(key=lambda p: p[0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_sum = sum(r for r, (_, g) in zip(ranks, pairs) if g == 0)
    n1, n2 = len(machine), len(human)
    return (rank_sum - n1 * (n1 + 1) / 2) / (n1 * n2)


def genre_overlap(human: list[Doc], machine: list[Doc]) -> tuple[float, list[str]]:
    h = {d.genre for d in human}
    m = {d.genre for d in machine}
    union = h | m
    if not union:
        return 0.0, []
    shared = sorted(h & m)
    return len(shared) / len(union), shared


def bootstrap_ci(
    machine: list[float], human: list[float], rounds: int = 2000, seed: int = 20260929
) -> tuple[float, float]:
    """표본이 작을 때 AUC 가 얼마나 흔들리는지 보여준다. 95% 구간."""
    rng = random.Random(seed)
    out = []
    for _ in range(rounds):
        a = [machine[rng.randrange(len(machine))] for _ in machine]
        b = [human[rng.randrange(len(human))] for _ in human]
        out.append(auc(a, b))
    out.sort()
    return out[int(0.025 * rounds)], out[int(0.975 * rounds)]


def verdict(value: float) -> str:
    if value >= AUC_GATE:
        return "게이트 통과"
    if value >= AUC_WEAK:
        return "약함 — 보류"
    if value <= 1 - AUC_WEAK:
        return "역전 — 방향 재검토"
    return "무차별"


def main() -> int:
    ap = argparse.ArgumentParser(description="한국어 리듬 지표의 사람/기계 분리도 측정")
    ap.add_argument("--corpus", default="research-private/corpus", type=Path)
    ap.add_argument("--genre", default=None, help="장르 하나로 좁힌다 (양쪽에 있어야 유효)")
    ap.add_argument("--min-chars", type=int, default=800)
    ap.add_argument("--min-docs", type=int, default=5)
    ap.add_argument("--report", type=Path, default=None, help="마크다운 리포트 경로")
    args = ap.parse_args()

    manifest = load_manifest(args.corpus)
    docs = load_docs(args.corpus, manifest, args.min_chars)
    if args.genre:
        docs = [d for d in docs if d.genre == args.genre]

    human = [d for d in docs if d.label == "human"]
    machine = [d for d in docs if d.label == "machine"]
    lines: list[str] = []
    say = lines.append

    say("# 분리도 측정 리포트")
    say("")
    say(f"코퍼스 `{args.corpus}` · 최소 {args.min_chars}자 · "
        f"장르 필터 `{args.genre or '없음'}`")
    say("")

    # ---- 게이트: 이 숫자를 믿어도 되는가 ----
    blocked: list[str] = []
    if len(human) < args.min_docs or len(machine) < args.min_docs:
        blocked.append(
            f"표본 부족 (human {len(human)} / machine {len(machine)}, "
            f"최소 {args.min_docs} 필요)"
        )
    ratio, shared = genre_overlap(human, machine)
    if ratio == 0.0:
        blocked.append("장르 교집합 0 — 비교 대상이 같은 문종이 아니다")
    elif shared and not args.genre:
        say(f"장르 교집합 {ratio:.2f} — {', '.join(shared)}")
        say("")
        say("> ⚠ 교집합 장르가 있어도 이 리포트는 **장르 전체를 섞어** 쟀다.")
        say("> `--genre` 로 한 장르만 좁혀 다시 재라. 0.70 을 넘는 값이")
        say("> 장르 하나에서 나올 때만 이 프로젝트의 진짜 근거가 된다.")
        say("")

    if blocked:
        say("## 측정 불가")
        say("")
        for b in blocked:
            say(f"- ⛔ {b}")
        say("")
        say("**AUC 을 내지 않는다.** 두 그룹이 같은 조건에서 나오지 않았으므로")
        say("어떤 수치를 넣어도 장르 차이 또는 표본 오차를 재는 것이 된다.")
        _emit("\n".join(lines), args.report)
        return 2

    say(f"표본: human {len(human)}건 / machine {len(machine)}건")
    say("")

    keys = list(human[0].values)
    rows = []
    for key in keys:
        a = [d.values[key] for d in machine]
        b = [d.values[key] for d in human]
        value = auc(a, b)
        lo, hi = bootstrap_ci(a, b)
        rows.append((key, value, lo, hi, verdict(value)))
    rows.sort(key=lambda r: -abs(r[1] - AUC_NOISE))

    say("| 지표 | AUC | 95% 구간 | 판정 |")
    say("|---|---|---|---|")
    for key, value, lo, hi, v in rows:
        say(f"| `{key}` | {value:.3f} | {lo:.2f}–{hi:.2f} | {v} |")

    best = rows[0]
    say("")
    say(f"최고 분리도: `{best[0]}` AUC {best[1]:.3f} → {best[4]}")
    say(f"진행 게이트는 AUC ≥ {AUC_GATE} 다.")
    _emit("\n".join(lines), args.report)
    return 0


def _emit(text: str, report: Path | None) -> None:
    print(text)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(text + "\n", encoding="utf-8")
        print(f"\n→ {report}")


if __name__ == "__main__":
    raise SystemExit(main())
