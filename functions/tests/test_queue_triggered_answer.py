"""Answerコンテナーの項目をupsertするQueueトリガーの関数アプリのテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from src.queue_triggered_answer import queue_triggered_answer


class TestQueueTriggeredAnswer(TestCase):
    """Answerコンテナーの項目をupsertするQueueトリガーの関数アプリのテストケース"""

    @patch("src.queue_triggered_answer.get_read_only_container")
    @patch("src.queue_triggered_answer.get_read_write_container")
    @patch("src.queue_triggered_answer.logging")
    def test_queue_triggered_answer_success(
        self, mock_logging, mock_get_read_write_container, mock_get_read_only_container
    ):
        """Answerコンテナーの項目をupsertするテスト"""

        mock_container_question = MagicMock()
        mock_container_answer = MagicMock()
        mock_get_read_only_container.return_value = mock_container_question
        mock_get_read_write_container.return_value = mock_container_answer
        query_items_return_value = [
            {
                "subjects": ["Subject 1"],
                "choices": ["Choice 1", "Choice 2"],
            }
        ]
        mock_container_question.query_items.return_value = query_items_return_value

        message_answer = {
            "testId": "1",
            "questionNumber": 1,
            "subjects": ["Subject 1"],
            "choices": ["Choice 1", "Choice 2"],
            "correctIndexes": [0],
            "explanations": ["Explanation 1"],
        }
        msg = func.QueueMessage(
            body=json.dumps(message_answer).encode("utf-8"),
            id="",
            pop_receipt="",
        )

        queue_triggered_answer(msg)

        expected_answer_item = {
            "id": "1_1",
            "questionNumber": 1,
            "correctIndexes": [0],
            "explanations": ["Explanation 1"],
            "testId": "1",
        }
        mock_container_answer.upsert_item.assert_called_once_with(expected_answer_item)
        mock_logging.info.assert_has_calls(
            [
                call({"message_answer": message_answer}),
                call({"items": query_items_return_value}),
                call({"answer_item": expected_answer_item}),
            ]
        )

    @patch("src.queue_triggered_answer.get_read_only_container")
    @patch("src.queue_triggered_answer.get_read_write_container")
    @patch("src.queue_triggered_answer.logging")
    def test_queue_triggered_answer_invalid_message(
        self, mock_logging, mock_get_read_write_container, mock_get_read_only_container
    ):
        """Answerコンテナーの項目をupsertしないテスト"""

        mock_container_question = MagicMock()
        mock_get_read_only_container.return_value = mock_container_question
        mock_container_question.query_items.return_value = []

        message_answer = {
            "testId": "1",
            "questionNumber": 1,
            "subjects": ["Subject 1"],
            "choices": ["Choice 1", "Choice 2"],
            "correctIndexes": [0],
            "explanations": ["Explanation 1"],
        }
        msg = func.QueueMessage(
            body=json.dumps(message_answer).encode("utf-8"),
            id="",
            pop_receipt="",
        )

        queue_triggered_answer(msg)

        mock_get_read_write_container.assert_not_called()
        mock_logging.info.assert_has_calls(
            [
                call({"message_answer": message_answer}),
                call({"items": []}),
            ]
        )
