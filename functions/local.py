"""ローカル環境でのインポート処理"""

import json
import os
import re
import time
from uuid import uuid4

from azure.cosmos import CosmosClient, PartitionKey
from type.cosmos import Question, Test
from type.importing import ImportData, ImportDatabaseData, ImportItem


def create_import_data() -> ImportData:
    """
    コマンドライン引数でコース名/テスト名指定した場合は、インポートデータから
    指定したコース名/テスト名における項目を抽出して、インポートデータを生成する
    """

    # dataファイル/ディレクトリが存在しない場合は空オブジェクトをreturn
    data_path = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(data_path):
        return {}

    # dataディレクトリに存在する、コース名をすべて取得
    course_directories = [
        dirent
        for dirent in os.listdir(data_path)
        if os.path.isdir(os.path.join(data_path, dirent))
    ]

    import_data: ImportData = {}
    for course_name in course_directories:
        # コース名のディレクトリに存在する、テスト名をすべて取得
        test_names = [
            file_name.replace(".json", "")
            for file_name in os.listdir(os.path.join(data_path, course_name))
            if file_name.endswith(".json")
        ]

        import_database_data: ImportDatabaseData = {}
        for test_name in test_names:
            # テスト名のjsonファイル名からjsonの中身を読込み
            with open(
                os.path.join(data_path, course_name, f"{test_name}.json"),
                "r",
                encoding="utf8",
            ) as f:
                import_items: list[ImportItem] = json.load(f)
            import_database_data[test_name] = import_items

        import_data[course_name] = import_database_data

    return import_data


def create_databases_and_containers(client: CosmosClient) -> None:
    """
    インポートデータの格納に必要な各データベース、コンテナーをすべて作成する
    """

    # Usersデータベース
    database_res = client.create_database_if_not_exists(id="Users")

    # Testコンテナー
    database_res.create_container_if_not_exists(
        id="Test",
        partition_key=PartitionKey(path="/id"),
        indexing_policy={
            "compositeIndexes": [
                [
                    {"path": "/courseName", "order": "ascending"},
                    {"path": "/testName", "order": "ascending"},
                ]
            ]
        },
    )

    # Questionコンテナー
    database_res.create_container_if_not_exists(
        id="Question", partition_key=PartitionKey(path="/id")
    )


def generate_test_items(import_data: ImportData, client: CosmosClient) -> list[Test]:
    """
    インポートデータのテスト項目を取得する
    """

    # UsersテータベースのTestコンテナーをreadAll
    inserted_test_items = []
    try:
        container = client.get_database_client("Users").get_container_client("Test")
        inserted_test_items = list(container.read_all_items())
    except Exception:
        print("generateTestItems: Not Found Items")

    test_items: list[Test] = []
    for course_name, tests in import_data.items():
        for test_name, items in tests.items():
            # UsersテータベースのTestコンテナー格納済の場合は格納した項目、
            # 未格納の場合はNoneを取得
            found_test_item = next(
                (
                    item
                    for item in inserted_test_items
                    if item["courseName"] == course_name
                    and item["testName"] == test_name
                ),
                None,
            )
            test_items.append(
                found_test_item
                or {
                    "courseName": course_name,
                    "testName": test_name,
                    "id": str(uuid4()),
                    "length": len(items),
                }
            )

    return test_items


def import_test_items(test_items: list[Test], client: CosmosClient) -> None:
    """
    UsersテータベースのTestコンテナーの項目をインポートする
    """

    container = client.get_database_client("Users").get_container_client("Test")
    for item in test_items:
        container.upsert_item(item)


def generate_question_items(
    import_data: ImportData, client: CosmosClient, test_items: list[Test]
) -> list[Question]:
    """
    インポートデータからUsersテータベースのQuestionコンテナーの未格納の項目のみ生成する
    """

    # UsersテータベースのQuestionコンテナーの全idを取得
    inserted_question_ids = [
        item["id"]
        for item in client.get_database_client("Users")
        .get_container_client("Question")
        .query_items(query="SELECT c.id FROM c", enable_cross_partition_query=True)
    ]

    question_items: list[Question] = []
    for course_name, tests in import_data.items():
        for test_name, items in tests.items():
            test_item = next(
                (
                    item
                    for item in test_items
                    if item["courseName"] == course_name
                    and item["testName"] == test_name
                ),
                None,
            )
            if not test_item:
                raise ValueError(
                    f"Course Name {course_name} and Test Name {test_name} Not Found."
                )

            test_id = test_item["id"]
            for idx, item in enumerate(items):
                if f"{test_id}_{idx + 1}" not in inserted_question_ids:
                    # communityVotesの最初の要素が「AB (100%)」のような形式の場合は回答が複数個、
                    # 「A (100%)」のような形式の場合は回答が1個のみ存在すると判定
                    is_multiplied: bool = bool(
                        re.match(
                            r"^[A-Z]{2,} \(\d+%\)$",
                            item["communityVotes"][0],
                        )
                    )
                    question_items.append(
                        {
                            **item,
                            "id": f"{test_id}_{idx + 1}",
                            "number": idx + 1,
                            "testId": test_id,
                            "isMultiplied": is_multiplied,
                        }
                    )

    return question_items


def import_question_items(question_items: list[Question], client: CosmosClient) -> None:
    """
    UsersテータベースのQuestionコンテナーの項目をインポートする
    比較的要求ユニット(RU)数が多いDB操作を行うため、upsertの合間に3秒間sleepする
    https://docs.microsoft.com/ja-jp/azure/cosmos-db/sql/troubleshoot-request-rate-too-large
    """

    container = client.get_database_client("Users").get_container_client("Question")
    for i, item in enumerate(question_items):
        res = container.upsert_item(item)
        if res["statusCode"] >= 400:
            raise ValueError(f"Status Code {res['statusCode']}: {json.dumps(item)}")
        print(f"{i + 1}th Response OK")
        time.sleep(3)


if __name__ == "__main__":
    # インポートデータ作成
    created_import_data = create_import_data()
    print("create_import_data: OK")

    # 各データベース・コンテナー作成
    cosmos_client = CosmosClient(
        "https://localhost:8081",
        "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
    )
    create_databases_and_containers(cosmos_client)
    print("create_databases_and_containers: OK")

    # Testコンテナーの項目を生成
    generated_test_items = generate_test_items(created_import_data, cosmos_client)
    print("generate_test_items: OK")

    # Testコンテナーの項目をインポート
    import_test_items(generated_test_items, cosmos_client)
    print("import_test_items: OK")

    # Questionコンテナーの項目を生成
    generated_question_items = generate_question_items(
        created_import_data, cosmos_client, generated_test_items
    )
    print("generate_question_items: OK")

    # Questionコンテナーの項目をインポート
    import_question_items(generated_question_items, cosmos_client)
    print("import_question_items: OK")
