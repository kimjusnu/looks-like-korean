"""tests/test_facts.py — 윤문 전후 사실 보존 대조 회귀 테스트. 예문은 직접 지었다."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from looks_like_korean.facts import compare_facts, extract_facts  # noqa: E402

BEFORE = (
    "지난해 신청률은 12%였습니다. 참여 주민은 1,000명이고 기간은 3개월입니다. "
    "문자 안내는 KT 대량 발송 API로 보냅니다. 주민들은 「안내문을 못 봤다」고 답했습니다."
)


class TestExtract(unittest.TestCase):
    def test_numbers_latin_quotes(self):
        facts = extract_facts(BEFORE)
        for key in [("number", "12%"), ("number", "1000명"), ("number", "3개월"),
                    ("latin", "KT"), ("latin", "API"), ("quote", "안내문을 못 봤다")]:
            with self.subTest(key=key):
                self.assertEqual(facts[key], 1)

    def test_comma_and_space_are_normalized(self):
        self.assertEqual(extract_facts("1,000 명")[("number", "1000명")], 1)
        self.assertEqual(extract_facts("1000명")[("number", "1000명")], 1)

    def test_list_numbers_and_quarter(self):
        facts = extract_facts("1. 첫째 항목\n2. 둘째 항목\n예금 만기는 4분기에 몰려 있고 제목은 35자입니다.")
        self.assertNotIn(("number", "1"), facts)
        self.assertEqual(facts[("number", "4")], 0)          # 단위 없는 한 자리는 뺀다
        self.assertNotIn(("number", "4분"), facts)          # 「4분기」를 「4분」으로 자르지 않는다
        self.assertEqual(facts[("number", "35자")], 1)

    def test_html_comment_is_ignored(self):
        self.assertEqual(extract_facts("<!-- 99% 초안 메모 --> 본문입니다."), extract_facts("본문입니다."))


class TestCompare(unittest.TestCase):
    def test_style_only_rewrite_is_clean(self):
        after = (
            "지난해 신청률은 12%에 그쳤습니다. 주민 1,000명이 3개월 동안 참여합니다. "
            "안내 문자는 KT 대량 발송 API로 보냅니다. 주민들은 「안내문을 못 봤다」고 했습니다."
        )
        report = compare_facts(BEFORE, after)
        self.assertEqual(report.findings, ())

    def test_missing_and_added_are_warned(self):
        after = (
            "지난해 신청률은 30%였습니다. 참여 주민은 1,000명이고 기간은 3개월입니다. "
            "문자 안내는 대량 발송 API로 보냅니다. 주민들은 「안내문을 못 봤다」고 답했습니다."
        )
        report = compare_facts(BEFORE, after)
        self.assertEqual(
            [(f.rule, f.severity) for f in report.findings],
            [("FACT-MISSING", "warn"), ("FACT-MISSING", "warn"), ("FACT-ADDED", "warn")],
        )
        self.assertEqual([v for _, v, _, _ in report.missing], ["KT", "12%"])
        self.assertEqual([v for _, v, _, _ in report.added], ["30%"])
        self.assertIn("신청률은 30%", report.findings[-1].excerpt)

    def test_count_drop_is_missing(self):
        report = compare_facts("12%와 12%를 비교했습니다.", "12%를 비교했습니다.")
        self.assertEqual(report.missing, (("number", "12%", 2, 1),))


class TestCli(unittest.TestCase):
    def test_facts_command_strict(self):
        import contextlib
        import io
        import tempfile

        from looks_like_korean.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.md", Path(tmp) / "b.md"
            a.write_text(BEFORE, encoding="utf-8")
            b.write_text(BEFORE.replace("12%", "30%"), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["facts", str(a), str(b), "--strict"])
            self.assertEqual(code, 1)
            self.assertIn("FACT-ADDED", out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["facts", str(a), str(a), "--strict"]), 0)


if __name__ == "__main__":
    unittest.main()
