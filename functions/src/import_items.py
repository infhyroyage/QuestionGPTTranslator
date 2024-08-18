"""
Module of Blob Triggers
"""

import json
import logging
import time
from uuid import uuid4

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Question, Test
from type.importing import ImportItem
from util.cosmos import get_read_write_container

bp_import_items = func.Blueprint()


@bp_import_items.blob_trigger(
    arg_name="blob",
    connection="AzureWebJobsStorage",
    path="import-items/{courseName}/{testName}.json",
)
def import_items(blob: func.InputStream):
    """
    Import Cosmos DB Items
    """

    try:
        # Blobトリガーで受け取ったメタデータから可変パラメーターを取得
        split_path = blob.name.split("/")
        course_name = split_path[1]
        test_name = split_path[2].split(".")[0]
        logging.info({"course_name": course_name, "test_name": test_name})

        # Blobトリガーで受け取ったjsonファイルのバイナリデータをImportItem[]型として読込み
        json_data: list[ImportItem] = json.loads(blob.read())

        # Initialize Cosmos DB Client
        test_container: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Test",
        )
        question_container: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Question",
        )

        # UsersテータベースのTestコンテナーの項目を取得
        query = "SELECT * FROM c WHERE c.courseName = @courseName and c.testName = @testName"
        parameters: list[dict[str, str]] = [
            {"name": "@courseName", "value": course_name},
            {"name": "@testName", "value": test_name},
        ]
        inserted_test_items: list[Test] = list(
            test_container.query_items(query=query, parameters=parameters)
        )
        logging.info({"inserted_test_items": inserted_test_items})
        if len(inserted_test_items) > 1:
            raise ValueError("Not Unique Test")

        # 取得したUsersテータベースのTestコンテナーの項目が存在し差分がない場合以外はupsert
        test_id: str | None = None
        if len(inserted_test_items) == 0 or (
            len(inserted_test_items) == 1
            and inserted_test_items[0]["length"] != len(json_data)
        ):
            test_id = (
                str(uuid4())
                if len(inserted_test_items) == 0
                else inserted_test_items[0]["id"]
            )
            upsert_test_item: Test = {
                "courseName": course_name,
                "testName": test_name,
                "id": test_id,
                "length": len(json_data),
            }
            logging.info({"upsert_test_item": upsert_test_item})
            test_container.upsert_item(upsert_test_item)
        else:
            test_id = inserted_test_items[0]["id"]

        # UsersテータベースのQuestionコンテナーの項目を全取得
        inserted_question_items: list[Question] = []
        if len(inserted_test_items) > 0:
            # UsersテータベースのTestコンテナーの項目が取得できた場合のみクエリを実行
            query = "SELECT * FROM c WHERE c.testId = @testId"
            parameters = [{"name": "@testId", "value": test_id}]
            inserted_question_items = list(
                question_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

        # 読み込んだjsonファイルの各ImportItemにて、取得したUsersテータベースのQuestionコンテナーに存在して差分がない項目を抽出
        inserted_import_items: list[ImportItem] = []
        for inserted_question_item in inserted_question_items:
            inserted_import_item: ImportItem = {
                "subjects": inserted_question_item["subjects"],
                "choices": inserted_question_item["choices"],
                "communityVotes": inserted_question_item["communityVotes"],
            }
            if "indicateSubjectImgIdxes" in inserted_question_item:
                inserted_import_item["indicateSubjectImgIdxes"] = (
                    inserted_question_item["indicateSubjectImgIdxes"]
                )
            if "indicateChoiceImgs" in inserted_question_item:
                inserted_import_item["indicateChoiceImgs"] = inserted_question_item[
                    "indicateChoiceImgs"
                ]
            if "escapeTranslatedIdxes" in inserted_question_item:
                escape_translated_idxes = {}
                if "subjects" in inserted_question_item["escapeTranslatedIdxes"]:
                    escape_translated_idxes["subjects"] = inserted_question_item[
                        "escapeTranslatedIdxes"
                    ]["subjects"]
                if "choices" in inserted_question_item["escapeTranslatedIdxes"]:
                    escape_translated_idxes["choices"] = inserted_question_item[
                        "escapeTranslatedIdxes"
                    ]["choices"]
                inserted_import_item["escapeTranslatedIdxes"] = escape_translated_idxes
            inserted_import_items.append(inserted_import_item)
        logging.info({"inserted_import_items": inserted_import_items})
        upsert_import_items: list[ImportItem] = []
        for json_import_item in json_data:
            if json_import_item not in inserted_import_items:
                upsert_import_items.append(json_import_item)
        logging.info({"upsert_import_items": upsert_import_items})

        # 暗号化したUsersテータベースのQuestionコンテナーの各項目をupsert
        # 比較的要求ユニット(RU)数が多いDB操作を行うため、upsertの合間に3秒間sleepする
        # https://docs.microsoft.com/ja-jp/azure/cosmos-db/sql/troubleshoot-request-rate-too-large
        for idx, item in enumerate(upsert_import_items):
            question_item: Question = {
                **item,
                "id": f"{test_id}_{idx + 1}",
                "number": idx + 1,
                "testId": test_id,
            }
            question_container.upsert_item(question_item)
            time.sleep(3)

        return func.HttpResponse(body="OK", status_code=200)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
