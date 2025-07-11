"""インポートデータファイルの項目をインポートするBlobトリガーの関数アプリのモジュール"""

import json
import logging
import time
from uuid import uuid4

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Question, Test
from type.importing import ImportItem
from util.cosmos import get_read_write_container


def upsert_test_item(
    course_name: str, test_name: str, json_data: list[ImportItem]
) -> tuple[str, bool]:
    """
    Testコンテナーの項目をupsertする

    Args:
        course_name (str): コース名
        test_name (str): テスト名
        json_data (list[ImportItem]): インポートデータ

    Returns:
        tuple[str, bool]: Testコンテナーの項目のIDと、その項目が既に存在するかどうか
    """

    # Testコンテナーのインスタンスを取得
    container: ContainerProxy = get_read_write_container(
        database_name="Users",
        container_name="Test",
    )

    # Testコンテナーの項目を取得
    inserted_test_items: list[Test] = list(
        container.query_items(
            query="SELECT * FROM c WHERE c.courseName = @courseName and c.testName = @testName",
            parameters=[
                {"name": "@courseName", "value": course_name},
                {"name": "@testName", "value": test_name},
            ],
        )
    )
    logging.info({"inserted_test_items": inserted_test_items})
    if len(inserted_test_items) > 1:
        raise ValueError("Not Unique Test")
    is_existed_test: bool = len(inserted_test_items) == 1

    # 取得したTestコンテナーの項目が存在し差分がない場合以外はupsert
    test_id: str
    if not is_existed_test or (
        is_existed_test and inserted_test_items[0]["length"] != len(json_data)
    ):
        test_id = inserted_test_items[0]["id"] if is_existed_test else str(uuid4())
        test_item: Test = {
            "courseName": course_name,
            "testName": test_name,
            "id": test_id,
            "length": len(json_data),
        }
        logging.info({"test_item": test_item})
        container.upsert_item(test_item)
    else:
        test_id = inserted_test_items[0]["id"]

    logging.info({"test_id": test_id, "is_existed_test": is_existed_test})

    return test_id, is_existed_test


def upsert_question_items(
    test_id: str, is_existed_test: bool, json_data: list[ImportItem]
) -> None:
    """
    Questionコンテナーの項目をupsertする

    Args:
        test_id (str): Testコンテナーの項目のidフィールドの値
        is_existed_test (bool): Testコンテナーの項目が取得できた場合はTrue、取得できない場合はFalse
        json_data (list[ImportItem]): インポートデータ
    """

    # Questionコンテナーのインスタンスを取得
    container: ContainerProxy = get_read_write_container(
        database_name="Users",
        container_name="Question",
    )

    # Testコンテナーの項目が取得できた場合のみ、クエリを実行して項目を全取得
    inserted_question_items: list[Question] = (
        list(
            container.query_items(
                query="SELECT * FROM c WHERE c.testId = @testId",
                parameters=[{"name": "@testId", "value": test_id}],
            )
        )
        if is_existed_test
        else []
    )

    # 読み込んだjsonファイルの各ImportItemにて、取得したQuestionコンテナーに存在して差分がない項目を抽出
    inserted_import_items: list[ImportItem] = []
    for inserted_question_item in inserted_question_items:
        inserted_import_item: ImportItem = {
            "subjects": inserted_question_item["subjects"],
            "choices": inserted_question_item["choices"],
            "answerNum": inserted_question_item["answerNum"],
        }

        if "indicateSubjectImgIdxes" in inserted_question_item:
            inserted_import_item["indicateSubjectImgIdxes"] = inserted_question_item[
                "indicateSubjectImgIdxes"
            ]
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
        if "discussions" in inserted_question_item:
            inserted_import_item["discussions"] = inserted_question_item["discussions"]
        inserted_import_items.append(inserted_import_item)
    logging.info({"inserted_import_items": inserted_import_items})

    # Questionコンテナーの各項目をupsert
    # 比較的要求ユニット(RU)数が多いDB操作を行うため、upsertの合間に3秒間sleepする
    # https://docs.microsoft.com/ja-jp/azure/cosmos-db/sql/troubleshoot-request-rate-too-large
    for idx, json_import_item in enumerate(json_data):
        if json_import_item not in inserted_import_items:
            question_item: Question = {
                **json_import_item,
                "id": f"{test_id}_{idx + 1}",
                "number": idx + 1,
                "testId": test_id,
            }
            logging.info({"question_item": question_item})
            container.upsert_item(question_item)
            time.sleep(3)


bp_blob_triggered_import = func.Blueprint()


@bp_blob_triggered_import.blob_trigger(
    arg_name="blob",
    connection="AzureWebJobsStorage",
    path="import-items/{courseName}/{testName}.json",
)
def blob_triggered_import(blob: func.InputStream):
    """
    アップロードしたインポートデータファイルからCosmos DBにインポートします
    """

    # インポートデータファイルのメタデータから可変パラメーターを取得
    split_path = blob.name.split("/")
    course_name = split_path[1]
    test_name = split_path[2].split(".")[0]
    logging.info({"course_name": course_name, "test_name": test_name})

    # インポートデータファイルの読込み
    json_data: list[ImportItem] = json.loads(blob.read())

    # Testコンテナーの項目をupsert
    test_id, is_existed_test = upsert_test_item(
        course_name=course_name,
        test_name=test_name,
        json_data=json_data,
    )

    # Questionコンテナーの項目をupsert
    upsert_question_items(
        test_id=test_id,
        is_existed_test=is_existed_test,
        json_data=json_data,
    )
