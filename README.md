# 八重洲メディアリサーチ (YAYS Media Research) — サイトアーカイブ

<https://www14.big.or.jp/~yays/> の静的ミラーです。GitHub Pages でそのまま表示できる形に整えてあります。

- 取得日: 2026-07-22
- 取得方法: `wget --mirror --page-requisites --convert-links --adjust-extension --no-iri` + 補完クロール(`tools/gapfill.py`)

## 公開手順 (GitHub Pages)

1. GitHub にこのリポジトリを push する
2. リポジトリの **Settings → Pages → Build and deployment**
   - Source: **Deploy from a branch**
   - Branch: **master** / **/(root)**
3. 数分後に `https://<ユーザー名>.github.io/<リポジトリ名>/` で公開される

## 原本からの変更点

忠実な表示のために最小限の機械的変換のみ行っています。

| 変更 | 理由 |
|---|---|
| Shift_JIS / EUC-JP / ISO-2022-JP → UTF-8 変換(`meta charset` も書き換え) | GitHub Pages は HTTP ヘッダで `charset=utf-8` を強制するため、変換しないと文字化けする |
| `noteky.cgi?c=...` 形式のファイル名 8 件を `?` `&` `=` を除いた名前にリネーム(参照リンクも書き換え) | `?` 付きファイル名は GitHub Pages で配信できない |
| ローカルに実体があるページへの絶対 URL (`http://www14.big.or.jp/~yays/...`) を相対パスに変換 | アーカイブ内で完結して閲覧できるようにするため |
| `.nojekyll` を追加 | Jekyll の処理をスキップし、全ファイルをそのまま配信するため |

以下は原本のまま残しています。

- 元サイト時点で既にリンク切れだったリンク(旧ギャラリーページ、`albumbbs.cgi` など)
- 外部サイトへのリンク(livedoor Blog、ts.novels.jp など)
- アクセスカウンター等、原サーバーの CGI への参照(原サーバー稼働中は動作)
- コメントアウトされた非表示コンテンツ(ライブに実在したものは合わせて回収済み)

## tools/

ミラー作成・検証に使ったスクリプト一式(再取得や監査に使用可能)。

- `postprocess.sh` — 文字コード検出・UTF-8 変換・meta 書き換え
- `rename_query_files.py` — `?` 付きファイル名の正規化と参照書き換え
- `gapfill.py` — ミラーから参照されているのにローカルに無いファイルをライブから補完
- `relativize.py` — オリジンへの絶対 URL をローカル相対パスへ変換
- `linkaudit.py` — リンク切れ・オリジン絶対 URL・外部リンクの監査
