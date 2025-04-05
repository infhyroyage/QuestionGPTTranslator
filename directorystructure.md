# ディレクトリ構成

以下のディレクトリ構造に従って実装を行ってください：

```
/
├── .cursor/                                     # Cursor IDE設定
│   └── rules/                                   # Project Rules
│       └── global.mdc                           # グローバルルール設定
├── .git/                                        # Gitリポジトリ
├── .github/                                     # GitHub連携設定
│   ├── workflows/                               # GitHub Actionsワークフロー
│   │   ├── create-azure-resources.yaml          # Azureリソース作成ワークフロー
│   │   ├── deploy-apim.yaml                     # Azure API Management自動デプロイ
│   │   ├── deploy-functions-app.yaml            # Azure Functions App自動デプロイ
│   │   ├── deploy-swagger-ui.yaml               # Swagger UI自動デプロイ
│   │   ├── regenerate-secrets.yaml              # シークレット再生成ワークフロー
│   │   ├── reusable-deploy-apim.yaml            # 再利用可能なAzure API Managementデプロイワークフロー
│   │   ├── reusable-deploy-functions-app.yaml   # 再利用可能なAzure Functions Appデプロイワークフロー
│   │   ├── scan-codeql.yaml                     # Pull Request発行時のCodeQLによるセキュリティスキャン
│   │   └── test-lint.yaml                       # Pull Request発行時のユニットテスト・pylint実行ワークフロー
│   ├── CODEOWNERS                               # コードオーナー設定
│   └── dependabot.yaml                          # 依存関係自動更新設定
├── functions/                                   # Azure Functionsの関数アプリ
│   ├── src/                                     # ソースコード
│   │   ├── blob_triggered_import.py             # Blobトリガー
│   │   ├── delete_progresses.py                 # [DELETE] /tests/{testId}/progresses
│   │   ├── get_answer.py                        # [GET] /tests/{testId}/answers/{questionNumber}
│   │   ├── get_healthcheck.py                   # [GET] /healthcheck
│   │   ├── get_question.py                      # [GET] /tests/{testId}/questions/{questionNumber}
│   │   ├── get_tests.py                         # [GET] /tests
│   │   ├── post_answer.py                       # [POST] /tests/{testId}/answers/{questionNumber}
│   │   ├── post_progress.py                     # [POST] /tests/{testId}/progresses/{questionNumber}
│   │   ├── put_en2ja.py                         # [PUT] /en2ja
│   │   └── queue_triggered_answer.py            # Queueトリガー
│   ├── util/                                    # ユーティリティ
│   │   ├── cosmos.py                            # Azure Cosmos DBアクセス処理
│   │   ├── local.py                             # ローカル環境構築
│   │   └── queue.py                             # Queue Storageアクセス処理
│   ├── tests/                                   # テストコード
│   │   ├── test_blob_triggered_import.py        # Blobトリガーのテスト
│   │   ├── test_cosmos.py                       # Cosmos DBユーティリティのテスト
│   │   ├── test_delete_progresses.py            # [DELETE] /tests/{testId}/progresses のテスト
│   │   ├── test_get_answer.py                   # [GET] /tests/{testId}/answers/{questionNumber} のテスト
│   │   ├── test_get_healthcheck.py              # [GET] /healthcheck のテスト
│   │   ├── test_get_question.py                 # [GET] /tests/{testId}/questions/{questionNumber} のテスト
│   │   ├── test_get_tests.py                    # [GET] /tests のテスト
│   │   ├── test_local.py                        # ローカル環境構築のテスト
│   │   ├── test_post_answer.py                  # [POST] /tests/{testId}/answers/{questionNumber} のテスト
│   │   ├── test_post_progress.py                # [POST] /tests/{testId}/progresses/{questionNumber} のテスト
│   │   ├── test_put_en2ja.py                    # [PUT] /en2ja のテスト
│   │   └── test_queue_triggered_answer.py       # Queueトリガーのテスト
│   ├── type/                                    # 型定義
│   │   ├── cosmos.py                            # Azure Cosmos DB関連の型定義
│   │   ├── importing.py                         # インポート処理の型定義
│   │   ├── message.py                           # メッセージの型定義
│   │   ├── openai.py                            # Azure OpenAI APIの型定義
│   │   ├── request.py                           # リクエストの型定義
│   │   ├── response.py                          # レスポンスの型定義
│   │   ├── structured.py                        # 構造化データの型定義
│   │   └── translation.py                       # 翻訳処理の型定義
│   ├── data/                                    # インポートデータファイル
│   ├── function_app.py                          # 関数アプリのエントリーポイント
│   ├── host.json                                # 関数アプリ実行環境設定
│   ├── import_local.py                          # ローカル環境でのインポート処理スクリプト
│   └── local.settings.json                      # ローカル環境設定
├── apim/                                        # API ManagementのSwagger・ポリシー
│   ├── apis-functions-policy.xml                # 関数APIのポリシー設定
│   ├── apis-functions-swagger.yaml              # 関数APIのSwagger定義
│   ├── apis-healthcheck-functions-policy.xml    # ヘルスチェックAPIのポリシー設定
│   └── apis-healthcheck-functions-swagger.yaml  # ヘルスチェックAPIのSwagger定義
├── azurite/                                     # Azuriteデータ
├── resources/                                   # Azureリソース定義(IaC)
│   ├── base.bicep                               # 基本インフラストラクチャ定義
│   ├── connect-apim-2-functions.bicep           # Azure API ManagementとAzure Functionsとの連携部分のインフラストラクチャ定義
│   └── functions-appsettings.json               # Azure Key Vaultから取得するAzure Functionsのアプリケーション設定
├── venv/                                        # Python仮想環境
├── .funcignore                                  # Azure Functionsデプロイ時の除外設定
├── .gitignore                                   # Git管理除外設定
├── .pylintrc                                    # pylintコード解析設定
├── architecture.drawio.svg                      # アーキテクチャ図
├── azureenvironment.md                          # Azure環境構築手順・削除手順
├── compose.yaml                                 # Docker Compose設定
├── directorystructure.md                        # ディレクトリ構成
├── LICENSE                                      # ライセンス情報
├── localenvironment.md                          # ローカル環境構築手順・削除手順
├── README.md                                    # プロジェクト概要説明
├── requirements.txt                             # Pythonパッケージ依存関係
└── technologystack.md                           # 技術スタック情報
```
