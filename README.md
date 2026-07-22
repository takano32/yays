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

## Wayback Machine からの復元 (2026-07-23)

ライブサーバー上で既に消失していたコンテンツ(HTTP 200 で BiG-NET の広告テンプレート
= soft-404 が返る状態)を、Wayback Machine の全キャプチャ(CDX API で列挙した
5,047 URL)から復元した。**回収成功 4,921 件(97.5%)**。

| セクション | 内容 | 復元数 |
|---|---|---:|
| `library/novel/` | 小説ライブラリ(投稿作品含む) | 1,400+ |
| `cgi-bin/resbbs4a/` | 感想掲示板 全スレッド・画像 | 1,500+ |
| `cgi-bin/noteky/` | メモ帳 BBS 全投稿・一覧 | 1,150+ |
| `cgi-bin/paintbbs*/` | お絵かき BBS | 280+ |
| `cgi-bin/newinfo/` | 萌え暦エントリ | 200+ |
| `reviews/` | 未リンクのレビューコーナー | 12(完全) |
| その他 | 特別企画・ギャラリー欠損分ほか | 100+ |

- スナップショットは 2019 年以前(soft-404 化以前)を優先し、取得後に汚染マーカー検査
- CGI のクエリ付き URL は `?`→`_` `&`→`_` `=`→`-` でファイル名化し、参照リンクも書き換え済み
- 復元不能はアーカイブ自体が soft-404 汚染の 94 件+Wayback ストレージ側の恒常的エラー 33 件のみ
- 残存するリンク切れの大半は「どこにも現存しない BBS 画面(未アーカイブのクエリビュー)」への参照

## tools/

ミラー作成・復元・検証に使ったスクリプト一式(再取得や監査に使用可能)。

- `postprocess.sh` — 文字コード検出・UTF-8 変換・meta 書き換え
- `rename_query_files.py` — `?` 付きファイル名の正規化と参照書き換え
- `gapfill.py` — ミラーから参照されているのにローカルに無いファイルをライブから補完
- `relativize.py` — オリジンへの絶対 URL をローカル相対パスへ変換
- `linkaudit.py` — リンク切れ・オリジン絶対 URL・外部リンクの監査
- `wayback_recover3.py` — Wayback CDX 列挙+並列復元(レジューム可能、要 `~/.cache/yays-recovery/` の CDX 索引)
- `fix_query_links.py` — 復元したクエリ URL への参照をサニタイズ済みファイル名へ書き換え
- `fix_rootrel.py` — ルート相対リンク(`/~yays/...`)の修正

## archive-meta/

復元の来歴データ(検証・再取得用)。

- `wayback-provenance.jsonl` — 復元した全ファイルの出典記録(Wayback タイムスタンプ・元 URL・保存先パス・成否)。1 行 1 URL
- `cdx_all.txt` — CDX API で列挙した `~yays/` 配下の全アーカイブ URL(ユニーク 5,428 件)
- `cdx_snapshots.txt` — 全 200 キャプチャの索引(29,831 レコード)。`tools/wayback_recover3.py` の入力
