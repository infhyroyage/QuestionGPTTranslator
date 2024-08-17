"""
Module of Blob Triggers
"""

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

    logging.info("Python blob trigger function processed blob: %s", blob.name)

    file = blob.read()
    logging.info(file)
