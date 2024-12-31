"""[GET] /tests/{testId} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.get_test import get_test, validate_request
from type.cosmos import Test
from type.response import GetTestRes


class TestValidateRequest(TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        result = validate_request(req)

        self.assertIsNone(result)

    def test_validate_request_test_id_empty(self):
        """testIdが空である場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {}
        result = validate_request(req)

        self.assertEqual(result, "testId is Empty")


class TestGetTest(TestCase):
    """get_test関数のテストケース"""

    @patch("src.get_test.validate_request")
    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_success(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """レスポンスが正常であることのテスト"""

        mock_container = MagicMock()
        mock_items: list[Test] = [
            {"id": "1", "courseName": "Math", "testName": "Algebra", "length": 10}
        ]
        mock_validate_request.return_value = None
        mock_container.query_items.return_value = mock_items
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response = get_test(req)

        self.assertEqual(response.status_code, 200)
        expected_body: GetTestRes = {
            "id": "1",
            "courseName": "Math",
            "testName": "Algebra",
            "length": 10,
        }
        self.assertEqual(response.get_body().decode(), json.dumps(expected_body))
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Test",
        )
        mock_container.query_items.assert_called_once_with(
            query="SELECT c.id, c.courseName, c.testName, c.length FROM c WHERE c.id = @testId",
            parameters=[{"name": "@testId", "value": "1"}],
        )
        mock_logging.info.assert_called_once_with({"items": mock_items})
        mock_logging.error.assert_not_called()

    @patch("src.get_test.validate_request")
    def test_get_test_validation_error(self, mock_validate_request):
        """バリデーションチェックに失敗した場合のテスト"""

        mock_validate_request.return_value = "Validation Error"

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}

        response = get_test(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "Validation Error")

    @patch("src.get_test.validate_request")
    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_not_found(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """テストが見つからない場合のテスト"""

        mock_container = MagicMock()
        mock_container.query_items.return_value = []
        mock_validate_request.return_value = None
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response = get_test(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body().decode(), "Not Found Test")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Test",
        )
        mock_container.query_items.assert_called_once_with(
            query="SELECT c.id, c.courseName, c.testName, c.length FROM c WHERE c.id = @testId",
            parameters=[{"name": "@testId", "value": "1"}],
        )
        mock_logging.info.assert_called_once_with({"items": []})
        mock_logging.error.assert_not_called()

    @patch("src.get_test.validate_request")
    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_not_unique(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """テストが一意でない場合のテスト"""

        mock_container = MagicMock()
        mock_items: list[Test] = [
            {"id": "1", "courseName": "Math", "testName": "Algebra", "length": 10},
            {"id": "1", "courseName": "Math", "testName": "Geometry", "length": 20},
        ]
        mock_container.query_items.return_value = mock_items
        mock_get_read_only_container.return_value = mock_container
        mock_validate_request.return_value = None
        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response = get_test(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Test",
        )
        mock_container.query_items.assert_called_once_with(
            query="SELECT c.id, c.courseName, c.testName, c.length FROM c WHERE c.id = @testId",
            parameters=[{"name": "@testId", "value": "1"}],
        )
        mock_logging.info.assert_called_once_with({"items": mock_items})
        mock_logging.error.assert_called_once()

    @patch("src.get_test.validate_request")
    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_exception(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_test.get_read_only_container"
        )
        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response = get_test(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body(), b"Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()
