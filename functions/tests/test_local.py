"""ローカル環境でのインポート処理のユーティリティ関数のテスト"""

import os
import unittest
from unittest.mock import MagicMock, mock_open, patch
from uuid import uuid4

from azure.cosmos import PartitionKey
from type.cosmos import Question, Test
from type.importing import ImportData
from util.local import (
    create_databases_and_containers,
    create_import_data,
    generate_question_items,
    generate_test_items,
    import_question_items,
    import_test_items,
)


class TestLocalUtils(unittest.TestCase):
    """ローカル環境でのインポート処理のユーティリティ関数のテストケース"""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"question": "Q1"}]',
    )
    @patch("util.local.os.path.exists")
    @patch("util.local.os.listdir")
    @patch("util.local.os.path.isdir")
    def test_create_import_data(
        self, mock_isdir, mock_listdir, mock_exists, mock_builtins_open
    ):
        """create_import_data関数のテスト"""

        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.side_effect = lambda path: {
            f"{os.getcwd()}/data": [
                "Math",
                "Science",
            ],
            f"{os.getcwd()}/data/Math": [
                "Algebra.json",
                "Geometry.json",
            ],
            f"{os.getcwd()}/data/Science": [
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
            indexing_policy={
                "compositeIndexes": [
                    [
                        {"path": "/courseName", "order": "ascending"},
                        {"path": "/testName", "order": "ascending"},
                    ]
                ]
            },
        )
        mock_database.create_container_if_not_exists.assert_any_call(
            id="Question", partition_key=PartitionKey(path="/id")
        )

    @patch("util.local.get_read_write_container")
    def test_generate_test_items(self, mock_get_read_write_container):
        """generate_test_items関数のテスト"""
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

        expected_items = [
            {"courseName": "Math", "testName": "Algebra", "id": "1", "length": 10},
            {
                "courseName": "Math",
                "testName": "Geometry",
                "id": str(uuid4()),
                "length": 1,
            },
        ]
        self.assertEqual(len(test_items), 2)
        self.assertEqual(test_items[0], expected_items[0])
        self.assertEqual(test_items[1]["courseName"], expected_items[1]["courseName"])
        self.assertEqual(test_items[1]["testName"], expected_items[1]["testName"])
        self.assertEqual(test_items[1]["length"], expected_items[1]["length"])

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
    def test_generate_question_items(self, mock_get_read_write_container):
        """generate_question_items関数のテスト"""
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
