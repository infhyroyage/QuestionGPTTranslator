# ローカル環境構築手順・削除手順

Azure 環境構築後に、以下のサーバーをすべて起動すると、ローカル開発を行うことができる。

| サーバー名                                     | 使用するサービス名                                                                                                 | ポート番号 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------- |
| Azure Functions(HTTP Trigger の関数アプリのみ) | [Azure Functions Core Tools](https://docs.microsoft.com/ja-jp/azure/azure-functions/functions-run-local)           | 9229       |
| Cosmos DB                                      | [Azure Cosmos DB Linux-based Emulator (preview)](https://learn.microsoft.com/ja-jp/azure/cosmos-db/emulator-linux) | 8081       |
| Blob Storage                                   | [Azurite](https://learn.microsoft.com/ja-jp/azure/storage/common/storage-use-azurite)                              | 10000      |
| Queue Storage                                  | [Azurite](https://learn.microsoft.com/ja-jp/azure/storage/common/storage-use-azurite)                              | 10001      |
| Table Storage                                  | [Azurite](https://learn.microsoft.com/ja-jp/azure/storage/common/storage-use-azurite)                              | 10002      |

> [!NOTE]  
> Table Storage は使用しないが、Azurite の仕様上、Blob Storage・Queue Storage と一緒にサーバーを起動する必要がある。

> [!NOTE]  
> 2024/11/24 現在、Azure Cosmos DB Linux-based Emulator (preview)は複合インデックスのインデックスポリシーがサポートされていないため、Azure Cosmos DB と一部のインデックスポリシーが異なる。

> [!TIP]  
> localhost 環境構築後、ブラウザから [データエクスプローラー](http://localhost:1234) にアクセスすると、Cosmos DB 内のデータを GUI で参照・更新できる。

## 構築手順

1. 以下をすべてインストールする。
   - Azure Functions Core Tools
   - Docker
   - Git
   - Python 3.12
2. GitHub アカウントを用意して、このリポジトリをフォークし、ローカル環境にクローンする
3. 以下を記述したファイル`local.settings.json`を QuestionGPTTranslator リポジトリの functions ディレクトリ配下に保存する。
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "COSMOSDB_KEY": "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
       "COSMOSDB_READONLY_KEY": "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
       "COSMOSDB_URI": "http://localhost:8081",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "NODE_TLS_REJECT_UNAUTHORIZED": "0",
       "OPENAI_API_KEY": "(Azure OpenAIのAPIキー)",
       "OPENAI_API_VERSION": "(Azure OpenAIのAPIバージョン)",
       "OPENAI_DEPLOYMENT_NAME": "(Azure OpenAIのデプロイ名)",
       "OPENAI_ENDPOINT": "(Azure OpenAIのエンドポイント)",
       "OPENAI_MODEL_NAME": "(Azure OpenAIのモデル名)",
       "PYTHON_PATH": "./venv/bin/python",
       "TRANSLATOR_KEY": "(TranslatorのAPIキー)"
     },
     "Host": {
       "CORS": "*",
       "LocalHttpPort": 9229
     },
     "ConnectionStrings": {}
   }
   ```
   - CORS は任意のオリジンを許可するように設定しているため、特定のオリジンのみ許可したい場合は`Host` > `CORS`にそのオリジンを設定すること。
4. ターミナルを起動して以下のコマンドを実行し、Cosmos DB、Blob/Queue/Table ストレージをすべて起動する。実行したターミナルはそのまま放置する。
   ```bash
   docker compose up
   ```
   実行後、以下の標準出力が表示されるまで待機する。
   ```
   localcosmosdb     | Started
   ```
5. Python 3.12 の仮想環境を作成する:
   ```bash
   python3.12 -m venv venv
   ```
6. Python 3.12 の仮想環境を有効化する:
   ```bash
   # Linux/macOSの場合
   source venv/bin/activate
   # Windowsの場合
   venv\Scripts\activate
   ```
7. 6 と同じターミナルで以下のコマンドを実行し、Azure Functions を起動する。実行したターミナルはそのまま放置する。
   ```bash
   cd functions
   func start --verbose
   ```
8. 7 とは別のターミナルで以下のコマンドを実行し、6 で作成した仮想環境の有効後、起動した Cosmos DB サーバーに対し、インポートデータファイルからインポートする。
   ```bash
   ./venv/Scripts/activate
   python functions/import_local.py
   ```
   - タイムアウトなどで失敗した場合、もう一度実行し直すこと。

## 削除手順

1. 構築手順の 7 で起動した Azure Functions のターミナルに対して Ctrl+C キーを入力し、起動した Azure Functions を停止する。
2. ターミナルを起動して以下のコマンドを実行し、構築手順の 4 で起動した Cosmos DB、Blob/Queue/Table ストレージをすべて停止する。
   ```bash
   docker compose down
   ```
