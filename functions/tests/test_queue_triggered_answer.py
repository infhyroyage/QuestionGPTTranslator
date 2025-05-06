"""Answerコンテナーの項目をupsertするQueueトリガーの関数アプリのテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from src.queue_triggered_answer import queue_triggered_answer


class TestQueueTriggeredAnswer(TestCase):
    """queue_triggered_answer関数のテストケース"""

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
        mock_item = {
            "subjects": ["Subject 1"],
            "choices": ["Choice 1", "Choice 2"],
            "answerNum": 1,
            "communityVotes": ["BC (70%)", "BD (30%)"],
        }
        mock_container_question.read_item.return_value = mock_item

        message_answer = {
            "testId": "1",
            "questionNumber": 1,
            "subjects": ["Subject 1"],
            "choices": ["Choice 1", "Choice 2"],
            "answerNum": 1,
            "correctIdxes": [0],
            "explanations": ["Explanation 1"],
            "communityVotes": ["BC (70%)", "BD (30%)"],
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
            "correctIdxes": [0],
            "explanations": ["Explanation 1"],
            "communityVotes": ["BC (70%)", "BD (30%)"],
            "testId": "1",
        }
        mock_container_answer.upsert_item.assert_called_once_with(expected_answer_item)
        mock_logging.info.assert_has_calls(
            [
                call({"message_answer": message_answer}),
                call({"item": mock_item}),
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
        mock_container_question.read_item.return_value = {
            "subjects": ["Different Subject"],
            "choices": ["Different Choice 1", "Different Choice 2"],
            "answerNum": 1,
            "communityVotes": ["XX (100%)"],
        }

        message_answer = {
            "testId": "1",
            "questionNumber": 1,
            "subjects": ["Subject 1"],
            "choices": ["Choice 1", "Choice 2"],
            "answerNum": 1,
            "correctIdxes": [0],
            "explanations": ["Explanation 1"],
            "communityVotes": ["BC (70%)", "BD (30%)"],
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
                call({"item": mock_container_question.read_item.return_value}),
            ]
        )
