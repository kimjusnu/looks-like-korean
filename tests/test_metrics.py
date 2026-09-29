"""tests/test_metrics.py — 결정론 엔진 회귀 테스트.

표준 라이브러리 unittest 만 쓴다(pytest 금지).
기대값은 **직접 만든 합성 픽스처**에서 고정한다. 외부 코퍼스에 기대지 않는다 —
코퍼스가 바뀌면 기대값이 조용히 틀어지니까.

핵심 회귀 방어선: 목록 번호 「1.」 「가.」 가 문장 수를 늘리면 **모든** 지표가
무의미해진다. 이 케이스를 절대 놓치지 않는다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# src 레이아웃이라 설치 없이도 돌아가게 경로를 한 번 물린다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from looks_like_korean import eomi, metrics  # noqa: E402
from looks_like_korean.eomi import classify_eomi, segment  # noqa: E402
from looks_like_korean.metrics import analyze  # noqa: E402


# ---------------------------------------------------------------------------
# 합성 픽스처
# ---------------------------------------------------------------------------

# 15문장 전부 합쇼체(-습니다/-ㅂ니다). run 길이를 정확히 고정하기 위해 15개로 센다.
# ⚠ 「…센다」 는 해라체다. 합쇼체를 만들려면 반드시 「…ㅂ니다/…습니다」 로 끝나야 한다.
POLITE_15 = [
    "이 문장은 정해진 길이를 잽니다.",
    "다음 문장은 같은 결말을 씁니다.",
    "셋째 문장도 같은 결말을 씁니다.",
    "넷째 문장 역시 같은 결말을 씁니다.",
    "다섯째 문장도 같은 결말을 씁니다.",
    "여섯째 문장 역시 같은 결말을 씁니다.",
    "일곱째 문장도 같은 결말을 씁니다.",
    "여덟째 문장 역시 같은 결말을 씁니다.",
    "아홉째 문장도 같은 결말을 씁니다.",
    "열째 문장 역시 같은 결말을 씁니다.",
    "열한째 문장도 같은 결말을 씁니다.",
    "열두째 문장 역시 같은 결말을 씁니다.",
    "열세째 문장도 같은 결말을 씁니다.",
    "열네째 문장 역시 같은 결말을 씁니다.",
    "열다섯째 문장도 같은 결말을 씁니다.",
]
assert len(POLITE_15) == 15


class TestUniformityIndex(unittest.TestCase):
    """헤드라인 지표. 1.0 = 한 레지스터, 0 = 완전 균등."""

    def test_single_register_paragraph_is_one(self):
        text = "\n\n".join(POLITE_15)
        a = analyze(text)
        self.assertEqual(a.register_counts["polite_formal"], 15)
        self.assertEqual(a.register_counts["polite_informal"], 0)
        self.assertAlmostEqual(a.value("uniformity_index"), 1.0, places=6)

    def test_four_registers_even_is_zero(self):
        # 4레지스터 × 4문장씩 = 완전 균등 → 정규화 엔트로피가 최대 → 0
        text = (
            "질문을 한다. 답을 한다. 길을 걷는다. 물을 마신다.\n\n"
            "내용을 봅니다. 결과를 봅니다. 흐름을 봅니다. 결론을 봅니다.\n\n"
            "그래요. 좋아요. 충분해요. 괜찮아요.\n\n"
            "좋음. 다름. 깊음. 큼."
        )
        a = analyze(text)
        counts = a.register_counts
        self.assertEqual(counts["plain"], 4)
        self.assertEqual(counts["polite_formal"], 4)
        self.assertEqual(counts["polite_informal"], 4)
        self.assertEqual(counts["nominal"], 4)
        self.assertEqual(counts["question"], 0)
        self.assertEqual(counts["none"], 0)
        self.assertEqual(a.metrics["uniformity_index"].detail["k"], 4)
        self.assertAlmostEqual(a.value("uniformity_index"), 0.0, places=6)

    def test_never_negative_or_above_one(self):
        a = analyze("간다. 온다. 간다. 온다. 간다. 온다. 간다. 온다. 간다. 온다.")
        v = a.value("uniformity_index")
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)

    def test_empty_input_is_zero_not_crash(self):
        a = analyze("")
        self.assertEqual(a.n_sentences, 0)
        self.assertEqual(a.value("uniformity_index"), 0.0)
        self.assertEqual(a.metrics["uniformity_index"].n, 0)


class TestRuns(unittest.TestCase):
    def test_max_same_register_run_is_15(self):
        a = analyze("\n\n".join(POLITE_15))
        self.assertEqual(a.value("max_same_register_run"), 15.0)

    def test_run_resets_on_switch(self):
        text = "간다. 온다. 가는 길이 멀다. 그래요. 좋음. 이렇습니다."
        a = analyze(text)
        self.assertEqual(a.n_sentences, 6)
        self.assertLess(a.value("max_same_register_run"), 6)
        self.assertEqual(a.register_counts["plain"], 3)
        self.assertEqual(a.register_counts["polite_informal"], 1)
        self.assertEqual(a.register_counts["nominal"], 1)
        self.assertEqual(a.register_counts["polite_formal"], 1)

    def test_switch_rate_needs_three_sentences(self):
        a = analyze("간다. 온다.")
        self.assertEqual(a.metrics["register_switch_rate"].value, 0.0)
        self.assertIn("측정 불가", a.metrics["register_switch_rate"].detail["note"])

    def test_switch_rate_all_same_is_zero(self):
        a = analyze("\n\n".join(POLITE_15))
        self.assertEqual(a.value("register_switch_rate"), 0.0)

    def test_switch_rate_all_alternating_is_one(self):
        text = "간다. 그래요. 가는 길이 멀음. 그러면 합니까? 이렇습니다."
        a = analyze(text)
        self.assertEqual(a.n_sentences, 5)
        self.assertEqual(a.value("register_switch_rate"), 1.0)
        self.assertEqual(a.metrics["register_switch_rate"].detail["switched"], 3)


class TestSegmentationRegression(unittest.TestCase):
    """이 절이 깨지면 모든 지표가 무의미해진다. 가장 중요하다."""

    PLAIN_4 = (
        "정리하면 이렇습니다. 두 번째 문장도 그렇습니다. "
        "세 번째 문장을 봅니다. 넷째 내용입니다."
    )
    NUMBERED_4 = (
        "1. 정리하면 이렇습니다.\n"
        "2. 두 번째 문장도 그렇습니다.\n"
        "3. 세 번째 문장을 봅니다.\n"
        "4. 넷째 내용입니다."
    )
    HANGUL_NUMBERED = (
        "가. 정리하면 이렇습니다.\n"
        "나. 두 번째 문장도 그렇습니다.\n"
        "다. 세 번째 문장을 봅니다.\n"
        "라. 넷째 내용입니다."
    )

    def test_list_numbers_do_not_add_sentences(self):
        base = segment(self.PLAIN_4)
        numbered = segment(self.NUMBERED_4)
        self.assertEqual(len(base), 4, "기준 픽스처가 4문장이어야 한다")
        self.assertEqual(len(numbered), len(base))

    def test_hangul_list_markers_do_not_add_sentences(self):
        self.assertEqual(len(segment(self.HANGUL_NUMBERED)), len(segment(self.PLAIN_4)))

    def test_list_markers_do_not_change_registers(self):
        a = analyze(self.PLAIN_4)
        b = analyze(self.NUMBERED_4)
        c = analyze(self.HANGUL_NUMBERED)
        self.assertEqual(a.register_counts, b.register_counts)
        self.assertEqual(a.register_counts, c.register_counts)

    def test_year_is_not_a_list_number(self):
        s = segment("기준 연도는 2026. 이다. 다음 해로 넘어간다.")
        self.assertEqual(len(s), 2)
        self.assertTrue(s[0].text.endswith("이다."))

    def test_decimal_is_not_a_boundary(self):
        s = segment("성장률은 3.14 퍼센트에 그쳤다. 다음 분기로 넘어갔다.")
        self.assertEqual(len(s), 2)
        self.assertIn("3.14", s[0].text)

    def test_circled_and_roman_markers(self):
        s = segment("① 첫 항목이다. ② 둘째 항목이다.")
        self.assertEqual(len(s), 2)
        s2 = segment("I. 첫 항목이다. II. 둘째 항목이다.")
        self.assertEqual(len(s2), 2)

    def test_markers_are_stripped_from_sentence_text(self):
        """마커가 문장 텍스트에 남으면 어절 수가 부풀고 「1.」 도 어미로 오탐된다."""
        s = segment("1. 정리하면 이렇습니다.\n2. 두 번째도 그렇습니다.")
        self.assertEqual([x.text for x in s], ["정리하면 이렇습니다.", "두 번째도 그렇습니다."])

    def test_stacked_markers_are_stripped(self):
        """한국어 업무문서는 「- ○」 「※ →」 처럼 마커가 겹쳐 있다."""
        s = segment("- ○ 첫 항목이다.\n※ → 둘째 항목이다.")
        self.assertEqual([x.text for x in s], ["첫 항목이다.", "둘째 항목이다."])

    def test_bold_line_is_not_a_list_item(self):
        s = segment("**선택기준** (총 100점, 공고 명시)")
        self.assertEqual(len(s), 1)
        self.assertTrue(s[0].text.startswith("선택기준"))

    def test_heading_without_space_after_hashes(self):
        s = segment("#142 제주 앱 명칭 공모")
        self.assertEqual(len(s), 1)
        self.assertTrue(s[0].text.startswith("142"))

    def test_closing_quote_can_end_a_sentence(self):
        """「…없음」 → 기준 미달… 처럼 닫는 괄호가 문장 끝을 알린다."""
        s = segment("유의: 「상하지 않을 수 있음」 → 기준 미달로 자리가 빌 수 있는 판")
        self.assertEqual(len(s), 2)
        self.assertEqual(classify_eomi(s[0].text)[0], "nominal")
        self.assertEqual(classify_eomi(s[1].text)[0], "none")

    def test_closing_quote_mid_sentence_is_not_a_boundary(self):
        s = segment("「가」와 「나」를 함께 쓴다.")
        self.assertEqual(len(s), 1)
        self.assertEqual(classify_eomi(s[0].text)[0], "plain")

    def test_url_is_masked_not_split(self):
        s = segment("출처는 https://www.jnuri.net/news/article.html?no=68907 에 있다.")
        self.assertEqual(len(s), 1)
        self.assertEqual(classify_eomi(s[0].text)[0], "plain")
        self.assertIn("[link]", s[0].text)

    def test_filename_is_not_split(self):
        s = segment("파일은 2026-09-01-후보와설명문-대안검토.md 이다.")
        self.assertEqual(len(s), 1)
        self.assertTrue(s[0].register == "plain")

    def test_code_block_is_dropped(self):
        text = (
            "설명하는 문장이다.\n\n"
            "```python\n"
            "print('합니다. 이것은 코드가 아니다.')\n"
            "def f(): return 1\n"
            "```\n\n"
            "이어지는 문장이다."
        )
        s = segment(text)
        self.assertEqual(len(s), 2)
        for sent in s:
            self.assertNotIn("print", sent.text)
            self.assertNotIn("def ", sent.text)

    def test_unterminated_fence_swallows_rest(self):
        text = "설명하는 문장이다.\n\n```\n코드 1. 코드 2. 코드 3."
        self.assertEqual(len(segment(text)), 1)

    def test_table_rows_and_headings_are_dropped(self):
        text = (
            "# 제목이 있다\n\n"
            "| 항목 | 배점 |\n|---|---|\n| 상징성 | 25점 |\n\n"
            "본문 문장이다."
        )
        s = segment(text)
        self.assertEqual(len(s), 2)
        self.assertIn("제목", s[0].text)
        self.assertIn("본문", s[1].text)


class TestArticleReference(unittest.TestCase):
    """조문 인용 「제12조」 가 종결로 오탐되면 안 된다."""

    def test_bare_article_is_none(self):
        self.assertEqual(classify_eomi("제12조")[0], "none")
        self.assertEqual(classify_eomi("제12조.")[0], "none")
        self.assertEqual(classify_eomi("제12조의 요건")[0], "none")
        self.assertEqual(classify_eomi("제1항")[0], "none")

    def test_article_inside_sentence_is_plain(self):
        self.assertEqual(classify_eomi("제12조에 따른다")[0], "plain")
        self.assertEqual(classify_eomi("이것은 제12조다")[0], "plain")

    def test_article_does_not_split_sentence(self):
        s = segment("법률 제12조는 다음과 같다. 제13조의 적용 범위가 넓다.")
        self.assertEqual(len(s), 2)
        for sent in s:
            bare = sent.text.rstrip(".。!?… ")
            # 조 번호 조각(「조」/「조는」)이 따로 떨어지지 않았는지
            self.assertTrue(bare.endswith(("같다", "넓다")), sent.text)
            self.assertTrue(sent.text.startswith("법률") or sent.text.startswith("제13조"))

    def test_article_number_is_not_misread_as_list(self):
        s = segment("1. 제12조는 다음과 같다. 2. 제13조도 그렇다.")
        self.assertEqual(len(s), 2)

    def test_article_list_does_not_inflate_registers(self):
        plain = "법률 제12조는 그렇다. 제13조도 그렇다."
        listed = "1. 제12조는 그렇다.\n2. 제13조도 그렇다."
        self.assertEqual(analyze(plain).register_counts, analyze(listed).register_counts)


class TestClassifier(unittest.TestCase):
    CASES = [
        ("그렇게 합니다", "polite_formal"),
        ("그렇습니다만", "polite_formal"),
        ("없습니다", "polite_formal"),
        ("확인합니다.", "polite_formal"),  # 마침표로 끝나도 합쇼체 표기
        ("내용을 봅니다", "polite_formal"),
        ("그래요", "polite_informal"),
        ("있어요", "polite_informal"),
        ("반갑습니다", "polite_formal"),
        ("좋아요", "polite_informal"),       # 「-아요」 는 「해요」 로 줄여 쓸 때가 많다
        ("그렇죠", "polite_informal"),
        ("도와주세요", "polite_informal"),
        ("무엇을까요", "polite_informal"),
        ("합니다", "polite_formal"),          # 명사형이지만 표기상 합쇼 → 합쇼로
        ("간다", "plain"),
        ("했다", "plain"),
        ("있다", "plain"),
        ("좋은 결과가 나왔다.", "plain"),
        ("가장 중요한 내용", "none"),
        ("다음 3가지", "none"),
        ("결과가 좋음", "nominal"),
        ("중요한 함", "nominal"),
        ("읽을 것", "nominal"),
        ("될지 모름", "nominal"),   # 「다르다→다라+ㅁ」 = 다름. 받침 ㄹ 경로
        ("언제 갈지", "nominal"),
        ("끝까지", "none"),          # 「까지」 는 부사격이므로 nominal 아님
        ("같이 하자", "none"),       # 「같이」 는 부사
        ("그것", "none"),            # 지시대명사 + 「것」
        ("그림", "none"),            # 받침 ㅁ 인 완결어
        ("이름", "none"),
        ("하면 안 된다", "plain"),   # 「안 된다」 류는 명사형 아님
        ("하면 안 됨", "plain"),     # 음성으로 떨어져도 제외
        ("읽는 가", "none"),         # 「-(으)ㄹ 가」 은 표준 종결이 아니다
        ("합니까", "question"),
        ("읍니까", "question"),
    ]

    def test_table(self):
        for text, expected in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(classify_eomi(text)[0], expected)

    def test_question_needs_question_mark(self):
        self.assertEqual(classify_eomi("가야 하나")[0], "none")
        self.assertEqual(classify_eomi("가야 하나?" , "?")[0], "question")

    def test_casual_nikka_is_not_question(self):
        """「~니까」 는 인과다. 물음표가 없으면 의문으로 판명하지 않는다."""
        self.assertNotEqual(classify_eomi("그러니까 간다")[0], "question")
        self.assertEqual(classify_eomi("어떻게 하니까?", "?")[0], "question")

    def test_explicit_question_suffix_wins_over_others(self):
        for text in ("합니까", "입니까", "하나요", "는가", "가냐"):
            with self.subTest(text=text):
                self.assertEqual(classify_eomi(text)[0], "question")

    def test_nominal_suffixes(self):
        for text in ("읽음", "임", "중요한 함", "할 것", "언제 갈지", "읽기", "다름", "점"):
            with self.subTest(text=text):
                self.assertEqual(classify_eomi(text)[0], "nominal", text)

    def test_ending_key_distinguishes_isms(self):
        self.assertEqual(classify_eomi("했다")[1], "했다")
        self.assertEqual(classify_eomi("있다")[1], "있다")
        self.assertEqual(classify_eomi("간다")[1], "간다")
        self.assertNotEqual(classify_eomi("그렇습니다만")[1], classify_eomi("그렇습니다")[1])

    def test_trailing_quotes_and_brackets_are_stripped(self):
        self.assertEqual(classify_eomi('「그래요」')[0], "polite_informal")
        self.assertEqual(classify_eomi("(간다)")[0], "plain")
        self.assertEqual(classify_eomi("간다……")[0], "plain")

    def test_no_hangul_is_none(self):
        self.assertEqual(classify_eomi("Hello world")[0], "none")
        self.assertEqual(classify_eomi("2026")[0], "none")
        self.assertEqual(classify_eomi("")[0], "none")


class TestEdgeInputs(unittest.TestCase):
    def test_empty(self):
        a = analyze("")
        self.assertEqual(a.n_sentences, 0)
        for key in metrics.METRIC_KEYS:
            self.assertIsInstance(a.value(key), float, key)

    def test_whitespace_only(self):
        a = analyze("   \n\n\t\n  ")
        self.assertEqual(a.n_sentences, 0)

    def test_no_hangul_at_all(self):
        a = analyze("Hello world.\n\nThis is a test.\n\n# Title only")
        self.assertEqual(a.n_sentences, 0)
        self.assertEqual(a.value("hangul_ratio"), 0.0)
        self.assertEqual(a.value("uniformity_index"), 0.0)

    def test_single_sentence(self):
        a = analyze("한 문장뿐이다.")
        self.assertEqual(a.n_sentences, 1)
        self.assertEqual(a.value("uniformity_index"), 1.0)
        self.assertEqual(a.value("max_same_register_run"), 1.0)
        self.assertEqual(a.value("sentence_len_logstd"), 0.0)
        self.assertEqual(a.value("register_switch_rate"), 0.0)
        self.assertEqual(a.value("repeat_ngram_rate"), 0.0)

    def test_single_sentence_no_period(self):
        a = analyze("한 문장뿐")
        self.assertEqual(a.n_sentences, 1)
        self.assertEqual(a.register_counts["none"], 1)

    def test_repeat_ngram_needs_four(self):
        a = analyze("간다. 온다. 간다.")
        self.assertEqual(a.value("repeat_ngram_rate"), 0.0)
        self.assertIn("측정 불가", a.metrics["repeat_ngram_rate"].detail["note"])

    def test_all_metrics_are_floats_and_have_evidence(self):
        a = analyze("# 혼합\n\n간다. 그래서 좋았음. 무엇을 할까?\n\n그래요.ilik\n\n끝")
        for key in metrics.METRIC_KEYS:
            m = a.metrics[key]
            self.assertIsInstance(m.value, float, key)
            self.assertIsInstance(m.detail, dict, key)
            self.assertIn(m.direction, ("human", "machine", "neutral"), key)


class TestLengthMetrics(unittest.TestCase):
    def test_gini_of_equal_lengths_is_zero(self):
        a = analyze("\n\n".join("한 둘 셋 넷." for _ in range(5)))
        self.assertAlmostEqual(a.value("sentence_len_gini"), 0.0, places=6)

    def test_gini_of_extreme_spread_is_high(self):
        long_sentence = " ".join(["기계가 쓰는 아주 긴 문장이다"] * 8) + "."
        a = analyze("짧다. " + long_sentence + " 끝. 그래요.")
        self.assertEqual(a.n_sentences, 4)
        self.assertGreater(a.value("sentence_len_gini"), 0.5)

    def test_gini_single_value_is_zero(self):
        self.assertEqual(metrics._gini([5.0]), 0.0)
        self.assertEqual(metrics._gini([]), 0.0)
        self.assertEqual(metrics._gini([0.0, 0.0]), 0.0)

    def test_logstd_zero_when_uniform(self):
        a = analyze("\n\n".join("가나다. 마바사. 아자차." for _ in range(6)))
        self.assertAlmostEqual(a.value("sentence_len_logstd"), 0.0, places=6)

    def test_pstdev_edges(self):
        self.assertEqual(metrics._pstdev([]), 0.0)
        self.assertEqual(metrics._pstdev([3.0]), 0.0)
        self.assertAlmostEqual(metrics._pstdev([1.0, 3.0]), 1.0, places=9)


class TestNominal(unittest.TestCase):
    def test_ratio(self):
        text = "간다. 좋다. 삼. 간다. 좋다. 삼."
        a = analyze(text)
        self.assertEqual(a.register_counts["nominal"], 2)
        self.assertAlmostEqual(a.value("nominal_ratio"), 2 / 6, places=6)

    def test_no_nominal_is_zero(self):
        a = analyze("간다. 온다. 간다. 온다.")
        self.assertEqual(a.value("nominal_ratio"), 0.0)
        self.assertEqual(a.value("nominal_position"), 0.0)

    def test_position_histogram_has_five_bins(self):
        a = analyze("좋음. 간다. 좋음. 간다. 좋음. 간다. 좋음.")
        hist = a.metrics["nominal_position"].detail["histogram"]
        self.assertEqual(len(hist), 5)
        self.assertEqual(sum(hist.values()), a.register_counts["nominal"])

    def test_position_is_relative_within_paragraph(self):
        a = analyze("좋음. 간다. 온다. 좋음.")
        # 두 문단 각 2문장 → 0.0 과 1.0
        self.assertAlmostEqual(a.value("nominal_position"), 0.5, places=6)


class TestHangulRatio(unittest.TestCase):
    def test_pure_hangul_is_one(self):
        a = analyze("한글만 있는 문장입니다.")
        self.assertAlmostEqual(a.value("hangul_ratio"), 1.0, places=6)

    def test_mixed_script(self):
        a = analyze("이 문장은 AI 라는 단어를 쓴다. 漢字 도 쓴다.")
        v = a.value("hangul_ratio")
        self.assertLess(v, 1.0)
        self.assertGreater(v, 0.0)
        d = a.metrics["hangul_ratio"].detail
        self.assertGreater(d["latin"], 0)
        self.assertGreater(d["han"], 0)
        self.assertAlmostEqual(d["nonhangul_ratio"], 1.0 - v, places=9)

    def test_direction_is_neutral(self):
        a = analyze("한글만 있는 문장입니다.")
        self.assertEqual(a.metrics["hangul_ratio"].direction, "neutral")
        self.assertEqual(a.metrics["nominal_position"].direction, "neutral")


class TestDeterminism(unittest.TestCase):
    TEXT = (
        "# 제목\n\n"
        "1. 첫 항목이다. 두 번째도 그렇다.\n\n"
        "그래요. 그럴 수 있나?\n\n"
        "```\ncode. code.\n```\n\n"
        "결과가 좋음. 출처는 https://example.com/a.b 에 있다.\n\n"
        "제12조는 다음과 같다.\n"
    )

    def test_repeated_runs_identical(self):
        a = analyze(self.TEXT)
        b = analyze(self.TEXT)
        self.assertEqual(a.register_counts, b.register_counts)
        for key in metrics.METRIC_KEYS:
            self.assertEqual(a.value(key), b.value(key), key)
        self.assertEqual(
            [s.text for s in a.sentences], [s.text for s in b.sentences]
        )

    def test_does_not_mutate_input(self):
        original = self.TEXT
        analyze(self.TEXT)
        self.assertEqual(self.TEXT, original)


class TestReport(unittest.TestCase):
    def test_render_score_has_all_metrics(self):
        from looks_like_korean.report import render_score, to_json
        import json

        a = analyze(TestDeterminism.TEXT)
        out = render_score(a, "테스트.md")
        for key in metrics.METRIC_KEYS:
            self.assertIn(key, out)
        self.assertIn("테스트.md", out)

        payload = json.loads(to_json({"a": a.n_sentences}))
        self.assertEqual(payload["a"], a.n_sentences)

    def test_json_is_serialisable(self):
        import json

        from looks_like_korean.report import analysis_to_dict, to_json

        a = analyze(TestDeterminism.TEXT)
        text = to_json(analysis_to_dict(a, "x.md"))
        data = json.loads(text)
        self.assertEqual(data["n_sentences"], a.n_sentences)
        self.assertEqual(len(data["metrics"]), len(metrics.METRIC_KEYS))

    def test_render_compare(self):
        from looks_like_korean.report import render_compare

        a = analyze("\n\n".join(POLITE_15))
        b = analyze("간다. 왔음. 무엇을? 그래요.")
        out = render_compare(a, b, "원문.md", "수정문.md")
        self.assertIn("uniformity_index", out)
        self.assertIn("원문.md", out)
        self.assertIn("수정문.md", out)
        self.assertIn("가설 없음", out)          # hangul_ratio / nominal_position

    def test_compare_verdict_points_at_the_human_side(self):
        """기계풍(한 레지스터) vs 사람풍(교차) — H2 방향이 지켜져야 한다."""
        from looks_like_korean.report import render_compare

        uniform = analyze("본APPLICATION이다. 본APPLICATION이다. 본APPLICATION이다. "
                          "본APPLICATION이다. 본APPLICATION이다.")
        mixed = analyze("간다. 왔음. 무엇을 할지 모름. 그래요. 이렇습니다. 찬성함.")
        out = render_compare(uniform, mixed, "기계풍", "사람풍")
        for key in ("uniformity_index", "max_same_register_run",
                    "register_switch_rate", "repeat_ngram_rate"):
            rows = [ln for ln in out.splitlines() if ln.strip().startswith(key)]
            self.assertEqual(len(rows), 2, f"{key}: 표와 판정 표에 모두 있어야 한다")
            self.assertIn("사람풍", rows[-1], f"{key}: 방향 반전")

    def test_compare_delta_is_after_minus_before(self):
        from looks_like_korean.report import render_compare

        a = analyze("\n\n".join(POLITE_15))
        b = analyze("간다. 왔음. 무엇을? 그래요.")
        out = render_compare(a, b, "원문", "수정문")
        row = [ln for ln in out.splitlines() if ln.strip().startswith("uniformity_index")][-1]
        self.assertIn("-1.000", row)

    def test_every_metric_has_a_direction(self):
        a = analyze(TestDeterminism.TEXT)
        for key in metrics.METRIC_KEYS:
            self.assertIn(a.metrics[key].direction, ("human", "machine", "neutral"), key)


class TestCli(unittest.TestCase):
    def _write(self, tmp: Path, name: str, text: str) -> str:
        p = tmp / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_score_and_compare(self):
        import contextlib
        import io
        import tempfile

        from looks_like_korean.cli import main

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            a = self._write(tmp, "a.md", "\n\n".join(POLITE_15))
            b = self._write(tmp, "b.md", "간다. 왔음. 무엇을? 그래요.")

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(["score", a]), 0)
            self.assertIn("uniformity_index", buf.getvalue())

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(["score", a, "--json"]), 0)
            self.assertIn('"uniformity_index"', buf.getvalue())

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(["compare", a, b]), 0)
            out = buf.getvalue()
            self.assertIn("a.md", out)
            self.assertIn("b.md", out)
            self.assertIn("원문", out)
            self.assertIn("수정문", out)
            self.assertIn("uniformity_index", out)

    def test_missing_file_exits(self):
        import contextlib
        import io

        from looks_like_korean.cli import main

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["score", "없는파일.md"])


if __name__ == "__main__":
    unittest.main()
