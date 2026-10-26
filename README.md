# KVM ドキュメント日本語訳

Linux カーネルの `Documentation/virt/kvm/` 配下を日本語訳したものです。Sphinx で HTML を生成し、Cloudflare Pages で公開しています。

- 公開サイト: <https://linux-kvm-docs-ja.pages.dev/>
- 翻訳の底本: Linux カーネル コミット `6b4b543fa187` の `Documentation/virt/kvm/`（RST 45 ファイル、約 18,200 行）

## 内容

| パス | 説明 |
|---|---|
| `source/` | 翻訳済みの reStructuredText。底本と同じディレクトリ構成 |
| `source/api.rst` | `Documentation/virt/kvm/api.rst`（底本 9,812 行）の全訳 |
| `conf.py` | Sphinx 設定。テーマは `sphinx_rtd_theme`、言語は `ja` |
| `tools/` | 翻訳後の後処理と検証に使ったスクリプト |
| `TRANSLATION-GUIDE.md` | 訳語集と文体の規則。訳文を直すときの基準 |

## ビルド

```sh
uv venv --python 3.12
uv pip install sphinx sphinx-rtd-theme
.venv/bin/python -m sphinx -b html -c . source build/html
```

`build/html/index.html` を開くと読めます。

## 検証

```sh
.venv/bin/python tools/check.py          # 底本と構造を比較（見出し数・アンカー・コード行）
.venv/bin/python tools/prepare.py        # 見出し下線の長さを整える（冪等）
.venv/bin/python tools/normalize_keys.py # RST フィールドキーの表記を統一（冪等）
```

`tools/check.py` は底本と訳文のコード行を突き合わせます。`-EBUSY ...` のような字下げされた散文は訳出対象なので、残る差分は既知の誤検出です。

## 翻訳の方針

`TRANSLATION-GUIDE.md` にまとめている。要点は次のとおり。

- コードブロック、識別子、定数、`:ref:` のリンク先、ディレクティブ名は原文のまま
- である調で統一し、英語の直訳調を避ける
- 原文にない内容を足さず、原文の内容を落とさない

## ライセンス

底本の Linux カーネルドキュメントと同じく GPL-2.0 です。各ファイルの先頭に `SPDX-License-Identifier: GPL-2.0` があります。全文は `LICENSE` を参照してください。
