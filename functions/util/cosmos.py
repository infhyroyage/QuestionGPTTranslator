"""Cosmos DBのユーティリティ関数"""

import os

from azure.cosmos import ContainerProxy, CosmosClient


def get_read_only_container(database_name: str, container_name: str) -> ContainerProxy:
    """
    指定したCosmos DBアカウントのコンテナーの読み取り専用インスタンスを返す

    Args:
        database_name (str): Cosmos DBアカウントのデータベース名
        container_name (str): Cosmos DBアカウントのコンテナー名

    Returns:
        ContainerProxy: Cosmos DBアカウントのコンテナーの読み取り専用インスタンス
    """

    return (
        CosmosClient(
            url=os.environ["COSMOSDB_URI"],
            credential=os.environ["COSMOSDB_READONLY_KEY"],
        )
        .get_database_client(database_name)
        .get_container_client(container_name)
    )


def get_read_write_container(database_name: str, container_name: str) -> ContainerProxy:
    """
    指定したCosmos DBアカウントのコンテナーのインスタンスを返す

    Args:
        database_name (str): Cosmos DBアカウントのデータベース名
        container_name (str): Cosmos DBアカウントのコンテナー名

    Returns:
        ContainerProxy: Cosmos DBアカウントのコンテナーのインスタンス
    """

    return (
        CosmosClient(
            url=os.environ["COSMOSDB_URI"],
            credential=os.environ["COSMOSDB_KEY"],
        )
        .get_database_client(database_name)
        .get_container_client(container_name)
    )
