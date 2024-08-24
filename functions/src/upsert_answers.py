"""
Module of Queue Triggers
"""

import logging

import azure.functions as func

bp_upsert_answers = func.Blueprint()


@bp_upsert_answers.queue_trigger(
    arg_name="msg",
    connection="AzureWebJobsStorage",
    queue_name="answers",
)
def upsert_answers(msg: func.QueueMessage):
    """
    Upsert Answer Items
    """

    logging.info("Queue message received: %s", msg.get_body().decode("utf-8"))
