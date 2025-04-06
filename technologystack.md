# 技術スタック

## Azure

- Azure API Management (API バージョン管理)
- Azure Functions (関数アプリ)
- Azure Storage Account
  - Blob Storage
  - Queue Storage
- Azure Cosmos DB (データベース)
- Azure Key Vault (シークレット管理)
- Azure Application Insights (ログ記録)
- Azure OpenAI (AI モデル)
- Azure Translator (翻訳(primary モデル))

## Azure 以外

- GitHub Actions (CI/CD)
- DeepL API (翻訳(secondary モデル))

## アーキテクチャー図

![architecture.drawio](architecture.drawio.svg)

| Azure リソース名                        | 概要                                                     | リージョン                              |
| --------------------------------------- | -------------------------------------------------------- | --------------------------------------- |
| リポジトリの変数`APIM_NAME`で指定       | ユーザーからアクセスする API Management                  | japaneast                               |
| リポジトリの変数`FUNCTIONS_NAME`で指定  | API Management からアクセスする Functions                | japaneast                               |
| `qgtranslator-je-funcplan`              | Functions のプラン                                       | japaneast                               |
| リポジトリの変数`STORAGE_NAME`で指定    | Functions から参照するストレージアカウント               | japaneast                               |
| リポジトリの変数`COSMOSDB_NAME`で指定   | Functions からアクセスする Cosmos DB                     | japaneast                               |
| リポジトリの変数`VAULT_NAME`で指定      | シークレットを管理する Key Vault                         | japaneast                               |
| `qgtranslator-je-insights`              | API Management/Functions を監視する Application Insights | japaneast                               |
| リポジトリの変数`OPENAI_NAME`で指定     | Functions からアクセスする Azure OpenAI                  | リポジトリの変数`OPENAI_LOCATION`で指定 |
| リポジトリの変数`TRANSLATOR_NAME`で指定 | Functions からアクセスする Translator                    | japaneast                               |

> [!WARNING]  
> Azure OpenAI は、以下をすべてサポートする場所・モデル名・モデルバージョン・API バージョンを使用する必要がある。
>
> - [Structured outputs](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/structured-outputs)
> - [Vision-enabled](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/gpt-with-vision)

> [!NOTE]  
> Translator の価格レベルは Free(無料)とする。この無料枠をすべて使い切った場合、代わりに DeepL へアクセスする。

## Azure Functions の関数アプリ

- azure-cosmos (Azure Cosmos DB の Python クライアント)
- azure-functions (Azure Functions の Python クライアント)
- azure-storage-queue (Azure Storage Queue の Python クライアント)
- coverage (テストカバレッジの計測)
- openai (Azure OpenAI の Python クライアント)
  - 破壊的変更が多いため、dependabot でのアップグレード更新対象外とする
- pydantic (データモデルの定義)
- pylint (コードの静的解析)
- requests (HTTP リクエスト)

## 開発ツール

- Python 3.12 (プログラミング言語)
  - LLM を扱うためのモジュールが豊富であるため Python を採用
- Azure Functions Core Tools (関数アプリのローカル実行)
- Docker Compose (ローカル開発時の環境構築)
  - Azurite (Azure Storage エミュレータ)
  - Azure Cosmos DB Emulator (Azure Cosmos DB エミュレータ)

# API バージョン管理

## 重要な制約事項

- Azure Cosmos DB に格納するデータは、**インポートデータファイル**と呼ぶ json ファイルを`data/(コース名)/(テスト名).json`で配置するが、GitHub では管理せず、ローカルで管理
- Azure OpenAI の API キー、API バージョン、デプロイ名、エンドポイント、モデル名は環境変数し、ローカルで管理
- ローカル開発時の環境変数情報である local.settings.json はローカルで管理

## API 開発時の実装規則

- functions/function_app.py に全エントリーポイントのブループリントを登録
- HTTP Trigger の関数アプリを開発する場合、その関数アプリの API リファレンスである Swagger ファイル (apim/apis-functions-swagger.yaml) で管理
  - [Swagger UI](https://infhyroyage.github.io/QuestionGPTTranslator/)も公開済み
  - `[GET] /healthcheck` のみ、別の Swagger ファイル(apim/apis-healthcheck-functions-swagger.yaml)で管理
  - API Management のデプロイは、この Swagger を利用
- 認証は Azure AD のサービスプリンシパルを使用し、API Management のポリシーで設定
- 以下のコマンド実行でユニットテストを実行し、 stmt のカバレッジ率が 80% 以上であることを確認
  ```bash
  cd functions && python -m unittest discover -s tests && python -m coverage report
  ```
- 以下のコマンド実行で pylint を実行し、警告・エラーを出力しないことを確認
  ```bash
  pylint functions/**/*.py
  ```
