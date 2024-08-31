# QuestionGPTTranslator

[![Create Azure Resources](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/create-azure-resources.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/create-azure-resources.yaml)
[![Deploy API Management](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-apim.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-apim.yaml)
[![Deploy Azure Functions Application](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-functions-app.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-functions-app.yaml)
[![Deploy to Swagger UI](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-swagger-ui.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/deploy-swagger-ui.yaml)
[![Regenerate Secrets](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/regenerate-secrets.yaml/badge.svg)](https://github.com/infhyroyage/QuestionGPTTranslator/actions/workflows/regenerate-secrets.yaml)

## 概要

[QuestionAnswerPortal](https://github.com/infhyroyage/QuestionAnswerPortal)の API サーバーを構成する。

## アーキテクチャー図

![architecture.drawio](architecture.drawio.svg)

| Azure リソース名           | 概要                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------ |
| `qgtranslator-je-apim`     | ユーザー/App Service からアクセスする API Management                                                   |
| `qgtranslator-je-func`     | API Management からアクセスする Functions                                                              |
| `qgtranslator-je-funcplan` | Functions のプラン                                                                                     |
| `qgtranslatorjesa`         | Functions から参照するストレージアカウント                                                             |
| `qgtranslator-je-cosmosdb` | Functions からアクセスする Cosmos DB                                                                   |
| `qgtranslator-je-vault`    | シークレットを管理する Key Vault                                                                       |
| `qgtranslator-je-insights` | App Service/API Management/Functions を一括で監視する Application Insights                             |
| `(Your Own OpenAI)`        | Functions からアクセスする OpenAI                                                                      |
| `(Your Own Translator)`    | Functions からアクセスする事前に作成した Translator(枠を使い切った場合は代わりに DeepL へアクセスする) |

## 使用する主要なパッケージのバージョン

| 名称                      | バージョン |
| ------------------------- | ---------- |
| Python                    | 3.11       |
| OpenAI Python API library | 1.42.0     |

上記以外のパッケージは、dependabot によってバージョン管理している。

---

Python 3.11 をインストール後、以下を実行。

```
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
```

サービスプリンシパルを作成。

```
az ad sp create-for-rbac --name QGTranslator_Contributor --role Contributor --scope /subscriptions/{サブスクリプション ID}
```
