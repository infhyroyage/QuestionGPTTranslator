# QuestionGPTTranslator

[![Create Azure Resources](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/create-azure-resources.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/create-azure-resources.yaml)
[![Deploy API Management](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-apim.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-apim.yaml)
[![Deploy Azure Functions Application](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-functions-app.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-functions-app.yaml)
[![Deploy to Swagger UI](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-swagger-ui.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-swagger-ui.yaml)
[![Regenerate Secrets](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/regenerate-secrets.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/regenerate-secrets.yaml)

## 概要

[QuestionGPTPortal](https://github.com/infhyroyage/QuestionGPTPortal)の API サーバーを構成する。

## アーキテクチャー図

![architecture.drawio](architecture.drawio.svg)

| Azure リソース名           | 概要                                                                                               |
| -------------------------- | -------------------------------------------------------------------------------------------------- |
| `qgtranslator-je-apim`     | ユーザー/App Service からアクセスする API Management                                               |
| `qgtranslator-je-func`     | API Management からアクセスする Functions                                                          |
| `qgtranslator-je-funcplan` | Functions のプラン                                                                                 |
| `qgtranslatorjesa`         | Functions から参照するストレージアカウント                                                         |
| `qgtranslator-je-cosmosdb` | Functions からアクセスする Cosmos DB                                                               |
| `qgtranslator-je-vault`    | シークレットを管理する Key Vault                                                                   |
| `qgtranslator-je-insights` | App Service/API Management/Functions を一括で監視する Application Insights                         |
| `(Your Own OpenAI)`        | Functions からアクセスする事前作成の Structured outputs をサポートする Azure OpenAI                |
| `(Your Own Translator)`    | Functions からアクセスする事前作成の Translator(枠を使い切った場合は代わりに DeepL へアクセスする) |

> [!WARNING]  
> Azure OpenAI は、[Structured outputs をサポートするモデル・バージョン](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/structured-outputs?tabs=python-secure#supported-models) を使用する必要がある。

## 使用する主要なパッケージのバージョン

| 名称                      | バージョン |
| ------------------------- | ---------- |
| Python                    | 3.11       |
| OpenAI Python API library | 1.58.1     |

上記以外のパッケージは、dependabot によってバージョン管理している。

## 初期構築

Azure リソース/localhost に環境を構築する事前準備として、以下の順で初期構築を必ずすべて行う必要がある。

1. Azure AD 認証認可用サービスプリンシパルの発行
2. GitHub Actions 用サービスプリンシパルの発行
3. リポジトリのシークレット・変数設定
4. インポートデータファイルの作成

### 1. Azure AD 認証認可用サービスプリンシパルの発行

[Microsoft ID Platform](https://learn.microsoft.com/ja-jp/azure/active-directory/develop/v2-overview)経由で Web アプリケーションに認証認可を実現するためのサービスプリンシパル QGTranslator_MSAL を以下の手順で発行する。

1. Azure Portal から Azure AD に遷移する。
2. App Registrations > New registration の順で押下し、以下の項目を入力後、Register ボタンを押下してサービスプリンシパルを登録する。
   - Name : `QGTranslator_MSAL`
   - Supported account types : `Accounts in this organizational directory only`
   - Redirect URI : `Single-page application(SPA)`(左) と `https://infhyroyage.github.io/QuestionGPTPortal`(右)
3. 登録して自動遷移した「QGTranslator_MSAL」の Overview にある「Application (client) ID」の値(=クライアント ID)を手元に控える。
4. Expose an API > Application ID URI の右にある小さな文字「Add」を押下し、Application ID URI の入力欄に`api://{3で手元に控えたクライアントID}`が自動反映されていることを確認し、Save ボタンを押下する。
5. Expose an API > Scopes defined by this API にある「Add a scope」を押下し、以下の項目を入力後、Save ボタンを押下する。
   - Scope name : `access_as_user`
   - Who can consent? : `Admins and users`
   - Admin consent display name : `QGTranslator`
   - Admin consent description : `Allow react app to access QGTranslator backend as the signed-in user`
   - User consent display name :`QGTranslator`
   - User consent description : `Allow react app to access QGTranslator backend on your behalf`
   - State : `Enabled`
6. API permissions > Configured permissions の API / Configured permissions にて、既定で Microsoft Graph API へのアクセス許可が与えられている「User.Read」の右側にある「...」を押下し、「Remove Permission」 > 「Yes, remove」を押下して、「User.Read」のアクセス許可を削除する。
7. API permissions > Configured permissions の API / Configured permissions にて、「+ Add a permission」を押下後、以下の順で操作する。
   1. 「My APIs」タブの`QGTranslator_MSAL`を選択。
   2. What type of permissions does your application require?にて「Delegated permissions」を選択。
   3. `QGTranslator`の`access_as_user`のチェックボックスを選択。
   4. Add permissions ボタンを押下。
8. Manifest から JSON 形式のマニフェストを表示し、`"accessTokenAcceptedVersion"`の値を`null`から`2`に変更する。

### 2. GitHub Actions 用サービスプリンシパルの発行

GitHub Actions から Azure リソースを環境を構築するためのサービスプリンシパル QGTranslator_Contributor を以下の手順で発行する。

1. Azure CLI にてログイン後、以下のコマンドを実行し、サービスプリンシパル`QGTranslator_Contributor`を発行する。
   ```bash
   az ad sp create-for-rbac --name QGTranslator_Contributor --role Contributor --scope /subscriptions/{サブスクリプションID}
   ```
2. 1 のコマンドを実行して得た以下の値を、それぞれ手元に控える。
   - `appId`(=クライアント ID)
   - `password`(=クライアントシークレット)
3. Azure Portal から Azure AD > App Registrations に遷移する。
4. QGTranslator_Contributor のリンク先にある Overview にある「Managed application in local directory」のリンク「QGTranslator_Contributor」を押下し、QGTranslator_Contributor のエンタープライズアプリケーションに遷移する。
5. Overview の Properties にある「Object ID」の値(=エンタープライズアプリケーションのオブジェクト ID)を手元に控える。

### 3. リポジトリのシークレット・変数設定

QuestionGPTTranslator リポジトリの Setting > Secrets And variables > Actions より、以下のシークレット・変数をすべて設定する。

#### シークレット

Secrets タブから「New repository secret」ボタンを押下して、下記の通り変数をすべて設定する。

| シークレット名                        | シークレット値                                                   |
| ------------------------------------- | ---------------------------------------------------------------- |
| AZURE_APIM_PUBLISHER_EMAIL            | API Management の発行者メールアドレス                            |
| AZURE_AD_SP_CONTRIBUTOR_CLIENT_SECRET | 2.で発行した QGTranslator_Contributor のクライアントシークレット |
| DEEPL_AUTH_KEY                        | DeepL API の認証キー                                             |
| OPENAI_API_KEY                        | 事前に作成した Azure OpenAI の API キー                          |
| TRANSLATOR_KEY                        | 事前に作成した Translator のキー                                 |

#### 変数

Variables タブから「New repository variable」ボタンを押下して、下記の通り変数をすべて設定する。

| 変数名                            | 変数値                                                                                    |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| AZURE_AD_EA_CONTRIBUTOR_OBJECT_ID | 2.で発行した QGTranslator_Contributor のエンタープライズアプリケーションのオブジェクト ID |
| AZURE_AD_SP_CONTRIBUTOR_CLIENT_ID | 2.で発行した QGTranslator_Contributor のクライアント ID                                   |
| AZURE_AD_SP_MSAL_CLIENT_ID        | 1.で発行した QGTranslator_MSAL のクライアント ID                                          |
| AZURE_SUBSCRIPTION_ID             | Azure サブスクリプション ID                                                               |
| AZURE_TENANT_ID                   | Azure ディレクトリ ID                                                                     |
| OPENAI_API_VERSION                | 事前に作成した Azure OpenAI の API バージョン                                             |
| OPENAI_DEPLOYMENT                 | 事前に作成した Azure OpenAI のデプロイ名                                                  |
| OPENAI_ENDPOINT                   | 事前に作成した Azure OpenAI のエンドポイント                                              |
| OPENAI_MODEL                      | 事前に作成した Azure OpenAI のモデル名                                                    |

### 4. インポートデータファイルの作成(TODO)

`qgtranslator-je-cosmosdb`に格納するデータは、GitHub 上で管理せず、**インポートデータファイル**と呼ぶ特定のフォーマットで記述した Typescript のソースコードを、ローカル上で管理する運用としている。
インポートデータファイルは、ローカルで git clone した QuestionGPTTranslator リポジトリ直下に`data/(コース名)/(テスト名).json`のパスでディレクトリ・json ファイルを作成する必要がある。
インポートデータファイルの json フォーマットを以下に示す。

```json
[
  {
    "subjects": ["問題文1", "https://www.example.com/aaa/xxx.png", "問題文2", ... ],
    "choices": ["選択肢1", "選択肢2", ... ],
    "communityVotes": ["回答割合1", "回答割合2", ... ],
    "indicateImgIdxes": [0, ... ],
    "indicateChoiceImgs": [null, "https://www.example.com/bbb/yyy.png", ... ],
    "escapeTranslatedIdxes": {
      "subjects": [0, ... ],
      "choices": [1, ... ],
    }
  },
  {
    "subjects": [ ... ],
    :
  },
]
```

json の各キーの説明を、以下に示す。

| キー名                    | 説明                                         | 必須指定 |
| ------------------------- | -------------------------------------------- | :------: |
| `subjects`                | 問題文/画像 URL                              |    o     |
| `choices`                 | 選択肢                                       |    o     |
| `communityVotes`          | コミュニティ回答割合                         |    o     |
| `indicateSubjectImgIdxes` | `subjects`で指定した画像 URL のインデックス  |          |
| `indicateChoiceImgs`      | `choices`の文章の後に続ける画像 URL          |          |
| `escapeTranslatedIdxes`   | 翻訳不要な`subjects`/`choices`のインデックス |          |

## Azure リソース環境構築

### 構築手順

1. QuestionGPTTranslator リポジトリの各 workflow をすべて有効化する。
2. QuestionGPTTranslator リポジトリの Actions > 左側の Create Azure Resources > 最後の実行名 の順で押下し、右上の「Re-run jobs」から「Re-run all jobs」を押下し、確認ダイアログ内の「Re-run jobs」ボタンを押下する。
3. ターミナルを起動して以下のコマンドを実行し、Azure にデプロイ済のストレージアカウントに対し、すべてのインポートデータファイルを 1 つずつ繰り返しアップロードする。
   ```bash
   az storage blob directory upload --account-name qgtranslatorjesa -c import-items -s "functions/data/*" -d . -r
   ```

### 削除手順

1. QuestionGPTTranslator リポジトリの各 workflow をすべて無効化する。
2. ターミナルを起動して以下のコマンドを実行し、リソースグループ`qgtranslator-je`を削除する。
   ```bash
   az group delete -n qgtranslator-je -y
   ```
3. 2 のターミナルで以下のコマンドを実行し、論理的に削除した`qgtranslator-je-vault`を物理的に削除する。
   ```bash
   az keyvault purge -n qgtranslator-je-vault
   ```
4. 3 のターミナルで以下のコマンドを実行し、論理的に削除した`qgtranslator-je-apim`を物理的に削除する。
   ```bash
   az rest -m DELETE -u https://management.azure.com/subscriptions/(サブスクリプションID)/providers/Microsoft.ApiManagement/locations/japaneast/deletedservices/qgtranslator-je-apim?api-version=2022-08-01
   ```

## API 追加開発時の対応

### 関数アプリ

functions/function_app.py に全エントリーポイントのブループリントを登録する。

### API Management

上記で生成した関数アプリが HTTP Trigger の場合、その関数アプリの API リファレンスである [Swagger](https://infhyroyage.github.io/QuestionGPTTranslator/) を apim/apis-functions-swagger.yaml に記述する。
API Management のデプロイは、この Swagger を使用する。

## localhost 環境構築

Azure にリソースを構築せず、localhost 上で以下のサーバーをそれぞれ起動することもできる。

| サーバー名                                     | 使用するサービス名                                                                                                 | ポート番号 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------- |
| Azure Functions(HTTP Trigger の関数アプリのみ) | [Azure Functions Core Tools](https://docs.microsoft.com/ja-jp/azure/azure-functions/functions-run-local)           | 9229       |
| Cosmos DB                                      | [Azure Cosmos DB Linux-based Emulator (preview)](https://learn.microsoft.com/ja-jp/azure/cosmos-db/emulator-linux) | 8081       |
| Blob ストレージ                                | [Azurite](https://learn.microsoft.com/ja-jp/azure/storage/common/storage-use-azurite)                              | 10000      |
| Queue ストレージ                               | [Azurite](https://learn.microsoft.com/ja-jp/azure/storage/common/storage-use-azurite)                              | 10001      |
| Table ストレージ                               | [Azurite](https://learn.microsoft.com/ja-jp/azure/storage/common/storage-use-azurite)                              | 10002      |

> [!NOTE]  
> 2024/11/24 現在、Azure Cosmos DB Linux-based Emulator (preview)は複合インデックスのインデックスポリシーがサポートされていないため、Azure Cosmos DB と一部のインデックスポリシーが異なる。

> [!TIP]  
> localhost 環境構築後、ブラウザから [データエクスプローラー](http://localhost:1234) にアクセスすると、Cosmos DB 内のデータを GUI で参照・更新できる。

### 構築手順

1. 以下をすべてインストールする。
   - Azure Functions Core Tools
   - Docker
   - Python 3.11
2. 以下を記述したファイル`local.settings.json`を QuestionGPTTranslator リポジトリの functions ディレクトリ配下に保存する。
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "COSMOSDB_KEY": "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
       "COSMOSDB_READONLY_KEY": "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
       "COSMOSDB_URI": "http://localhost:8081",
       "DEEPL_AUTH_KEY": "(Azureリソース環境構築時にGitHubへ登録したシークレットDEEPL_AUTH_KEYの値)",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "NODE_TLS_REJECT_UNAUTHORIZED": "0",
       "OPENAI_API_KEY": "(Azureリソース環境構築時にGitHubへ登録したシークレットOPENAI_API_KEYの値)",
       "OPENAI_API_VERSION": "(Azureリソース環境構築時にGitHubへ登録した変数OPENAI_API_VERSIONの値)",
       "OPENAI_DEPLOYMENT": "(Azureリソース環境構築時にGitHubへ登録した変数OPENAI_DEPLOYMENTの値)",
       "OPENAI_ENDPOINT": "(Azureリソース環境構築時にGitHubへ登録した変数OPENAI_ENDPOINTの値)",
       "OPENAI_MODEL": "(Azureリソース環境構築時にGitHubへ登録した変数OPENAI_MODELの値)",
       "PYTHON_PATH": "./venv/bin/python",
       "TRANSLATOR_KEY": "(Azureリソース環境構築時にGitHubへ登録したシークレットTRANSLATOR_KEYの値)"
     },
     "Host": {
       "CORS": "*",
       "LocalHttpPort": 9229
     },
     "ConnectionStrings": {}
   }
   ```
   - CORS は任意のオリジンを許可するように設定しているため、特定のオリジンのみ許可したい場合は`Host` > `CORS`にそのオリジンを設定すること。
3. ターミナルを起動して以下のコマンドを実行し、Cosmos DB、Blob/Queue/Table ストレージをすべて起動する。実行したターミナルはそのまま放置する。
   ```bash
   docker compose up
   ```
   実行後、以下の標準出力が表示されるまで待機する。
   ```
   localcosmosdb     | Started
   ```
4. 3 とは別のターミナルで以下のコマンドを実行し、Python3.11 の仮想環境を作成・有効化し、PyPI パッケージをインストールする。
   ```bash
   python3.11 -m venv venv
   ./venv/Scripts/activate
   pip install -r requirements.txt
   ```
5. 4 と同じターミナルで以下のコマンドを実行し、Azure Functions を起動する。実行したターミナルはそのまま放置する。
   ```bash
   cd functions
   func start --verbose
   ```
6. 5 とは別のターミナルで以下のコマンドを実行し、4 で作成した仮想環境の有効後、起動した Cosmos DB サーバーに対し、インポートデータファイルからインポートする。
   ```bash
   ./venv/Scripts/activate
   python functions/import_local.py
   ```
   - タイムアウトなどで失敗した場合、もう一度実行し直すこと。

### 削除手順

1. 構築手順の 5 で起動した Azure Functions のターミナルに対して Ctrl+C キーを入力し、起動した Azure Functions を停止する。
2. ターミナルを起動して以下のコマンドを実行し、構築手順の 3 で起動した Cosmos DB、Blob/Queue/Table ストレージをすべて停止する。
   ```bash
   docker compose down
   ```

## 完全初期化

初期構築以前の完全なクリーンな状態に戻すためには、初期構築で行ったサービスプリンシパル・シークレット・変数それぞれを以下の順で削除すれば良い。

1. リポジトリの各シークレット・変数の削除
2. GitHub Actions 用サービスプリンシパルの削除
3. Azure AD 認証認可用サービスプリンシパルの削除

### 1. リポジトリのシークレット・変数の削除

QuestionGPTTranslator リポジトリの Setting > Secrets And variables > Actions より、Secrets・Variables タブから初期構築時に設定した各シークレット・変数に対し、ゴミ箱のボタンを押下する。

### 2. GitHub Actions 用サービスプリンシパルの削除

1. Azure Portal から Azure AD > App Registrations に遷移する。
2. QGTranslator_Contributor のリンク先にある Delete ボタンを押下し、「I understand the implications of deleting this app registration.」のチェックを入れて Delete ボタンを押下する。

### 3. Azure AD 認証認可用サービスプリンシパルの削除

1. Azure Portal から Azure AD > App Registrations に遷移する。
2. QGTranslator_MSAL のリンク先にある Delete ボタンを押下し、「I understand the implications of deleting this app registration.」のチェックを入れて Delete ボタンを押下する。
