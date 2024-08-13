"""
Utility functions for Cosmos DB
"""

import os

from azure.cosmos import ContainerProxy, CosmosClient


def get_read_only_container(database_name: str, container_name: str) -> ContainerProxy:
    """
    Get a read-only container from Cosmos DB

    Args:
        database_name (str): Database Name
        container_name (str): Container Name

    Returns:
        ContainerProxy: Read-only Container
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
    Get a read-write container from Cosmos DB

    Args:
        database_name (str): Database Name
        container_name (str): Container Name

    Returns:
        ContainerProxy: Read-write Container
    """

    return (
        CosmosClient(
            url=os.environ["COSMOSDB_URI"],
            credential=os.environ["COSMOSDB_KEY"],
        )
        .get_database_client(database_name)
        .get_container_client(container_name)
    )
