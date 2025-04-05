"""Answerコンテナーの項目をupsertするQueueトリガーの関数アプリのモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Answer, Question
from type.message import MessageAnswer
from util.cosmos import get_read_only_container, get_read_write_container

bp_queue_triggered_answer = func.Blueprint()


@bp_queue_triggered_answer.queue_trigger(
    arg_name="msg",
    connection="AzureWebJobsStorage",
    queue_name="answers",
)
def queue_triggered_answer(msg: func.QueueMessage):
    """
    キューストレージに格納したメッセージからAnswerコンテナーの項目をupsertします
    """

    # メッセージをMessage型として読込み
    message_answer: MessageAnswer = json.loads(msg.get_body().decode("utf-8"))
    logging.info({"message_answer": message_answer})

    # メッセージに該当するQuestionコンテナーの項目を取得
    # 取得できない場合は不正なメッセージとみなし、その場で正常終了する
    container_question: ContainerProxy = get_read_only_container(
        database_name="Users",
        container_name="Question",
    )
    item: Question = container_question.read_item(
        item=f"{message_answer['testId']}_{message_answer['questionNumber']}",
        partition_key=message_answer["testId"],
    )
    logging.info({"item": item})

    # 取得した項目とメッセージとのsubjects/choices/communityVotesが
    # すべて一致する場合のみ、Answerコンテナーの項目をupsertする
    # 上記以外の場合は不正なメッセージとみなし、その場で正常終了する
    if (
        item["subjects"] == message_answer["subjects"]
        and item["choices"] == message_answer["choices"]
        and item["communityVotes"] == message_answer["communityVotes"]
    ):
        container_answer: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Answer",
        )
        answer_item: Answer = {
            "id": f"{message_answer['testId']}_{message_answer['questionNumber']}",
            "questionNumber": message_answer["questionNumber"],
            "correctIdxes": message_answer["correctIdxes"],
            "explanations": message_answer["explanations"],
            "communityVotes": message_answer["communityVotes"],
            "testId": message_answer["testId"],
        }
        logging.info({"answer_item": answer_item})
        container_answer.upsert_item(answer_item)
