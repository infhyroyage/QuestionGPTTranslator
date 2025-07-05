"""コミュニティ投票集計のテストケース"""

import unittest
from type.cosmos import QuestionDiscussion
from util.community_votes import calculate_community_votes


class TestCalculateCommunityVotes(unittest.TestCase):
    """calculate_community_votes関数のテストケース"""

    def test_calculate_community_votes_empty_discussions(self):
        """discussionsが空の場合のテスト"""
        discussions = []
        result = calculate_community_votes(discussions)
        self.assertIsNone(result)

    def test_calculate_community_votes_none_discussions(self):
        """discussionsがNoneの場合のテスト"""
        discussions = None
        result = calculate_community_votes(discussions)
        self.assertIsNone(result)

    def test_calculate_community_votes_no_selected_answers(self):
        """selectedAnswerがない場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="Great question!",
                upvotedNum=5,
                selectedAnswer=None
            )
        ]
        result = calculate_community_votes(discussions)
        self.assertIsNone(result)

    def test_calculate_community_votes_single_answer(self):
        """単一の回答の場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="I think A is correct",
                upvotedNum=5,
                selectedAnswer="A"
            )
        ]
        result = calculate_community_votes(discussions)
        self.assertEqual(result, ["A (100%)"])

    def test_calculate_community_votes_multiple_answers(self):
        """複数の回答の場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="I think A is correct",
                upvotedNum=5,
                selectedAnswer="A"
            ),
            QuestionDiscussion(
                comment="B is the right answer",
                upvotedNum=3,
                selectedAnswer="B"
            ),
            QuestionDiscussion(
                comment="A definitely",
                upvotedNum=2,
                selectedAnswer="A"
            )
        ]
        result = calculate_community_votes(discussions)
        # A: 2回 (67%), B: 1回 (33%)
        self.assertEqual(result, ["A (67%)", "B (33%)"])

    def test_calculate_community_votes_equal_distribution(self):
        """等しい分布の場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="A is correct",
                upvotedNum=5,
                selectedAnswer="A"
            ),
            QuestionDiscussion(
                comment="B is correct",
                upvotedNum=3,
                selectedAnswer="B"
            )
        ]
        result = calculate_community_votes(discussions)
        # A: 1回 (50%), B: 1回 (50%)
        self.assertEqual(result, ["A (50%)", "B (50%)"])

    def test_calculate_community_votes_sorted_order(self):
        """アルファベット順にソートされることのテスト"""
        discussions = [
            QuestionDiscussion(
                comment="C is correct",
                upvotedNum=5,
                selectedAnswer="C"
            ),
            QuestionDiscussion(
                comment="A is correct",
                upvotedNum=3,
                selectedAnswer="A"
            ),
            QuestionDiscussion(
                comment="B is correct",
                upvotedNum=2,
                selectedAnswer="B"
            )
        ]
        result = calculate_community_votes(discussions)
        # アルファベット順でソート
        self.assertEqual(result, ["A (33%)", "B (33%)", "C (33%)"])

    def test_calculate_community_votes_mixed_answers(self):
        """選択肢が混在する場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="I think A is correct",
                upvotedNum=5,
                selectedAnswer="A"
            ),
            QuestionDiscussion(
                comment="No answer",
                upvotedNum=3,
                selectedAnswer=None
            ),
            QuestionDiscussion(
                comment="B is right",
                upvotedNum=2,
                selectedAnswer="B"
            ),
            QuestionDiscussion(
                comment="A again",
                upvotedNum=1,
                selectedAnswer="A"
            )
        ]
        result = calculate_community_votes(discussions)
        # A: 2回 (67%), B: 1回 (33%) - Noneは除外
        self.assertEqual(result, ["A (67%)", "B (33%)"])


if __name__ == '__main__':
    unittest.main()