"""[GET] /tests/{testId}/answers/{questionNumber} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.get_answer import get_answer, validate_request


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
    @patch("src.get_answer.logging")
    def test_get_answer_success(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """discussionsからcommunityVotesを動的算出する場合のレスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_answer_container = MagicMock()
        mock_question_container = MagicMock()
        mock_answer_item = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
        }
        mock_question_item = {
            "discussions": [
                {"comment": "B is correct", "upvotedNum": 5, "selectedAnswer": "B"},
                {"comment": "C is right", "upvotedNum": 3, "selectedAnswer": "C"},
                {"comment": "B definitely", "upvotedNum": 2, "selectedAnswer": "B"},
            ]
        }
        mock_answer_container.read_item.return_value = mock_answer_item
        mock_question_container.read_item.return_value = mock_question_item
        mock_get_read_only_container.side_effect = [mock_answer_container, mock_question_container]

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 200)
        mock_validate_request.assert_called_once_with(req)
        self.assertEqual(mock_get_read_only_container.call_count, 2)
        mock_get_read_only_container.assert_any_call(
            database_name="Users",
            container_name="Answer",
        )
        mock_get_read_only_container.assert_any_call(
            database_name="Users",
            container_name="Question",
        )
        mock_answer_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_question_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        expected_body = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
            "communityVotes": ["B (67%)", "C (33%)"],
            "isExisted": True,
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)
        mock_logging.info.assert_has_calls(
            [call({"answer_item": mock_answer_item}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_answer.validate_request")
    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.logging")
    def test_get_answer_success_without_community_votes(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """discussionsが存在しない場合のレスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_answer_container = MagicMock()
        mock_question_container = MagicMock()
        mock_answer_item = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
        }
        mock_question_item = {
            "discussions": []
        }
        mock_answer_container.read_item.return_value = mock_answer_item
        mock_question_container.read_item.return_value = mock_question_item
        mock_get_read_only_container.side_effect = [mock_answer_container, mock_question_container]

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 200)
        mock_validate_request.assert_called_once_with(req)
        self.assertEqual(mock_get_read_only_container.call_count, 2)
        mock_get_read_only_container.assert_any_call(
            database_name="Users",
            container_name="Answer",
        )
        mock_get_read_only_container.assert_any_call(
            database_name="Users",
            container_name="Question",
        )
        mock_answer_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_question_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        expected_body = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
            "isExisted": True,
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)
        mock_logging.info.assert_has_calls(
            [call({"answer_item": mock_answer_item}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

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
            database_name="Users",
            container_name="Answer",
        )
        mock_answer_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

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
