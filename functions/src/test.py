"""
Module of [GET] /tests/{testId}
"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Test
from type.response import GetTestRes
from util.cosmos import get_read_only_container

bp_test = func.Blueprint()


@bp_test.route(
    route="tests/{testId}",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def test(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve Test
    """

    try:
        # Validate Path Parameters
        test_id = req.route_params.get("testId")
        if test_id is None:
            raise ValueError(f"Invalid testId: {test_id}")

        # Initialize Cosmos DB Client
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Test",
        )

        # Execute Query
        query = (
            "SELECT c.id, c.courseName, c.testName, c.length"
            "FROM c"
            "WHERE c.id = @testId"
        )
        parameters: list[dict[str, str]] = [{"name": "@testId", "value": test_id}]
        items: list[Test] = list(
            container.query_items(query=query, parameters=parameters)
        )
        logging.info({"items": items})

        # Check the number of items
        if len(items) == 0:
            return func.HttpResponse(body="Not Found Test", status_code=404)
        if len(items) > 1:
            raise ValueError("Not Unique Test")

        body: GetTestRes = items[0]
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
