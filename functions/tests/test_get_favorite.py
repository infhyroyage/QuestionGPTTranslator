"""[GET] /tests/{testId}/favorites/{questionNumber} のテスト"""

import json
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.get_favorite import get_favorite, validate_request


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, None)

    def test_validate_request_empty_test_id(self):
        """testIdが空である場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests//favorites/1",
            route_params={"testId": "", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "testId is Empty")

    def test_validate_request_empty_question_number(self):
        """questionNumberが空である場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites/",
            route_params={"testId": "test-id", "questionNumber": ""},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "questionNumber is Empty")

    def test_validate_request_invalid_question_number(self):
        """questionNumberが数字ではない場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites/abc",
            route_params={"testId": "test-id", "questionNumber": "abc"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "Invalid questionNumber: abc")

    def test_validate_request_empty_user_id(self):
        """X-User-Idヘッダーが空である場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "X-User-Id header is Empty")


class TestGetFavorite(unittest.TestCase):
    """get_favorite関数のテストケース"""

    @patch("src.get_favorite.validate_request")
    @patch("src.get_favorite.get_read_only_container")
    @patch("src.get_favorite.logging")
    def test_get_favorite_success(
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
            "id": "user-id_test-id_1",
            "userId": "user-id",
            "testId": "test-id",
            "questionNumber": 1,
            "isFavorite": True,
        }
        mock_container.read_item.return_value = mock_item

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = get_favorite(req)

        self.assertEqual(res.status_code, 200)
        response_body = json.loads(res.get_body().decode("utf-8"))
        self.assertEqual(response_body, {"isFavorite": True})
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Favorite",
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id_test-id_1", partition_key="test-id"
        )
        mock_logging.info.assert_has_calls(
            [
                call(
                    {"question_number": 1, "test_id": "test-id", "user_id": "user-id"}
                ),
                call({"item": mock_item}),
                call({"body": {"isFavorite": True}}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_favorite.validate_request")
    @patch("src.get_favorite.logging")
    def test_get_favorite_validation_error(
        self,
        mock_logging,
        mock_validate_request,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_request.return_value = "testId is Empty"

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests//favorites/1",
            route_params={"testId": "", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = get_favorite(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_body().decode("utf-8"), "testId is Empty")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.get_favorite.validate_request")
    @patch("src.get_favorite.get_read_only_container")
    @patch("src.get_favorite.logging")
    def test_get_favorite_not_found(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """お気に入り情報が存在しない場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_container.read_item.side_effect = CosmosResourceNotFoundError

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = get_favorite(req)

        self.assertEqual(res.status_code, 200)
        response_body = json.loads(res.get_body().decode("utf-8"))
        self.assertEqual(response_body, {"isFavorite": False})
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Favorite",
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id_test-id_1", partition_key="test-id"
        )
        mock_logging.info.assert_has_calls(
            [
                call(
                    {"question_number": 1, "test_id": "test-id", "user_id": "user-id"}
                ),
                call({"body": {"isFavorite": False}}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_favorite.validate_request")
    @patch("src.get_favorite.get_read_only_container")
    @patch("src.get_favorite.logging")
    def test_get_favorite_exception(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_read_only_container.side_effect = Exception("Test exception")

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = get_favorite(req)

        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.get_body().decode("utf-8"), "Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_called_once_with(
            {"question_number": 1, "test_id": "test-id", "user_id": "user-id"}
        )
        mock_logging.error.assert_called_once()
