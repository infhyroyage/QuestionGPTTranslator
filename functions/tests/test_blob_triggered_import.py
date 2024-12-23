"""インポートデータファイルの項目をインポートするBlobトリガーの関数アプリのテスト"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from src.blob_triggered_import import upsert_question_items, upsert_test_item
from type.cosmos import Test
from type.importing import ImportItem


class TestBlobTriggeredImport(TestCase):
    """blob_triggered_importモジュールのテストケース"""

    @patch("src.blob_triggered_import.get_read_write_container")
    @patch("src.blob_triggered_import.uuid4")
    def test_upsert_test_item_new(self, mock_uuid4, mock_get_read_write_container):
        """新しいTest項目をupsertするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = []
        mock_uuid4.return_value = "new-uuid"

        course_name = "Math"
        test_name = "Algebra"
        json_data = [
            ImportItem(subjects=["Q1"], choices=["A", "B"], communityVotes=["A (100%)"])
        ]

        test_id, is_existed_test = upsert_test_item(course_name, test_name, json_data)

        self.assertFalse(is_existed_test)
        self.assertEqual(test_id, "new-uuid")
        mock_container.upsert_item.assert_called_once()

    @patch("src.blob_triggered_import.get_read_write_container")
    def test_upsert_test_item_existing(self, mock_get_read_write_container):
        """既存のTest項目をupsertするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        existing_test_id = "existing-uuid"
        mock_container.query_items.return_value = [
            Test(id=existing_test_id, courseName="Math", testName="Algebra", length=1)
        ]

        course_name = "Math"
        test_name = "Algebra"
        json_data = [
            ImportItem(subjects=["Q1"], choices=["A", "B"], communityVotes=["A (100%)"])
        ]

        test_id, is_existed_test = upsert_test_item(course_name, test_name, json_data)

        self.assertTrue(is_existed_test)
        self.assertEqual(test_id, existing_test_id)
        mock_container.upsert_item.assert_not_called()

    @patch("src.blob_triggered_import.get_read_write_container")
    def test_upsert_test_item_not_unique(self, mock_get_read_write_container):
        """Test項目が一意でない場合にValueErrorをraiseするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = [
            Test(id="uuid1", courseName="Math", testName="Algebra", length=1),
            Test(id="uuid2", courseName="Math", testName="Algebra", length=1),
        ]

        course_name = "Math"
        test_name = "Algebra"
        json_data = [
            ImportItem(subjects=["Q1"], choices=["A", "B"], communityVotes=["A (100%)"])
        ]

        with self.assertRaises(ValueError) as context:
            upsert_test_item(course_name, test_name, json_data)

        self.assertEqual(str(context.exception), "Not Unique Test")

    @patch("src.blob_triggered_import.time.sleep")
    @patch("src.blob_triggered_import.get_read_write_container")
    @patch("src.blob_triggered_import.uuid4")
    def test_upsert_question_items(
        self,
        mock_uuid4,
        mock_get_read_write_container,
        mock_sleep,  # pylint: disable=W0613
    ):
        """Testコンテナーの項目が取得できない場合でQuestion項目をupsertするテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = []
        mock_uuid4.return_value = "new-uuid"

        test_id = "new-uuid"
        is_existed_test = False
        json_data = [
            ImportItem(subjects=["Q1"], choices=["A", "B"], communityVotes=["A (100%)"])
        ]

        upsert_question_items(test_id, is_existed_test, json_data)

        expected_question_item = {
            "subjects": ["Q1"],
            "choices": ["A", "B"],
            "communityVotes": ["A (100%)"],
            "id": "new-uuid_1",
            "number": 1,
            "testId": "new-uuid",
            "isMultiplied": False,
        }
        mock_container.upsert_item.assert_called_once_with(expected_question_item)

    # TODO: ユニットテストの完成
