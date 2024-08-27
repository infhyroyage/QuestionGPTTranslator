"""
Module of [GET] /tests
"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Test
from type.response import GetTestsRes
from util.cosmos import get_read_only_container

bp_get_tests = func.Blueprint()


@bp_get_tests.route(
    route="tests",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_tests(
    req: func.HttpRequest,  # pylint: disable=unused-argument
) -> func.HttpResponse:
    """
    Retrieve All Tests
    """

    try:
        # Initialize Cosmos DB Client
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Test",
        )

        # Execute Query
        query = (
            "SELECT c.id, c.courseName, c.testName, c.length"
            "FROM c"
            "ORDER BY c.courseName ASC, c.testName ASC"
        )
        items: list[Test] = list(container.query_items(query=query))
        logging.info({"items": items})

        # Format the response by grouping items by courseName
        body: GetTestsRes = {}
        for item in items:
            tmp_item = {"id": item["id"], "testName": item["testName"]}
            if item["courseName"] in body:
                body[item["courseName"]].append(tmp_item)
            else:
                body[item["courseName"]] = [tmp_item]
        logging.info({"body": body})
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
