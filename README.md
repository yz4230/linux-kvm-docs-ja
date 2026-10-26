# 仮想化ドキュメント日本語訳（Linux カーネル `Documentation/virt`）

Linux カーネルの `Documentation/virt/` を日本語訳し、Sphinx で HTML を生成して Cloudflare Pages で公開している。

- 公開サイト: <https://linux-kvm-docs-ja.pages.dev/>
- 翻訳の底本: Linux カーネル コミット `6b4b543fa187` の `Documentation/virt/`
- 訳出範囲: `virt/kvm/`（RST 45 ファイル、約 18,200 行）と `virt/index.rst`・`paravirt_ops`・`guest-halt-polling`・`ne_overview`・`acrn/`・`coco/`（10 ファイル、約 730 行）
- 未訳: `virt/uml/`（1,294 行）と `virt/hyperv/`（1,699 行）。KVM とは別系統のため対象外

## 構成

| パス | 説明 |
|---|---|
| `source/` | 訳文。底本の `Documentation/virt/` と同じ木構成 |
| `source/index.rst` | サイトの入口。底本の `virt/index.rst` |
| `source/kvm/api.rst` | `virt/kvm/api.rst`（底本 9,812 行）の全訳。底本では 16 分割して並列翻訳し、再結合した |
| `conf.py` | Sphinx 設定。テーマは `sphinx_rtd_theme`、言語は `ja` |
| `tools/` | 後処理と検証のスクリプト（下記） |
| `TRANSLATION-GUIDE.md` | 訳語集と文体の規則。訳文を直すときの基準 |

## ビルド

```sh
uv venv --python 3.12
uv pip install sphinx sphinx-rtd-theme
.venv/bin/python -m sphinx -b html -c . source build/html
.venv/bin/python tools/make_redirects.py     # build/html/_redirects を生成
```

`build/html/index.html` を開くと読める。

## 検証

| コマンド | 内容 |
|---|---|
| `tools/check.py` | 底本と訳文の構造を比較する。見出し数、`.. _label:` アンカー、ディレクティブ、コード行、未処理の Markdown フェンス |
| `tools/prepare.py` | `chunks/` の `api_*.rst` を `source/kvm/api.rst` に結合し、見出し下線の長さを整える（冪等） |
| `tools/normalize_keys.py` | RST フィールドキーの表記を英語に統一し、底本と突き合わせる（冪等） |
| `tools/fixups.py` | 底本ごとに異なるキー表記（`:Architecture:` と `:Architectures:`、`Where:` と `where:` など）を個別に合わせる |
| `tools/repair_api.py` | `check.py` が見つけた `api.rst` の欠落コードブロックを原文どおり復元する |
| `tools/make_redirects.py` | `virt/` への構成変更で移動した URL の 301 リダイレクトを生成する |

`tools/check.py` は底本と訳文のコード行を突き合わせる。`-EBUSY ...` のような字下げされた散文は訳出対象なので、残る差分は既知の誤検出である。

## 翻訳の方針

`TRANSLATION-GUIDE.md` にまとめている。要点は次のとおり。

- コードブロック、識別子、定数、`:ref:` のリンク先、ディレクティブ名は原文のまま
- である調で統一し、英語の直訳調を避ける
- 原文にない内容を足さず、原文の内容を落とさない

## ライセンス

底本の Linux カーネルドキュメントと同じく GPL-2.0。各ファイルの先頭に `SPDX-License-Identifier: GPL-2.0` がある。全文は `LICENSE` を参照。
