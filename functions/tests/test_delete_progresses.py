"""delete_progresses関数のテスト"""

import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from src.delete_progresses import chunk_list, delete_progresses, validate_request


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = func.HttpRequest(
            method="DELETE",
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
            method="DELETE",
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
            method="DELETE",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": ""},
        )
        errors = validate_request(req)
        self.assertEqual(errors, "X-User-Id header is Empty")


class TestChunkList(unittest.TestCase):
    """chunk_list関数のテストケース"""

    def test_chunk_list_empty(self):
        """空のリストの場合のテスト"""
        chunks = list(chunk_list([], 10))
        self.assertEqual(chunks, [])

    def test_chunk_list_less_than_chunk_size(self):
        """チャンクサイズより小さいリストの場合のテスト"""
        items = [1, 2, 3]
        chunks = list(chunk_list(items, 10))
        self.assertEqual(chunks, [[1, 2, 3]])

    def test_chunk_list_equal_to_chunk_size(self):
        """チャンクサイズと同じサイズのリストの場合のテスト"""
        items = [1, 2, 3]
        chunks = list(chunk_list(items, 3))
        self.assertEqual(chunks, [[1, 2, 3]])

    def test_chunk_list_greater_than_chunk_size(self):
        """チャンクサイズより大きいリストの場合のテスト"""
        items = [1, 2, 3, 4, 5, 6, 7]
        chunks = list(chunk_list(items, 3))
        self.assertEqual(chunks, [[1, 2, 3], [4, 5, 6], [7]])


class TestDeleteProgresses(unittest.TestCase):
    """delete_progresses関数のテストケース"""

    @patch("src.delete_progresses.validate_request")
    @patch("src.delete_progresses.get_read_write_container")
    @patch("src.delete_progresses.chunk_list")
    @patch("src.delete_progresses.logging")
    def test_delete_progresses_success(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        mock_logging,
        mock_chunk_list,
        mock_get_read_write_container,
        mock_validate_request,
    ):
        """正常系のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        items = [{"id": "user-id-1_test-id-1_1"}, {"id": "user-id-1_test-id-1_2"}]
        mock_container.query_items.return_value = items
        mock_chunk_list.return_value = [
            [{"id": "user-id-1_test-id-1_1"}, {"id": "user-id-1_test-id-1_2"}]
        ]

        req = func.HttpRequest(
            method="DELETE",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = delete_progresses(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_body(), b"OK")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users", container_name="Progress"
        )
        mock_container.query_items.assert_called_once_with(
            query="SELECT c.id FROM c WHERE c.userId = @userId AND c.testId = @testId",
            parameters=[
                {"name": "@userId", "value": "user-id-1"},
                {"name": "@testId", "value": "test-id-1"},
            ],
            partition_key="test-id-1",
        )
        mock_chunk_list.assert_called_once_with(items, 50)
        mock_container.delete_item.assert_has_calls(
            [
                call(item="user-id-1_test-id-1_1", partition_key="test-id-1"),
                call(item="user-id-1_test-id-1_2", partition_key="test-id-1"),
            ]
        )
        mock_logging.info.assert_has_calls(
            [
                call({"test_id": "test-id-1", "user_id": "user-id-1"}),
                call({"items": items}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.delete_progresses.validate_request")
    @patch("src.delete_progresses.logging")
    def test_delete_progresses_validation_error(
        self,
        mock_logging,
        mock_validate_request,
    ):
        """バリデーションエラーのテスト"""

        mock_validate_request.return_value = "testId is Empty"

        req = func.HttpRequest(
            method="DELETE",
            body=None,
            url="/tests//progresses",
            route_params={"testId": ""},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = delete_progresses(req)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_body(), b"testId is Empty")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.delete_progresses.validate_request")
    @patch("src.delete_progresses.get_read_write_container")
    @patch("src.delete_progresses.logging")
    def test_delete_progresses_empty_items(
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_request,
    ):
        """対象アイテムが存在しない場合のテスト"""

        mock_validate_request.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = []

        req = func.HttpRequest(
            method="DELETE",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = delete_progresses(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_body(), b"OK")
        mock_container.query_items.assert_called_once()
        mock_container.delete_item.assert_not_called()
        mock_logging.info.assert_has_calls(
            [
                call({"test_id": "test-id-1", "user_id": "user-id-1"}),
                call({"items": []}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.delete_progresses.validate_request")
    @patch("src.delete_progresses.get_read_write_container")
    @patch("src.delete_progresses.logging")
    def test_delete_progresses_exception(
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_request,
    ):
        """例外発生時のテスト"""

        mock_validate_request.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.side_effect = Exception("Test Exception")

        req = func.HttpRequest(
            method="DELETE",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        resp = delete_progresses(req)

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.get_body(), b"Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "test_id": "test-id-1",
                "user_id": "user-id-1",
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.delete_progresses.validate_request")
    @patch("src.delete_progresses.get_read_write_container")
    @patch("src.delete_progresses.chunk_list")
    @patch("src.delete_progresses.logging")
    def test_delete_progresses_with_multiple_chunks(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        mock_logging,
        mock_chunk_list,
        mock_get_read_write_container,
        mock_validate_request,
    ):
        """複数チャンクがある場合のテスト"""

        # モックの設定
        mock_validate_request.return_value = []

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container

        # テスト対象データ - 60個のアイテムを想定
        items = [{"id": f"user-id-1_test-id-1_{i}"} for i in range(60)]
        mock_container.query_items.return_value = items

        # チャンク処理のモック設定 - 50個と10個の2チャンクに分割
        chunk1 = [{"id": f"user-id-1_test-id-1_{i}"} for i in range(50)]
        chunk2 = [{"id": f"user-id-1_test-id-1_{i}"} for i in range(50, 60)]
        mock_chunk_list.return_value = [chunk1, chunk2]

        # リクエストの作成
        req = func.HttpRequest(
            method="DELETE",
            body=None,
            url="/tests/test-id-1/progresses",
            route_params={"testId": "test-id-1"},
            headers={"X-User-Id": "user-id-1"},
        )

        # 関数の実行
        resp = delete_progresses(req)

        # アサーション
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_body(), b"OK")

        # モックの呼び出し確認
        mock_chunk_list.assert_called_once_with(items, 50)
        self.assertEqual(mock_container.delete_item.call_count, 60)
        mock_logging.info.assert_has_calls(
            [
                call({"test_id": "test-id-1", "user_id": "user-id-1"}),
                call({"items": items}),
            ]
        )
        mock_logging.error.assert_not_called()
