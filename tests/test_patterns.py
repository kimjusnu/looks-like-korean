"""tests/test_patterns.py — 문장 패턴 검사 회귀 테스트.

규칙마다 「걸려야 하는 문장」과 「걸리면 안 되는 문장」을 한 쌍씩 둔다.
예문은 모두 직접 지은 합성 문장이다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from looks_like_korean.eomi import segment  # noqa: E402
from looks_like_korean.patterns import check_patterns, connective_comma_rate  # noqa: E402


def codes(text: str, genre: str = "general") -> list[str]:
    return [f.rule for f in check_patterns(text, genre)]


class TestRulePairs(unittest.TestCase):
    CASES = [
        # (규칙, 장르, 걸려야 하는 문장, 걸리면 안 되는 문장)
        ("PAT-CONJ-COMMA", "general", "따라서, 비용이 줄어듭니다.", "따라서 비용이 줄어듭니다."),
        ("FRAME-NOT-JUST", "general", "이 앱은 단순한 가계부를 넘어 습관을 바꿉니다.", "이 앱은 가계부 기능만 있습니다."),
        ("PAT-DASH", "general", "이 기능은 — 누르지 않아도 — 저장합니다.", "2024–2025년 자료를 봤습니다."),
        ("PAT-DOUBLE-PASSIVE", "general", "결과가 공개되어졌습니다.", "결과가 공개되었습니다."),
        ("PAT-SELF-EVAL", "self-intro", "저는 이 직무에 적합한 인재라고 확신합니다.", "저는 예약 시스템을 두 달 동안 운영했습니다."),
        ("PAT-SELF-EVAL", "self-intro", "마감과 품질을 함께 지키는 개발자가 되겠습니다.", "입사 후에는 결제 오류 알림부터 손보겠습니다."),
        ("FRAME-LESSON", "self-intro", "이 경험을 통해 소통의 중요성을 배웠습니다.", "그 뒤로 회의 첫 10분은 남은 일부터 셉니다."),
        ("PAT-UI-GENERIC-ERROR", "ui", "오류가 발생했습니다.", "인터넷 연결이 끊겼어요. 연결되면 다시 시도해 주세요."),
        ("PAT-TRANS", "general", "회의를 통해 일정을 정했습니다.", "회의에서 일정을 정했습니다."),
        ("PAT-CLICHE", "proposal", "이러한 결과는 제도 개선이 필요함을 보여 줍니다.", "신청률이 12%에서 30%로 올랐습니다."),
        ("PAT-HYPE", "proposal", "획기적인 방식으로 문제를 풉니다.", "문자 안내로 문제를 풉니다."),
        ("PAT-UI-SORRY", "ui", "불편을 드려 죄송합니다.", "잠시 뒤 다시 시도해 주세요."),
        ("PAT-UI-PLEASE", "ui", "비밀번호를 입력해 주시기 바랍니다.", "비밀번호를 입력해 주세요."),
        ("PAT-UI-EXCLAIM", "ui", "저장했어요!", "저장했어요."),
        ("FMT-EMOJI", "ui", "업로드를 마쳤어요 🎉", "업로드를 마쳤어요."),
        ("PAT-UI-GENERIC-ERROR", "ui", "알 수 없는 오류가 발생했습니다 😢", "파일이 너무 커요. 20MB 이하로 올려 주세요."),
        ("PAT-UI-ROBOT", "ui", "입력값이 유효하지 않습니다.", "전화번호는 숫자만 입력해 주세요."),
        ("PAT-UI-INTERJECTION", "ui", "앗! 연결이 끊겼어요.", "연결이 끊겼어요."),
    ]

    def test_pairs(self):
        for rule, genre, hit, miss in self.CASES:
            with self.subTest(rule=rule):
                self.assertIn(rule, codes(hit, genre), hit)
                self.assertNotIn(rule, codes(miss, genre), miss)


class TestGenreScope(unittest.TestCase):
    def test_self_eval_only_in_self_intro(self):
        text = "저는 이 직무에 적합한 인재라고 확신합니다."
        self.assertNotIn("PAT-SELF-EVAL", codes(text, "proposal"))

    def test_ui_rules_only_in_ui(self):
        self.assertNotIn("PAT-UI-EXCLAIM", codes("드디어 끝났습니다!", "general"))

    def test_long_sentence_skips_list_items(self):
        long_item = "- " + "가" * 120 + "입니다."
        self.assertNotIn("PAT-LONG", codes(long_item, "proposal"))
        self.assertIn("PAT-LONG", codes("가" * 120 + "입니다.", "proposal"))

    def test_headings_and_quotes_are_skipped(self):
        self.assertEqual(codes("## 따라서, 이렇게 합니다\n\n본문입니다."), [])
        self.assertNotIn("PAT-TRANS", codes("그는 「회의를 통해 정하자」"))


class TestConnectiveComma(unittest.TestCase):
    AI_LIKE = (
        "현장 데이터를 모았고, 이를 바탕으로 개선안을 만들었으며, 결과를 팀에 공유했습니다. "
        "일정이 짧았지만, 모두가 참여했고, 목표를 넘겼습니다."
    )
    HUMAN_LIKE = (
        "현장 데이터를 모아 개선안을 만들었습니다. 결과는 팀에 공유했고 다음 주에 다시 봅니다. "
        "일정이 짧았지만 모두 참여했습니다."
    )

    def test_rate_counts(self):
        # 모았고, · 만들었으며, · 짧았지만, · 참여했고,
        self.assertEqual(connective_comma_rate(segment(self.AI_LIKE)), (4, 4))
        self.assertEqual(connective_comma_rate(segment(self.HUMAN_LIKE))[0], 0)

    def test_high_rate_is_one_review_plus_locations(self):
        found = check_patterns(self.AI_LIKE, "self-intro")
        doc = [f for f in found if f.rule == "PAT-COMMA-RATE"]
        self.assertEqual(len(doc), 1)
        self.assertEqual(doc[0].severity, "review")
        self.assertEqual(sum(f.rule == "PAT-COMMA" for f in found), 2)

    def test_low_rate_is_silent(self):
        self.assertNotIn("PAT-COMMA-RATE", codes(self.HUMAN_LIKE))

    def test_formal_genres_skip_comma_rate(self):
        # 사람이 쓴 공공·학술 문서도 비율이 20% 안팎이라 격식 장르에서는 재지 않는다.
        for genre in ("proposal", "notice", "ui"):
            with self.subTest(genre=genre):
                self.assertNotIn("PAT-COMMA-RATE", codes(self.AI_LIKE, genre))

    def test_noun_lists_are_not_connectives(self):
        text = "광고, 홍보, 참고 자료를 모았습니다. 측면, 전면, 화면을 모두 봤습니다. 최고, 최저 값을 적었습니다."
        self.assertEqual(connective_comma_rate(segment(text))[0], 0)


class TestChatResidue(unittest.TestCase):
    def test_first_and_last_sentence_only(self):
        head = "제안 요지를 5줄로 정리해 드릴게요. 신청률은 12%입니다. 문자 안내를 제안합니다."
        self.assertIn("PAT-CHAT-RESIDUE", codes(head, "proposal"))
        preface = "자기소개서 본문을 500자 안팎으로 맞추어 쓰겠습니다. 저는 예약 사이트를 만들었습니다."
        self.assertIn("PAT-CHAT-RESIDUE", codes(preface, "self-intro"))
        middle = "저는 예약 사이트를 만들었습니다. 고객에게 편한 화면을 만들어 드리겠습니다. 그 일을 계속하고 싶습니다."
        self.assertNotIn("PAT-CHAT-RESIDUE", codes(middle, "self-intro"))


class TestErrors(unittest.TestCase):
    def test_unknown_genre(self):
        with self.assertRaises(ValueError):
            check_patterns("문장입니다.", "poem")


if __name__ == "__main__":
    unittest.main()
