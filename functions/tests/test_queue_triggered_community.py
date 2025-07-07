"""Communityコンテナーの項目をupsertするQueueトリガーの関数アプリのテスト"""

import json
import unittest
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.queue_triggered_community import queue_triggered_community
from type.cosmos import Community
from type.message import MessageCommunity


class TestQueueTriggeredCommunity(unittest.TestCase):
    """queue_triggered_community関数のテストケース"""

    @patch("src.queue_triggered_community.get_read_write_container")
    @patch("src.queue_triggered_community.logging")
    def test_queue_triggered_community(
        self,
        mock_logging,
        mock_get_read_write_container,
    ):
        """正常にCommunityコンテナーの項目をupsertする場合のテスト"""

        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container

        message_community: MessageCommunity = {
            "testId": "1",
            "questionNumber": 1,
            "discussionsSummary": "Community discussion focuses on answer B with strong consensus.",
            "votes": ["B (80%)", "C (20%)"],
        }

        msg: func.QueueMessage = MagicMock(spec=func.QueueMessage)
        msg.get_body.return_value = json.dumps(message_community).encode("utf-8")

        queue_triggered_community(msg)

        expected_community_item: Community = {
            "id": "1_1",
            "questionNumber": 1,
            "testId": "1",
            "discussionsSummary": "Community discussion focuses on answer B with strong consensus.",
            "votes": ["B (80%)", "C (20%)"],
        }

        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Community",
        )
        mock_container.upsert_item.assert_called_once_with(expected_community_item)
        mock_logging.info.assert_has_calls(
            [
                unittest.mock.call({"message_community": message_community}),
                unittest.mock.call({"community_item": expected_community_item}),
            ]
        )
