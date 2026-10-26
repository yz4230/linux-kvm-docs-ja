.. SPDX-License-Identifier: GPL-2.0

===================
Linux KVM ハイパーコール
===================

X86:
 KVM ハイパーコールは、vmcall 命令か vmmcall 命令のいずれかの 3 バイトの
 シーケンスを持つ。ハイパーバイザはこれを、サポートが保証された命令に
 置き換えることができる。

 最大 4 個の引数を、それぞれ rbx、rcx、rdx、rsi に渡せる。ハイパーコール番号は
 rax に置き、戻り値は rax に置かれる。特定のハイパーコールが明示的に
 述べていない限り、他のレジスタは破壊されない。

S390:
  R2-R7 は引数 1-6 に使う。加えて、R1 はハイパーコール番号に使う。
  戻り値は R2 に書き込まれる。

  S390 は、ハイパーコールとして diagnose 命令 (0x500) を、R1 のハイパーコール
  番号とともに使う。

  KVM がサポートする S390 の diagnose 呼び出しについて詳しくは、
  Documentation/virt/kvm/s390/s390-diag.rst を参照。

PowerPC:
  R3-R10 と、R11 のハイパーコール番号を使う。R4-R11 は出力レジスタとして使う。
  戻り値は R3 に置かれる。

  KVM ハイパーコールは 4 バイトのオペコードを使い、これはデバイスツリーの
  /hypervisor ノード内の 'hypercall-instructions' プロパティでパッチされる。
  詳しくは Documentation/virt/kvm/ppc-pv.rst を参照。

MIPS:
  KVM ハイパーコールは、コード 0 の HYPCALL 命令を使い、ハイパーコール番号を
  $2 (v0) に置く。最大 4 個の引数を $4-$7 (a0-a3) に置き、戻り値は
  $2 (v0) に置かれる。

KVM ハイパーコールのドキュメント
============================

各ハイパーコールのテンプレートは次のとおりである。
1. ハイパーコール名
2. アーキテクチャ
3. 状態 (非推奨、廃止、有効)
4. 目的

1. KVM_HC_VAPIC_POLL_IRQ
------------------------

:Architecture: x86
:Status: 有効
:Purpose: ゲストエグジットを発生させ、ホストが再入時に保留中の割り込みを確認できるようにする。

2. KVM_HC_MMU_OP
----------------

:Architecture: x86
:Status: 非推奨
:Purpose: PTE への書き込み、TLB のフラッシュ、PT の解放などの MMU 操作をサポートする。

3. KVM_HC_FEATURES
------------------

:Architecture: PPC
:Status: 有効
:Purpose: ハイパーコールの可用性をゲストに公開する。x86 プラットフォームでは、利用可能なハイパーコールを列挙するのに cpuid が使われていた。PPC では、デバイスツリーに基づく検索 (EPAPR が定める方法でもある) か、KVM 固有の列挙メカニズム (このハイパーコール) のどちらかを使える。

4. KVM_HC_PPC_MAP_MAGIC_PAGE
----------------------------

:Architecture: PPC
:Status: 有効
:Purpose: ハイパーバイザとゲスト間の通信を可能にするため、スーパーバイザが参照できるレジスタ状態の一部を含む共有ページがある。ゲストは、このハイパーコールを使ってこの共有ページをマップし、メモリ経由で自身のスーパーバイザレジスタにアクセスできる。

5. KVM_HC_KICK_CPU
------------------

:Architecture: x86
:Status: 有効
:Purpose: HLT 状態から vCPU を起床させるためのハイパーコール
:Usage example:
  準仮想化ゲストの vCPU が、イベントの発生 (例: スピンロックが利用可能になる) を待ってゲストカーネルモードでビジーウェイトしている場合、しきい値の時間間隔を超えてビジーウェイトした後で HLT 命令を実行できる。HLT 命令を実行すると、ハイパーバイザは適切なイベントが発生するまでその vCPU をスリープさせる。同じゲストの別の vCPU は、起床させる vCPU の APIC ID (a1) を指定して KVM_HC_KICK_CPU ハイパーコールを発行することで、スリープ中の vCPU を起床させることができる。追加の引数 (a0) は将来の使用のためにハイパーコールで使われる。

6. KVM_HC_CLOCK_PAIRING
-----------------------
:Architecture: x86
:Status: 有効
:Purpose: ホストとゲストのクロックを同期させるためのハイパーコール

Usage:
a0: ホストが "struct kvm_clock_pairing" 構造体をコピーするゲスト物理アドレス。

a1: clock_type。現時点では KVM_CLOCK_PAIRING_WALLCLOCK (0) のみがサポートされる (ホストの CLOCK_REALTIME クロックに対応)。

       ::

		struct kvm_clock_pairing {
			__s64 sec;
			__s64 nsec;
			__u64 tsc;
			__u32 flags;
			__u32 pad[9];
		};

       Where:
               * sec: clock_type クロックからの秒数。
               * nsec: clock_type クロックからのナノ秒数。
               * tsc: sec/nsec ペアの計算に使われるゲスト TSC 値
               * flags: フラグ。現時点では未使用 (0)。

このハイパーコールにより、ゲストはホストとゲストにまたがる正確なタイムスタンプを計算できる。ゲストは、返された TSC 値を使って、同じ瞬間における自身のクロックの CLOCK_REALTIME を計算できる。

ホストが TSC クロックソースを使っていない場合、またはクロックタイプが KVM_CLOCK_PAIRING_WALLCLOCK と異なる場合、KVM_EOPNOTSUPP を返す。

7. KVM_HC_SEND_IPI
------------------

:Architecture: x86
:Status: 有効
:Purpose: 複数の vCPU に IPI を送信する。

- a0: 宛先 APIC ID のビットマップの下位部分
- a1: 宛先 APIC ID のビットマップの上位部分
- a2: ビットマップ内の最小 APIC ID
- a3: APIC ICR

このハイパーコールにより、ゲストはマルチキャスト IPI を送信できる。64 ビットモードでは 1 回のハイパーコールで最大 128 の宛先、32 ビットモードでは 1 回のハイパーコールで 64 の vCPU まで送信できる。宛先は、最初の 2 つの引数 (a0 と a1) に含まれるビットマップで表される。a0 のビット 0 は 3 番目の引数 (a2) の APIC ID に対応し、ビット 1 は APIC ID a2+1 に対応する。以下同様である。

IPI の送信に成功した CPU の数を返す。

8. KVM_HC_SCHED_YIELD
---------------------

:Architecture: x86
:Status: 有効
:Purpose: IPI の対象 vCPU がプリエンプトされた場合に譲るためのハイパーコール

a0: 宛先 APIC ID

:Usage example: vCPU に call-function IPI-many を送信する際、IPI の対象 vCPU のいずれかがプリエンプトされていたら譲る。

9. KVM_HC_MAP_GPA_RANGE
-------------------------
:Architecture: x86
:Status: 有効
:Purpose: 指定された属性で GPA 範囲をマップするよう KVM に要求する。

a0: 開始ページのゲスト物理アドレス
a1: (4kb) ページ数 (GPA 空間で連続している必要がある)
a2: 属性

    ここで 'attributes' は:
        * ビット 3:0 - 優先ページサイズのエンコーディング。0 = 4kb、1 = 2mb、2 = 1gb など
        * ビット 4 - plaintext = 0、encrypted = 1
        * ビット 63:5 - 予約済み (ゼロでなければならない)

**実装上の注意**: このハイパーコールは、KVM_CAP_EXIT_HYPERCALL ケイパビリティを介してユーザ空間で実装される。ユーザ空間は、ゲスト CPUID で KVM_FEATURE_HC_MAP_GPA_RANGE を通知する前に、そのケイパビリティを有効にしなければならない。さらに、ゲストが KVM_FEATURE_MIGRATION_CONTROL をサポートしている場合、ユーザ空間は MSR_KVM_MIGRATION_CONTROL への書き込みを処理するための MSR フィルタも設定しなければならない。
