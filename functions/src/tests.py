"""
Module of [GET] /tests
"""

import json
import logging
import os

import azure.functions as func
from utils.cosmos import get_read_only_container

COSMOS_DB_DATABASE_NAME = "Users"
COSMOS_DB_CONTAINER_NAME = "Test"

bp_tests = func.Blueprint()


@bp_tests.route(route="tests")
def main(req: func.HttpRequest) -> func.HttpResponse:  # pylint: disable=unused-argument
    """
    Retrieve All Tests
    """

    try:
        # Initialize Cosmos DB Client
        container = get_read_only_container(
            database_name=COSMOS_DB_DATABASE_NAME,
            container_name=COSMOS_DB_CONTAINER_NAME,
        )

        # Execute Query
        # TODO: Azure SDK for Pythonで複合インデックスをサポートしたら修正する
        # Azure上では複合インデックスを作成するインデックスポリシーを定義している
        # 暫定的に、Azure上のみORDER BY句を設定している
        query = "SELECT c.id, c.courseName, c.testName, c.length FROM c"
        if os.environ["COSMOSDB_URI"] != "https://localhost:8081":
            query += " ORDER BY c.courseName ASC, c.testName ASC"
        items = list(
            container.query_items(query=query, enable_cross_partition_query=True)
        )
        logging.info({"items": items})

        # Format the response by grouping items by courseName
        body = {}
        for item in items:
            tmp_item = {"id": item["id"], "testName": item["testName"]}
            if item["courseName"] in body:
                body[item["courseName"]].append(tmp_item)
            else:
                body[item["courseName"]] = [tmp_item]
        logging.info({"body": body})

        return func.HttpResponse(
            body=json.dumps(body), status_code=200, mimetype="application/json"
        )
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
