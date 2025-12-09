# 技術スタック

## 1. 要件と概要

### 1.1 要件

生成 AI を活用した、英語の IT 資格試験問題の学習支援システムのバックエンドを提供する。

### 1.2 ソリューション概要

Azure Functions をベースとしたサーバーレスアプリケーションにより、Azure OpenAI・Azure Translator を活用した多言語対応の学習プラットフォームを構築する。Azure API Management を通じてセキュアな API アクセスを提供し、Azure Cosmos DB で学習データと進捗を管理することで、スケーラブルかつ高可用性な学習環境を実現する。

### 1.3 データフロー

システム全体の処理フローは以下の通りである:

1. ユーザーがインポートデータファイルを Azure Blob Storage にアップロードし、Azure Storage Blob トリガーの関数アプリが Azure Cosmos DB にテスト・問題のデータをインポートする。
2. 関数アプリが API Management 経由で問題・選択肢を取得し、Azure Translator で翻訳を実行する。
3. Azure OpenAI が正解の選択肢と各選択肢の正解/不正解理由を生成し、Azure Storage Queue トリガーの関数アプリが Azure Cosmos DB に非同期で保存する。
4. Azure OpenAI がコミュニティのディスカッションの内容要約や回答投票割合を計算し、Azure Storage Queue トリガーの関数アプリが Azure Cosmos DB に非同期で保存する。
5. 関数アプリが回答履歴・お気に入り情報を Azure Cosmos DB で管理する。

## 2. アーキテクチャ

### 2.1 使用サービス

#### Azure サービス

本システムでは、以下の Azure サービスを利用して、スケーラブルかつ耐障害性の高いアーキテクチャを構築する:

- Azure API Management (API バージョン管理・認証・ルーティング)
- Azure Functions (サーバーレスアプリケーションロジック)
- Azure Storage Account
  - Blob Storage (インポートデータファイル格納)
  - Queue Storage (非同期処理メッセージキュー)
- Azure Cosmos DB (NoSQL データベース・学習データ管理)
- Azure Key Vault (シークレット・API キー管理)
- Azure Application Insights (ログ記録・モニタリング)
- Azure OpenAI (AI モデル・正解解説生成・ディスカッション要約)
- Azure Translator (翻訳サービス)

#### 外部サービス

Azure 以外の外部サービスとも連携することにより、コア機能を実現する:

- GitHub (コードリポジトリ、CI/CD パイプライン管理)
- Microsoft ID Platform (Entra ID 認証・アクセストークン発行)

### 2.2 Azure リソース構成

以下の表は、本システムで使用する主要な Azure リソースとその役割を示している:

| Azure リソース名           | Azure サービス             | 概要                                                     | リージョン     |
| -------------------------- | -------------------------- | -------------------------------------------------------- | -------------- |
| (ユーザー指定)             | Azure API Management       | ユーザーからアクセスする API Management                  | japaneast      |
| (ユーザー指定)             | Azure Functions            | API Management からアクセスする Functions                | japaneast      |
| `qgtranslator-je-funcplan` | Azure App Service Plan     | Functions のプラン                                       | japaneast      |
| (ユーザー指定)             | Azure Storage Account      | Functions から参照するストレージアカウント               | japaneast      |
| (ユーザー指定)             | Azure Cosmos DB            | Functions からアクセスする Cosmos DB                     | japaneast      |
| (ユーザー指定)             | Azure Key Vault            | シークレットを管理する Key Vault                         | japaneast      |
| `qgtranslator-je-insights` | Azure Application Insights | API Management/Functions を監視する Application Insights | japaneast      |
| (ユーザー指定)             | Azure OpenAI               | Functions からアクセスする Azure OpenAI                  | (ユーザー指定) |
| (ユーザー指定)             | Azure Translator           | Functions からアクセスする Translator                    | japaneast      |

> [!WARNING]  
> Azure OpenAI は、以下をすべてサポートする場所・モデル名・モデルバージョン・API バージョンを使用する必要がある。
>
> - [Structured outputs](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/structured-outputs)
> - [Vision-enabled](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/gpt-with-vision)

### 2.3 Azure アーキテクチャー図

以下の図は、システム全体のアーキテクチャを示している:

![architecture.drawio](architecture.drawio.svg)

## 3. コア機能の実装詳細

### 3.1 インポートデータファイルによるテスト・問題データのインポート機能

Azure Cosmos DB に格納するデータは、**インポートデータファイル**とよばれる json ファイル`data/(コース名)/(テスト名).json`として管理する:
インポートデータファイルの json フォーマットを以下に示す。

```json
[
  {
    "subjects": ["問題文1", "https://www.example.com/aaa/xxx.png", "問題文2", ... ],
    "choices": ["選択肢1", "選択肢2", ... ],
    "answerNum": 1,
    "indicateSubjectImgIdxes": [0, ... ],
    "indicateChoiceImgs": [null, "https://www.example.com/bbb/yyy.png", ... ],
    "escapeTranslatedIdxes": {
      "subjects": [0, ... ],
      "choices": [1, ... ],
    },
    "discussions": [
      {
        "comment": "コメント1",
        "upvotedNum": 2,
        "selectedAnswer": "A"
      },
      {
        "comment": "コメント2",
        :
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

json の各キーの説明を、以下に示す。

| キー名                    | 説明                                         | 必須指定 |
| ------------------------- | -------------------------------------------- | :------: |
| `subjects`                | 問題文/画像 URL                              |    o     |
| `choices`                 | 選択肢                                       |    o     |
| `answerNum`               | 回答の選択肢の個数                           |    o     |
| `indicateSubjectImgIdxes` | `subjects`で指定した画像 URL のインデックス  |          |
| `indicateChoiceImgs`      | `choices`の文章の後に続ける画像 URL          |          |
| `escapeTranslatedIdxes`   | 翻訳不要な`subjects`/`choices`のインデックス |          |
| `discussions`             | コミュニティでのディスカッション             |          |

`discussions`キーで配列で設定する連想配列の各キーの説明を、以下に示す。

| キー名           | 説明                     | 必須指定 |
| ---------------- | ------------------------ | :------: |
| `comment`        | ユーザーのコメント       |    o     |
| `upvotedNum`     | 賛成票数                 |    o     |
| `selectedAnswer` | ユーザーが選択した選択肢 |          |

インポートデータファイルに記載したテスト・問題のデータは、Azure 環境では Blob Storage に`import-items/{courseName}/{testName}.json` パスでアップロードすることで、データインポートされる。そのアップロードをもとに、Azure Storage Blob トリガーの関数アプリが Azure Cosmos DB にテスト・問題のデータを非同期でインポートする。

また、ローカル環境では専用のインポート処理を行う Python ファイル `functions/import_local.py`を実行することで、データインポートされる。

### 3.2 Azure OpenAI による正解・解説・ディスカッション要約の生成

Azure OpenAI を用いて、問題文や選択肢の文章から正解の選択肢・解説(正解/不正解の理由)、およびコミュニティの各コメントから要約を生成する。Azure OpenAI では Vision-enabled をサポートするモデルの使用を必須としているため、問題文や選択肢に画像が含まれていても適切に生成できる。

また、Azure OpenAI を実行して正解の選択肢、解説(正解/不正解の理由)、コミュニティの各コメントの要約を生成する関数アプリは、関数アプリの実行時間が長くなるため、生成直後に生成結果を Azure Cosmos DB に保存しておくことで、同じ入力パラメーターで関数アプリ再実行した際にわざわざ Azure OpenAI を実行せずに Azure Cosmos DB に保存した生成結果をそのまま出力する仕組みを採用する。
これにより、実行時間の短縮と、Azure OpenAI の利用料金の削減を実現する。
なお、この Azure Cosmos DB への保存処理は、関数アプリが Queue Storage にメッセージを送信し、Azure Storage Queue トリガーの関数アプリが非同期で保存する。

### 3.3 日本語翻訳システム

翻訳機能は Azure Translator (Standard Tier) を使用する。
インポートデータファイルで問題文・選択肢ごとに `isEscapedTranslation` フラグを設定すると、翻訳不要な文章(コマンド、コード等)をスキップすることができる。
