"""[POST] /tests/{testId}/progresses/{questionNumber} のテスト"""

import json
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.post_progress import (
    post_progress,
    validate_body,
    validate_headers,
    validate_route_params,
)


class TestValidateBody(unittest.TestCase):
    """validate_body関数のテストケース"""

    def test_validate_body_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, [])

    def test_validate_body_empty(self):
        """リクエストボディが空の場合のテスト"""

        req_body_encoded = None
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Request Body is Empty"])

    def test_validate_body_missing_is_correct(self):
        """リクエストボディにisCorrectが存在しない場合のテスト"""

        req_body = {
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["isCorrect is required"])

    def test_validate_body_invalid_is_correct(self):
        """isCorrectがboolでない場合のテスト"""

        req_body = {
            "isCorrect": "true",
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid isCorrect: true"])

    def test_validate_body_missing_selected_idxes(self):
        """リクエストボディにselectedIdxesが存在しない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["selectedIdxes is required"])

    def test_validate_body_invalid_selected_idxes(self):
        """selectedIdxesがlistでない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "selectedIdxes": 0,
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid selectedIdxes: 0"])

    def test_validate_body_invalid_selected_idx_item(self):
        """selectedIdxesの要素が数値でない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "selectedIdxes": [0, "1"],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid selectedIdxes[1]: 1"])

    def test_validate_body_missing_correct_idxes(self):
        """リクエストボディにcorrectIdxesが存在しない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["correctIdxes is required"])

    def test_validate_body_invalid_correct_idxes(self):
        """correctIdxesがlistでない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": 0,
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid correctIdxes: 0"])

    def test_validate_body_invalid_correct_idx_item(self):
        """correctIdxesの要素が数値でない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0, "1"],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid correctIdxes[1]: 1"])


class TestValidateRouteParams(unittest.TestCase):
    """validate_route_params関数のテストケース"""

    def test_validate_route_params_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        route_params = {"testId": "test-id", "questionNumber": "1"}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, [])

    def test_validate_route_params_empty_test_id(self):
        """testIdが空である場合のテスト"""

        route_params = {"testId": "", "questionNumber": "1"}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["testId is Empty"])

    def test_validate_route_params_empty_question_number(self):
        """questionNumberが空である場合のテスト"""

        route_params = {"testId": "test-id", "questionNumber": ""}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["questionNumber is Empty"])

    def test_validate_route_params_invalid_question_number(self):
        """questionNumberが数字ではない場合のテスト"""

        route_params = {"testId": "test-id", "questionNumber": "abc"}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["Invalid questionNumber: abc"])


class TestValidateHeaders(unittest.TestCase):
    """validate_headers関数のテストケース"""

    def test_validate_headers_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        headers = {"X-User-Id": "user-id"}
        errors = validate_headers(headers)
        self.assertEqual(errors, [])

    def test_validate_headers_empty_user_id(self):
        """X-User-Idヘッダーが空である場合のテスト"""

        headers = {}
        errors = validate_headers(headers)
        self.assertEqual(errors, ["X-User-Id header is Empty"])


class TestPostProgress(unittest.TestCase):
    """post_progress関数のテストケース"""

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_success_with_next_question_number(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """指定した問題番号が最後に保存した問題番号の次の問題番号である場合にて、レスポンスが正常であることのテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.return_value = {
            "id": "user-id_test-id",
            "userId": "user-id",
            "testId": "test-id",
            "progresses": [
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢A", "選択肢B"],
                    "choiceImgs": [None, None],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ],
        }

        request_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/2",
            route_params={"testId": "test-id", "questionNumber": "2"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_progress(req)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_body().decode("utf-8"), "OK")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Progress",
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id_test-id", partition_key="test-id"
        )
        mock_container.upsert_item.assert_called_once_with(
            {
                "id": "user-id_test-id",
                "userId": "user-id",
                "testId": "test-id",
                "progresses": [
                    {
                        "isCorrect": True,
                        "choiceSentences": ["選択肢A", "選択肢B"],
                        "choiceImgs": [None, None],
                        "selectedIdxes": [0],
                        "correctIdxes": [0],
                    },
                    {
                        "isCorrect": True,
                        "selectedIdxes": [0],
                        "correctIdxes": [0],
                    },
                ],
            }
        )
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 2,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"inserted_progress_num": 1}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_with_same_question_number(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """指定した問題番号が最後に保存した問題番号と同じ場合にて、レスポンスが正常であることのテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.return_value = {
            "id": "user-id_test-id",
            "userId": "user-id",
            "testId": "test-id",
            "progresses": [
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢A", "選択肢B"],
                    "choiceImgs": [None, None],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ],
        }

        request_body = {
            "isCorrect": False,
            "selectedIdxes": [1],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_progress(req)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_body().decode("utf-8"), "OK")
        mock_container.upsert_item.assert_called_once_with(
            {
                "id": "user-id_test-id",
                "userId": "user-id",
                "testId": "test-id",
                "progresses": [
                    {
                        "isCorrect": False,
                        "selectedIdxes": [1],
                        "correctIdxes": [0],
                    }
                ],
            }
        )
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 1,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"inserted_progress_num": 1}),
            ]
        )

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_with_new_user(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """何も回答履歴を保存していない場合に、レスポンスが正常であることのテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.side_effect = CosmosResourceNotFoundError

        request_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_progress(req)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_body().decode("utf-8"), "OK")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Progress",
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id_test-id", partition_key="test-id"
        )
        mock_container.upsert_item.assert_called_once_with(
            {
                "id": "user-id_test-id",
                "userId": "user-id",
                "testId": "test-id",
                "progresses": [
                    {
                        "isCorrect": True,
                        "selectedIdxes": [0],
                        "correctIdxes": [0],
                    }
                ],
            }
        )
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 1,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"inserted_progress_num": 0}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.logging")
    def test_post_progress_validation_error(
        self,
        mock_logging,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = ["Validation Error"]

        request_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_progress(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_body().decode("utf-8"), "Validation Error")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_invalid_question_number_without_saved_progress(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """何も回答履歴を保存していない場合に、誤った問題番号を指定した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.return_value = {
            "id": "user-id_test-id",
            "userId": "user-id",
            "testId": "test-id",
            "progresses": [],
        }

        request_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_progress(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_body().decode("utf-8"), "questionNumber must be 1")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Progress",
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id_test-id", partition_key="test-id"
        )
        mock_container.upsert_item.assert_not_called()
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 3,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"inserted_progress_num": 0}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_invalid_question_number_with_saved_progress(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """途中まで回答履歴を保存した場合に、誤った問題番号を指定した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.read_item.return_value = {
            "id": "user-id_test-id",
            "userId": "user-id",
            "testId": "test-id",
            "progresses": [
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢A", "選択肢B"],
                    "choiceImgs": [None, None],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ],
        }

        request_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_progress(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.get_body().decode("utf-8"), "questionNumber must be 1 or 2"
        )
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Progress",
        )
        mock_container.read_item.assert_called_once_with(
            item="user-id_test-id", partition_key="test-id"
        )
        mock_container.upsert_item.assert_not_called()
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 3,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"inserted_progress_num": 1}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_exception(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """例外が発生した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_get_read_write_container.side_effect = Exception("Test Exception")

        request_body = {
            "isCorrect": True,
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )

        res = post_progress(req)

        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.get_body().decode("utf-8"), "Internal Server Error")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_logging.info.assert_called_once_with(
            {"question_number": 3, "test_id": "test-id", "user_id": "user-id"}
        )
        mock_logging.error.assert_called_once()
