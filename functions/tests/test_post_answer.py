"""[POST] /answer のテスト"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from src.post_answer import (
    create_system_prompt,
    create_user_prompt,
    queue_message_answer,
)
from type.message import MessageAnswer


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

    @patch("src.post_answer.QueueClient.from_connection_string")
    @patch.dict(os.environ, {"AzureWebJobsStorage": "on-azure"})
    def test_queue_message_answer_azure(self, mock_queue_client):
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

    @patch("src.post_answer.QueueClient.from_connection_string")
    @patch.dict(os.environ, {"AzureWebJobsStorage": "UseDevelopmentStorage=true"})
    def test_queue_message_answer_local(self, mock_queue_client):
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


if __name__ == "__main__":
    unittest.main()
