"""ローカル環境でのインポート処理"""

import os

from util.local import (
    create_databases_and_containers,
    create_import_data,
    create_queue_storages,
    generate_question_items,
    generate_test_items,
    import_question_items,
    import_test_items,
)

# Azure Cosmos DB EmulatorのURIとキーを設定
os.environ["COSMOSDB_URI"] = "http://localhost:8081"
os.environ["COSMOSDB_KEY"] = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)

# Queue Storageを作成
create_queue_storages()
print("create_queue_storages: OK")

# 各データベース・コンテナー作成
create_databases_and_containers()
print("create_databases_and_containers: OK")

# インポートデータ作成
created_import_data = create_import_data()
print(f"create_import_data: OK(length: {len(created_import_data)})")

# Testコンテナーの項目を生成
generated_test_items = generate_test_items(created_import_data)
print(f"generate_test_items: OK(length: {len(generated_test_items)})")

# Testコンテナーの項目をインポート
import_test_items(generated_test_items)
print("import_test_items: OK")

# Questionコンテナーの項目を生成
generated_question_items = generate_question_items(
    created_import_data, generated_test_items
)
print(f"generate_question_items: OK(length: {len(generated_question_items)})")

# Questionコンテナーの項目をインポート
import_question_items(generated_question_items)
print("import_question_items: OK")
