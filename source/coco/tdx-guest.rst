.. SPDX-License-Identifier: GPL-2.0

===================================================================
TDX ゲスト API ドキュメント
===================================================================

1. 概要
=======

TDX ゲストドライバは、/dev/tdx-guest misc デバイスを通じて IOCTL
インターフェースを公開し、ユーザ空間が TDX ゲスト固有の詳細を取得できる
ようにする。

2. API の説明
=============

この節では、サポートされている各 IOCTL について、一般的な説明とあわせて
次の情報を示す。

:Input parameters: IOCTL に渡すパラメータと関連する詳細。
:Output: 出力データと戻り値の詳細（一般的でないエラー値に関する詳細を
       含む）。

2.1 TDX_CMD_GET_REPORT0
-----------------------

:Input parameters: struct tdx_report_req
:Output: 実行に成功すると、TDREPORT データが
       tdx_report_req.tdreport にコピーされ、0 を返す。不正なオペランドには
       -EINVAL を、TDCALL の失敗には -EIO を、その他の一般的な失敗には
       標準のエラー番号を返す。

TDX_CMD_GET_REPORT0 IOCTL は、アテステーションソフトウェアが
TDCALL[TDG.MR.REPORT] を使って TDX モジュールから TDREPORT0（別名 TDREPORT
サブタイプ 0）を取得するために使える。

サブタイプ固有の TDREPORT 要求を一意に識別するため、この IOCTL CMD の末尾に
サブタイプインデックスが追加されている。サブタイプオプションは TDX Module
v1.0 仕様の "TDG.MR.REPORT" と題された節で言及されているが、現在は使われて
おらず、この値は 0 であることが想定されている。そのため IOCTL の実装を単純に
保つ目的で、サブタイプオプションは入力 ABI の一部に含められなかった。ただし
将来 TDX Module が複数のサブタイプをサポートした場合は、それを扱う新しい
IOCTL CMD が作られる。IOCTL の命名を一貫させるため、サブタイプインデックスは
IOCTL CMD の一部として追加されている。

参考文献
---------

TDX の参考資料はここにまとめられている:

https://www.intel.com/content/www/us/en/developer/articles/technical/intel-trust-domain-extensions.html

このドライバは TDX module 仕様 v1.0 と TDX GHCI 仕様 v1.0 に基づく。
