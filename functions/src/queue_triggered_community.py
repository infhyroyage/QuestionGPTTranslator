"""Communityコンテナーの項目をupsertするQueueトリガーの関数アプリのモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Community
from type.message import MessageCommunity
from util.cosmos import get_read_write_container

bp_queue_triggered_community = func.Blueprint()


@bp_queue_triggered_community.queue_trigger(
    arg_name="msg",
    connection="AzureWebJobsStorage",
    queue_name="communities",
)
def queue_triggered_community(msg: func.QueueMessage):
    """
    キューストレージに格納したメッセージからCommunityコンテナーの項目をupsertします
    """

    # メッセージをMessageCommunity型として読込み
    message_community: MessageCommunity = json.loads(msg.get_body().decode("utf-8"))
    logging.info({"message_community": message_community})

    # Communityコンテナーの項目をupsert
    container_community: ContainerProxy = get_read_write_container(
        database_name="Users",
        container_name="Community",
    )
    community_item: Community = {
        "id": f"{message_community['testId']}_{message_community['questionNumber']}",
        "questionNumber": message_community["questionNumber"],
        "testId": message_community["testId"],
        "discussionsSummary": message_community["discussionsSummary"],
        "votes": message_community["votes"],
    }
    logging.info({"community_item": community_item})
    container_community.upsert_item(community_item)
