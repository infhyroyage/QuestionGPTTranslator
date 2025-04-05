# ディレクトリ構成

以下のディレクトリ構造に従って実装を行ってください：

```
/
├── .cursor/                          # Cursor設定
│   └── rules/                        # Project Rules
├── .git/                             # Gitリポジトリ
├── .github/                          # GitHub Actions設定
├── functions/                        # Azure Functionsの関数アプリ
│   ├── src/                          # ソースコード
│   │   ├── __init__.py
│   │   ├── get_answer.py             # [GET] /tests/{testId}/answers/{questionNumber}
│   │   ├── get_healthcheck.py        # [GET] /healthcheck
│   │   ├── get_question.py           # [GET] /tests/{testId}/questions/{questionNumber}
│   │   ├── get_tests.py              # [GET] /tests
│   │   ├── post_answer.py            # [POST] /tests/{testId}/answers/{questionNumber}
│   │   ├── post_progress.py          # [POST] /tests/{testId}/progresses/{questionNumber}
│   │   ├── put_en2ja.py              # [PUT] /en2ja
│   │   ├── blob_triggered_import.py  # Blobトリガー
│   │   └── queue_triggered_answer.py # Queueトリガー
│   ├── util/                         # ユーティリティ
│   │   ├── __init__.py
│   │   ├── cosmos.py                 # Cosmos DB
│   │   ├── local.py                  # ローカル環境でのインポート処理
│   │   └── queue.py                  # Queue Storage
│   ├── tests/                        # テストコード
│   ├── type/                         # 型定義
│   ├── data/                         # インポートデータファイル
│   ├── function_app.py               # エントリーポイント
│   ├── host.json                     # ホスト設定
│   ├── local.settings.json           # ローカル環境設定
│   └── import_local.py               # ローカル環境でのインポート処理
├── apim/                             # API ManagementのSwagger・ポリシー
├── azurite/                          # Azurite
├── resources/                        # Azureリソース定義(IaC)
├── venv/                             # Python仮想環境
├── .funcignore                       # Azure Functions除外設定
├── .gitignore                        # Git除外設定
├── .pylintrc                         # pylint設定
├── architecture.drawio.svg           # アーキテクチャ図
├── compose.yaml                      # Docker Compose設定
├── LICENSE                           # ライセンス
├── README.md                         # READMEファイル
├── directorystructure.md             # ディレクトリ構成
├── requirements.txt                  # Pythonパッケージ
└── technologystack.md                # 技術スタック
```
