"""cli.py — 명령행 인터페이스.

    python -m looks_like_korean score 파일.md
    python -m looks_like_korean score 파일.md --json
    python -m looks_like_korean compare 원문.md 수정문.md
    python -m looks_like_korean compare 원문.md 수정문.md --json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .metrics import METRIC_KEYS, analyze
from .report import analysis_to_dict, render_compare, render_score, to_json

__all__ = ["main"]


def _force_utf8() -> None:
    """Windows 콘솔(cp949/cp1252)에서도 한글이 깨지지 않게 한다.

    표준출력이 StringIO 로 redirected 된 테스트 환경에서는 reconfigure 가
    없을 수 있으므로 getattr 로 감싼다. 실패해도 조용히 넘어간다 —
    계측값이 깨지는 것과 출력 인코딩이 깨지는 것 중 후자는 치명적이지 않다.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError, AttributeError):
            pass


def _read_text(path: str) -> str:
    """UTF-8 로 읽는다. BOM 이 붙은 파일도 같이 처리한다."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"오류 · 파일이 없습니다: {path}")
    if p.is_dir():
        raise SystemExit(f"오류 · 디렉터리입니다: {path}")
    data = p.read_bytes()
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("cp949", errors="replace")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="looks_like_korean",
        description="결정론적 한국어 리듬 계측 엔진 (LLM 호출 없음 · 결정론적)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="원고 한 편의 지표를 낸다")
    p_score.add_argument("file", help="측정할 마크다운/텍스트 파일")
    p_score.add_argument("--json", action="store_true", help="기계 판독용 JSON")

    p_cmp = sub.add_parser("compare", help="두 원고를 나란히 비교한다")
    p_cmp.add_argument("before", help="원문 파일")
    p_cmp.add_argument("after", help="수정문 파일")
    p_cmp.add_argument("--json", action="store_true", help="기계 판독용 JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    args = _build_parser().parse_args(argv)

    if args.command == "score":
        text = _read_text(args.file)
        analysis = analyze(text)
        if args.json:
            print(to_json(analysis_to_dict(analysis, Path(args.file).name)))
        else:
            print(render_score(analysis, Path(args.file).name))
        return 0

    text_a = _read_text(args.before)
    text_b = _read_text(args.after)
    a = analyze(text_a)
    b = analyze(text_b)
    if args.json:
        print(to_json({
            "command": "compare",
            "metric_order": list(METRIC_KEYS),
            "before": analysis_to_dict(a, Path(args.before).name),
            "after": analysis_to_dict(b, Path(args.after).name),
        }))
    else:
        print(render_compare(a, b, Path(args.before).name, Path(args.after).name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
