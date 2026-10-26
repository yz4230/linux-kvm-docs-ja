# KVM ドキュメント日本語訳ガイド（全エージェント共通）

## 目的
Linux カーネルの `Documentation/virt/kvm/` 配下の reStructuredText (RST) を、日本のカーネル開発者が読んで違和感のない技術文書として日本語訳する。

## 大原則
1. **原文にない内容を足さない。** 事実・数値・条件・評価を補わない。確信の度合いも変えない（"may" → 「かもしれない」、"must" → 「〜しなければならない」、"should" → 「〜すべき」、"will" → 「〜する」）。
2. **原文にある内容を落とさない。** 段落・箇条書きの項目・表の行を欠かさない。
3. **マークアップは原文どおり保持する。** 見出しの下線、`:ref:`、``リテラル``、`.. note::` / `.. warning::` / `.. toctree::`、箇条書き、表、字下げされたコードブロック（literal block）は一切変更しない。
4. **コード・識別子・定数は翻訳しない。** `KVM_RUN`、`struct kvm_run`、`ioctl(fd, ...)`、`/dev/kvm`、`EINVAL`、`ENOTTY` などはそのまま。`` `` で囲まれた部分の中身は英語のまま。
5. **コードブロック（`::` のあとに字下げされた部分）の中身は一字も変えない。** コメントも含めて原文のまま。

## 文体
- **である調**で統一する（「〜だ」「〜である」「〜する」）。です・ます体は使わない。
- 一文一義。1文は 50〜60 字を目安にする。長い英文は日本語でも分けてよい。
- 主語と述語を近づける。修飾語は長いものを先に置く。
- 「〜することができる」→「〜できる」、「〜という形になる」→「〜になる」のように冗長な言い回しを削る。
- 二重否定を避ける。否定と条件の入れ子は素直な形にする（意味が変わる場合は原文どおり残す）。
- 漢字が続きすぎる箇所はひらがなを交えて開く。「の」の3連続を避ける。

## 翻訳調（英語の直訳）を避ける
`skill://natural-japanese` の「読み手が何のことか取れない言い回しは、ふだんの言葉に戻す」に従う。特に:
- 英語のフレーズを1語ずつ置き換えない（"first-class citizen"→「一級市民」、"edge case"→「端のケース」、"graceful degradation"→「優雅な劣化」、"source of truth"→「真実の源」は避ける）。
- すでに名前のあるものは、その名前で書く。同じ文書内で同じものを別の言葉で呼び直さない。
- 無生物を擬人化しない（「データが語る」「設定が育つ」など）。
- 動作を名詞にまとめて誰が何をするかを消さない（「〜の対応」ではなく「〜を直す」）。
- 「〜について」「〜に関する」で中身をぼかさない。

## 用語集（この訳語で統一する）
| 英語 | 訳語 |
|---|---|
| guest | ゲスト |
| host | ホスト |
| virtual machine / VM | 仮想マシン（VM）（初出はこの形、以降は VM） |
| vcpu / vCPU | vCPU |
| hypervisor | ハイパーバイザ |
| kernel | カーネル |
| in-kernel | カーネル内 |
| userspace / user space | ユーザ空間 |
| file descriptor | ファイルディスクリプタ |
| process | プロセス |
| thread | スレッド |
| address space | アドレス空間 |
| capability | ケイパビリティ |
| ioctl | ioctl |
| struct | 構造体 |
| union | 共用体 |
| register | レジスタ |
| interrupt | 割り込み |
| exception | 例外 |
| trap | トラップ |
| emulation | エミュレーション |
| shadow page table | シャドウページテーブル |
| page table | ページテーブル |
| page fault | ページフォールト |
| memory slot | メモリスロット |
| dirty page | ダーティページ |
| dirty log | ダーティログ |
| live migration | ライブマイグレーション |
| migration | マイグレーション |
| nested virtualization | ネスト仮想化 |
| nested guest | ネストゲスト |
| paravirtualization | 準仮想化 |
| hypercall | ハイパーコール |
| signal | シグナル |
| callback | コールバック |
| flag | フラグ |
| reserved | 予約済み |
| deprecated | 非推奨 |
| reference count | 参照カウント |
| trace | トレース |
| workload | ワークロード |
| benchmark | ベンチマーク |
| secure / protected guest | 保護ゲスト |
| confidential computing | コンフィデンシャルコンピューティング |
| attestation | アテステーション |
| VM-Entry | VM エントリ |
| VM-Exit | VM エグジット |
| stage-2 | ステージ 2 |
| API | API |
| MSR / TLB / APIC / MMIO / PIO / IDT / GDT / NMI / MSI / IRQ / PCI / DMA / DMA API / SMP / RCU | そのまま |
| atomic | アトミック |
| lock / locking | ロック |
| spinlock | スピンロック |
| mutex | ミューテックス |
| guest memory | ゲストメモリ |
| host memory | ホストメモリ |
| backing store | バッキングストア |
| feature | 機能 |
| Note: / Warning: | 備考 / 警告 |

## ディレクティブ
- `.. note::` `.. warning::` `.. toctree::` の**ディレクティブ名は英語のまま**。中身の本文だけ訳す。
- `.. SPDX-License-Identifier: GPL-2.0` の行はそのまま残す。
- `.. _label_name:` のラベル行はそのまま残す（訳さない）。
- `:ref:` の `` `...` `` の中身（リンク先名・ラベル）はそのまま。表示テキスト部分（`<...>` の前）は訳してよい。
- 見出しの下線記号は原文と同じ文字を使い、**下線の長さは訳文の文字数以上**にする（日本語1文字＝1文字として数える）。

## 表
- RST のグリッド表・簡易表の枠線と桁揃えは原文の構造を保つ。セルの中身だけ訳す。桁幅が合わなくなりそうな場合は、その表を `.. list-table::` に変換してよい（構造が保てないときだけ）。単純な表は、罫線の長さを訳文に合わせて調整してよい。

## 出力
- 指定された行範囲だけを訳す。範囲外の行は出力しない。
- 出力は RST そのもの（説明文やコードフェンス ``` で囲まない）。ファイルにそのまま書ける形で返す。
