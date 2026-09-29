"""tests/test_genre.py — 장르별 말투 일치 검사 회귀 테스트.

예문은 모두 직접 지은 합성 문장이다. 외부 코퍼스에 기대지 않는다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from looks_like_korean.eomi import extract_blocks, segment  # noqa: E402
from looks_like_korean.genre import check_register, speech_level  # noqa: E402


def rules(report) -> list[tuple[str, int | None]]:
    return [(f.rule, f.sentence_index) for f in report.findings]


FORMAL_INTRO = (
    "저는 작은 문제를 끝까지 파고드는 편입니다. "
    "지난해 동아리 예약 시스템을 직접 만들었습니다. "
    "사용자 스무 명이 매주 이 시스템을 썼습니다."
)


class TestBlockKind(unittest.TestCase):
    def test_list_and_heading_are_marked(self):
        text = "## 경험\n\n본문 문장입니다.\n\n- 목록 항목임\n"
        kinds = [(s.kind, s.text) for s in segment(text)]
        self.assertEqual(kinds, [("heading", "경험"), ("prose", "본문 문장입니다."), ("list", "목록 항목임")])

    def test_heading_glued_to_body_is_prose(self):
        # 빈 줄 없이 붙은 제목은 기존 규칙대로 본문과 한 블록이 된다.
        text = "## 경험\n본문 문장입니다."
        self.assertEqual([s.kind for s in segment(text)], ["prose"])

    def test_extract_blocks_unchanged(self):
        text = "첫 문단입니다.\n\n- 항목 하나\n- 항목 둘\n\n끝 문단입니다."
        self.assertEqual(extract_blocks(text), ["첫 문단입니다.", "항목 하나", "항목 둘", "끝 문단입니다."])


class TestSpeechLevel(unittest.TestCase):
    def level_of(self, sentence: str) -> str | None:
        return speech_level(segment(sentence)[0])

    def test_levels(self):
        self.assertEqual(self.level_of("자료를 정리했습니다."), "formal")
        self.assertEqual(self.level_of("자료를 정리했어요."), "informal")
        self.assertEqual(self.level_of("자료를 정리했다."), "plain")

    def test_question_levels(self):
        self.assertEqual(self.level_of("삭제하시겠습니까?"), "formal")
        self.assertEqual(self.level_of("삭제할까요?"), "informal")
        self.assertEqual(self.level_of("무엇이 문제인가?"), "plain")

    def test_nominal_has_no_level(self):
        self.assertIsNone(self.level_of("자료 정리 완료함"))


class TestSelfIntro(unittest.TestCase):
    def test_all_formal_is_clean(self):
        self.assertEqual(check_register(FORMAL_INTRO, "self-intro").findings, ())

    def test_informal_sentence_is_flagged(self):
        text = FORMAL_INTRO + " 그때 처음으로 보람을 느꼈어요."
        report = check_register(text, "self-intro")
        self.assertEqual(rules(report), [("REG-MIX", 3)])
        self.assertIn("자기소개서에는", report.findings[0].message)
        self.assertEqual(report.findings[0].severity, "warn")

    def test_whole_document_in_plain_is_one_finding(self):
        text = "나는 문제를 끝까지 판다. 동아리 예약 시스템을 만들었다. 스무 명이 매주 썼다."
        report = check_register(text, "self-intro")
        self.assertEqual(rules(report), [("REG-DOC", None)])
        self.assertIn("--level plain", report.findings[0].suggestion)

    def test_forced_level_accepts_plain_document(self):
        text = "나는 문제를 끝까지 판다. 동아리 예약 시스템을 만들었다. 스무 명이 매주 썼다."
        report = check_register(text, "self-intro", level="plain")
        self.assertEqual(report.findings, ())
        self.assertEqual(report.target_reason, "직접 지정")

    def test_nominal_prose_is_warned(self):
        text = FORMAL_INTRO + " 그 경험으로 협업의 가치를 배움."
        self.assertEqual(rules(check_register(text, "self-intro")), [("REG-NOM", 3)])


class TestProposal(unittest.TestCase):
    def test_majority_decides_and_minority_is_flagged(self):
        text = (
            "현재 주민 대부분이 신청 방법을 모릅니다. 안내문은 구청 누리집에만 있습니다. "
            "그래서 신청률이 낮다. 우리는 문자 안내를 제안합니다."
        )
        report = check_register(text, "proposal")
        self.assertEqual(report.target_level, "formal")
        self.assertEqual(report.target_reason, "본문 다수결")
        self.assertEqual(rules(report), [("REG-MIX", 2)])

    def test_list_items_may_be_nominal(self):
        text = "추진 계획은 다음과 같습니다.\n\n- 문자 안내 시범 운영\n- 신청 절차 간소화함\n"
        self.assertEqual(check_register(text, "proposal").findings, ())

    def test_nominal_prose_is_review_only(self):
        text = "추진 계획은 다음과 같습니다. 1단계는 석 달 동안 진행합니다. 1단계에서 문자 안내를 시범 운영함."
        report = check_register(text, "proposal")
        self.assertEqual(rules(report), [("REG-NOM", 2)])
        self.assertEqual(report.findings[0].severity, "review")

    def test_bullet_style_document_skips_nominal_check(self):
        # 목록 기호 없이 줄마다 명사형으로 끝내는 개조식 제안서
        text = "현재 신청률이 낮음\n안내문이 누리집에만 있음\n문자 안내를 도입하면 신청률이 오를 것으로 기대됨\n"
        report = check_register(text, "proposal")
        self.assertTrue(report.bullet_style)
        self.assertEqual(report.findings, ())

    def test_negative_nominal_is_not_plain(self):
        # 「~하지 않음」은 해라체가 아니라 개조식 부정 명사형이다.
        text = "신청 절차는 그대로 둡니다. 새 시스템은 만들지 않음. 기존 창구에서 함께 받습니다. 예산이 더 들지 않습니다."
        report = check_register(text, "proposal")
        self.assertNotIn("REG-MIX", [f.rule for f in report.findings])
        self.assertEqual(report.level_counts, {"formal": 3})

    def test_noun_ending_da_is_not_plain(self):
        text = "사고 통계를 정리했습니다. 비교한 여섯 개 도 가운데 최다. 원인은 세 가지입니다."
        self.assertNotIn("REG-MIX", [f.rule for f in check_register(text, "proposal").findings])

    def test_item_like_lines_skip_nominal_check(self):
        text = (
            "추진 계획은 다음과 같습니다. 예산은 이미 확보했습니다. 담당 부서도 정했습니다.\n\n"
            "◦ 예산 증액을 요구하지 않음\n\n제안분야: 행정 혁신\n\n〔그림 2〕 신청률 변화"
        )
        self.assertEqual(check_register(text, "proposal").findings, ())

    def test_quoted_speech_is_skipped(self):
        text = "민원인에게는 안내 문자를 보냅니다. 문자에는 「같은 민원이 이미 접수됐다」라고 적습니다. 담당자는 한 번만 답합니다."
        self.assertEqual(check_register(text, "proposal").findings, ())
        text2 = '한 줄로 요약합니다. 핵심은 이것입니다: "공동을 찾지 않는다.'
        self.assertEqual(check_register(text2, "proposal").findings, ())


class TestNotice(unittest.TestCase):
    def test_command_nominal_is_warned(self):
        text = "신청서는 이번 달 말까지 내 주십시오. 기한을 넘긴 서류는 받지 않을 것."
        report = check_register(text, "notice")
        self.assertEqual(rules(report), [("REG-NOM", 1)])
        self.assertEqual(report.findings[0].severity, "warn")


class TestUi(unittest.TestCase):
    def test_formal_question_in_informal_product(self):
        text = "저장했어요. 사진을 올려 주세요. 이 글을 삭제하시겠습니까?"
        report = check_register(text, "ui")
        self.assertEqual(report.target_level, "informal")
        self.assertEqual(rules(report), [("REG-MIX", 2)])

    def test_trailing_emoji_does_not_hide_level(self):
        text = "저장했어요. 사진을 올려 주세요. 알 수 없는 오류가 발생했습니다 😢"
        report = check_register(text, "ui")
        self.assertEqual(report.level_counts, {"informal": 2, "formal": 1})
        self.assertEqual(rules(report), [("REG-MIX", 2)])

    def test_headings_are_ignored(self):
        text = "## 설정\n\n알림을 켰어요.\n\n## 계정\n\n비밀번호를 바꿨어요."
        self.assertEqual(check_register(text, "ui").findings, ())


class TestCli(unittest.TestCase):
    def run_cli(self, text: str, *extra: str) -> tuple[int, str]:
        import contextlib
        import io
        import tempfile

        from looks_like_korean.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(text, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["check", str(path), *extra])
        return code, out.getvalue()

    def test_strict_exit_code(self):
        mixed = FORMAL_INTRO + " 그때 처음으로 보람을 느꼈어요."
        self.assertEqual(self.run_cli(mixed, "--genre", "self-intro", "--strict")[0], 1)
        self.assertEqual(self.run_cli(mixed, "--genre", "self-intro")[0], 0)
        self.assertEqual(self.run_cli(FORMAL_INTRO, "--genre", "self-intro", "--strict")[0], 0)

    def test_json_output(self):
        import json

        code, out = self.run_cli(FORMAL_INTRO + " 보람을 느꼈어요.", "--genre", "self-intro", "--json")
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["target_level"], "formal")
        self.assertEqual(payload["counts"], {"warn": 1, "review": 0})
        self.assertEqual(payload["findings"][0]["rule"], "REG-MIX")


class TestErrors(unittest.TestCase):
    def test_unknown_genre(self):
        with self.assertRaises(ValueError):
            check_register("문장입니다.", "poem")

    def test_unknown_level(self):
        with self.assertRaises(ValueError):
            check_register("문장입니다.", "general", level="banmal")


if __name__ == "__main__":
    unittest.main()
