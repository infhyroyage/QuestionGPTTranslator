"""[GET] /tests/{testId}/communities/{questionNumber} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.get_community import get_community, validate_request


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


class TestGetCommunity(TestCase):
    """get_community関数のテストケース"""

    @patch("src.get_community.validate_request")
    @patch("src.get_community.get_read_only_container")
    @patch("src.get_community.logging")
    def test_get_community_success_with_votes(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """Communityコンテナーのvotesフィールドを含む場合のレスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_community_container = MagicMock()
        mock_community_item = {
            "id": "1_1",
            "testId": "1",
            "questionNumber": 1,
            "discussionsSummary": (
                "Users discuss correct answers and share insights about this question."
            ),
            "votes": ["B (67%)", "C (33%)"],
        }
        mock_community_container.read_item.return_value = mock_community_item
        mock_get_read_only_container.return_value = mock_community_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_community(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users", container_name="Community"
        )
        mock_community_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )

        expected_body = {
            "discussionsSummary": (
                "Users discuss correct answers and share insights about this question."
            ),
            "votes": ["B (67%)", "C (33%)"],
            "isExisted": True,
        }
        actual_body = response.get_body().decode()
        self.assertEqual(json.loads(actual_body), expected_body)

        mock_logging.info.assert_has_calls(
            [call({"item": mock_community_item}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_community.validate_request")
    @patch("src.get_community.get_read_only_container")
    @patch("src.get_community.logging")
    def test_get_community_success_without_votes(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """votesフィールドが空の場合のレスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_community_container = MagicMock()
        mock_community_item = {
            "id": "1_1",
            "testId": "1",
            "questionNumber": 1,
            "discussionsSummary": (
                "Users discuss correct answers and share insights about this question."
            ),
            "votes": [],
        }
        mock_community_container.read_item.return_value = mock_community_item
        mock_get_read_only_container.return_value = mock_community_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_community(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users", container_name="Community"
        )
        mock_community_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )

        expected_body = {
            "discussionsSummary": (
                "Users discuss correct answers and share insights about this question."
            ),
            "votes": [],
            "isExisted": True,
        }
        actual_body = response.get_body().decode()
        self.assertEqual(json.loads(actual_body), expected_body)

        mock_logging.info.assert_has_calls(
            [call({"item": mock_community_item}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_community.validate_request")
    def test_get_community_validation_error(self, mock_validate_request):
        """バリデーションチェックに失敗した場合のテスト"""

        mock_validate_request.return_value = "Validation Error"

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_community(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "Validation Error")

    @patch("src.get_community.validate_request")
    @patch("src.get_community.get_read_only_container")
    @patch("src.get_community.logging")
    def test_get_community_not_found(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """コミュニティ要約が見つからない場合のレスポンスのテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_container.read_item.side_effect = CosmosResourceNotFoundError
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_community(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        expected_body = {
            "isExisted": False,
        }
        actual_body = response.get_body().decode()
        self.assertEqual(json.loads(actual_body), expected_body)

        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Community",
        )
        mock_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.get_community.validate_request")
    @patch("src.get_community.get_read_only_container")
    @patch("src.get_community.logging")
    def test_get_community_exception(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_community.get_read_only_container"
        )

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_community(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()
