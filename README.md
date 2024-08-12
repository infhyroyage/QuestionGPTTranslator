# QuestionGPTTranslator

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
