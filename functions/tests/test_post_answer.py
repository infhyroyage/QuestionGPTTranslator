"""[POST] /answer のテスト"""

import json
import os
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from src.post_answer import (
    MAX_RETRY_NUMBER,
    create_system_prompt,
    create_user_prompt,
    generate_correct_answers,
    post_answer,
    queue_message_answer,
)
from type.message import MessageAnswer
from type.structured import AnswerFormat


class TestPostAnswer(unittest.TestCase):
    """[POST] /answer のテストケース"""

    def test_create_system_prompt(self):
        """Azure OpenAIのシステムプロンプトのテスト"""

        course_name = "Math"
        # pylint: disable=line-too-long
        expected_prompt = 'You are a professional who provides correct explanations for candidates of the exam named "Math".'

        self.assertEqual(create_system_prompt(course_name), expected_prompt)

    def test_create_user_prompt(self):
        """Azure OpenAIのユーザープロンプトのテスト"""

        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]
        # pylint: disable=line-too-long
        expected_prompt = (
            "For a given question and the choices, you must generate sentences that show the correct option/options and explain why each option is correct/incorrect.\n"
            'Unless there is an instruction such as "Select THREE" in the question, there is basically only one correct option.\n'
            "For reference, here are two examples.\n\n"
            "# First example\n"
            "Assume that the following question and choices are given:\n"
            "---\n"
            "A company is launching a new web service on an Amazon Elastic Container Service (Amazon ECS) cluster. The cluster consists of 100 Amazon EC2 instances. Company policy requires the security group on the cluster instances to block all inbound traffic except HTTPS (port 443).\n"
            "Which solution will meet these requirements?\n\n"
            "1. Change the SSH port to 2222 on the cluster instances by using a user data script. Log in to each instance by using SSH over port 2222.\n"
            "2. Change the SSH port to 2222 on the cluster instances by using a user data script. Use AWS Trusted Advisor to remotely manage the cluster instances over port 2222.\n"
            "3. Launch the cluster instances with no SSH key pairs. Use AWS Systems Manager Run Command to remotely manage the cluster instances.\n"
            "4. Launch the cluster instances with no SSH key pairs. Use AWS Trusted Advisor to remotely manage the cluster instances.\n"
            "---\n"
            'For the question and choices in this first example, generate a sentence that shows the correct option, starting with "Correct Option: ", followed by sentences that explain why each option is correct/incorrect, as follows:\n'
            "---\n"
            "Correct Option: 3\n"
            "Option 1 is incorrect because the requirements state that the only inbound port that should be open is 443.\n"
            "Option 2 is incorrect because the requirements state that the only inbound port that should be open is 443.\n"
            "Option 3 is correct because AWS Systems Manager Run Command requires no inbound ports to be open. Run Command operates entirely over outbound HTTPS, which is open by default for security groups.\n"
            "Option 4 is incorrect because AWS Trusted Advisor does not perform this management function.\n"
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
            "1. Run the MySQL database on multiple EC2 instances.\n"
            "2. Place the web tier instances behind an ALB.\n"
            "3. Migrate the MySQL database to Amazon Aurora Serxverless.\n"
            "4. Migrate all EC2 instance types to Graviton2.\n"
            "5. Replace the ALB for the application tier instances with a company-managed load balancer.\n"
            "---\n"
            'For the question and choices in this second example, generate a sentence that shows the correct options, starting with "Correct Options: ", followed by sentences that explain why each option is correct/incorrect, as follows:\n'
            "---\n"
            "Correct Options: 2, 3\n"
            "Option 1 is incorrect because additional EC2 instances will not minimize operational overhead. A managed service would be a better option.\n"
            "Option 2 is correct because you can improve availability and scalability of the web tier by placing the web tier behind an Application Load Balancer (ALB). The ALB serves as the single point of contact for clients and distributes incoming application traffic to the Amazon EC2 instances.\n"
            "Option 3 is correct because Amazon Aurora Serverless provides high performance and high availability with reduced operational complexity.\n"
            "Option 4 is incorrect because the application includes Windows instances, which are not available for Graviton2.\n"
            "Option 5 is incorrect because a company-managed load balancer will not minimize operational overhead.\n"
            "---\n\n"
            "# Main Topic\n"
            "For the question and choices below, generate sentences that show the correct option/options and explain why each option is correct/incorrect.\n"
            'Unless there is an instruction such as "Select THREE" in the question, there will generally only be one correct option.\n'
            "---\n"
            "What is 2 + 2?\n\n"
            "1. 3\n"
            "2. 4\n"
            "3. 5\n"
            "---"
        )

        self.assertEqual(create_user_prompt(subjects, choices), expected_prompt)

    @patch("src.post_answer.AzureOpenAI")
    @patch("src.post_answer.create_system_prompt")
    @patch("src.post_answer.create_user_prompt")
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
        mock_create_user_prompt,
        mock_create_system_prompt,
        mock_azure_openai,
    ):
        """リトライせずに、正解の選択肢のインデックス・正解/不正解の理由を生成するテスト"""

        mock_create_system_prompt.return_value = "system_prompt"
        mock_create_user_prompt.return_value = "user_prompt"
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.correct_indexes = [2]
        mock_response.choices[0].message.parsed.explanations = [
            "Option 2 is correct because 2 + 2 equals 4."
        ]
        mock_azure_openai.return_value.beta.chat.completions.parse.return_value = (
            mock_response
        )

        course_name = "Math"
        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]

        correct_answers = generate_correct_answers(course_name, subjects, choices)

        self.assertEqual(correct_answers["correct_indexes"], [2])
        self.assertEqual(
            correct_answers["explanations"],
            ["Option 2 is correct because 2 + 2 equals 4."],
        )
        mock_create_system_prompt.assert_called_once_with(course_name)
        mock_create_user_prompt.assert_called_once_with(subjects, choices)
        mock_azure_openai.assert_called_once_with(
            api_key="test_api_key",
            api_version="test_api_version",
            azure_deployment="test_deployment",
            azure_endpoint="test_endpoint",
        )
        mock_azure_openai.return_value.beta.chat.completions.parse.assert_called_once_with(
            model="test_model",
            messages=[
                {"role": "system", "content": "system_prompt"},
                {"role": "user", "content": "user_prompt"},
            ],
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
    @patch("src.post_answer.create_system_prompt")
    @patch("src.post_answer.create_user_prompt")
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
        mock_create_user_prompt,
        mock_create_system_prompt,
        mock_azure_openai,
    ):
        """MAX_RETRY_NUMBER回リトライしても、正解の選択肢のインデックス・正解/不正解の理由が生成できない場合のテスト"""

        mock_create_system_prompt.return_value = "system_prompt"
        mock_create_user_prompt.return_value = "user_prompt"
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed = None
        mock_azure_openai.return_value.beta.chat.completions.parse.return_value = (
            mock_response
        )

        course_name = "Math"
        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]

        correct_answers = generate_correct_answers(course_name, subjects, choices)

        self.assertIsNone(correct_answers)
        mock_create_system_prompt.assert_called_once_with(course_name)
        mock_create_user_prompt.assert_called_once_with(subjects, choices)
        mock_logging.info.assert_has_calls(
            [
                call({"retry_number": i / 2}) if i % 2 == 0 else call({"parsed": None})
                for i in range(MAX_RETRY_NUMBER * 2)
            ]
        )
        mock_logging.warning.assert_not_called()

    @patch("src.post_answer.AzureOpenAI")
    @patch("src.post_answer.create_system_prompt")
    @patch("src.post_answer.create_user_prompt")
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
        mock_create_user_prompt,
        mock_create_system_prompt,
        mock_azure_openai,
    ):
        """正解の選択肢のインデックス・正解/不正解の理由の生成でエラーが発生した場合のテスト"""

        mock_create_system_prompt.return_value = "system_prompt"
        mock_create_user_prompt.return_value = "user_prompt"
        mock_azure_openai.return_value.beta.chat.completions.parse.side_effect = [
            Exception("Azure OpenAI Error"),
        ]

        course_name = "Math"
        subjects = ["What is 2 + 2?"]
        choices = ["3", "4", "5"]

        correct_answers = generate_correct_answers(course_name, subjects, choices)

        self.assertIsNone(correct_answers)
        mock_create_system_prompt.assert_called_once_with(course_name)
        mock_create_user_prompt.assert_called_once_with(subjects, choices)
        mock_logging.info.assert_called_once_with({"retry_number": 0})
        mock_logging.warning.assert_called_once()

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
            correctIndexes=[1],
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
            correctIndexes=[1],
            explanations=["Option 2 is correct because 2 + 2 equals 4."],
        )

        queue_message_answer(message_answer)

        mock_queue.send_message.assert_called_once_with(
            json.dumps(message_answer).encode("utf-8")
        )
        mock_logging.info.assert_called_once_with({"message_answer": message_answer})

    @patch("src.post_answer.generate_correct_answers")
    @patch("src.post_answer.queue_message_answer")
    @patch("src.post_answer.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_key",
            "OPENAI_API_VERSION": "v1",
            "OPENAI_DEPLOYMENT": "test_deployment",
            "OPENAI_ENDPOINT": "https://test.endpoint",
            "OPENAI_MODEL": "test_model",
            "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        },
    )
    def test_post_answer(
        self,
        mock_logging,
        mock_queue_message_answer,
        mock_generate_correct_answers,
    ):
        """レスポンスが正常であることのテスト"""

        mock_generate_correct_answers.return_value = {
            "correct_indexes": [1],
            "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
        }

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.get_body()),
            {
                "correctIdxes": [1],
                "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
            },
        )
        mock_generate_correct_answers.assert_called_once_with(
            "Math", ["What is 2 + 2?"], ["3", "4", "5"]
        )
        mock_queue_message_answer.assert_called_once_with(
            {
                "testId": "1",
                "questionNumber": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
                "correctIndexes": [1],
                "explanations": ["Option 2 is correct because 2 + 2 equals 4."],
            }
        )
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": "1",
                "test_id": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_answer.logging")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_key",
            "OPENAI_API_VERSION": "v1",
            "OPENAI_DEPLOYMENT": "test_deployment",
            "OPENAI_ENDPOINT": "https://test.endpoint",
            "OPENAI_MODEL": "test_model",
            "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        },
    )
    def test_post_answer_invalid_test_id(self, mock_logging):
        """testIdが空であるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": "1",
                "test_id": None,
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_question_number_empty(self, mock_logging):
        """questionNumberが空であるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": None,
                "test_id": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_question_number_not_digit(self, mock_logging):
        """questionNumberが数値でないレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "a"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": "a",
                "test_id": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_course_name_empty(self, mock_logging):
        """courseNameが空であるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_course_name_empty_string(self, mock_logging):
        """courseNameが空文字であるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "",
                "question_number": "1",
                "test_id": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_subjects_empty(self, mock_logging):
        """subjectsが空であるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_subjects_not_list(self, mock_logging):
        """subjectsがlistでないレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": "What is 2 + 2?",
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": "1",
                "test_id": "1",
                "subjects": "What is 2 + 2?",
                "choices": ["3", "4", "5"],
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_subjects_empty_list(self, mock_logging):
        """subjectsが空のlistであるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": [],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": "1",
                "test_id": "1",
                "subjects": [],
                "choices": ["3", "4", "5"],
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_choices_empty(self, mock_logging):
        """choicesが空であるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_choices_not_list(self, mock_logging):
        """choicesがlistでないレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
                "choices": "3",
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": "1",
                "test_id": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": "3",
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.post_answer.logging")
    def test_post_answer_invalid_choices_empty_list(self, mock_logging):
        """choicesが空のlistであるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
                "choices": [],
            }
        ).encode("utf-8")

        response = post_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode("utf-8"), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "course_name": "Math",
                "question_number": "1",
                "test_id": "1",
                "subjects": ["What is 2 + 2?"],
                "choices": [],
            }
        )
        mock_logging.error.assert_called_once()
