"""
Module of Blob Triggers
"""

import json
import logging

import azure.functions as func

bp_import_items = func.Blueprint()


@bp_import_items.blob_trigger(
    arg_name="blob",
    connection="AzureWebJobsStorage",
    path="import-items/{courseName}/{testName}.json",
)
def import_items(blob: func.InputStream):
    """
    Import Cosmos DB Items
    """

    course_name = blob.name.split("/")[1]
    test_name = blob.name.split("/")[2].split(".")[0]
    logging.info({"course_name": course_name, "test_name": test_name})

    file = json.loads(blob.read())
    logging.info(file)
