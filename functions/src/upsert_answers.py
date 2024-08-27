"""
Module of Queue Triggers
"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Answer, Question
from type.message import MessageAnswer
from util.cosmos import get_read_write_container

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
    logging.info({"message_answer": message_answer})

    # メッセージに該当するUsersテータベースのQuestionコンテナーの項目を取得
    container_question: ContainerProxy = get_read_write_container(
        database_name="Users",
        container_name="Question",
    )
    query = "SELECT c.subjects, c.choices FROM c WHERE c.id = @id"
    parameters = [
        {
            "name": "@id",
            "value": f"{message_answer['testId']}_{message_answer['questionNumber']}",
        },
    ]
    items: list[Question] = list(
        container_question.query_items(query=query, parameters=parameters)
    )
    logging.info({"items": items})

    # 1項目のみ取得し、取得した項目とメッセージとのsubjects/choicesがすべて一致する場合のみ、
    # UsersテータベースのAnswerコンテナーの項目をupsertする
    # 上記以外の場合は不正なメッセージとみなし、その場で正常終了する
    if (
        len(items) == 1
        and items[0]["subjects"] == message_answer["subjects"]
        and items[0]["choices"] == message_answer["choices"]
    ):
        container_answer: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Answer",
        )
        answer_item: Answer = {
            "id": f"{message_answer['testId']}_{message_answer['questionNumber']}",
            "questionNumber": message_answer["questionNumber"],
            "correctIndexes": message_answer["correctIndexes"],
            "explanations": message_answer["explanations"],
            "testId": message_answer["testId"],
        }
        logging.info({"answer_item": answer_item})
        container_answer.upsert_item(answer_item)
