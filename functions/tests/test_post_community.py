"""[POST] /tests/{testId}/communities/{questionNumber} のテスト"""

import json
import os
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.post_community import (
    MAX_RETRY_NUMBER,
    SYSTEM_PROMPT,
    calculate_community_votes,
    create_discussion_summary_prompt,
    generate_discussion_summary,
    post_community,
    queue_message_community,
    validate_request,
)
from type.cosmos import Question, QuestionDiscussion


class TestCalculateCommunityVotes(unittest.TestCase):
    """calculate_community_votes関数のテストケース"""

    def test_calculate_community_votes_no_selected_answers(self):
        """selectedAnswerがない場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="Great question!", upvotedNum=5, selectedAnswer=None
            )
        ]
        result = calculate_community_votes(discussions)
        self.assertEqual(result, [])

    def test_calculate_community_votes_single_answer(self):
        """単一の回答の場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="I think A is correct", upvotedNum=5, selectedAnswer="A"
            )
        ]
        result = calculate_community_votes(discussions)
        self.assertEqual(result, ["A (100%)"])

    def test_calculate_community_votes_multiple_answers(self):
        """複数の回答の場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="I think A is correct", upvotedNum=5, selectedAnswer="A"
            ),
            QuestionDiscussion(
                comment="B is the right answer", upvotedNum=3, selectedAnswer="B"
            ),
            QuestionDiscussion(
                comment="A definitely", upvotedNum=2, selectedAnswer="A"
            ),
        ]
        result = calculate_community_votes(discussions)
        # A: 2回 (67%), B: 1回 (33%)
        self.assertEqual(result, ["A (67%)", "B (33%)"])

    def test_calculate_community_votes_equal_distribution(self):
        """等しい分布の場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="A is correct", upvotedNum=5, selectedAnswer="A"
            ),
            QuestionDiscussion(
                comment="B is correct", upvotedNum=3, selectedAnswer="B"
            ),
        ]
        result = calculate_community_votes(discussions)
        # A: 1回 (50%), B: 1回 (50%)
        self.assertEqual(result, ["A (50%)", "B (50%)"])

    def test_calculate_community_votes_sorted_order(self):
        """アルファベット順にソートされることのテスト"""
        discussions = [
            QuestionDiscussion(
                comment="C is correct", upvotedNum=5, selectedAnswer="C"
            ),
            QuestionDiscussion(
                comment="A is correct", upvotedNum=3, selectedAnswer="A"
            ),
            QuestionDiscussion(
                comment="B is correct", upvotedNum=2, selectedAnswer="B"
            ),
        ]
        result = calculate_community_votes(discussions)
        # アルファベット順でソート
        self.assertEqual(result, ["A (33%)", "B (33%)", "C (33%)"])

    def test_calculate_community_votes_mixed_answers(self):
        """選択肢が混在する場合のテスト"""
        discussions = [
            QuestionDiscussion(
                comment="I think A is correct", upvotedNum=5, selectedAnswer="A"
            ),
            QuestionDiscussion(comment="No answer", upvotedNum=3, selectedAnswer=None),
            QuestionDiscussion(comment="B is right", upvotedNum=2, selectedAnswer="B"),
            QuestionDiscussion(comment="A again", upvotedNum=1, selectedAnswer="A"),
        ]
        result = calculate_community_votes(discussions)
        # A: 2回 (67%), B: 1回 (33%) - Noneは除外
        self.assertEqual(result, ["A (67%)", "B (33%)"])


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        result = validate_request(req)

        self.assertIsNone(result)

    def test_validate_request_invalid_test_id(self):
        """testIdが空である場合のテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"questionNumber": "1"}

        result = validate_request(req)

        self.assertEqual(result, "testId is Empty")

    def test_validate_request_question_number_empty(self):
        """questionNumberが空である場合のテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}

        result = validate_request(req)

        self.assertEqual(result, "questionNumber is Empty")

    def test_validate_request_question_number_not_digit(self):
        """questionNumberが数値でない場合のテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "a"}

        result = validate_request(req)

        self.assertEqual(result, "Invalid questionNumber: a")


class TestCreateDiscussionSummaryPrompt(unittest.TestCase):
    """create_discussion_summary_prompt関数のテストケース"""

    def test_create_discussion_summary_prompt_empty_discussions(self):
        """ディスカッションが空の場合のテスト"""

        discussions = []

        result = create_discussion_summary_prompt(discussions)

        self.assertEqual(
            result, "No community discussions available for this question."
        )

    def test_create_discussion_summary_prompt_single_discussion(self):
        """単一のディスカッションの場合のテスト"""

        discussions = [
            {
                "comment": "I think the answer is A because of AWS best practices.",
                "upvotedNum": 5,
                "selectedAnswer": "A",
            }
        ]

        result = create_discussion_summary_prompt(discussions)

        expected_prompt = """Please create a concise summary (approximately 200 characters) \
of the following community discussions about an exam question. Focus on the main points, \
popular opinions (based on upvotes), and the general consensus on answer choices.

Community Discussions:
Discussion 1:
- Comment: I think the answer is A because of AWS best practices.
- Upvotes: 5
- Selected Answer: A

Please provide a summary that captures:
1. The overall sentiment and main discussion points
2. Popular answer choices mentioned by users
3. Key insights or concerns raised by the community

Summary (approximately 200 characters):"""

        self.assertEqual(result, expected_prompt)

    def test_create_discussion_summary_prompt_multiple_discussions(self):
        """複数のディスカッションの場合のテスト"""

        discussions = [
            {
                "comment": "I think the answer is A because of AWS best practices.",
                "upvotedNum": 5,
                "selectedAnswer": "A",
            },
            {
                "comment": "I disagree, B is correct based on the documentation.",
                "upvotedNum": 3,
                "selectedAnswer": "B",
            },
            {
                "comment": "The question is unclear about the requirements.",
                "upvotedNum": 1,
                "selectedAnswer": None,
            },
        ]

        result = create_discussion_summary_prompt(discussions)

        expected_prompt = """Please create a concise summary (approximately 200 characters) \
of the following community discussions about an exam question. Focus on the main points, \
popular opinions (based on upvotes), and the general consensus on answer choices.

Community Discussions:
Discussion 1:
- Comment: I think the answer is A because of AWS best practices.
- Upvotes: 5
- Selected Answer: A

Discussion 2:
- Comment: I disagree, B is correct based on the documentation.
- Upvotes: 3
- Selected Answer: B

Discussion 3:
- Comment: The question is unclear about the requirements.
- Upvotes: 1
- Selected Answer: Not specified

Please provide a summary that captures:
1. The overall sentiment and main discussion points
2. Popular answer choices mentioned by users
3. Key insights or concerns raised by the community

Summary (approximately 200 characters):"""

        self.assertEqual(result, expected_prompt)


class TestGenerateDiscussionSummary(unittest.TestCase):
    """generate_discussion_summary関数のテストケース"""

    @patch("src.post_community.AzureOpenAI")
    @patch("src.post_community.create_discussion_summary_prompt")
    @patch("src.post_community.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_API_VERSION": "test_api_version",
            "OPENAI_DEPLOYMENT_NAME": "test_deployment_name",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL_NAME": "test_model_name",
        },
    )
    def test_generate_discussion_summary_no_retry(
        self,
        mock_logging,
        mock_create_discussion_summary_prompt,
        mock_azure_openai,
    ):
        """リトライせずに、ディスカッション要約を生成するテスト"""

        mock_prompt = "Test prompt for discussion summary"
        mock_create_discussion_summary_prompt.return_value = mock_prompt
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "Community discussion focuses on answers A and B "
            "with A being more popular."
        )
        mock_azure_openai.return_value.chat.completions.create.return_value = (
            mock_response
        )

        discussions = [
            {
                "comment": "I think the answer is A because of AWS best practices.",
                "upvotedNum": 5,
                "selectedAnswer": "A",
            }
        ]

        summary = generate_discussion_summary(discussions)

        self.assertEqual(
            summary,
            "Community discussion focuses on answers A and B "
            "with A being more popular.",
        )
        mock_create_discussion_summary_prompt.assert_called_once_with(discussions)
        mock_azure_openai.assert_called_once_with(
            api_key="test_api_key",
            api_version="test_api_version",
            azure_deployment="test_deployment_name",
            azure_endpoint="test_endpoint",
        )
        mock_azure_openai.return_value.chat.completions.create.assert_called_once_with(
            model="test_model_name",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": mock_prompt,
                },
            ],
        )
        mock_logging.info.assert_has_calls(
            [
                call({"retry_number": 0}),
                call(
                    {
                        "content": "Community discussion focuses on answers A and B "
                        "with A being more popular."
                    }
                ),
            ]
        )
        mock_logging.warning.assert_not_called()

    @patch("src.post_community.AzureOpenAI")
    @patch("src.post_community.create_discussion_summary_prompt")
    @patch("src.post_community.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_API_VERSION": "test_api_version",
            "OPENAI_DEPLOYMENT_NAME": "test_deployment_name",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL_NAME": "test_model_name",
        },
    )
    def test_generate_discussion_summary_max_retry(
        self,
        mock_logging,
        mock_create_discussion_summary_prompt,
        mock_azure_openai,
    ):
        """MAX_RETRY_NUMBER回リトライしても、ディスカッション要約が生成できない場合のテスト"""

        mock_prompt = "Test prompt for discussion summary"
        mock_create_discussion_summary_prompt.return_value = mock_prompt
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_azure_openai.return_value.chat.completions.create.return_value = (
            mock_response
        )

        discussions = [
            {
                "comment": "I think the answer is A because of AWS best practices.",
                "upvotedNum": 5,
                "selectedAnswer": "A",
            }
        ]

        summary = generate_discussion_summary(discussions)

        self.assertIsNone(summary)
        mock_create_discussion_summary_prompt.assert_called_once_with(discussions)
        self.assertEqual(
            mock_azure_openai.return_value.chat.completions.create.call_count,
            MAX_RETRY_NUMBER,
        )
        expected_calls = []
        for i in range(MAX_RETRY_NUMBER):
            expected_calls.extend([call({"retry_number": i}), call({"content": None})])
        mock_logging.info.assert_has_calls(expected_calls)
        mock_logging.warning.assert_not_called()

    @patch("src.post_community.AzureOpenAI")
    @patch("src.post_community.create_discussion_summary_prompt")
    @patch("src.post_community.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_API_VERSION": "test_api_version",
            "OPENAI_DEPLOYMENT_NAME": "test_deployment_name",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL_NAME": "test_model_name",
        },
    )
    def test_generate_discussion_summary_raise_error(
        self,
        mock_logging,
        mock_create_discussion_summary_prompt,
        mock_azure_openai,
    ):
        """Azure OpenAI APIで例外が発生した場合のテスト"""

        mock_prompt = "Test prompt for discussion summary"
        mock_create_discussion_summary_prompt.return_value = mock_prompt
        mock_azure_openai.return_value.chat.completions.create.side_effect = Exception(
            "API Error"
        )

        discussions = [
            {
                "comment": "I think the answer is A because of AWS best practices.",
                "upvotedNum": 5,
                "selectedAnswer": "A",
            }
        ]

        summary = generate_discussion_summary(discussions)

        self.assertIsNone(summary)
        mock_create_discussion_summary_prompt.assert_called_once_with(discussions)
        mock_logging.warning.assert_called_once()


class TestQueueMessageCommunity(unittest.TestCase):
    """queue_message_community関数のテストケース"""

    @patch("src.post_community.get_queue_client")
    @patch("src.post_community.logging")
    def test_queue_message_community_normal(self, mock_logging, mock_get_queue_client):
        """正常にキューメッセージを格納する場合のテスト"""

        mock_queue_client = MagicMock()
        mock_get_queue_client.return_value = mock_queue_client

        message_community = {
            "testId": "test123",
            "questionNumber": 1,
            "discussionsSummary": "Test summary",
            "votes": ["A (60%)", "B (40%)"],
        }

        queue_message_community(message_community)

        mock_get_queue_client.assert_called_once_with("communities")
        mock_queue_client.send_message.assert_called_once()
        mock_logging.info.assert_called_once_with(
            {"message_community": message_community}
        )

    @patch("src.post_community.get_queue_client")
    @patch("src.post_community.logging")
    def test_queue_message_community_development_storage(
        self, mock_logging, mock_get_queue_client
    ):
        """ローカル開発環境（Azurite）でキューメッセージを格納する場合のテスト"""

        mock_queue_client = MagicMock()
        mock_get_queue_client.return_value = mock_queue_client

        message_community = {
            "testId": "test123",
            "questionNumber": 1,
            "discussionsSummary": "Test summary",
            "votes": ["A (60%)", "B (40%)"],
        }

        queue_message_community(message_community)

        mock_get_queue_client.assert_called_once_with("communities")
        mock_queue_client.send_message.assert_called_once()
        mock_logging.info.assert_called_once_with(
            {"message_community": message_community}
        )


class TestPostDiscussion(unittest.TestCase):
    """post_community関数のテストケース"""

    @patch("src.post_community.validate_request")
    @patch("src.post_community.get_read_only_container")
    @patch("src.post_community.generate_discussion_summary")
    @patch("src.post_community.calculate_community_votes")
    @patch("src.post_community.queue_message_community")
    @patch("src.post_community.logging")
    def test_post_community(  # pylint: disable=R0913,R0917
        self,
        mock_logging,
        mock_queue_message_community,
        mock_calculate_community_votes,
        mock_generate_discussion_summary,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """正常にディスカッション要約を生成する場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_item: Question = {
            "id": "1_1",
            "number": 1,
            "subjects": ["What is 2 + 2?"],
            "choices": ["3", "4", "5"],
            "answerNum": 1,
            "testId": "1",
            "discussions": [
                {
                    "comment": "I think the answer is B because 2 + 2 = 4.",
                    "upvotedNum": 10,
                    "selectedAnswer": "B",
                },
                {
                    "comment": "C is also possible.",
                    "upvotedNum": 3,
                    "selectedAnswer": "C",
                },
                {
                    "comment": "B is definitely correct.",
                    "upvotedNum": 2,
                    "selectedAnswer": "B",
                },
            ],
        }
        mock_container.read_item.return_value = mock_item
        mock_generate_discussion_summary.return_value = (
            "Community agrees B is correct with strong consensus."
        )
        mock_calculate_community_votes.return_value = ["B (67%)", "C (33%)"]

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_community(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        expected_body = {
            "discussionsSummary": "Community agrees B is correct with strong consensus.",
            "votes": ["B (67%)", "C (33%)"],
            "isExisted": True,
        }
        actual_body = response.get_body().decode()
        self.assertEqual(json.loads(actual_body), expected_body)

        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(item="1_1", partition_key="1")
        mock_generate_discussion_summary.assert_called_once_with(
            mock_item["discussions"]
        )
        mock_calculate_community_votes.assert_called_once_with(mock_item["discussions"])
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call({"item": mock_item}),
            ]
        )
        mock_queue_message_community.assert_called_once_with(
            {
                "testId": "1",
                "questionNumber": 1,
                "discussionsSummary": "Community agrees B is correct with strong consensus.",
                "votes": ["B (67%)", "C (33%)"],
            }
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_community.validate_request")
    @patch("src.post_community.logging")
    def test_post_community_validation_error(
        self,
        mock_logging,
        mock_validate_request,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_request.return_value = "testId is Empty"

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"questionNumber": "1"}

        response = post_community(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "testId is Empty")

        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.post_community.validate_request")
    @patch("src.post_community.get_read_only_container")
    @patch("src.post_community.logging")
    def test_post_community_not_found_question_error(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """Questionコンテナーの項目が見つからない場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(
            message="Not Found"
        )

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_community(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body().decode(), "Not Found Question")

        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(item="1_1", partition_key="1")
        mock_logging.info.assert_called_once_with(
            {"question_number": "1", "test_id": "1"}
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_community.validate_request")
    @patch("src.post_community.get_read_only_container")
    @patch("src.post_community.logging")
    def test_post_community_no_discussions_success(  # pylint: disable=R0913,R0917
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """discussionsフィールドが存在しない場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_item: Question = {
            "id": "1_1",
            "number": 1,
            "subjects": ["What is 2 + 2?"],
            "choices": ["3", "4", "5"],
            "answerNum": 1,
            "testId": "1",
            "discussions": None,
        }
        mock_container.read_item.return_value = mock_item

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_community(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        expected_body = {
            "isExisted": False,
        }
        actual_body = response.get_body().decode()
        self.assertEqual(json.loads(actual_body), expected_body)

        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(item="1_1", partition_key="1")
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call({"item": mock_item}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_community.validate_request")
    @patch("src.post_community.get_read_only_container")
    @patch("src.post_community.generate_discussion_summary")
    @patch("src.post_community.calculate_community_votes")
    @patch("src.post_community.logging")
    def test_post_community_generate_summary_error(  # pylint: disable=R0913,R0917
        self,
        mock_logging,
        mock_calculate_community_votes,
        mock_generate_discussion_summary,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """ディスカッション要約の生成に失敗した場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_only_container.return_value = mock_container
        mock_item: Question = {
            "id": "1_1",
            "number": 1,
            "subjects": ["What is 2 + 2?"],
            "choices": ["3", "4", "5"],
            "answerNum": 1,
            "testId": "1",
            "discussions": [
                {
                    "comment": "I think the answer is B because 2 + 2 = 4.",
                    "upvotedNum": 10,
                    "selectedAnswer": "B",
                }
            ],
        }
        mock_container.read_item.return_value = mock_item
        mock_generate_discussion_summary.return_value = None
        mock_calculate_community_votes.return_value = ["B (100%)"]

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_community(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")

        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(item="1_1", partition_key="1")
        mock_generate_discussion_summary.assert_called_once_with(
            mock_item["discussions"]
        )
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call({"item": mock_item}),
            ]
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_community.validate_request")
    @patch("src.post_community.get_read_only_container")
    @patch("src.post_community.logging")
    def test_post_community_unexpected_exception(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """予期しない例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        # get_read_only_containerで例外を発生させる
        mock_get_read_only_container.side_effect = Exception(
            "Unexpected database error"
        )

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_community(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")

        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_logging.info.assert_called_once_with(
            {"question_number": "1", "test_id": "1"}
        )
        mock_logging.error.assert_called_once()
