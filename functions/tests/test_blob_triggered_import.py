"""インポートデータファイルの項目をインポートするBlobトリガーの関数アプリのテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from src.blob_triggered_import import (
    blob_triggered_import,
    upsert_question_items,
    upsert_test_item,
)
from type.cosmos import Question, Test
from type.importing import ImportItem


class TestBlobTriggeredImport(TestCase):
    """blob_triggered_importモジュールのテストケース"""

    @patch("src.blob_triggered_import.get_read_write_container")
    @patch("src.blob_triggered_import.uuid4")
    @patch("src.blob_triggered_import.logging")
    def test_upsert_test_item_new(
        self, mock_logging, mock_uuid4, mock_get_read_write_container
    ):
        """新しいTest項目をupsertするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = []
        mock_uuid4.return_value = "test-id"

        course_name = "Math"
        test_name = "Algebra"
        json_data = [
            ImportItem(subjects=["Q1"], choices=["A", "B"], communityVotes=["A (100%)"])
        ]

        test_id, is_existed_test = upsert_test_item(course_name, test_name, json_data)

        self.assertFalse(is_existed_test)
        self.assertEqual(test_id, "test-id")
        test_item = {
            "courseName": course_name,
            "testName": test_name,
            "id": "test-id",
            "length": 1,
        }
        mock_container.upsert_item.assert_called_once_with(test_item)
        mock_logging.info.assert_has_calls(
            [
                call({"inserted_test_items": []}),
                call({"test_item": test_item}),
                call({"test_id": "test-id", "is_existed_test": False}),
            ]
        )

    @patch("src.blob_triggered_import.get_read_write_container")
    @patch("src.blob_triggered_import.logging")
    def test_upsert_test_item_existing(
        self, mock_logging, mock_get_read_write_container
    ):
        """既存のTest項目をupsertするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        existing_test_id = "existing-uuid"
        inserted_test_items = [
            Test(id=existing_test_id, courseName="Math", testName="Algebra", length=1)
        ]
        mock_container.query_items.return_value = inserted_test_items

        course_name = "Math"
        test_name = "Algebra"
        json_data = [
            ImportItem(subjects=["Q1"], choices=["A", "B"], communityVotes=["A (100%)"])
        ]

        test_id, is_existed_test = upsert_test_item(course_name, test_name, json_data)

        self.assertTrue(is_existed_test)
        self.assertEqual(test_id, existing_test_id)
        mock_container.upsert_item.assert_not_called()
        mock_logging.info.assert_has_calls(
            [
                call({"inserted_test_items": inserted_test_items}),
                call({"test_id": existing_test_id, "is_existed_test": True}),
            ]
        )

    @patch("src.blob_triggered_import.get_read_write_container")
    @patch("src.blob_triggered_import.logging")
    def test_upsert_test_item_not_unique(
        self, mock_logging, mock_get_read_write_container
    ):
        """Test項目が一意でない場合にValueErrorをraiseするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        inserted_test_items = [
            Test(id="uuid1", courseName="Math", testName="Algebra", length=1),
            Test(id="uuid2", courseName="Math", testName="Algebra", length=1),
        ]
        mock_container.query_items.return_value = inserted_test_items

        course_name = "Math"
        test_name = "Algebra"
        json_data = [
            ImportItem(subjects=["Q1"], choices=["A", "B"], communityVotes=["A (100%)"])
        ]

        with self.assertRaises(ValueError) as context:
            upsert_test_item(course_name, test_name, json_data)

        self.assertEqual(str(context.exception), "Not Unique Test")
        mock_logging.info.assert_called_once_with(
            {"inserted_test_items": inserted_test_items}
        )

    @patch("src.blob_triggered_import.time.sleep")
    @patch("src.blob_triggered_import.get_read_write_container")
    @patch("src.blob_triggered_import.logging")
    def test_upsert_question_items_not_found_test(
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_sleep,  # pylint: disable=W0613
    ):
        """Testコンテナーの項目が取得できない場合でQuestion項目をupsertするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = []

        test_id = "test-id"
        is_existed_test = False
        json_data = [
            ImportItem(
                subjects=["Q1"],
                choices=["A"],
                communityVotes=["A (100%)"],
            ),
            ImportItem(
                subjects=["Q2-1", "Q2-2", "Q2-3"],
                choices=["B", "C"],
                communityVotes=["BC (70%)", "BD (30%)"],
                indicateSubjectImgIdxes=[0, 2],
                indicateChoiceImgs=["img1", "img2"],
                escapeTranslatedIdxes={"subjects": [0, 2], "choices": [1, 3]},
            ),
        ]

        upsert_question_items(test_id, is_existed_test, json_data)

        expected_question_item_1st = {
            "subjects": ["Q1"],
            "choices": ["A"],
            "communityVotes": ["A (100%)"],
            "id": "test-id_1",
            "number": 1,
            "testId": "test-id",
            "isMultiplied": False,
        }
        expected_question_item_2nd = {
            "subjects": ["Q2-1", "Q2-2", "Q2-3"],
            "choices": ["B", "C"],
            "communityVotes": ["BC (70%)", "BD (30%)"],
            "indicateSubjectImgIdxes": [0, 2],
            "indicateChoiceImgs": ["img1", "img2"],
            "escapeTranslatedIdxes": {"subjects": [0, 2], "choices": [1, 3]},
            "id": "test-id_2",
            "number": 2,
            "testId": "test-id",
            "isMultiplied": True,
        }
        mock_container.upsert_item.assert_has_calls(
            [call(expected_question_item_1st), call(expected_question_item_2nd)]
        )
        mock_logging.info.assert_has_calls(
            [
                call({"inserted_import_items": []}),
                call({"question_item": expected_question_item_1st}),
                call({"question_item": expected_question_item_2nd}),
            ]
        )

    @patch("src.blob_triggered_import.time.sleep")
    @patch("src.blob_triggered_import.get_read_write_container")
    @patch("src.blob_triggered_import.logging")
    def test_upsert_question_items_found_test(
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_sleep,  # pylint: disable=W0613
    ):
        """Testコンテナーの項目が取得できる場合でQuestion項目をupsertするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = [
            Question(
                id="test-id_2",
                number=2,
                subjects=["Q2-1", "Q2-2", "Q2-3"],
                choices=["B", "C"],
                isMultiplied=True,
                communityVotes=["BC (70%)", "BD (30%)"],
                indicateSubjectImgIdxes=[0, 2],
                indicateChoiceImgs=["img1", "img2"],
                escapeTranslatedIdxes={"subjects": [0, 2], "choices": [1, 3]},
                testId="test-id",
            ),
            Question(
                id="test-id_3",
                number=3,
                subjects=["Q3-1", "Q3-2"],
                choices=["D"],
                isMultiplied=False,
                communityVotes=["D (95%)", "B (5%)"],
                testId="test-id",
            ),
        ]
        test_id = "test-id"
        is_existed_test = True
        json_data = [
            ImportItem(
                subjects=["Q1"],
                choices=["A"],
                communityVotes=["A (100%)"],
            ),
            ImportItem(
                subjects=["Q2-1", "Q2-2", "Q2-3"],
                choices=["B", "C"],
                communityVotes=["BC (70%)", "BD (30%)"],
                indicateSubjectImgIdxes=[0, 2],
                indicateChoiceImgs=["img1", "img2"],
                escapeTranslatedIdxes={"subjects": [0, 2], "choices": [1, 3]},
            ),
        ]

        upsert_question_items(test_id, is_existed_test, json_data)

        expected_question_item = {
            "subjects": ["Q1"],
            "choices": ["A"],
            "communityVotes": ["A (100%)"],
            "id": "test-id_1",
            "number": 1,
            "testId": "test-id",
            "isMultiplied": False,
        }
        mock_container.upsert_item.assert_called_once_with(expected_question_item)
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "inserted_import_items": [
                            {
                                "subjects": ["Q2-1", "Q2-2", "Q2-3"],
                                "choices": ["B", "C"],
                                "communityVotes": ["BC (70%)", "BD (30%)"],
                                "indicateSubjectImgIdxes": [0, 2],
                                "indicateChoiceImgs": ["img1", "img2"],
                                "escapeTranslatedIdxes": {
                                    "subjects": [0, 2],
                                    "choices": [1, 3],
                                },
                            },
                            {
                                "subjects": ["Q3-1", "Q3-2"],
                                "choices": ["D"],
                                "communityVotes": ["D (95%)", "B (5%)"],
                            },
                        ]
                    }
                ),
                call({"question_item": expected_question_item}),
            ]
        )

    @patch("src.blob_triggered_import.upsert_test_item")
    @patch("src.blob_triggered_import.upsert_question_items")
    @patch("src.blob_triggered_import.logging")
    def test_blob_triggered_import(
        self, mock_logging, mock_upsert_question_items, mock_upsert_test_item
    ):
        """blob_triggered_import関数のテスト"""

        mock_upsert_test_item.return_value = ("test-id", False)

        blob_data = json.dumps(
            [{"subjects": ["Q1"], "choices": ["A"], "communityVotes": ["A (100%)"]}]
        ).encode("utf-8")

        mock_blob = MagicMock()
        mock_blob.name = "import-items/Math/Algebra.json"
        mock_blob.read.return_value = blob_data

        blob_triggered_import(mock_blob)

        mock_upsert_test_item.assert_called_once_with(
            course_name="Math",
            test_name="Algebra",
            json_data=[
                {"subjects": ["Q1"], "choices": ["A"], "communityVotes": ["A (100%)"]}
            ],
        )
        mock_upsert_question_items.assert_called_once_with(
            test_id="test-id",
            is_existed_test=False,
            json_data=[
                {"subjects": ["Q1"], "choices": ["A"], "communityVotes": ["A (100%)"]}
            ],
        )
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "test_name": "Algebra",
            }
        )
