"""[POST] /tests/{testId}/favorites/{questionNumber} のテスト"""

import json
import unittest
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.post_favorite import post_favorite, validate_request
from type.request import PostFavoriteReq


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, None)

    def test_validate_request_empty_test_id(self):
        """testIdが空である場合のテスト"""

        req_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests//favorites/1",
            route_params={"testId": "", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "testId is Empty")

    def test_validate_request_empty_question_number(self):
        """questionNumberが空である場合のテスト"""

        req_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/",
            route_params={"testId": "test-id", "questionNumber": ""},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "questionNumber is Empty")

    def test_validate_request_invalid_question_number(self):
        """questionNumberが数字ではない場合のテスト"""

        req_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/abc",
            route_params={"testId": "test-id", "questionNumber": "abc"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "Invalid questionNumber: abc")

    def test_validate_request_empty_user_id(self):
        """X-User-Idヘッダーが空である場合のテスト"""

        req_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "X-User-Id header is Empty")

    def test_validate_request_empty_body(self):
        """リクエストボディが空の場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=None,
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "Request Body is Empty")

    def test_validate_request_missing_is_favorite(self):
        """リクエストボディにisFavoriteが存在しない場合のテスト"""

        req_body: PostFavoriteReq = {}
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "isFavorite is required")

    def test_validate_request_invalid_is_favorite(self):
        """isFavoriteがboolでない場合のテスト"""

        req_body: PostFavoriteReq = {
            "isFavorite": "true",
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        errors = validate_request(req)

        self.assertEqual(errors, "Invalid isFavorite: true")


class TestPostFavorite(unittest.TestCase):
    """post_favorite関数のテストケース"""

    @patch("src.post_favorite.validate_request")
    @patch("src.post_favorite.get_read_write_container")
    @patch("src.post_favorite.logging")
    def test_post_favorite_success(
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_request,
    ):
        """正常な場合にレスポンスが正常であることのテスト"""

        mock_validate_request.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container

        request_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(request_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_favorite(req)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_body().decode("utf-8"), "OK")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Favorite",
        )
        mock_container.upsert_item.assert_called_once_with(
            {
                "id": "user-id_test-id_1",
                "userId": "user-id",
                "testId": "test-id",
                "questionNumber": 1,
                "isFavorite": True,
            }
        )
        mock_logging.info.assert_called_once_with(
            {
                "question_number": 1,
                "test_id": "test-id",
                "user_id": "user-id",
            }
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_favorite.validate_request")
    @patch("src.post_favorite.logging")
    def test_post_favorite_validation_error(
        self,
        mock_logging,
        mock_validate_request,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_request.return_value = "testId is Empty"

        request_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(request_body).encode("utf-8"),
            url="/api/tests//favorites/1",
            route_params={"testId": "", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_favorite(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_body().decode("utf-8"), "testId is Empty")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.post_favorite.validate_request")
    @patch("src.post_favorite.get_read_write_container")
    @patch("src.post_favorite.logging")
    def test_post_favorite_exception(
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_request,
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.upsert_item.side_effect = Exception("Test exception")

        request_body: PostFavoriteReq = {
            "isFavorite": True,
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(request_body).encode("utf-8"),
            url="/api/tests/test-id/favorites/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_favorite(req)

        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.error.assert_called_once()
