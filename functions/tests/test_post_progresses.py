"""post_progresses関数のテスト"""

import json
import unittest
from unittest.mock import MagicMock, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.post_progresses import (
    post_progresses,
    validate_body,
    validate_headers,
    validate_route_params,
)


class TestValidateBody(unittest.TestCase):
    """validate_body関数のテストケース"""

    def test_validate_body_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req_body = json.dumps({"order": [3, 5, 1, 2, 4]}).encode()
        errors = validate_body(req_body)
        self.assertEqual(errors, [])

    def test_validate_body_empty(self):
        """リクエストボディが空の場合のテスト"""

        req_body = b""
        errors = validate_body(req_body)
        self.assertEqual(errors, ["Request Body is Empty"])

    def test_validate_body_missing_order(self):
        """orderがない場合のテスト"""

        req_body = json.dumps({"not_order": [1, 2, 3]}).encode()
        errors = validate_body(req_body)
        self.assertEqual(errors, ["order is required"])

    def test_validate_body_invalid_order_type(self):
        """orderがリストでない場合のテスト"""

        req_body = json.dumps({"order": "not a list"}).encode()
        errors = validate_body(req_body)
        self.assertEqual(errors, ["Invalid order: not a list"])

    def test_validate_body_invalid_order_item(self):
        """orderの要素が数値でない場合のテスト"""

        req_body = json.dumps({"order": [1, "2", 3]}).encode()
        errors = validate_body(req_body)
        self.assertEqual(errors, ["Invalid order[1]: 2"])


class TestValidateRouteParams(unittest.TestCase):
    """validate_route_params関数のテストケース"""

    def test_validate_route_params_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        route_params = {"testId": "test-id-1"}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, [])

    def test_validate_route_params_empty_test_id(self):
        """testIdが空の場合のテスト"""

        route_params = {"testId": ""}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["testId is Empty"])

    def test_validate_route_params_missing_test_id(self):
        """testIdがない場合のテスト"""

        route_params = {}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["testId is Empty"])


class TestValidateHeaders(unittest.TestCase):
    """validate_headers関数のテストケース"""

    def test_validate_headers_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        headers = {"X-User-Id": "user-id-1"}
        errors = validate_headers(headers)
        self.assertEqual(errors, [])

    def test_validate_headers_empty_user_id(self):
        """X-User-Idが空の場合のテスト"""

        headers = {"X-User-Id": ""}
        errors = validate_headers(headers)
        self.assertEqual(errors, ["X-User-Id header is Empty"])

    def test_validate_headers_missing_user_id(self):
        """X-User-Idがない場合のテスト"""

        headers = {}
        errors = validate_headers(headers)
        self.assertEqual(errors, ["X-User-Id header is Empty"])


class TestPostProgresses(unittest.TestCase):
    """post_progresses関数のテストケース"""

    @patch("src.post_progresses.validate_body")
    @patch("src.post_progresses.validate_route_params")
    @patch("src.post_progresses.validate_headers")
    @patch("src.post_progresses.get_read_write_container")
    @patch("src.post_progresses.logging")
    def test_post_progresses_success(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_headers,
        mock_validate_route_params,
        mock_validate_body,
    ):
        """レスポンスが正常であることのテスト"""

        mock_validate_body.return_value = []
        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.side_effect = CosmosResourceNotFoundError

        req_body = json.dumps({"order": [3, 5, 1, 2, 4]}).encode()
        req = func.HttpRequest(
            method="POST",
            body=req_body,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = post_progresses(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_body(), b"OK")
        mock_validate_body.assert_called_once_with(req_body)
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users", container_name="Progress"
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id-1_test-id-1", partition_key="test-id-1"
        )
        mock_container.upsert_item.assert_called_once_with(
            {
                "id": "user-id-1_test-id-1",
                "userId": "user-id-1",
                "testId": "test-id-1",
                "order": [3, 5, 1, 2, 4],
                "progresses": [],
            }
        )
        mock_logging.info.assert_called_once_with(
            {"test_id": "test-id-1", "user_id": "user-id-1"}
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progresses.validate_body")
    @patch("src.post_progresses.validate_route_params")
    @patch("src.post_progresses.validate_headers")
    @patch("src.post_progresses.logging")
    def test_post_progresses_validation_error(
        self,
        mock_logging,
        mock_validate_headers,
        mock_validate_route_params,
        mock_validate_body,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_body.return_value = ["Invalid order: not a list"]
        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []

        req_body = json.dumps({"order": "not a list"}).encode()
        req = func.HttpRequest(
            method="POST",
            body=req_body,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = post_progresses(req)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_body(), b"Invalid order: not a list")
        mock_validate_body.assert_called_once_with(req_body)
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.post_progresses.validate_body")
    @patch("src.post_progresses.validate_route_params")
    @patch("src.post_progresses.validate_headers")
    @patch("src.post_progresses.get_read_write_container")
    @patch("src.post_progresses.logging")
    def test_post_progresses_already_exists(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_headers,
        mock_validate_route_params,
        mock_validate_body,
    ):
        """既にテストを解く問題番号の順番を保存していた場合のテスト"""

        mock_validate_body.return_value = []
        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.return_value = {
            "id": "user-id-1_test-id-1",
            "userId": "user-id-1",
            "testId": "test-id-1",
            "order": [3, 5, 1, 2, 4],
            "progresses": [],
        }

        req_body = json.dumps({"order": [5, 4, 3, 2, 1]}).encode()
        req = func.HttpRequest(
            method="POST",
            body=req_body,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = post_progresses(req)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_body(), b"Progresses Order Already exists")
        mock_validate_body.assert_called_once_with(req_body)
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users", container_name="Progress"
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id-1_test-id-1", partition_key="test-id-1"
        )
        mock_container.upsert_item.assert_not_called()
        mock_logging.info.assert_called_once_with(
            {"test_id": "test-id-1", "user_id": "user-id-1"}
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progresses.validate_body")
    @patch("src.post_progresses.validate_route_params")
    @patch("src.post_progresses.validate_headers")
    @patch("src.post_progresses.get_read_write_container")
    @patch("src.post_progresses.logging")
    def test_post_progresses_exception(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_headers,
        mock_validate_route_params,
        mock_validate_body,
    ):
        """例外が発生した場合のテスト"""

        mock_validate_body.return_value = []
        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.side_effect = CosmosResourceNotFoundError
        mock_container.upsert_item.side_effect = Exception("Test Exception")

        req_body = json.dumps({"order": [3, 5, 1, 2, 4]}).encode()
        req = func.HttpRequest(
            method="POST",
            body=req_body,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = post_progresses(req)

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.get_body(), b"Internal Server Error")
        mock_validate_body.assert_called_once_with(req_body)
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users", container_name="Progress"
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id-1_test-id-1", partition_key="test-id-1"
        )
        mock_container.upsert_item.assert_called_once()
        mock_logging.info.assert_called_once_with(
            {"test_id": "test-id-1", "user_id": "user-id-1"}
        )
        mock_logging.error.assert_called_once()
