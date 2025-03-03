"""[POST] /tests/{testId}/answers/{questionNumber} のテスト"""

import json
import os
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from src.post_answer import (
    MAX_RETRY_NUMBER,
    SYSTEM_PROMPT,
    create_chat_completions_messages,
    generate_correct_answers,
    get_question_items,
    post_answer,
    queue_message_answer,
    validate_request,
)
from type.cosmos import Question
from type.message import MessageAnswer
from type.structured import AnswerFormat


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


class TestGetQuestionItems(unittest.TestCase):
    """get_question_items関数のテストケース"""

    @patch("src.post_answer.get_read_only_container")
    def test_get_question_items(self, mock_get_read_only_container):
        """Questionコンテナーの項目を取得するテスト"""

        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            Question(
                subjects=["What is 2 + 2?"],
                choices=["3", "4", "5"],
                communityVotes=["BC (70%)", "BD (30%)"],
            )
        ]
        mock_get_read_only_container.return_value = mock_container

        result = get_question_items("1", "1")

        self.assertEqual(
            result,
            [
                Question(
                    subjects=["What is 2 + 2?"],
                    choices=["3", "4", "5"],
                    communityVotes=["BC (70%)", "BD (30%)"],
                )
            ],
        )
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.query_items.assert_called_once_with(
            query=(
                "SELECT c.subjects, c.choices, c.indicateSubjectImgIdxes, "
                "c.indicateChoiceImgs, c.communityVotes "
                "FROM c WHERE c.testId = @testId AND c.number = @number"
            ),
            parameters=[
                {"name": "@testId", "value": "1"},
                {"name": "@number", "value": 1},
            ],
            enable_cross_partition_query=True,
        )


class TestCreateChatCompletionsMessages(unittest.TestCase):
    """create_chat_completions_messages関数のテストケース"""

    # pylint: disable=line-too-long
    USER_CONTENT_TEXT_HEADER = (
        "For a given question and the choices, you must generate sentences that show the correct option/options and explain why each option is correct/incorrect.\n"
        'Unless there is an instruction such as "Select THREE" in the question, there is basically only one correct option.\n'
        "For reference, here are two examples.\n\n"
        "# First example\n"
        "Assume that the following question and choices are given:\n"
        "---\n"
        "A company is launching a new web service on an Amazon Elastic Container Service (Amazon ECS) cluster. The cluster consists of 100 Amazon EC2 instances. Company policy requires the security group on the cluster instances to block all inbound traffic except HTTPS (port 443).\n"
        "Which solution will meet these requirements?\n\n"
        "0. Change the SSH port to 2222 on the cluster instances by using a user data script. Log in to each instance by using SSH over port 2222.\n"
        "1. Change the SSH port to 2222 on the cluster instances by using a user data script. Use AWS Trusted Advisor to remotely manage the cluster instances over port 2222.\n"
        "2. Launch the cluster instances with no SSH key pairs. Use AWS Systems Manager Run Command to remotely manage the cluster instances.\n"
        "3. Launch the cluster instances with no SSH key pairs. Use AWS Trusted Advisor to remotely manage the cluster instances.\n"
        "---\n"
        'For the question and choices in this first example, generate a sentence that shows the correct option, starting with "Correct Option: ", followed by sentences that explain why each option is correct/incorrect, as follows:\n'
        "---\n"
        "Correct Option: 2\n"
        'Option "Change the SSH port to 2222 on the cluster instances by using a user data script. Log in to each instance by using SSH over port 2222." is incorrect because the requirements state that the only inbound port that should be open is 443.\n'
        'Option "Change the SSH port to 2222 on the cluster instances by using a user data script. Use AWS Trusted Advisor to remotely manage the cluster instances over port 2222." is incorrect because the requirements state that the only inbound port that should be open is 443.\n'
        'Option "Launch the cluster instances with no SSH key pairs. Use AWS Systems Manager Run Command to remotely manage the cluster instances." is correct because AWS Systems Manager Run Command requires no inbound ports to be open. Run Command operates entirely over outbound HTTPS, which is open by default for security groups.\n'
        'Option "Launch the cluster instances with no SSH key pairs. Use AWS Trusted Advisor to remotely manage the cluster instances." is incorrect because AWS Trusted Advisor does not perform this management function.\n'
        "---\n\n"
        "# Second Example\n"
        "Assume that the following question and choices are given:\n"
        "---\n"
        "A company has deployed a multi-tier web application in the AWS Cloud. The application consists of the following tiers:\n"
        "* A Windows-based web tier that is hosted on Amazon EC2 instances with Elastic IP addresses\n"
        "* A Linux-based application tier that is hosted on EC2 instances that run behind an Application Load Balancer (ALB) that uses path-based routing\n"
        "* A MySQL database that runs on a Linux EC2 instance\n"
        "All the EC2 instances are using Intel-based x86 CPUs. A solutions architect needs to modernize the infrastructure to achieve better performance. The solution must minimize the operational overhead of the application.\n"
        "Which combination of actions should the solutions architect take to meet these requirements? (Select TWO.)\n\n"
        "0. Run the MySQL database on multiple EC2 instances.\n"
        "1. Place the web tier instances behind an ALB.\n"
        "2. Migrate the MySQL database to Amazon Aurora Serxverless.\n"
        "3. Migrate all EC2 instance types to Graviton2.\n"
        "4. Replace the ALB for the application tier instances with a company-managed load balancer.\n"
        "---\n"
        'For the question and choices in this second example, generate a sentence that shows the correct options, starting with "Correct Options: ", followed by sentences that explain why each option is correct/incorrect, as follows:\n'
        "---\n"
        "Correct Options: 1, 2\n"
        'Option "Run the MySQL database on multiple EC2 instances." is incorrect because additional EC2 instances will not minimize operational overhead. A managed service would be a better option.\n'
        'Option "Place the web tier instances behind an ALB." is correct because you can improve availability and scalability of the web tier by placing the web tier behind an Application Load Balancer (ALB). The ALB serves as the single point of contact for clients and distributes incoming application traffic to the Amazon EC2 instances.\n'
        'Option "Migrate the MySQL database to Amazon Aurora Serxverless." is correct because Amazon Aurora Serverless provides high performance and high availability with reduced operational complexity.\n'
        'Option "Migrate all EC2 instance types to Graviton2." is incorrect because the application includes Windows instances, which are not available for Graviton2.\n'
        'Option "Replace the ALB for the application tier instances with a company-managed load balancer." is incorrect because a company-managed load balancer will not minimize operational overhead.\n'
        "---\n\n"
        "# Main Topic\n"
        "For the question and choices below, generate sentences that show the correct option/options and explain why each option is correct/incorrect.\n"
        'Unless there is an instruction such as "Select THREE" in the question, there will generally only be one correct option.\n'
        "---\n"
    )
    USER_CONTENT_TEXT_FOOTER = "---"

    def test_create_chat_completions_messages_no_images(self):
        """すべての問題文・選択肢に画像URLが含まれない場合のテスト"""

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]
        indicate_subject_img_idxes = None
        indicate_choice_imgs = None
        messages = create_chat_completions_messages(
            subjects, choices, indicate_subject_img_idxes, indicate_choice_imgs
        )

        self.assertEqual(
            messages,
            [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                self.USER_CONTENT_TEXT_HEADER
                                + "What is 2 + 2?\n\n"
                                + "0. 3\n"
                                + "1. 4\n"
                                + "2. 5\n"
                                + self.USER_CONTENT_TEXT_FOOTER
                            ),
                        }
                    ],
                },
            ],
        )

    def test_create_chat_completions_messages_subject_images(self):
        """問題文に画像URLが含まれる場合のテスト"""

        subjects = [
            "What is 2 + 2?",
            "https://example.com/image1.jpg",
        ]
        choices = ["3", "4", "5"]
        indicate_subject_img_idxes = [1]
        indicate_choice_imgs = None
        messages = create_chat_completions_messages(
            subjects, choices, indicate_subject_img_idxes, indicate_choice_imgs
        )

        self.assertEqual(
            messages,
            [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                self.USER_CONTENT_TEXT_HEADER + "What is 2 + 2?\n"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.com/image1.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "0. 3\n"
                            + "1. 4\n"
                            + "2. 5\n"
                            + self.USER_CONTENT_TEXT_FOOTER,
                        },
                    ],
                },
            ],
        )

    def test_create_chat_completions_messages_choice_images(self):
        """選択肢に画像URLが含まれる場合のテスト"""

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]
        indicate_subject_img_idxes = None
        indicate_choice_imgs = [
            "https://example.com/image1.jpg",
            None,
            "https://example.com/image3.jpg",
        ]
        messages = create_chat_completions_messages(
            subjects, choices, indicate_subject_img_idxes, indicate_choice_imgs
        )

        self.assertEqual(
            messages,
            [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                self.USER_CONTENT_TEXT_HEADER
                                + "What is 2 + 2?\n\n"
                                + "0. 3\n"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.com/image1.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "1. 4\n" + "2. 5\n",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.com/image3.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": self.USER_CONTENT_TEXT_FOOTER,
                        },
                    ],
                },
            ],
        )


class TestGenerateCorrectAnswers(unittest.TestCase):
    """generate_correct_answers関数のテストケース"""

    @patch("src.post_answer.AzureOpenAI")
    @patch("src.post_answer.create_chat_completions_messages")
    @patch("src.post_answer.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_API_VERSION": "test_api_version",
            "OPENAI_DEPLOYMENT": "test_deployment",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL": "test_model",
        },
    )
    def test_generate_correct_answers_no_retry(
        self,
        mock_logging,
        mock_create_chat_completions_messages,
        mock_azure_openai,
    ):
        """リトライせずに、正解の選択肢のインデックス・正解/不正解の理由を生成するテスト"""

        mock_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "user_content",
                    }
                ],
            },
        ]
        mock_create_chat_completions_messages.return_value = mock_messages
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.correct_indexes = [2]
        mock_response.choices[0].message.parsed.explanations = [
            "Option 2 is correct because 2 + 2 equals 4."
        ]
        mock_azure_openai.return_value.beta.chat.completions.parse.return_value = (
            mock_response
        )

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]

        correct_answers = generate_correct_answers(subjects, choices, None, None)

        self.assertEqual(correct_answers["correct_indexes"], [2])
        self.assertEqual(
            correct_answers["explanations"],
            ["Option 2 is correct because 2 + 2 equals 4."],
        )
        mock_create_chat_completions_messages.assert_called_once_with(
            subjects, choices, None, None
        )
        mock_azure_openai.assert_called_once_with(
            api_key="test_api_key",
            api_version="test_api_version",
            azure_deployment="test_deployment",
            azure_endpoint="test_endpoint",
        )
        mock_azure_openai.return_value.beta.chat.completions.parse.assert_called_once_with(
            model="test_model",
            messages=mock_messages,
            response_format=AnswerFormat,
        )
        mock_logging.info.assert_has_calls(
            [
                call({"retry_number": 0}),
                call({"parsed": mock_response.choices[0].message.parsed}),
            ]
        )
        mock_logging.warning.assert_not_called()

    @patch("src.post_answer.AzureOpenAI")
    @patch("src.post_answer.create_chat_completions_messages")
    @patch("src.post_answer.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_API_VERSION": "test_api_version",
            "OPENAI_DEPLOYMENT": "test_deployment",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL": "test_model",
        },
    )
    def test_generate_correct_answers_max_retry(
        self,
        mock_logging,
        mock_create_chat_completions_messages,
        mock_azure_openai,
    ):
        """MAX_RETRY_NUMBER回リトライしても、正解の選択肢のインデックス・正解/不正解の理由が生成できない場合のテスト"""

        mock_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "user_content",
                    }
                ],
            },
        ]
        mock_create_chat_completions_messages.return_value = mock_messages
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed = None
        mock_azure_openai.return_value.beta.chat.completions.parse.return_value = (
            mock_response
        )

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]

        correct_answers = generate_correct_answers(subjects, choices, None, None)

        self.assertIsNone(correct_answers)
        mock_create_chat_completions_messages.assert_called_once_with(
            subjects, choices, None, None
        )
        mock_logging.info.assert_has_calls(
            [
                call({"retry_number": i / 2}) if i % 2 == 0 else call({"parsed": None})
                for i in range(MAX_RETRY_NUMBER * 2)
            ]
        )
        mock_logging.warning.assert_not_called()

    @patch("src.post_answer.AzureOpenAI")
    @patch("src.post_answer.create_chat_completions_messages")
    @patch("src.post_answer.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_API_VERSION": "test_api_version",
            "OPENAI_DEPLOYMENT": "test_deployment",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL": "test_model",
        },
    )
    def test_generate_correct_answers_raise_error(
        self,
        mock_logging,
        mock_create_chat_completions_messages,
        mock_azure_openai,
    ):
        """正解の選択肢のインデックス・正解/不正解の理由の生成でエラーが発生した場合のテスト"""

        mock_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "user_content",
                    }
                ],
            },
        ]
        mock_create_chat_completions_messages.return_value = mock_messages
        mock_azure_openai.return_value.beta.chat.completions.parse.side_effect = [
            Exception("Azure OpenAI Error"),
        ]

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]

        correct_answers = generate_correct_answers(subjects, choices, None, None)

        self.assertIsNone(correct_answers)
        mock_create_chat_completions_messages.assert_called_once_with(
            subjects, choices, None, None
        )
        mock_logging.info.assert_called_once_with({"retry_number": 0})
        mock_logging.warning.assert_called_once()


class TestQueueMessageAnswer(unittest.TestCase):
    """queue_message_answer関数のテストケース"""

    @patch("src.post_answer.QueueClient.from_connection_string")
    @patch("src.post_answer.logging")
    @patch.dict(os.environ, {"AzureWebJobsStorage": "on-azure"})
    def test_queue_message_answer_azure(self, mock_logging, mock_queue_client):
        """Azureにて、キューストレージにAnswerコンテナーの項目用のメッセージを格納するテスト"""

        mock_queue = MagicMock()
        mock_queue_client.return_value = mock_queue

        message_answer = MessageAnswer(
            testId="1",
            questionNumber=1,
            subjects=["What is 2 + 2?"],
            choices=["3", "4", "5"],
            correctIdxes=[1],
            explanations=["Option 2 is correct because 2 + 2 equals 4."],
        )

        queue_message_answer(message_answer)

        mock_queue.send_message.assert_called_once_with(
            json.dumps(message_answer).encode("utf-8")
        )
        mock_logging.info.assert_called_once_with({"message_answer": message_answer})

    @patch("src.post_answer.QueueClient.from_connection_string")
    @patch("src.post_answer.logging")
    @patch.dict(os.environ, {"AzureWebJobsStorage": "UseDevelopmentStorage=true"})
    def test_queue_message_answer_local(self, mock_logging, mock_queue_client):
        """ローカル環境にて、キューストレージにAnswerコンテナーの項目用のメッセージを格納するテスト"""

        mock_queue = MagicMock()
        mock_queue_client.return_value = mock_queue

        message_answer = MessageAnswer(
            testId="1",
            questionNumber=1,
            subjects=["What is 2 + 2?"],
            choices=["3", "4", "5"],
            correctIdxes=[1],
            explanations=["Option 2 is correct because 2 + 2 equals 4."],
        )

        queue_message_answer(message_answer)

        mock_queue.send_message.assert_called_once_with(
            json.dumps(message_answer).encode("utf-8")
        )
        mock_logging.info.assert_called_once_with({"message_answer": message_answer})


class TestPostAnswer(unittest.TestCase):
    """post_answer関数のテストケース"""

    @patch("src.post_answer.validate_request")
    @patch("src.post_answer.get_question_items")
    @patch("src.post_answer.generate_correct_answers")
    @patch("src.post_answer.queue_message_answer")
    @patch("src.post_answer.logging")
    def test_post_answer(  # pylint: disable=too-many-arguments
        self,
        mock_logging,
        mock_queue_message_answer,
        mock_generate_correct_answers,
        mock_get_question_items,
        mock_validate_request,
    ):
        """レスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_get_question_items.return_value = [
            Question(
                subjects=["What is 2 + 2?"],
                choices=["3", "4", "5"],
                communityVotes=["BC (70%)", "BD (30%)"],
            )
        ]
        mock_generate_correct_answers.return_value = {
            "correct_indexes": [1],
            "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
        }

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_answer(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.get_body()),
            {
                "correctIdxes": [1],
                "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
                "communityVotes": ["BC (70%)", "BD (30%)"],
            },
        )
        mock_validate_request.assert_called_once_with(req)
        mock_get_question_items.assert_called_once_with("1", "1")
        mock_generate_correct_answers.assert_called_once_with(
            ["What is 2 + 2?"], ["3", "4", "5"], None, None
        )
        mock_queue_message_answer.assert_called_once_with(
            {
                "testId": "1",
                "questionNumber": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
                "correctIdxes": [1],
                "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
                "communityVotes": ["BC (70%)", "BD (30%)"],
            }
        )
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call(
                    {
                        "items": [
                            {
                                "subjects": ["What is 2 + 2?"],
                                "choices": ["3", "4", "5"],
                                "communityVotes": ["BC (70%)", "BD (30%)"],
                            }
                        ]
                    }
                ),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_answer.validate_request")
    @patch("src.post_answer.logging")
    def test_post_answer_validation_error(
        self,
        mock_logging,
        mock_validate_request,
    ):
        """バリデーションチェックに失敗した場合のテスト"""

        mock_validate_request.return_value = "Validation Error"

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_answer(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "Validation Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.post_answer.validate_request")
    @patch("src.post_answer.get_question_items")
    @patch("src.post_answer.logging")
    def test_post_answer_not_found_question_error(
        self,
        mock_logging,
        mock_get_question_items,
        mock_validate_request,
    ):
        """Questionコンテナーの項目が見つからない場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_question_items.return_value = []

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_answer(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body(), b"Not Found Question")
        mock_validate_request.assert_called_once_with(req)
        mock_get_question_items.assert_called_once_with("1", "1")
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call({"items": []}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_answer.validate_request")
    @patch("src.post_answer.get_question_items")
    @patch("src.post_answer.logging")
    def test_post_answer_not_unique_question_error(
        self,
        mock_logging,
        mock_get_question_items,
        mock_validate_request,
    ):
        """Questionコンテナーの項目が見つからない場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_question_items.return_value = [
            Question(
                subjects=["What is 2 + 2?"],
                choices=["3", "4", "5"],
            ),
            Question(
                subjects=["What is 2 + 2?"],
                choices=["3", "4", "5"],
            ),
        ]

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body(), b"Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_get_question_items.assert_called_once_with("1", "1")
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call(
                    {
                        "items": [
                            {
                                "subjects": ["What is 2 + 2?"],
                                "choices": ["3", "4", "5"],
                            },
                            {
                                "subjects": ["What is 2 + 2?"],
                                "choices": ["3", "4", "5"],
                            },
                        ]
                    }
                ),
            ]
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.validate_request")
    @patch("src.post_answer.get_question_items")
    @patch("src.post_answer.generate_correct_answers")
    @patch("src.post_answer.logging")
    def test_post_answer_generate_correct_answers_error(
        self,
        mock_logging,
        mock_generate_correct_answers,
        mock_get_question_items,
        mock_validate_request,
    ):
        """正解の選択肢・正解/不正解の理由を生成できない場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_question_items.return_value = [
            Question(
                subjects=["What is 2 + 2?"],
                choices=["3", "4", "5"],
            )
        ]
        mock_generate_correct_answers.return_value = None

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body(), b"Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_get_question_items.assert_called_once_with("1", "1")
        mock_generate_correct_answers.assert_called_once_with(
            ["What is 2 + 2?"], ["3", "4", "5"], None, None
        )
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call(
                    {
                        "items": [
                            {"subjects": ["What is 2 + 2?"], "choices": ["3", "4", "5"]}
                        ]
                    }
                ),
            ]
        )
        mock_logging.error.assert_called_once()
