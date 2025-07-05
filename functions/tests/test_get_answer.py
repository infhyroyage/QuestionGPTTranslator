"""[GET] /tests/{testId}/answers/{questionNumber} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.get_answer import calculate_community_votes, get_answer, validate_request


class TestCalculateCommunityVotes(TestCase):
    """calculate_community_votes関数のテストケース"""

    def test_calculate_community_votes_with_valid_discussions(self):
        """有効なdiscussionsでのcommunityVotes算出のテスト"""

        discussions = [
            {"comment": "Test comment 1", "selectedAnswer": "A"},
            {"comment": "Test comment 2", "selectedAnswer": "B"},
            {"comment": "Test comment 3", "selectedAnswer": "A"},
            {"comment": "Test comment 4", "selectedAnswer": "A"},
            {"comment": "Test comment 5", "selectedAnswer": "B"},
        ]

        result = calculate_community_votes(discussions)

        expected = ["A (60%)", "B (40%)"]
        self.assertEqual(sorted(result), sorted(expected))

    def test_calculate_community_votes_with_none_discussions(self):
        """discussionsがNoneの場合のテスト"""

        result = calculate_community_votes(None)

        self.assertIsNone(result)

    def test_calculate_community_votes_with_empty_discussions(self):
        """discussionsが空の場合のテスト"""

        result = calculate_community_votes([])

        self.assertIsNone(result)

    def test_calculate_community_votes_with_no_selected_answers(self):
        """selectedAnswerがすべてNoneの場合のテスト"""

        discussions = [
            {"comment": "Test comment 1", "selectedAnswer": None},
            {"comment": "Test comment 2", "selectedAnswer": None},
        ]

        result = calculate_community_votes(discussions)

        self.assertIsNone(result)

    def test_calculate_community_votes_with_mixed_selected_answers(self):
        """selectedAnswerが混在する場合のテスト"""

        discussions = [
            {"comment": "Test comment 1", "selectedAnswer": "A"},
            {"comment": "Test comment 2", "selectedAnswer": None},
            {"comment": "Test comment 3", "selectedAnswer": "B"},
            {"comment": "Test comment 4", "selectedAnswer": "A"},
        ]

        result = calculate_community_votes(discussions)

        expected = ["A (67%)", "B (33%)"]
        self.assertEqual(sorted(result), sorted(expected))


class TestValidateRequest(TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        result = validate_request(req)

        self.assertIsNone(result)

    def test_validate_request_test_id_empty(self):
        """testIdが空である場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"questionNumber": "1"}

        result = validate_request(req)

        self.assertEqual(result, "testId is Empty")

    def test_validate_request_question_number_empty(self):
        """questionNumberが空である場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}

        result = validate_request(req)

        self.assertEqual(result, "questionNumber is Empty")

    def test_validate_request_question_number_not_digit(self):
        """questionNumberが数値でない場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "a"}

        result = validate_request(req)

        self.assertEqual(result, "Invalid questionNumber: a")


class TestGetAnswer(TestCase):
    """get_answer関数のテストケース"""

    @patch("src.get_answer.validate_request")
    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.calculate_community_votes")
    @patch("src.get_answer.logging")
    def test_get_answer_success_with_community_votes(
        self, mock_logging, mock_calculate_community_votes, mock_get_read_only_container, mock_validate_request
    ):
        """discussionsからcommunityVotesが算出される場合のテスト"""

        mock_validate_request.return_value = None
        mock_answer_container = MagicMock()
        mock_question_container = MagicMock()
        mock_answer_item = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
        }
        mock_question_item = {
            "discussions": [
                {"comment": "Test comment 1", "selectedAnswer": "A"},
                {"comment": "Test comment 2", "selectedAnswer": "B"},
            ]
        }
        mock_answer_container.read_item.return_value = mock_answer_item
        mock_question_container.read_item.return_value = mock_question_item
        mock_get_read_only_container.side_effect = [mock_answer_container, mock_question_container]
        mock_calculate_community_votes.return_value = ["A (50%)", "B (50%)"]

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 200)
        mock_validate_request.assert_called_once_with(req)
        self.assertEqual(mock_get_read_only_container.call_count, 2)
        mock_get_read_only_container.assert_any_call(
            database_name="Users", container_name="Answer"
        )
        mock_get_read_only_container.assert_any_call(
            database_name="Users", container_name="Question"
        )
        mock_answer_container.read_item.assert_called_once_with(
            item="1_1", partition_key="1"
        )
        mock_question_container.read_item.assert_called_once_with(
            item="1_1", partition_key="1"
        )
        mock_calculate_community_votes.assert_called_once_with(mock_question_item["discussions"])
        expected_body = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
            "communityVotes": ["A (50%)", "B (50%)"],
            "isExisted": True,
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)

    @patch("src.get_answer.validate_request")
    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.calculate_community_votes")
    @patch("src.get_answer.logging")
    def test_get_answer_success_without_community_votes(
        self, mock_logging, mock_calculate_community_votes, mock_get_read_only_container, mock_validate_request
    ):
        """discussionsからcommunityVotesが算出されない場合のテスト"""

        mock_validate_request.return_value = None
        mock_answer_container = MagicMock()
        mock_question_container = MagicMock()
        mock_answer_item = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
        }
        mock_question_item = {
            "discussions": None
        }
        mock_answer_container.read_item.return_value = mock_answer_item
        mock_question_container.read_item.return_value = mock_question_item
        mock_get_read_only_container.side_effect = [mock_answer_container, mock_question_container]
        mock_calculate_community_votes.return_value = None

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 200)
        mock_validate_request.assert_called_once_with(req)
        self.assertEqual(mock_get_read_only_container.call_count, 2)
        mock_calculate_community_votes.assert_called_once_with(None)
        expected_body = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
            "isExisted": True,
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)

    @patch("src.get_answer.validate_request")
    def test_get_answer_validation_error(self, mock_validate_request):
        """バリデーションチェックに失敗した場合のテスト"""

        mock_validate_request.return_value = "Validation Error"

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "Validation Error")

    @patch("src.get_answer.validate_request")
    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.logging")
    def test_get_answer_not_found(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """回答が見つからない場合のレスポンスのテスト"""

        mock_validate_request.return_value = None
        mock_answer_container = MagicMock()
        mock_answer_container.read_item.side_effect = CosmosResourceNotFoundError
        mock_get_read_only_container.return_value = mock_answer_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 200)
        expected_body = {
            "isExisted": False,
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users", container_name="Answer"
        )
        mock_answer_container.read_item.assert_called_once_with(
            item="1_1", partition_key="1"
        )

    @patch("src.get_answer.validate_request")
    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.logging")
    def test_get_answer_exception(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_test.get_read_only_container"
        )

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()
