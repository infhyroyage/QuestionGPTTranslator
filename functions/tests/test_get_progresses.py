"""get_progresses関数のテスト"""

import json
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.get_progresses import get_progresses, validate_request
from type.response import GetProgressesRes


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )
        errors = validate_request(req)
        self.assertIsNone(errors)

    def test_validate_request_empty_test_id(self):
        """testIdが空の場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/tests//progresses",
            route_params={"testId": ""},
            headers={"X-User-Id": "user-id-1"},
        )
        errors = validate_request(req)
        self.assertEqual(errors, "testId is Empty")

    def test_validate_request_empty_user_id(self):
        """X-User-Idが空の場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": ""},
        )
        errors = validate_request(req)
        self.assertEqual(errors, "X-User-Id header is Empty")


class TestGetProgresses(unittest.TestCase):
    """get_progresses関数のテストケース"""

    @patch("src.get_progresses.validate_request")
    @patch("src.get_progresses.get_read_only_container")
    @patch("src.get_progresses.logging")
    def test_get_progresses_success(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """レスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_item = {
            "id": "user-id-1_test-id-1",
            "userId": "user-id-1",
            "testId": "test-id-1",
            "progresses": [
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                },
                {
                    "isCorrect": False,
                    "choiceSentences": ["選択肢A", "選択肢B"],
                    "choiceImgs": [None, None],
                    "selectedIdxes": [0],
                    "correctIdxes": [1],
                },
            ],
        }
        mock_container.read_item.return_value = mock_item

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = get_progresses(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "application/json")
        expect_body: GetProgressesRes = [
            {
                "isCorrect": True,
                "choiceSentences": ["選択肢1", "選択肢2"],
                "choiceImgs": [None, "https://example.com/img.png"],
                "selectedIdxes": [0],
                "correctIdxes": [0],
            },
            {
                "isCorrect": False,
                "choiceSentences": ["選択肢A", "選択肢B"],
                "choiceImgs": [None, None],
                "selectedIdxes": [0],
                "correctIdxes": [1],
            },
        ]
        self.assertEqual(json.loads(resp.get_body().decode()), expect_body)
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users", container_name="Progress"
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id-1_test-id-1", partition_key="test-id-1"
        )
        mock_logging.info.assert_has_calls(
            [
                call({"test_id": "test-id-1", "user_id": "user-id-1"}),
                call({"item": mock_item}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_progresses.validate_request")
    @patch("src.get_progresses.logging")
    def test_get_progresses_validation_error(
        self,
        mock_logging,
        mock_validate_request,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_request.return_value = "testId is Empty"

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/tests//progresses",
            route_params={"testId": ""},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = get_progresses(req)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_body(), b"testId is Empty")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.get_progresses.validate_request")
    @patch("src.get_progresses.get_read_only_container")
    @patch("src.get_progresses.logging")
    def test_get_progresses_not_found(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """進捗項目が存在しない場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_container.read_item.side_effect = CosmosResourceNotFoundError

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = get_progresses(req)

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_body(), b"Not Found Progress")
        mock_container.read_item.assert_called_once_with(
            item="user-id-1_test-id-1", partition_key="test-id-1"
        )
        mock_logging.info.assert_called_once_with(
            {"test_id": "test-id-1", "user_id": "user-id-1"}
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_progresses.validate_request")
    @patch("src.get_progresses.get_read_only_container")
    @patch("src.get_progresses.logging")
    def test_get_progresses_exception(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_container.read_item.side_effect = Exception("Test Exception")

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = get_progresses(req)

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.get_body(), b"Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "test_id": "test-id-1",
                "user_id": "user-id-1",
            }
        )
        mock_logging.error.assert_called_once()
