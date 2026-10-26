.. SPDX-License-Identifier: GPL-2.0

==================
KVM の CPUID ビット
==================

:Author: Glauber Costa <glommer@gmail.com>

kvm ホスト上で動くゲストは、cpuid を使って自分の機能の一部を調べられる。
ただし、これは常に機能するとは限らない。ユーザ空間が、ゲストを起動する前に
KVM 関連の cpuid 機能の一部、あるいは全部をマスクできるためである。

KVM の cpuid ファンクションは次のとおりである:

function: KVM_CPUID_SIGNATURE (0x40000000)

returns::

   eax = 0x40000001
   ebx = 0x4b4d564b
   ecx = 0x564b4d56
   edx = 0x4d

ebx、ecx、edx の値は文字列 "KVMKVMKVM" に対応する点に注意する。eax の値は、
このリーフに存在する最大の cpuid ファンクションに対応し、将来さらに
ファンクションが追加されれば更新される。古いホストは eax の値を 0x0 に
設定する点にも注意する。これは値が 0x40000001 であるかのように解釈しなければ
ならない。このファンクションは KVM cpuid リーフの存在を問い合わせる。

function: define KVM_CPUID_FEATURES (0x40000001)

returns::

          ebx, ecx
          eax = an OR'ed group of (1 << flag)

ここで ``flag`` は次のように定義される:

.. list-table::
   :header-rows: 1

   * - flag
     - value
     - meaning
   * - KVM_FEATURE_CLOCKSOURCE
     - 0
     - kvmclock が msr 0x11 と 0x12 で利用できる
   * - KVM_FEATURE_NOP_IO_DELAY
     - 1
     - PIO 操作での遅延を行う必要がない
   * - KVM_FEATURE_MMU_OP
     - 2
     - 非推奨
   * - KVM_FEATURE_CLOCKSOURCE2
     - 3
     - kvmclock が msr 0x4b564d00 と 0x4b564d01 で利用できる
   * - KVM_FEATURE_ASYNC_PF
     - 4
     - msr 0x4b564d02 に書き込むと非同期 PF を有効にできる
   * - KVM_FEATURE_STEAL_TIME
     - 5
     - msr 0x4b564d03 に書き込むとステールタイムを有効にできる
   * - KVM_FEATURE_PV_EOI
     - 6
     - msr 0x4b564d04 に書き込むと準仮想化された割り込み終了ハンドラを
       有効にできる
   * - KVM_FEATURE_PV_UNHALT
     - 7
     - ゲストは準仮想化スピンロック対応を有効にする前にこの機能ビットを
       確認する
   * - KVM_FEATURE_PV_TLB_FLUSH
     - 9
     - ゲストは準仮想化 TLB フラッシュを有効にする前にこの機能ビットを
       確認する
   * - KVM_FEATURE_ASYNC_PF_VMEXIT
     - 10
     - msr 0x4b564d02 に書き込むときにビット 2 を設定すると、準仮想化された
       非同期 PF の VM エグジットを有効にできる
   * - KVM_FEATURE_PV_SEND_IPI
     - 11
     - ゲストは準仮想化された IPI 送信を有効にする前にこの機能ビットを
       確認する
   * - KVM_FEATURE_POLL_CONTROL
     - 12
     - msr 0x4b564d05 に書き込むと HLT でのホスト側ポーリングを無効にできる。
   * - KVM_FEATURE_PV_SCHED_YIELD
     - 13
     - ゲストは準仮想化された sched yield を使う前にこの機能ビットを確認する。
   * - KVM_FEATURE_ASYNC_PF_INT
     - 14
     - ゲストは 2 つ目の非同期 PF 制御用 msr 0x4b564d06 と非同期 PF 確認応答用
       msr 0x4b564d07 を使う前にこの機能ビットを確認する。
   * - KVM_FEATURE_MSI_EXT_DEST_ID
     - 15
     - ゲストは MSI アドレスのビット 11〜5 の拡張宛先 ID ビットを使う前に
       この機能ビットを確認する。
   * - KVM_FEATURE_HC_MAP_GPA_RANGE
     - 16
     - ゲストはページ状態の変化を通知する map gpa range ハイパーコールを
       使う前にこの機能ビットを確認する
   * - KVM_FEATURE_MIGRATION_CONTROL
     - 17
     - ゲストは MSR_KVM_MIGRATION_CONTROL を使う前にこの機能ビットを確認する
   * - KVM_FEATURE_CLOCKSOURCE_STABLE_BIT
     - 24
     - kvmclock でゲスト側の CPU ごとのクロック変動（warp）が想定されない
       とき、ホストは警告を出す

::

      edx = an OR'ed group of (1 << flag)

ここで ``flag`` は次のように定義される:

.. list-table::
   :header-rows: 1

   * - flag
     - value
     - meaning
   * - KVM_HINTS_REALTIME
     - 0
     - ゲストはこの機能ビットを確認して、vCPU が無期限にプリエンプトされない
       と判断し、最適化を可能にする
