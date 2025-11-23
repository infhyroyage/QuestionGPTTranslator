"""Queue Storageのユーティリティ関数のテスト"""

import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from azure.storage.queue import QueueClient
from util.queue import AZURITE_QUEUE_STORAGE_CONNECTION_STRING, get_queue_client


class TestGetQueueClient(TestCase):
    """get_queue_client関数のテストケース"""

    @patch("util.queue.QueueClient.from_connection_string")
    @patch.dict(os.environ, {"AzureWebJobsStorage": "UseDevelopmentStorage=true"})
    def test_get_queue_client_local_environment(self, mock_from_connection_string):
        """ローカル環境でget_queue_client関数を呼び出すテスト"""

        mock_queue_client = MagicMock(spec=QueueClient)
        mock_from_connection_string.return_value = mock_queue_client

        result = get_queue_client("test-queue")

        mock_from_connection_string.assert_called_once()
        call_kwargs = mock_from_connection_string.call_args[1]
        self.assertEqual(
            call_kwargs["conn_str"], AZURITE_QUEUE_STORAGE_CONNECTION_STRING
        )
        self.assertEqual(call_kwargs["queue_name"], "test-queue")
        self.assertIsNotNone(call_kwargs["message_encode_policy"])
        self.assertEqual(result, mock_queue_client)

    @patch("util.queue.DefaultAzureCredential")
    @patch("util.queue.QueueClient")
    @patch.dict(
        os.environ,
        {
            "AzureWebJobsStorage__accountName": "teststorageaccount",
        },
    )
    def test_get_queue_client_azure_environment(
        self, mock_queue_client_class, mock_default_azure_credential
    ):
        """Azure環境でget_queue_client関数を呼び出すテスト"""

        mock_queue_client = MagicMock(spec=QueueClient)
        mock_queue_client_class.return_value = mock_queue_client
        mock_credential = MagicMock()
        mock_default_azure_credential.return_value = mock_credential

        result = get_queue_client("test-queue")

        mock_default_azure_credential.assert_called_once()
        mock_queue_client_class.assert_called_once()
        call_kwargs = mock_queue_client_class.call_args[1]
        self.assertEqual(
            call_kwargs["account_url"],
            "https://teststorageaccount.queue.core.windows.net",
        )
        self.assertEqual(call_kwargs["queue_name"], "test-queue")
        self.assertEqual(call_kwargs["credential"], mock_credential)
        self.assertIsNotNone(call_kwargs["message_encode_policy"])
        self.assertEqual(result, mock_queue_client)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_queue_client_azure_environment_missing_account_name(self):
        """Azure環境でAzureWebJobsStorage__accountNameが未設定の場合のテスト"""

        with self.assertRaises(ValueError) as context:
            get_queue_client("test-queue")

        self.assertIn(
            "AzureWebJobsStorage__accountName environment variable is not set",
            str(context.exception),
        )
