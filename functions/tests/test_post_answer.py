"""[POST] /tests/{testId}/answers/{questionNumber} のテスト"""

import json
import os
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.post_answer import (
    MAX_RETRY_NUMBER,
    SYSTEM_PROMPT,
    create_chat_completions_messages,
    generate_correct_answers,
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


class TestCreateChatCompletionsMessages(unittest.TestCase):
    """create_chat_completions_messages関数のテストケース"""

    # pylint: disable=line-too-long
    USER_CONTENT_TEXT_HEADER = (
        "For a given question and the choices, you must generate exactly {answer_num} correct option(s) followed by sentences explaining why each option is correct/incorrect.\n"
        "You should select exactly {answer_num} option(s) as correct, regardless of any instructions in the question.\n"
        "For reference, here are two examples.\n\n"
        "# First example\n"
        "Assume that the following question and choices are given:\n"
        "---\n"
        "A company is launching a new web service on an Amazon Elastic Container Service (Amazon ECS) cluster. The cluster consists of 100 Amazon EC2 instances. Company policy requires the security group on the cluster instances to block all inbound traffic except HTTPS (port 443).\n"
        "Which solution will meet these requirements?\n\n"
        "A. Change the SSH port to 2222 on the cluster instances by using a user data script. Log in to each instance by using SSH over port 2222.\n"
        "B. Change the SSH port to 2222 on the cluster instances by using a user data script. Use AWS Trusted Advisor to remotely manage the cluster instances over port 2222.\n"
        "C. Launch the cluster instances with no SSH key pairs. Use AWS Systems Manager Run Command to remotely manage the cluster instances.\n"
        "D. Launch the cluster instances with no SSH key pairs. Use AWS Trusted Advisor to remotely manage the cluster instances.\n"
        "---\n"
        "For the question and choices in this first example, generate the JSON format with `correct_indexes` and `explanations`.\n"
        "`correct_indexes` shows an array of indexes of correct options and `explanations` shows an array of explanations of why each option is correct/incorrect.\n"
        "Since there is only one correct answer required for this example, the number of `correct_indexes` is only one, as follows:\n"
        "---\n"
        "{{\n"
        '    "correct_indexes": [2],\n'
        '    "explanations": [\n'
        '        "Option A is incorrect because the requirements state that the only inbound port that should be open is 443.",\n'
        '        "Option B is incorrect because the requirements state that the only inbound port that should be open is 443.",\n'
        '        "Option C is correct because AWS Systems Manager Run Command requires no inbound ports to be open. Run Command operates entirely over outbound HTTPS, which is open by default for security groups.",\n'
        '        "Option D is incorrect because AWS Trusted Advisor does not perform this management function."\n'
        "    ]\n"
        "}}\n"
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
        "A. Run the MySQL database on multiple EC2 instances.\n"
        "B. Place the web tier instances behind an ALB.\n"
        "C. Migrate the MySQL database to Amazon Aurora Serxverless.\n"
        "D. Migrate all EC2 instance types to Graviton2.\n"
        "E. Replace the ALB for the application tier instances with a company-managed load balancer.\n"
        "---\n"
        "For the question and choices in this second example, generate the JSON format with `correct_indexes` and `explanations`.\n"
        "`correct_indexes` shows an array of indexes of correct options and `explanations` shows an array of explanations of why each option is correct/incorrect.\n"
        "For this example, since two correct answers are required, the number of `correct_indexes` is two, as follows:\n"
        "---\n"
        "{{\n"
        '    "correct_indexes": [1, 2],\n'
        '    "explanations": [\n'
        '        "Option A is incorrect because additional EC2 instances will not minimize operational overhead. A managed service would be a better option.",\n'
        '        "Option B is correct because you can improve availability and scalability of the web tier by placing the web tier behind an Application Load Balancer (ALB). The ALB serves as the single point of contact for clients and distributes incoming application traffic to the Amazon EC2 instances.",\n'
        '        "Option C is correct because Amazon Aurora Serverless provides high performance and high availability with reduced operational complexity.",\n'
        '        "Option D is incorrect because the application includes Windows instances, which are not available for Graviton2.",\n'
        '        "Option E is incorrect because a company-managed load balancer will not minimize operational overhead."\n'
        "    ]\n"
        "}}\n"
        "---\n\n"
        "# Main Topic\n"
        "For the question and choices below, generate the JSON format with `correct_indexes` and `explanations`.\n"
        "Remember to select exactly {answer_num} correct option(s) in your response.\n"
        "---\n"
    )
    USER_CONTENT_TEXT_FOOTER = "---"

    def test_create_chat_completions_messages_no_images(self):
        """問題文・選択肢に画像URLが含まれない場合のテスト"""

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]
        answer_num = 1
        indicate_subject_img_idxes = None
        indicate_choice_imgs = None
        messages = create_chat_completions_messages(
            subjects,
            choices,
            answer_num,
            indicate_subject_img_idxes,
            indicate_choice_imgs,
        )

        self.assertEqual(
            messages,
            [
                {
                    "role": "developer",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                self.USER_CONTENT_TEXT_HEADER.format(
                                    answer_num=answer_num
                                )
                                + "What is 2 + 2?\n\n"
                                + "A. 3\n"
                                + "B. 4\n"
                                + "C. 5\n"
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
        answer_num = 1
        indicate_subject_img_idxes = [1]
        indicate_choice_imgs = None
        messages = create_chat_completions_messages(
            subjects,
            choices,
            answer_num,
            indicate_subject_img_idxes,
            indicate_choice_imgs,
        )

        self.assertEqual(
            messages,
            [
                {
                    "role": "developer",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                self.USER_CONTENT_TEXT_HEADER.format(
                                    answer_num=answer_num
                                )
                                + "What is 2 + 2?\n"
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
                            "text": "A. 3\n"
                            + "B. 4\n"
                            + "C. 5\n"
                            + self.USER_CONTENT_TEXT_FOOTER,
                        },
                    ],
                },
            ],
        )

    def test_create_chat_completions_messages_choice_sentences_and_images(self):
        """選択肢の文章の後に画像URLが続く場合のテスト"""

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]
        answer_num = 1
        indicate_subject_img_idxes = None
        indicate_choice_imgs = [
            "https://example.com/image1.jpg",
            None,
            "https://example.com/image3.jpg",
        ]
        messages = create_chat_completions_messages(
            subjects,
            choices,
            answer_num,
            indicate_subject_img_idxes,
            indicate_choice_imgs,
        )

        self.assertEqual(
            messages,
            [
                {
                    "role": "developer",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                self.USER_CONTENT_TEXT_HEADER.format(
                                    answer_num=answer_num
                                )
                                + "What is 2 + 2?\n\n"
                                + "A. 3\n"
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
                            "text": "B. 4\n" + "C. 5\n",
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

    def test_create_chat_completions_messages_choice_images(self):
        """選択肢が画像URLのみの場合のテスト"""

        subjects = ["What is 2 + 2?"]
        choices = [None, None, None]
        answer_num = 1
        indicate_subject_img_idxes = None
        indicate_choice_imgs = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg",
        ]
        messages = create_chat_completions_messages(
            subjects,
            choices,
            answer_num,
            indicate_subject_img_idxes,
            indicate_choice_imgs,
        )

        self.assertEqual(
            messages,
            [
                {
                    "role": "developer",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                self.USER_CONTENT_TEXT_HEADER.format(
                                    answer_num=answer_num
                                )
                                + "What is 2 + 2?\n\n"
                                + "A. \n"
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
                            "text": "B. \n",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.com/image2.jpg",
                            },
                        },
                        {
                            "type": "text",
                            "text": "C. \n",
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
            "OPENAI_DEPLOYMENT_NAME": "test_deployment_name",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL_NAME": "test_model_name",
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
            {"role": "developer", "content": SYSTEM_PROMPT},
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

        correct_answers = generate_correct_answers(subjects, choices, 1, None, None)

        self.assertEqual(correct_answers["correct_indexes"], [2])
        self.assertEqual(
            correct_answers["explanations"],
            ["Option 2 is correct because 2 + 2 equals 4."],
        )
        mock_create_chat_completions_messages.assert_called_once_with(
            subjects, choices, 1, None, None
        )
        mock_azure_openai.assert_called_once_with(
            api_key="test_api_key",
            api_version="test_api_version",
            azure_deployment="test_deployment_name",
            azure_endpoint="test_endpoint",
        )
        mock_azure_openai.return_value.beta.chat.completions.parse.assert_called_once_with(
            model="test_model_name",
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
            "OPENAI_DEPLOYMENT_NAME": "test_deployment_name",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL_NAME": "test_model_name",
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
            {"role": "developer", "content": SYSTEM_PROMPT},
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

        correct_answers = generate_correct_answers(subjects, choices, 1, None, None)

        self.assertIsNone(correct_answers)
        mock_create_chat_completions_messages.assert_called_once_with(
            subjects, choices, 1, None, None
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
            "OPENAI_DEPLOYMENT_NAME": "test_deployment_name",
            "OPENAI_ENDPOINT": "test_endpoint",
            "OPENAI_MODEL_NAME": "test_model_name",
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
            {"role": "developer", "content": SYSTEM_PROMPT},
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

        correct_answers = generate_correct_answers(subjects, choices, 1, None, None)

        self.assertIsNone(correct_answers)
        mock_create_chat_completions_messages.assert_called_once_with(
            subjects, choices, 1, None, None
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
            answerNum=1,
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
            answerNum=1,
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
    @patch("src.post_answer.get_read_only_container")
    @patch("src.post_answer.generate_correct_answers")
    @patch("src.post_answer.queue_message_answer")
    @patch("src.post_answer.logging")
    def test_post_answer(  # pylint: disable=R0913,R0917
        self,
        mock_logging,
        mock_queue_message_answer,
        mock_generate_correct_answers,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """レスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_item = Question(
            subjects=["What is 2 + 2?"],
            choices=["3", "4", "5"],
            discussions=[
                {
                    "comment": "I think B is correct",
                    "upvotedNum": 5,
                    "selectedAnswer": "B",
                },
                {"comment": "C is right", "upvotedNum": 3, "selectedAnswer": "C"},
                {"comment": "B definitely", "upvotedNum": 2, "selectedAnswer": "B"},
            ],
            answerNum=1,
        )
        mock_container.read_item.return_value = mock_item
        mock_get_read_only_container.return_value = mock_container
        mock_generate_correct_answers.return_value = {
            "correct_indexes": [1],
            "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
        }

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response: func.HttpResponse = post_answer(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.get_body()),
            {
                "correctIdxes": [1],
                "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
            },
        )
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_generate_correct_answers.assert_called_once_with(
            ["What is 2 + 2?"],
            ["3", "4", "5"],
            1,
            None,
            None,
        )
        mock_queue_message_answer.assert_called_once_with(
            MessageAnswer(
                testId="1",
                questionNumber=1,
                subjects=["What is 2 + 2?"],
                choices=["3", "4", "5"],
                answerNum=1,
                correctIdxes=[1],
                explanations=["Option 2 is correct because 2 + 2 equals 4."],
            )
        )
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call({"item": mock_item}),
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
    @patch("src.post_answer.get_read_only_container")
    @patch("src.post_answer.logging")
    def test_post_answer_not_found_question_error(
        self,
        mock_logging,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """Questionコンテナーの項目が見つからない場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_container.read_item.side_effect = CosmosResourceNotFoundError
        mock_get_read_only_container.return_value = mock_container

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_answer(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body(), b"Not Found Question")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_logging.info.assert_called_once()
        mock_logging.error.assert_not_called()

    @patch("src.post_answer.validate_request")
    @patch("src.post_answer.get_read_only_container")
    @patch("src.post_answer.generate_correct_answers")
    @patch("src.post_answer.logging")
    def test_post_answer_generate_correct_answers_error(
        self,
        mock_logging,
        mock_generate_correct_answers,
        mock_get_read_only_container,
        mock_validate_request,
    ):
        """正解の選択肢・正解/不正解の理由を生成できない場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_item = Question(
            subjects=["What is 2 + 2?"],
            choices=["3", "4", "5"],
            discussions=[],
            answerNum=1,
        )
        mock_container.read_item.return_value = mock_item
        mock_get_read_only_container.return_value = mock_container
        mock_generate_correct_answers.return_value = None

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body(), b"Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_generate_correct_answers.assert_called_once_with(
            ["What is 2 + 2?"],
            ["3", "4", "5"],
            1,
            None,
            None,
        )
        mock_logging.info.assert_has_calls(
            [
                call({"question_number": "1", "test_id": "1"}),
                call({"item": mock_item}),
            ]
        )
        mock_logging.error.assert_called_once()
