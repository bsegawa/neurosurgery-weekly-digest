# Neurosurgery Weekly Digest

PubMedから直近の脳神経外科論文を検索し、重要度と臨床的有用性から約10報を選び、
日本語要約・Visual構造化サマリを静的Webページとして公開してLINEへ通知する仕組みです。

## 動作

- 毎週金曜日 10:00（日本時間）にGitHub Actionsを実行
- 脳血管障害、脳腫瘍、脊椎・脊髄、外傷、機能的脳神経外科、小児・先天性、その他を横断検索
- PubMed抄録を根拠に選定・要約（抄録にない情報は補完しません）
- 元論文、DOI、PubMed、PubMed Centralへのリンクを表示
- GitHub Pagesに最新号とバックナンバーを保存
- LINE Messaging APIのプッシュメッセージで最新号を通知

## 必要なGitHub Secrets

Repositoryの `Settings` → `Secrets and variables` → `Actions` で登録します。

| 名前 | 内容 |
|---|---|
| `OPENAI_API_KEY` | OpenAI APIキー |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging APIのチャネルアクセストークン |
| `LINE_USER_ID` | LINE Developersの「あなたのユーザーID」 |

秘密情報をソースコード、Issue、チャット、ログへ貼り付けないでください。

任意のRepository Variable:

| 名前 | 既定値 | 用途 |
|---|---:|---|
| `OPENAI_MODEL` | `gpt-5.4-mini` | 要約モデル |
| `DIGEST_PAPER_COUNT` | `10` | 掲載論文数 |
| `PUBMED_LOOKBACK_DAYS` | `8` | PubMed検索期間 |
| `NCBI_EMAIL` | 空 | NCBIへ通知する連絡先 |

## 初期設定

1. このリポジトリをpublicで作成します（掲載内容に個人情報・患者情報は含めません）。
2. `Settings` → `Pages` → `Build and deployment` のSourceを `GitHub Actions` にします。
3. 上記3つのSecretsを登録します。
4. `Actions` → `Weekly neurosurgery digest` → `Run workflow` を実行します。
5. テスト配信と公開ページを確認します。

定期実行は `.github/workflows/weekly-digest.yml` のUTC cronで行います。
日本標準時には夏時間がないため、金曜10:00 JSTは金曜01:00 UTCです。

## ローカル確認

秘密情報なしでデモページを生成できます。

```bash
python -m src.main --demo
python -m unittest discover -s tests -v
```

## 注意

要約は原則としてPubMedに収載されたタイトル・書誌情報・抄録のみを根拠にAI生成します。
診療判断の代替ではありません。必ず原著本文、ガイドライン、添付文書等を確認してください。

