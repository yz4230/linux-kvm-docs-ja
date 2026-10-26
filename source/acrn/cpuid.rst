.. SPDX-License-Identifier: GPL-2.0

=================
ACRN CPUID ビット
=================

ACRN ハイパーバイザ上で動作するゲスト VM は、CPUID を使って自身の一部の機能を確認できる。

ACRN の CPUID 関数は次のとおりである。

function: 0x40000000

returns::

   eax = 0x40000010
   ebx = 0x4e524341
   ecx = 0x4e524341
   edx = 0x4e524341

ebx、ecx、edx の値は文字列 "ACRNACRNACRN" に対応する。eax の値はこのリーフに存在する
最大の CPUID 関数に対応し、将来さらに関数を追加した場合は更新される。

function: define ACRN_CPUID_FEATURES (0x40000001)

returns::

          ebx, ecx, edx
          eax = an OR'ed group of (1 << flag)

ここで ``flag`` は次のように定義される。

================================= =========== ================================
フラグ                            値          意味
================================= =========== ================================
ACRN_FEATURE_PRIVILEGED_VM        0           ゲスト VM は特権 VM である
================================= =========== ================================

function: 0x40000010

returns::

          ebx, ecx, edx
          eax = (Virtual) TSC frequency in kHz.
