"""Queue Storageのユーティリティ関数"""

import os

from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueClient

# pylint: disable=line-too-long
AZURITE_QUEUE_STORAGE_CONNECTION_STRING: str = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
)


def get_queue_client(queue_name: str) -> QueueClient:
    """
    環境に応じたQueueClientを取得します

    Args:
        queue_name (str): キュー名

    Returns:
        QueueClient: キュークライアント

    Raises:
        ValueError: Azure環境でAzureWebJobsStorage__accountNameが設定されていない場合
    """
    # ローカル環境の場合はAzuriteへの接続文字列を使用し、
    # Azure環境の場合はManaged Identityを使用
    if os.environ.get("AzureWebJobsStorage", "") == "UseDevelopmentStorage=true":
        return QueueClient.from_connection_string(
            conn_str=AZURITE_QUEUE_STORAGE_CONNECTION_STRING,
            queue_name=queue_name,
        )

    account_name = os.environ.get("AzureWebJobsStorage__accountName")
    if not account_name:
        raise ValueError(
            "AzureWebJobsStorage__accountName environment variable is not set"
        )

    account_url = f"https://{account_name}.queue.core.windows.net"
    return QueueClient(
        account_url=account_url,
        queue_name=queue_name,
        credential=DefaultAzureCredential(),
    )
