"""tests/test_tone.py — AI 말버릇 틀(tone.py) 회귀 테스트. 예문은 직접 지었다."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from looks_like_korean.patterns import check_tone  # noqa: E402
from looks_like_korean.tone import TONE_RULES  # noqa: E402


def codes(text: str, genre: str) -> list[str]:
    return [f.rule for f in check_tone(text, genre)]


class TestTable(unittest.TestCase):
    def test_rules_compile_and_codes_are_unique(self):
        for code, severity, _name, pattern, _fix, _genres, scope in TONE_RULES:
            re.compile(pattern)
            self.assertIn(severity, ("warn", "review"), code)
            self.assertIn(scope, ("text", "raw"), code)
        all_codes = [r[0] for r in TONE_RULES]
        self.assertEqual(len(all_codes), len(set(all_codes)))


class TestRules(unittest.TestCase):
    def test_flatter_in_chat(self):
        self.assertIn("TONE-FLATTER", codes("좋은 질문이에요. 결론부터 말하면 됩니다.", "chat"))
        self.assertIn("TONE-FLATTER", codes("핵심을 정확히 짚으셨네요. 회의는 줄이는 게 맞습니다.", "chat"))
        self.assertNotIn("TONE-FLATTER", codes("좋은 질문이에요. 결론부터 말하면 됩니다.", "general"))

    def test_quoted_phrases_are_not_the_writers_habit(self):
        text = "“좋은 질문이에요” 같은 첫 문장은 바로 티가 납니다. 첫 문장에는 판단을 씁니다."
        self.assertNotIn("TONE-FLATTER", codes(text, "chat"))

    def test_not_just_frame(self):
        self.assertIn("FRAME-NOT-JUST", codes("이 앱은 단순한 가계부가 아니라 습관 도구입니다.", "general"))
        self.assertNotIn("FRAME-NOT-JUST", codes("이 앱은 지난달보다 더 쓴 항목을 알려 줍니다.", "general"))

    def test_offer_more_ending(self):
        text = "송별 메시지를 썼습니다.\n\n어떤 분위기인지 알려 주시면 더 맞춤형으로 다듬어 드릴게요."
        self.assertIn("TONE-OFFER-MORE", codes(text, "general"))

    def test_meta_preamble_only_at_start(self):
        self.assertIn("TONE-META-PREAMBLE", codes("아래는 요청하신 지원 동기입니다.\n\n저는 예약 사이트를 만들었습니다.", "self-intro"))
        self.assertNotIn("TONE-META-PREAMBLE", codes("저는 예약 사이트를 만들었습니다.\n\n아래는 사용 기록입니다.", "self-intro"))

    def test_bold_is_genre_scoped(self):
        text = "회의를 **줄이는** 게 맞습니다."
        self.assertIn("FMT-BOLD", codes(text, "chat"))
        self.assertNotIn("FMT-BOLD", codes(text, "proposal"))


class TestGrouping(unittest.TestCase):
    def test_one_finding_per_rule_with_count_and_line(self):
        text = "첫 줄입니다.\n**하나** 그리고 **둘**\n마지막 **셋**"
        bold = [f for f in check_tone(text, "chat") if f.rule == "FMT-BOLD"]
        self.assertEqual(len(bold), 1)
        self.assertIn("3곳", bold[0].message)
        self.assertEqual(bold[0].line, 2)
        self.assertIsNone(bold[0].sentence_index)


class TestErrors(unittest.TestCase):
    def test_unknown_genre(self):
        with self.assertRaises(ValueError):
            check_tone("문장입니다.", "poem")


if __name__ == "__main__":
    unittest.main()
