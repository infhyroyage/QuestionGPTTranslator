# Azure 環境構築手順・削除手順

## 構築手順

### 1. Azure サブスクリプションの新規作成

当リポジトリ専用の Azure サブスクリプションを新規作成する。

1. [Azure Portal](https://portal.azure.com/) にログインし、サブスクリプションに遷移する。
2. 「+ 追加」ボタンを押下する。
3. 表示されたフォームに必要事項を入力し、「確認と作成」ボタンを押下する。
   - サブスクリプション名: 任意の名前（例: `QuestionGPTTranslator`）
   - 課金アカウント: 適切な課金アカウントを選択
   - 請求者セクション: 適切な請求者セクションを選択
   - プラン: 適切なプランを選択
4. 内容を確認し、「作成」ボタンを押下する。
5. 作成されたサブスクリプションのサブスクリプション ID を手元に控える。

### 2. Azure AD 認証認可用サービスプリンシパルの発行

新規作成した Azure サブスクリプションに対し、[Microsoft ID Platform](https://learn.microsoft.com/ja-jp/azure/active-directory/develop/v2-overview)経由で Web アプリケーションに認証認可を実現するためのサービスプリンシパル QGTranslator_MSAL を以下の手順で発行する。

1. [Azure Portal](https://portal.azure.com/)にログインし、Azure AD に遷移する。
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

### 3. GitHub Actions 用サービスプリンシパルの発行

新規作成した Azure サブスクリプションに対し、GitHub Actions から Azure リソースを環境を構築するためのサービスプリンシパル QGTranslator_Contributor を以下の手順で発行する。

1. [Azure Portal](https://portal.azure.com/)にログインし、CloudShell を起動する。
2. 以下のコマンドを実行し、サービスプリンシパル`QGTranslator_Contributor`を発行する。
   ```bash
   az ad sp create-for-rbac --name QGTranslator_Contributor --role Contributor --scope /subscriptions/{手元に控えたサブスクリプションID}
   ```
3. 2 のコマンドを実行して得た以下の値を、それぞれ手元に控える。
   - `appId`(=クライアント ID)
   - `password`(=クライアントシークレット)
4. CloudShell を閉じ、Azure AD > App Registrations に遷移する。
5. QGTranslator_Contributor のリンク先にある Overview にある「Managed application in local directory」のリンク「QGTranslator_Contributor」を押下し、QGTranslator_Contributor のエンタープライズアプリケーションに遷移する。
6. Overview の Properties にある「Object ID」の値(=エンタープライズアプリケーションのオブジェクト ID)を手元に控える。

### 4. GitHub Actions 用シークレット・変数設定

当リポジトリの Setting > Secrets And variables > Actions より、以下の GitHub Actions 用シークレット・変数をすべて設定する。

#### シークレット

Secrets タブから「New repository secret」ボタンを押下して、下記の通りシークレットをすべて設定する。

| シークレット名                        | シークレット値                                                   |
| ------------------------------------- | ---------------------------------------------------------------- |
| AZURE_APIM_PUBLISHER_EMAIL            | API Management の発行者メールアドレス                            |
| AZURE_AD_SP_CONTRIBUTOR_CLIENT_SECRET | 2.で発行した QGTranslator_Contributor のクライアントシークレット |
| DEEPL_AUTH_KEY                        | DeepL API の認証キー                                             |

#### 変数

Variables タブから「New repository variable」ボタンを押下して、下記の通り変数をすべて設定する。

| 変数名                            | 変数値                                                                                    |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| APIM_NAME                         | Azure API Management 名                                                                   |
| AZURE_AD_EA_CONTRIBUTOR_OBJECT_ID | 3.で発行した QGTranslator_Contributor のエンタープライズアプリケーションのオブジェクト ID |
| AZURE_AD_SP_CONTRIBUTOR_CLIENT_ID | 3.で発行した QGTranslator_Contributor のクライアント ID                                   |
| AZURE_AD_SP_MSAL_CLIENT_ID        | 2.で発行した QGTranslator_MSAL のクライアント ID                                          |
| AZURE_SUBSCRIPTION_ID             | 1.で新規作成した Azure サブスクリプションのサブスクリプション ID                          |
| AZURE_TENANT_ID                   | Azure ディレクトリ ID                                                                     |
| COSMOSDB_NAME                     | Azure Cosmos DB 名                                                                        |
| FUNCTIONS_NAME                    | Azure Functions 名                                                                        |
| OPENAI_API_VERSION                | Azure OpenAI の API バージョン                                                            |
| OPENAI_DEPLOYMENT_NAME            | Azure OpenAI のデプロイ名                                                                 |
| OPENAI_LOCATION                   | Azure OpenAI のリージョン                                                                 |
| OPENAI_MODEL_NAME                 | Azure OpenAI のモデル名                                                                   |
| OPENAI_MODEL_VERSION              | Azure OpenAI のモデルのバージョン                                                         |
| OPENAI_NAME                       | Azure OpenAI 名                                                                           |
| STORAGE_NAME                      | Azure ストレージアカウント名                                                              |
| TRANSLATOR_NAME                   | Azure Translator 名                                                                       |
| VAULT_NAME                        | Azure Key Vault 名                                                                        |

### 5. Azure リソースの構築

新規作成した Azure サブスクリプションに対し、[technologystack.md](technologystack.md)に記載した Azure リソースを構築する。

1. 当リポジトリの Actions > 左側の Create Azure Resources を押下する。
2. Create Azure Resources の workflow が無効化されている場合は、workflow を有効化する。
3. 右上の「Re-run jobs」から「Re-run all jobs」を押下し、確認ダイアログ内の「Re-run jobs」ボタンを押下する。

### 6. インポートデータファイルの作成・アップロード

Azure Cosmos DB に格納するデータであるインポートデータファイルを、以下の json フォーマットで`data/(コース名)/(テスト名).json`に作成する。

```json
[
  {
    "subjects": ["問題文1", "https://www.example.com/aaa/xxx.png", "問題文2", ... ],
    "choices": ["選択肢1", "選択肢2", ... ],
    "answerNum": 1,
    "indicateImgIdxes": [0, ... ],
    "indicateChoiceImgs": [null, "https://www.example.com/bbb/yyy.png", ... ],
    "escapeTranslatedIdxes": {
      "subjects": [0, ... ],
      "choices": [1, ... ],
    },
    "discussions": [
      {
        "comment": "コメント1",
        "upvotedNum": 1,
        "selectedAnswer": "選択肢1"
      },
      {
        "comment": "コメント2",
        "upvotedNum": 2,
        "selectedAnswer": "選択肢2"
      },
      :
    ]
  },
  {
    "subjects": [ ... ],
    :
  },
]
```

インポートデータファイルには、以下の属性を持つ連想配列を記載する。

| 属性名                    | 説明                                         | 必須指定 |
| ------------------------- | -------------------------------------------- | :------: |
| `subjects`                | 問題文/画像 URL                              |    o     |
| `choices`                 | 選択肢(画像 URL のみの場合は null)           |    o     |
| `answerNum`               | 回答の選択肢の個数                           |    o     |
| `indicateSubjectImgIdxes` | `subjects`で指定した画像 URL のインデックス  |          |
| `indicateChoiceImgs`      | `choices`の文章の後に続ける画像 URL          |          |
| `escapeTranslatedIdxes`   | 翻訳不要な`subjects`/`choices`のインデックス |          |
| `discussions`             | コミュニティでのディスカッション             |          |

上記の`discussions`には、以下の属性を持つ連想配列の配列を記載する。

| 属性名           | 説明                     | 必須指定 |
| ---------------- | ------------------------ | :------: |
| `comment`        | ユーザーのコメント       |    o     |
| `upvotedNum`     | 賛成票数                 |    o     |
| `selectedAnswer` | ユーザーが選択した選択肢 |          |

インポートデータファイルを作成したら、以下のコマンドを実行し、Azure Storage Account の Blob Storage にアップロードする。

```bash
az storage blob directory upload --account-name (当リポジトリの変数STORAGE_NAMEの値) -c import-items -s "functions/data/*" -d . -r
```

## 削除手順

1. 当リポジトリの各 workflow をすべて無効化する。
2. ターミナルを起動して以下のコマンドを実行し、リソースグループ`qgtranslator-je`を削除する。
   ```bash
   az group delete -n qgtranslator-je -y
   ```
3. 2 のターミナルで以下のコマンドを実行し、論理的に削除した Azure Key Vault を物理的に削除する。
   ```bash
   az keyvault purge -n (当リポジトリの変数VAULT_NAMEの値)
   ```
4. 3 のターミナルで以下のコマンドを実行し、論理的に削除した Azure API Management を物理的に削除する。
   ```bash
   az rest -m DELETE -u "https://management.azure.com/subscriptions/(手元に控えたサブスクリプションID)/providers/Microsoft.ApiManagement/locations/japaneast/deletedservices/(当リポジトリの変数APIM_NAMEの値)?api-version=2022-08-01"
   ```
5. 4 のターミナルで以下のコマンドを実行し、論理的に削除した Azure Translator を物理的に削除する。
   ```bash
   az resource delete --ids /subscriptions/{手元に控えたサブスクリプションID}/providers/Microsoft.CognitiveServices/locations/japaneast/resourceGroups/qgtranslator-je/deletedAccounts/(当リポジトリの変数TRANSLATOR_NAMEの値)
   ```
6. 5 のターミナルで以下のコマンドを実行し、論理的に削除した Azure OpenAI を物理的に削除する。
   ```bash
   az resource delete --ids /subscriptions/{手元に控えたサブスクリプションID}/providers/Microsoft.CognitiveServices/locations/(当リポジトリの変数OPENAI_LOCATIONの値)/resourceGroups/qgtranslator-je/deletedAccounts/(当リポジトリの変数OPENAI_NAMEの値)
   ```
7. 当リポジトリの Setting > Secrets And variables > Actions より、Secrets・Variables タブから初期構築時に設定した各シークレット・変数に対し、ゴミ箱のボタンを押下する。
8. [Azure Portal](https://portal.azure.com/) にログインし、Azure AD > App Registrations に遷移後、QGTranslator_Contributor のリンク先にある Delete ボタンを押下し、「I understand the implications of deleting this app registration.」のチェックを入れて Delete ボタンを押下する。
9. 8 に続けて、QGTranslator_MSAL のリンク先にある Delete ボタンを押下し、「I understand the implications of deleting this app registration.」のチェックを入れて Delete ボタンを押下する。
10. 構築手順の 1.で新規作成した Azure サブスクリプションを選択後、上部メニューから Delete ボタンを押下し、サブスクリプション名を入力し、Delete ボタンを押下する。
