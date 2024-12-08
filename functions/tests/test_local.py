"""ローカル環境でのインポート処理のユーティリティ関数のテスト"""

import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from azure.core.exceptions import ResourceExistsError
from azure.cosmos import PartitionKey
from type.cosmos import Question, Test
from type.importing import ImportData
from util.local import (
    create_databases_and_containers,
    create_import_data,
    create_queue_storages,
    generate_question_items,
    generate_test_items,
    import_question_items,
    import_test_items,
)
from util.queue import AZURITE_QUEUE_STORAGE_CONNECTION_STRING


class TestLocalUtils(unittest.TestCase):
    """ローカル環境でのインポート処理のユーティリティ関数のテストケース"""

    @patch("util.local.QueueClient.from_connection_string")
    def test_create_queue_storages_when_queue_not_exists(
        self, mock_from_connection_string
    ):
        """まだQueueが存在しない場合のcreate_queue_storages関数のテスト"""
        mock_queue_client = MagicMock()
        mock_from_connection_string.return_value = mock_queue_client

        create_queue_storages()

        mock_from_connection_string.assert_called_once_with(
            conn_str=AZURITE_QUEUE_STORAGE_CONNECTION_STRING,
            queue_name="answers",
        )
        mock_queue_client.create_queue.assert_called_once()

    @patch("util.local.QueueClient.from_connection_string")
    def test_create_queue_storages_when_queue_exists(self, mock_from_connection_string):
        """Queueが既に存在する場合のcreate_queue_storages関数のテスト"""
        mock_queue_client = MagicMock()
        mock_from_connection_string.return_value = mock_queue_client
        mock_queue_client.create_queue.side_effect = ResourceExistsError

        create_queue_storages()

        mock_from_connection_string.assert_called_once_with(
            conn_str=AZURITE_QUEUE_STORAGE_CONNECTION_STRING,
            queue_name="answers",
        )
        mock_queue_client.create_queue.assert_called_once()

    @patch("util.local.CosmosClient")
    @patch(
        "util.local.os.environ",
        {
            "COSMOSDB_URI": "https://fake-uri",
            "COSMOSDB_KEY": "fake-key",
        },
    )
    def test_create_databases_and_containers(self, mock_cosmos_client):
        """create_databases_and_containers関数のテスト"""
        mock_client_instance = mock_cosmos_client.return_value
        mock_database = mock_client_instance.create_database_if_not_exists.return_value

        create_databases_and_containers()

        mock_cosmos_client.assert_called_once_with("https://fake-uri", "fake-key")
        mock_client_instance.create_database_if_not_exists.assert_called_once_with(
            id="Users"
        )
        mock_database.create_container_if_not_exists.assert_any_call(
            id="Test",
            partition_key=PartitionKey(path="/id"),
            # Azure Cosmos DBでは複合インデックスのインデックスポリシーをサポートするが
            # 2024/11/24現在、Azure Cosmos DB Linux-based Emulator (preview)では未サポートのため
            # そのインデックスポリシーを定義しない
            # indexing_policy={
            #     "compositeIndexes": [
            #         [
            #             {"path": "/courseName", "order": "ascending"},
            #             {"path": "/testName", "order": "ascending"},
            #         ]
            #     ]
            # },
        )
        mock_database.create_container_if_not_exists.assert_any_call(
            id="Question", partition_key=PartitionKey(path="/id")
        )

    @patch("util.local.os.path.exists")
    def test_create_import_data_when_data_not_exists(self, mock_exists):
        """dataファイル/ディレクトリが存在しない場合のcreate_import_data関数のテスト"""

        mock_exists.return_value = False

        import_data = create_import_data()

        expected_data = {}
        self.assertEqual(import_data, expected_data)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"question": "Q1"}]',
    )
    @patch("util.local.os.path.exists")
    @patch("util.local.os.listdir")
    @patch("util.local.os.path.isdir")
    def test_create_import_data_when_data_exists(
        self,
        mock_isdir,
        mock_listdir,
        mock_exists,
        mock_builtins_open,  # pylint: disable=W0613
    ):
        """dataファイル/ディレクトリが存在する場合のcreate_import_data関数のテスト"""

        data_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data")
        )

        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.side_effect = lambda path: {
            data_path: [
                "Math",
                "Science",
            ],
            f"{data_path}/Math": [
                "Algebra.json",
                "Geometry.json",
            ],
            f"{data_path}/Science": [
                "Algebra.json",
                "Geometry.json",
            ],
        }[path]

        import_data = create_import_data()

        expected_data = {
            "Math": {
                "Algebra": [{"question": "Q1"}],
                "Geometry": [{"question": "Q1"}],
            },
            "Science": {
                "Algebra": [{"question": "Q1"}],
                "Geometry": [{"question": "Q1"}],
            },
        }
        self.assertEqual(import_data, expected_data)

    @patch("util.local.get_read_write_container")
    def test_generate_test_items_when_retrieved_successfully(
        self, mock_get_read_write_container
    ):
        """テスト項目を正常取得した場合のgenerate_test_items関数のテスト"""
        mock_container = MagicMock()
        mock_container.read_all_items.return_value = [
            {"courseName": "Math", "testName": "Algebra", "id": "1", "length": 10}
        ]
        mock_get_read_write_container.return_value = mock_container

        import_data: ImportData = {
            "Math": {
                "Algebra": [{"question": "Q1"}],
                "Geometry": [{"question": "Q2"}],
            }
        }
        test_items = generate_test_items(import_data)

        self.assertEqual(len(test_items), 2)
        self.assertEqual(
            test_items[0],
            {"courseName": "Math", "testName": "Algebra", "id": "1", "length": 10},
        )
        self.assertEqual(test_items[1]["courseName"], "Math")
        self.assertEqual(test_items[1]["testName"], "Geometry")
        self.assertEqual(test_items[1]["length"], 1)
        self.assertIn("id", test_items[1])

    @patch("util.local.get_read_write_container")
    def test_generate_test_items_when_retrieved_failed(
        self, mock_get_read_write_container
    ):
        """テスト項目の取得に失敗した場合のgenerate_test_items関数のテスト"""
        mock_container = MagicMock()
        mock_container.read_all_items.side_effect = Exception(
            "Error in util.local.get_read_write_container"
        )
        mock_get_read_write_container.return_value = mock_container

        import_data: ImportData = {
            "Math": {
                "Algebra": [{"question": "Q1"}],
                "Geometry": [{"question": "Q2"}],
            }
        }
        test_items = generate_test_items(import_data)

        self.assertEqual(len(test_items), 2)
        self.assertEqual(test_items[0]["courseName"], "Math")
        self.assertEqual(test_items[0]["testName"], "Algebra")
        self.assertEqual(test_items[0]["length"], 1)
        self.assertIn("id", test_items[0])
        self.assertEqual(test_items[1]["courseName"], "Math")
        self.assertEqual(test_items[1]["testName"], "Geometry")
        self.assertEqual(test_items[1]["length"], 1)
        self.assertIn("id", test_items[1])

    @patch("util.local.get_read_write_container")
    def test_import_test_items(self, mock_get_read_write_container):
        """import_test_items関数のテスト"""
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container

        test_items: list[Test] = [
            {"courseName": "Math", "testName": "Algebra", "id": "1", "length": 10}
        ]
        import_test_items(test_items)

        mock_container.upsert_item.assert_called_once_with(test_items[0])

    @patch("util.local.get_read_write_container")
    def test_generate_question_items_without_value_error(
        self, mock_get_read_write_container
    ):
        """途中でValueErrorが発生しない場合のgenerate_question_items関数のテスト"""
        mock_container = MagicMock()
        mock_container.query_items.return_value = [{"id": "2"}]
        mock_get_read_write_container.return_value = mock_container

        import_data: ImportData = {
            "Math": {
                "Algebra": [{"question": "Q1", "communityVotes": ["AB (100%)"]}],
            }
        }
        test_items: list[Test] = [
            {"courseName": "Math", "testName": "Algebra", "id": "1", "length": 1}
        ]
        question_items = generate_question_items(import_data, test_items)

        expected_items = [
            {
                "question": "Q1",
                "communityVotes": ["AB (100%)"],
                "id": "1_1",
                "number": 1,
                "testId": "1",
                "isMultiplied": True,
            }
        ]
        self.assertEqual(question_items, expected_items)

    @patch("util.local.get_read_write_container")
    def test_generate_question_items_with_value_error(
        self, mock_get_read_write_container
    ):
        """途中でValueErrorが発生した場合のgenerate_question_items関数のテスト"""
        mock_container = MagicMock()
        mock_container.query_items.return_value = [{"id": "2"}]
        mock_get_read_write_container.return_value = mock_container

        import_data: ImportData = {
            "Math": {
                "Algebra": [{"question": "Q1", "communityVotes": ["AB (100%)"]}],
            }
        }
        test_items: list[Test] = [
            {"courseName": "Science", "testName": "Physics", "id": "1", "length": 1}
        ]

        with self.assertRaises(ValueError) as context:
            generate_question_items(import_data, test_items)

        self.assertEqual(
            str(context.exception), "Course Name Math and Test Name Algebra Not Found."
        )

    @patch("util.local.get_read_write_container")
    def test_import_question_items(self, mock_get_read_write_container):
        """import_question_items関数のテスト"""
        mock_container = MagicMock()
        mock_container.upsert_item.return_value = {"statusCode": 200}
        mock_get_read_write_container.return_value = mock_container

        question_items: list[Question] = [
            {
                "question": "Q1",
                "communityVotes": ["AB (100%)"],
                "id": "1_1",
                "number": 1,
                "testId": "1",
                "isMultiplied": True,
            }
        ]
        import_question_items(question_items)

        mock_container.upsert_item.assert_called_once_with(question_items[0])
