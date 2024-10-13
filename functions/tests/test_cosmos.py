"""Cosmos DBのユーティリティ関数のテスト"""

import os
import unittest
from unittest.mock import MagicMock, patch

from azure.cosmos import ContainerProxy
from util.cosmos import get_read_only_container, get_read_write_container


class TestCosmosUtils(unittest.TestCase):
    """Cosmos DBのユーティリティ関数のテストケース"""

    @patch("util.cosmos.CosmosClient")
    @patch.dict(
        os.environ,
        {
            "COSMOSDB_URI": "https://fake-uri",
            "COSMOSDB_READONLY_KEY": "fake-readonly-key",
            "COSMOSDB_KEY": "fake-key",
        },
    )
    def test_get_read_only_container(self, mock_cosmos_client):
        """get_read_only_container関数のテスト"""

        mock_container = MagicMock(spec=ContainerProxy)
        mock_database_client = MagicMock()
        mock_database_client.get_container_client.return_value = mock_container
        mock_cosmos_client.return_value.get_database_client.return_value = (
            mock_database_client
        )

        container = get_read_only_container("TestDB", "TestContainer")

        mock_cosmos_client.assert_called_once_with(
            url="https://fake-uri", credential="fake-readonly-key"
        )
        mock_database_client.get_container_client.assert_called_once_with(
            "TestContainer"
        )
        self.assertEqual(container, mock_container)

    @patch("util.cosmos.CosmosClient")
    @patch.dict(
        os.environ,
        {
            "COSMOSDB_URI": "https://fake-uri",
            "COSMOSDB_READONLY_KEY": "fake-readonly-key",
            "COSMOSDB_KEY": "fake-key",
        },
    )
    def test_get_read_write_container(self, mock_cosmos_client):
        """get_read_write_container関数のテスト"""

        mock_container = MagicMock(spec=ContainerProxy)
        mock_database_client = MagicMock()
        mock_database_client.get_container_client.return_value = mock_container
        mock_cosmos_client.return_value.get_database_client.return_value = (
            mock_database_client
        )

        container = get_read_write_container("TestDB", "TestContainer")

        mock_cosmos_client.assert_called_once_with(
            url="https://fake-uri", credential="fake-key"
        )
        mock_database_client.get_container_client.assert_called_once_with(
            "TestContainer"
        )
        self.assertEqual(container, mock_container)
