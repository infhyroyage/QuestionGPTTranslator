"""[GET] /tests/{testId}/favorites のテスト"""

import json
import unittest
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.get_favorites import get_favorites, validate_request


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites",
            route_params={"testId": "test-id"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, None)

    def test_validate_request_empty_test_id(self):
        """testIdが空である場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests//favorites",
            route_params={"testId": ""},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "testId is Empty")

    def test_validate_request_empty_user_id(self):
        """X-User-Idヘッダーが空である場合のテスト"""

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites",
            route_params={"testId": "test-id"},
            headers={},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "X-User-Id header is Empty")


class TestGetFavorites(unittest.TestCase):
    """get_favorites関数のテストケース"""

    @patch("src.get_favorites.validate_request")
    @patch("src.get_favorites.get_read_only_container")
    @patch("src.get_favorites.logging")
    def test_get_favorites_success(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """レスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_items = [
            {
                "id": "user-id_test-id_1",
                "userId": "user-id",
                "testId": "test-id",
                "questionNumber": 1,
                "isFavorite": True,
            },
            {
                "id": "user-id_test-id_2",
                "userId": "user-id",
                "testId": "test-id",
                "questionNumber": 2,
                "isFavorite": False,
            },
        ]
        mock_container.query_items.return_value = mock_items

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests/test-id/favorites",
            route_params={"testId": "test-id"},
            headers={"X-User-Id": "user-id"},
        )

        res = get_favorites(req)

        self.assertEqual(res.status_code, 200)
        response_body = json.loads(res.get_body().decode("utf-8"))
        self.assertEqual(
            response_body,
            [
                {"questionNumber": 1, "isFavorite": True},
                {"questionNumber": 2, "isFavorite": False},
            ],
        )
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Favorite",
        )
        mock_container.query_items.assert_called_once()
        mock_logging.info.assert_called_once_with(
            {
                "test_id": "test-id",
                "user_id": "user-id",
            }
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_favorites.validate_request")
    @patch("src.get_favorites.logging")
    def test_get_favorites_validation_error(
        self,
        mock_logging,
        mock_validate_request,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_request.return_value = "testId is Empty"

        req = func.HttpRequest(
            method="GET",
            body=None,
            url="/api/tests//favorites",
            route_params={"testId": ""},
            headers={"X-User-Id": "user-id"},
        )

        res = get_favorites(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_body().decode("utf-8"), "testId is Empty")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.get_favorites.validate_request")
    @patch("src.get_favorites.get_read_only_container")
    @patch("src.get_favorites.logging")
    def test_get_favorites_exception(
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
            url="/api/tests/test-id/favorites",
            route_params={"testId": "test-id"},
            headers={"X-User-Id": "user-id"},
        )

        res = get_favorites(req)

        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.get_body().decode("utf-8"), "Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_called_once_with(
            {"test_id": "test-id", "user_id": "user-id"}
        )
        mock_logging.error.assert_called_once()
