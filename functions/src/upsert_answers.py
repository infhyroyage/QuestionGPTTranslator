"""
Module of Queue Triggers
"""

import json
import logging
from typing import List, TypedDict

import azure.functions as func
from azure.cosmos import ContainerProxy
from util.cosmos import get_read_write_container
from type.cosmos import Answer


class MessageAnswer(TypedDict):
    """
    Message Type for Answer Item
    """

    questionNumber: int
    correctIdxes: List[int]
    explanations: List[str]
    testId: str


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

    # Queueトリガーで受け取ったjson形式のメッセージをMessage型として読込み
    message_answer: MessageAnswer = json.loads(msg.get_body().decode("utf-8"))

    # Initialize Cosmos DB Client
    container: ContainerProxy = get_read_write_container(
        database_name="Users",
        container_name="Test",
    )

    # UsersテータベースのAnswerコンテナーの項目をupsert
    answer_item: Answer = {
        "id": f"{message_answer["testId"]}_{message_answer["questionNumber"]}",
        "questionNumber": message_answer["questionNumber"],
        "correctIdxes": message_answer["correctIdxes"],
        "explanations": message_answer["explanations"],
        "testId": message_answer["testId"],
    }
    logging.info({"answer_item": answer_item})
    container.upsert_item(answer_item)
