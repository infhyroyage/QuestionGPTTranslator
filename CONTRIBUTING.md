# Contribution Guide

## 開発ツール

本システムの開発には、以下のツールとテクノロジーを使用する:

- Python 3.12 (プログラミング言語)
- Azure Functions Core Tools (ローカルテストとデプロイ)
- Docker/Docker Compose (ローカル開発環境構築)
- coverage (ユニットテスト・カバレッジ測定)
- pylint (コード静的解析)
- Swagger/OpenAPI 3.0 (API ドキュメント管理)

## ローカル開発環境のセットアップ

[localenvironment.md](localenvironment.md) 参照。

## 開発時の実装規則

コード品質と一貫性を確保するため、以下の実装規則に従う:

- ほとんどのインフラストラクチャは Infrastructure as Code (IaC) で管理し、手動構成は行わない。本システムでは、Azure Bicep テンプレートで以下の Azure リソースを定義する:
  - Azure API Management
  - Azure Functions・App Service Plan
  - Azure Storage Account (Blob Storage・Queue Storage)
  - Azure Cosmos DB
  - Azure Key Vault
  - Azure Application Insights
  - Azure OpenAI
  - Azure Translator
- 関数アプリの各エントリーポイントは、functions/function_app.py にブループリントを登録する。
- 関数アプリは、functions/src ディレクトリに個別ファイルで実装する。
- 関数アプリ間で共通する処理は functions/util ディレクトリにユーティリティ関数として実装する。
- 関数アプリで使用する以下の型定義は、 functions/type ディレクトリ配下に Pydanticm モデルとして定義する。
  - API リクエストデータ： functions/type/request.py
  - API レスポンスデータ： functions/type/response.py
  - Azure Cosmos DB のドキュメント構造： functions/type/cosmos.py
  - Azure OpenAI Structured Outputs： functions/type/structured.py
- 関数アプリの Python のユニットテストは functions/tests に実装し、stmt のカバレッジ率 80%以上をみたすようにして、コード品質を担保する。ユニットテストは、以下のコマンドで実行する。
  ```bash
  cd functions && coverage run -m unittest discover -s tests && coverage report -m && cd ..
  ```
- 関数アプリは Python を用いてコーディングし、.pylintrc に記載した例外を除き、必ず Pylint の警告・エラーをすべて解消するように、コード品質を担保する。Pylint の静的解析は、以下のコマンドで実行する。
  ```bash
  pylint functions/**/*.py
  ```
- HTTP Trigger 関数の関数アプリの API リファレンスは Swagger ファイルとして、基本的に apim/apis-functions-swagger.yaml で管理する。ただし、ヘルスチェック API のみ認証処理を行わないため、別の Swagger ファイル apim/apis-healthcheck-functions-swagger.yaml で管理する。
  - API Management のデプロイは、これらの Swagger ファイルをインポートする。
- Microsoft ID Platform で Entra ID で認証して発行したアクセストークン(JWT)は、`X-User-Id` ヘッダーに設定された状態で Azure API Management のポリシー設定により検証される。
- Azure Cosmos DB には強い整合性を採用して、確実な重複防止を保証する。
- Azure OpenAI は、以下の機能を利用する。
  - Structured Outputs
  - Vision-enabled
- 長い実行時間を要求される生成 AI の処理が含まれている API には、Queue Storage キュートリガー関数にて Azure Cosmos DB に保存する非同期処理を採用する。
- 英語 → 日本語の翻訳システムは、Azure Translator(無料枠)をプライマリ、無料枠の超過分を DeepL API でセカンダリとして採用する。
- 以下の CI/CD パイプラインは GitHub Actions によって自動化する:
  - 全 Azure リソースデプロイ: .github/workflows/create-azure-resources.yaml
  - Functions アプリのみのデプロイ: .github/workflows/deploy-functions-app.yaml
  - API Management のみのデプロイ: .github/workflows/deploy-apim.yaml
  - apim/apis-functions-swagger.yaml の Swagger UI デプロイ: .github/workflows/deploy-swagger-ui.yaml
  - シークレット日次再発行: .github/workflows/regenerate-secrets.yaml
  - Pull Request 発行時のユニットテスト・Pylint 実行: .github/workflows/test-lint.yaml

## 新しい機能の追加手順

### API エンドポイントの新設

1. functions/src に関数ファイルを新設
2. functions/function_app.py にブループリント登録
3. apim/apis-functions-swagger.yaml に API 定義追加
4. functions/type に型定義を追加
5. functions/tests にユニットテストを追加

### CosmosDB コンテナーの新設

1. functions/type/cosmos.py に Azure 環境用の型定義を追加
2. functions/util/local.py にローカル環境用の型定義を追加
3. functions/tests にユニットテストを追加

## コミット・プルリクエストのワークフロー

### セキュリティ上の制約事項

以下の機密情報は Azure Key Vault で安全に管理するため、リポジトリにコミットしないこと:

- Azure OpenAI の API キー
- Azure Translator・DeepL API の API キー
- Azure Cosmos DB の API キー

また、以下のファイルはローカル環境で管理するため、リポジトリにコミットしないこと:

- local.settings.json (ローカル開発時の関数アプリの環境変数)
- インポートデータファイル (`data/(コース名)/(テスト名).json`)

### プルリクエストの要件

プルリクエスト作成時は以下をすべて満たすこと:

- [ ] 以下のコマンドを実行して、すべてのユニットテストが成功し、カバレッジを 80% 以上にする:
  ```bash
  cd functions && coverage run -m unittest discover -s tests && coverage report -m && cd ..
  ```
- [ ] 以下のコマンドを実行して、Pylint の警告・エラーをすべて解消する:
  ```bash
  pylint functions/**/*.py
  ```
- [ ] ターゲットを main ブランチに設定している。

## Python の依存関係管理

本システムでは、セキュリティの脆弱性や新機能に対応するように定期的にパッケージのバージョンアップを自動的に提案する GitHub の機能である GitHub Dependabot を使用して、Python パッケージの依存関係を `requirements.txt` として管理する。
GitHub Dependabot は以下の実行方式に従い、`.github/dependabot.yaml`で管理する:

- **実行スケジュール**: 毎週月曜日 10:00 (Asia/Tokyo)
- **対象ファイル**: `requirements.txt`
- **更新方式**: プルリクエストによる自動提案
- **特別な制約**: `openai` パッケージは破壊的変更が多いため、管理対象外
