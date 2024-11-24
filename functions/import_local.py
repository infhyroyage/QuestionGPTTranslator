"""ローカル環境でのインポート処理"""

import os

from util.local import (
    create_databases_and_containers,
    create_import_data,
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

# インポートデータ作成
created_import_data = create_import_data()
print("create_import_data: OK")

# 各データベース・コンテナー作成
create_databases_and_containers()
print("create_databases_and_containers: OK")

# Testコンテナーの項目を生成
generated_test_items = generate_test_items(created_import_data)
print("generate_test_items: OK")

# Testコンテナーの項目をインポート
import_test_items(generated_test_items)
print("import_test_items: OK")

# Questionコンテナーの項目を生成
generated_question_items = generate_question_items(
    created_import_data, generated_test_items
)
print("generate_question_items: OK")

# Questionコンテナーの項目をインポート
import_question_items(generated_question_items)
print("import_question_items: OK")
