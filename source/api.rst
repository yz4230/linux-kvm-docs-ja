.. SPDX-License-Identifier: GPL-2.0

===================================================================
KVM (Kernel-based Virtual Machine) API 仕様書
===================================================================

1. 概要
=======

kvm API は、いくつかの種類のファイルディスクリプタと、それらに
対して発行する ioctl を中心に組み立てられている。最初に
open("/dev/kvm") を呼ぶと、kvm サブシステムへのハンドルを取得する。
このハンドルにはシステム ioctl を発行できる。このハンドルに
KVM_CREATE_VM ioctl を発行すると VM ファイルディスクリプタが作られ、
これに VM ioctl を発行できる。VM fd に KVM_CREATE_VCPU または
KVM_CREATE_DEVICE ioctl を発行すると、仮想 CPU またはデバイスが作られ、
新しいリソースを指すファイルディスクリプタが返る。

言い換えると、kvm API とは、仮想マシンのさまざまな側面を制御するために、
いくつかの種類のファイルディスクリプタに発行する ioctl の集合である。
ioctl は、それを受け付けるファイルディスクリプタによって、次のクラスに
分かれる:

 - システム ioctl: kvm サブシステム全体に影響するグローバル属性を
   照会・設定する。加えて、仮想マシンを作るのにもシステム ioctl を使う。

 - VM ioctl: 仮想マシン全体に影響する属性（たとえばメモリ配置）を
   照会・設定する。加えて、仮想 CPU（vCPU）やデバイスを作るのにも
   VM ioctl を使う。

   VM ioctl は、その VM を作ったのと同じプロセス（アドレス空間）から
   発行しなければならない。

 - vCPU ioctl: 1 つの仮想 CPU の動作を制御する属性を照会・設定する。

   vCPU ioctl は、その vCPU を作ったのと同じスレッドから発行すべきで
   ある。ただし、このドキュメントで非同期と記された vCPU ioctl は除く。
   そうしないと、スレッドを切り替えた後の最初の ioctl で性能低下が
   起きるおそれがある。

 - デバイス ioctl: 1 つのデバイスの動作を制御する属性を照会・設定する。

   デバイス ioctl は、その VM を作ったのと同じプロセス（アドレス空間）
   から発行しなければならない。

ほとんどの ioctl は特定の 1 種類のファイルディスクリプタに固有だが、
同じ ioctl が複数のクラスに属することもある。

KVM API は時代とともに拡張されてきた。そのため KVM は ``KVM_CAP_*``
という形の定数を数多く定義しており、各定数は 1 つ以上の ioctl が提供する
一連の機能に対応する。これらの「ケイパビリティ」が利用できるかどうかは、
:ref:`KVM_CHECK_EXTENSION <KVM_CHECK_EXTENSION>` で確認できる。また、
機能を使いたい VM や vCPU では、あらかじめ有効化が必要なケイパビリティも
ある（:ref:`cap_enable` と :ref:`cap_enable_vm` を参照）。


2. 制約
=======

一般に、ファイルディスクリプタは fork() と UNIX ドメインソケットの
SCM_RIGHTS 機構によってプロセス間を移動できる。この種の小細工は、
kvm では明示的にサポートされていない。ホストに害は及ばないが、
その実際の動作は API では保証されない。KVM がサポートする ioctl の
利用モデルの詳細は「概要」を参照。

VM ioctl は VM を作ったプロセスからしか発行できないが、VM の
ライフサイクルは作成者（プロセス）ではなくファイルディスクリプタに
結び付いている点に注意が必要である。言い換えると、VM とそのリソースは、
*関連するアドレス空間も含めて*、VM のファイルディスクリプタへの最後の
参照が解放されるまで解放されない。たとえば ioctl(KVM_CREATE_VM) の後に
fork() すると、親（元の）プロセスとその子の両方が VM の
ファイルディスクリプタへの参照を手放すまで、VM は解放されない。

VM のリソースは、そのファイルディスクリプタへの最後の参照が解放される
まで解放されない。そのため fork() や dup() などで VM への参照を安易に
増やすのは避けるべきであり、望まない副作用を招くおそれがある。たとえば
VM を停止しても、そのプロセスのために確保されたメモリが解放されず、
アカウンティングから外れないことがある。


3. 拡張
=======

Linux 2.6.22 以降、KVM ABI は安定しており、後方互換性を壊す変更は
認められない。ただし、後方互換な API 拡張を照会・利用できる拡張機構が
用意されている。

この拡張の仕組みは Linux のバージョン番号には基づかない。代わりに kvm は
拡張識別子と、特定の拡張識別子が利用できるかを照会する仕組みを定義して
いる。利用できるなら、そのアプリケーションで使える一連の ioctl が
存在する。


4. API の説明
=============

この節では、kvm ゲストを制御するために使える ioctl を説明する。
各 ioctl について、説明とあわせて次の情報を示す:

  Capability:
      この ioctl はどの KVM 拡張が提供するか。'basic' の場合もある。
      これは API バージョン 12 に対応するカーネルならどれでも提供される
      （:ref:`KVM_GET_API_VERSION <KVM_GET_API_VERSION>` を参照）。
      あるいは :ref:`KVM_CHECK_EXTENSION <KVM_CHECK_EXTENSION>` で
      確認できる KVM_CAP_xyz 形式の定数である。

  Architectures:
      この ioctl を提供する命令セットアーキテクチャ。
      x86 には i386 と x86_64 の両方が含まれる。

  Type:
      system、vm、vcpu、guest_memfd のいずれか。

  Parameters:
      この ioctl が受け付けるパラメータ。

  Returns:
      戻り値。一般的なエラー番号（EBADF、ENOMEM、EINVAL）は詳述しないが、
      固有の意味を持つエラーは詳述する。


.. _KVM_GET_API_VERSION:

4.1 KVM_GET_API_VERSION
-----------------------

:Capability: basic
:Architectures: all
:Type: system ioctl
:Parameters: none
:Returns: the constant KVM_API_VERSION (=12)

これは安定した kvm API のバージョンを示す。この番号が変わるとは想定されて
いない。ただし Linux 2.6.20 と 2.6.21 はもっと前のバージョンを報告する。
これらは文書化されておらず、サポートもされない。KVM_GET_API_VERSION が
12 以外の値を返したら、アプリケーションは動作を拒否すべきである。
この確認を通過すれば、'basic' と記された ioctl はすべて利用できる。


4.2 KVM_CREATE_VM
-----------------

:Capability: basic
:Architectures: all
:Type: system ioctl
:Parameters: machine type identifier (KVM_VM_*)
:Returns: a VM fd that can be used to control the new virtual machine.

新しい VM には仮想 CPU もメモリもない。
マシンタイプには 0 を使うのが普通である。

X86:
^^^^

対応する X86 の VM タイプは KVM_CAP_VM_TYPES で照会できる。

S390:
^^^^^

S390 でユーザが制御する仮想マシンを作るには、KVM_CAP_S390_UCONTROL を
確認し、特権ユーザ（CAP_SYS_ADMIN）としてフラグ KVM_VM_S390_UCONTROL を
使う。

MIPS:
^^^^^

MIPS で、既定の trap & emulate 実装（ユーザモードに収めるため仮想メモリ
配置を変える）ではなく、ハードウェア支援による仮想化（VZ ASE）を使うには、
KVM_CAP_MIPS_VZ を確認し、フラグ KVM_VM_MIPS_VZ を使う。

ARM64:
^^^^^^

arm64 では、VM の物理アドレスサイズ（IPA サイズ上限）は既定で 40bit に
制限される。ホストが拡張 KVM_CAP_ARM_VM_IPA_SIZE に対応していれば、
この上限は設定できる。対応している場合、KVM_VM_TYPE_ARM_IPA_SIZE(IPA_Bits)
を使ってマシンタイプ識別子でサイズを設定する。ここで IPA_Bits は、その VM
が使う物理アドレスの最大幅である。IPA_Bits はマシンタイプ識別子の
bits[7-0] にエンコードされる。

例えば、ゲストが 48bit の物理アドレスサイズを使うように設定するには::

    vm_fd = ioctl(dev_fd, KVM_CREATE_VM, KVM_VM_TYPE_ARM_IPA_SIZE(48));

要求するサイズ（IPA_Bits）は次のいずれかでなければならない:

 ==   =========================================================
  0   既定サイズの 40bit を意味する（後方互換のため）
  N   N bit を意味する。N は 32 <= N <= Host_IPA_Limit を満たす
      正の整数である
 ==   =========================================================

Host_IPA_Limit は、そのホストで IPA_Bits が取り得る最大値であり、
CPU の機能とカーネル設定に依存する。この上限は、実行時に
KVM_CHECK_EXTENSION ioctl() の KVM_CAP_ARM_VM_IPA_SIZE で取得できる。

要求した IPA サイズ（暗黙でも明示でも）がホストでサポートされていない
場合、VM の作成は失敗する。

IPA サイズを設定しても、ゲスト CPU が ID_AA64MMFR0_EL1[PARange] で
公開する機能には影響しないことに注意。影響するのは、ステージ 2 が変換
するアドレスのサイズ（ゲスト物理アドレスからホスト物理アドレスへの
変換）だけである。


4.3 KVM_GET_MSR_INDEX_LIST, KVM_GET_MSR_FEATURE_INDEX_LIST
----------------------------------------------------------

:Capability: basic, KVM_CAP_GET_MSR_FEATURES for KVM_GET_MSR_FEATURE_INDEX_LIST
:Architectures: x86
:Type: system ioctl
:Parameters: struct kvm_msr_list (in/out)
:Returns: 0 on success; -1 on error

Errors:

  ======     ============================================================
  EFAULT     msr インデックスのリストを読み書きできない
  E2BIG      msr インデックスのリストが大きすぎて、ユーザが指定した
             配列に収まらない
  ======     ============================================================

::

  struct kvm_msr_list {
	__u32 nmsrs; /* number of msrs in entries */
	__u32 indices[0];
  };

ユーザは nmsrs に indices 配列のサイズを設定する。すると kvm は、実際の
msr 数に合わせて nmsrs を調整し、indices 配列に各 msr の番号を書き込む。

KVM_GET_MSR_INDEX_LIST は、サポートされているゲスト msr を返す。
このリストは kvm のバージョンとホストのプロセッサによって異なるが、
それ以外では変わらない。

備考: kvm が MCE 対応（KVM_CAP_MCE）を示す場合、MCE バンクの MSR は
MSR リストに返されない。KVM_X86_SETUP_MCE ioctl で設定するバンク数は
vCPU ごとに異なり得るためである。

KVM_GET_MSR_FEATURE_INDEX_LIST は、KVM_GET_MSRS システム ioctl に
渡せる MSR のリストを返す。これによりユーザ空間は、MSR 経由で公開される
ホストのケイパビリティとプロセッサの機能（たとえば VMX のケイパビリティ）
を調べられる。このリストも kvm のバージョンとホストのプロセッサによって
異なるが、それ以外では変わらない。


.. _KVM_CHECK_EXTENSION:

4.4 KVM_CHECK_EXTENSION
-----------------------

:Capability: basic、vm ioctl の場合は KVM_CAP_CHECK_EXTENSION_VM
:Architectures: all
:Type: system ioctl, vm ioctl
:Parameters: 拡張識別子 (KVM_CAP_*)
:Returns: 未対応なら 0、対応していれば 1（またはその他の正の整数）

この API を使うと、アプリケーションはコア kvm API の拡張について問い合わせできる。
ユーザ空間は拡張識別子（整数）を渡し、その拡張が利用できるかどうかを表す整数を
受け取る。一般に 0 は「なし」、1 は「あり」を意味するが、拡張によっては整数の
戻り値で追加情報を報告することがある。

仮想マシン（VM）は初期化の内容によって利用できるケイパビリティが異なりうる。
そのため、ケイパビリティの問い合わせには vm ioctl を使うことが推奨される
（vm fd で KVM_CAP_CHECK_EXTENSION_VM を使えば利用できる）。

4.5 KVM_GET_VCPU_MMAP_SIZE
--------------------------

:Capability: basic
:Architectures: all
:Type: system ioctl
:Parameters: none
:Returns: vcpu mmap 領域のサイズ（バイト単位）

KVM_RUN ioctl（後述）は、共有メモリ領域を介してユーザ空間と通信する。
この ioctl はその領域のサイズを返す。詳しくは KVM_RUN の説明を参照。

KVM_RUN の通信用領域のサイズのほかにも、VCPU ファイルディスクリプタの
別の領域を mmap できる。具体的には次のとおり。

- KVM_CAP_COALESCED_MMIO が利用できる場合、KVM_COALESCED_MMIO_PAGE_OFFSET *
  PAGE_SIZE の位置の 1 ページ。歴史的な理由により、このページは
  KVM_GET_VCPU_MMAP_SIZE の結果に含まれる。KVM_CAP_COALESCED_MMIO は
  まだ文書化されていない。

- KVM_CAP_DIRTY_LOG_RING が利用できる場合、KVM_DIRTY_LOG_PAGE_OFFSET *
  PAGE_SIZE の位置の複数ページ。KVM_CAP_DIRTY_LOG_RING の詳細は
  :ref:`KVM_CAP_DIRTY_LOG_RING` を参照。


4.7 KVM_CREATE_VCPU
-------------------

:Capability: basic
:Architectures: all
:Type: vm ioctl
:Parameters: vcpu id（x86 では apic id）
:Returns: 成功時は vcpu fd、エラー時は -1

この API は VM に vCPU を追加する。追加できるのは max_vcpus 個までである。
vcpu id は [0, max_vcpu_id) の範囲の整数である。

推奨される max_vcpus の値は、実行時に KVM_CHECK_EXTENSION ioctl() の
KVM_CAP_NR_VCPUS で取得できる。
max_vcpus の最大値は、実行時に KVM_CHECK_EXTENSION ioctl() の
KVM_CAP_MAX_VCPUS で取得できる。

KVM_CAP_NR_VCPUS が存在しない場合は、max_vcpus は最大 4 CPU とみなすべきである。
KVM_CAP_MAX_VCPUS が存在しない場合は、max_vcpus は KVM_CAP_NR_VCPUS が返す値と
同じとみなすべきである。

max_vcpu_id の最大値は、実行時に KVM_CHECK_EXTENSION ioctl() の
KVM_CAP_MAX_VCPU_ID で取得できる。

KVM_CAP_MAX_VCPU_ID が存在しない場合は、max_vcpu_id は KVM_CAP_MAX_VCPUS が
返す値と同じとみなすべきである。

book3s_hv モードを使う powerpc では、vCPU は 1 つ以上の仮想 CPU コア内の
仮想スレッドにマッピングされる。（ハードウェアが、CPU コア内の全ハードウェア
スレッドが同じパーティションにあることを要求するためである。）
KVM_CAP_PPC_SMT ケイパビリティは、仮想コア（vcore）あたりの vCPU 数を示す。
vcore id は、vcpu id を vcore あたりの vCPU 数で割って得る。ある vcore 内の
vCPU は、互いに常に同じ物理コア上にある（ただし、その物理コアは時と場合により
異なりうる）。ユーザ空間は、vcpu id の割り当てによってゲストのスレッディング
（SMT）モードを制御できる。たとえば、ユーザ空間がシングルスレッドのゲスト
vCPU を望むなら、すべての vcpu id を vcore あたりの vCPU 数の倍数にすべきである。

S390 のユーザ制御仮想マシンで作成した仮想 CPU では、生成された vcpu fd を
ページオフセット KVM_S390_SIE_PAGE_OFFSET でメモリマップし、その仮想 CPU の
ハードウェア制御ブロックのメモリマップを取得できる。


4.8 KVM_GET_DIRTY_LOG
---------------------

:Capability: basic
:Architectures: all
:Type: vm ioctl
:Parameters: struct kvm_dirty_log (in/out)
:Returns: 成功時は 0、エラー時は -1

::

  /* for KVM_GET_DIRTY_LOG */
  struct kvm_dirty_log {
	__u32 slot;
	__u32 padding;
	union {
		void __user *dirty_bitmap; /* one bit per page */
		__u64 padding;
	};
  };

メモリスロットを指定すると、この ioctl の前回の呼び出し以降にダーティになった
ページを含むビットマップを返す。ビット 0 はメモリスロットの先頭ページである。
パディングの問題を避けるため、構造体全体をクリアしておくこと。

KVM_CAP_MULTI_ADDRESS_SPACE が利用できる場合、slot フィールドのビット 16〜31 は、
ダーティビットマップを返す対象のアドレス空間を指定する。slot フィールドの
使い方の詳細は KVM_SET_USER_MEMORY_REGION を参照。

KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2 が有効でない限り、ダーティビットマップの
ビットは ioctl が返る前にクリアされる。詳細はこのケイパビリティの説明を参照。

なお、Xen の shared_info ページは、構成されている場合は常にダーティと
みなさなければならない。KVM はそれを明示的にダーティとはマークしない。


4.10 KVM_RUN
------------

:Capability: basic
:Architectures: all
:Type: vcpu ioctl
:Parameters: none
:Returns: 成功時は 0、エラー時は -1

Errors:

  =======    ==============================================================
  EINTR      マスクされていないシグナルが保留中
  ENOEXEC    vCPU が初期化されていない、またはゲストがデバイスメモリから
             命令を実行しようとした (arm64)
  ENOSYS     シンドローム情報のないメモリスロット外のデータアボートで、
             KVM_CAP_ARM_NISV_TO_USER が有効でない (arm64)
  EPERM      SVE 機能セットが確定していない (arm64)
  =======    ==============================================================

この ioctl はゲストの仮想 CPU を実行するために使う。明示的なパラメータはないが、
暗黙のパラメータブロックがあり、vcpu fd をオフセット 0 で mmap() すると
取得できる。サイズは KVM_GET_VCPU_MMAP_SIZE で与えられる。パラメータブロックの
形式は 'struct kvm_run'（後述）である。


4.11 KVM_GET_REGS
-----------------

:Capability: basic
:Architectures: all except arm64
:Type: vcpu ioctl
:Parameters: struct kvm_regs (out)
:Returns: 成功時は 0、エラー時は -1

vCPU から汎用レジスタを読み出す。

::

  /* x86 */
  struct kvm_regs {
	/* out (KVM_GET_REGS) / in (KVM_SET_REGS) */
	__u64 rax, rbx, rcx, rdx;
	__u64 rsi, rdi, rsp, rbp;
	__u64 r8,  r9,  r10, r11;
	__u64 r12, r13, r14, r15;
	__u64 rip, rflags;
  };

  /* mips */
  struct kvm_regs {
	/* out (KVM_GET_REGS) / in (KVM_SET_REGS) */
	__u64 gpr[32];
	__u64 hi;
	__u64 lo;
	__u64 pc;
  };

  /* LoongArch */
  struct kvm_regs {
	/* out (KVM_GET_REGS) / in (KVM_SET_REGS) */
	unsigned long gpr[32];
	unsigned long pc;
  };


4.12 KVM_SET_REGS
-----------------

:Capability: basic
:Architectures: all except arm64
:Type: vcpu ioctl
:Parameters: struct kvm_regs (in)
:Returns: 成功時は 0、エラー時は -1

vCPU に汎用レジスタを書き込む。

データ構造は KVM_GET_REGS を参照。


4.13 KVM_GET_SREGS
------------------

:Capability: basic
:Architectures: x86, ppc
:Type: vcpu ioctl
:Parameters: struct kvm_sregs (out)
:Returns: 成功時は 0、エラー時は -1

vCPU から特殊レジスタを読み出す。

::

  /* x86 */
  struct kvm_sregs {
	struct kvm_segment cs, ds, es, fs, gs, ss;
	struct kvm_segment tr, ldt;
	struct kvm_dtable gdt, idt;
	__u64 cr0, cr2, cr3, cr4, cr8;
	__u64 efer;
	__u64 apic_base;
	__u64 interrupt_bitmap[(KVM_NR_INTERRUPTS + 63) / 64];
  };

  /* ppc -- see arch/powerpc/include/uapi/asm/kvm.h */

interrupt_bitmap は、保留中の外部割り込みのビットマップである。セットできる
ビットは最大 1 つである。この割り込みは APIC がすでに応答したが、まだ CPU コアに
注入されていない。


4.14 KVM_SET_SREGS
------------------

:Capability: basic
:Architectures: x86, ppc
:Type: vcpu ioctl
:Parameters: struct kvm_sregs (in)
:Returns: 成功時は 0、エラー時は -1

vCPU に特殊レジスタを書き込む。データ構造は KVM_GET_SREGS を参照。


4.15 KVM_TRANSLATE
------------------

:Capability: basic
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_translation (in/out)
:Returns: 成功時は 0、エラー時は -1

vCPU の現在のアドレス変換モードに従って仮想アドレスを変換する。

::

  struct kvm_translation {
	/* in */
	__u64 linear_address;

	/* out */
	__u64 physical_address;
	__u8  valid;
	__u8  writeable;
	__u8  usermode;
	__u8  pad[5];
  };


4.16 KVM_INTERRUPT
------------------

:Capability: basic
:Architectures: x86, ppc, mips, riscv, loongarch
:Type: vcpu ioctl
:Parameters: struct kvm_interrupt (in)
:Returns: 成功時は 0、失敗時は負の値

注入するハードウェア割り込みベクタをキューに入れる。

::

  /* for KVM_INTERRUPT */
  struct kvm_interrupt {
	/* in */
	__u32 irq;
  };

X86:
^^^^

:Returns:

	========= ===================================
	  0       成功
	 -EEXIST  割り込みがすでにキューに入っている
	 -EINVAL  irq 番号が無効
	 -ENXIO   PIC がカーネル内にある
	 -EFAULT  ポインタが無効
	========= ===================================

なお、'irq' は割り込みベクタであり、割り込みピンや割り込み線ではない。
この ioctl は、カーネル内の PIC を使わない場合に役立つ。

PPC:
^^^^

注入する外部割り込みをキューに入れる。この ioctl には、3 つの異なる irq 値の
使い方がある。

a) KVM_INTERRUPT_SET

   ゲストが割り込みを受け取れる状態になった時点で、エッジタイプの外部割り込みを
   ゲストに注入する。注入されると、その割り込みは完了する。

b) KVM_INTERRUPT_UNSET

   保留中の割り込みを解除する。

   KVM_CAP_PPC_UNSET_IRQ がある場合のみ利用できる。

c) KVM_INTERRUPT_SET_LEVEL

   ゲストのコンテキストにレベルタイプの外部割り込みを注入する。この割り込みは、
   KVM_INTERRUPT_UNSET を指定した ioctl が実行されるまで保留のままである。

   KVM_CAP_PPC_IRQ_LEVEL がある場合のみ利用できる。

なお、上に挙げた以外の 'irq' の値は無効であり、予期しない動作を引き起こす。

これは非同期の vcpu ioctl であり、どのスレッドからでも呼び出せる。

MIPS:
^^^^^

仮想 CPU に注入する外部割り込みをキューに入れる。負の割り込み番号を指定すると、
その割り込みをキューから取り除く。

これは非同期の vcpu ioctl であり、どのスレッドからでも呼び出せる。

RISC-V:
^^^^^^^

仮想 CPU に注入する外部割り込みをキューに入れる。この ioctl には、2 つの異なる
irq 値の使い方がある。

a) KVM_INTERRUPT_SET

   仮想 CPU に外部割り込みを設定し、仮想 CPU は準備ができた時点でこれを受け取る。

b) KVM_INTERRUPT_UNSET

   仮想 CPU の保留中の外部割り込みをクリアする。

これは非同期の vcpu ioctl であり、どのスレッドからでも呼び出せる。

LOONGARCH:
^^^^^^^^^^

仮想 CPU に注入する外部割り込みをキューに入れる。負の割り込み番号を指定すると、
その割り込みをキューから取り除く。

これは非同期の vcpu ioctl であり、どのスレッドからでも呼び出せる。


4.18 KVM_GET_MSRS
-----------------

:Capability: basic (vcpu), KVM_CAP_GET_MSR_FEATURES (system)
:Architectures: x86
:Type: system ioctl, vcpu ioctl
:Parameters: struct kvm_msrs (in/out)
:Returns: 正常に返された msr の数。エラー時は -1

system ioctl として使う場合：
VM で利用できる MSR ベースの機能の値を読み出す。KVM_GET_SUPPORTED_CPUID に
似ているが、MSR のインデックスと値を返す。MSR ベースの機能の一覧は、
system ioctl の KVM_GET_MSR_FEATURE_INDEX_LIST で取得できる。

vcpu ioctl として使う場合：
vCPU からモデル固有レジスタを読み出す。対応している msr インデックスは、
system ioctl の KVM_GET_MSR_INDEX_LIST で取得できる。

::

  struct kvm_msrs {
	__u32 nmsrs; /* number of msrs in entries */
	__u32 pad;

	struct kvm_msr_entry entries[0];
  };

  struct kvm_msr_entry {
	__u32 index;
	__u32 reserved;
	__u64 data;
  };

アプリケーションコードは、'nmsrs' メンバ（entries 配列のサイズを表す）と、
各配列エントリの 'index' メンバを設定すべきである。kvm が 'data' メンバを埋める。


4.19 KVM_SET_MSRS
-----------------

:Capability: basic
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_msrs (in)
:Returns: 正常に設定された msr の数（後述）。エラー時は -1

vCPU にモデル固有レジスタを書き込む。データ構造は KVM_GET_MSRS を参照。

アプリケーションコードは、'nmsrs' メンバ（entries 配列のサイズを表す）と、
各配列エントリの 'index' および 'data' メンバを設定すべきである。

配列 entries[] 内の MSR を 1 つずつ設定しようとする。予約ビットを設定した、
KVM がその MSR をサポート／エミュレートしていないなど、MSR の設定が失敗した
場合は、MSR リストの処理を中止し、設定に成功した MSR の数を返す。


4.20 KVM_SET_CPUID
------------------

:Capability: basic
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_cpuid (in)
:Returns: 成功時は 0、エラー時は -1

cpuid 命令に対する vCPU の応答を定義する。アプリケーションは、利用できるなら
KVM_SET_CPUID2 ioctl を使うべきである。

注意点:
  - この IOCTL が失敗した場合、以前の有効な CPUID 設定（存在すれば）が壊れて
    いないことを KVM は保証しない。その場合は、ユーザ空間が KVM_GET_CPUID2 で
    結果の CPUID 設定のコピーを取得できる。
  - KVM_RUN の後に KVM_SET_CPUID{,2} を使う場合、すなわちゲストの実行後に
    ゲスト vCPU モデルを変更する場合は、ゲストが不安定になることがある。
  - APIC ID やトポロジなどを除いて異種の CPUID 設定を使う場合は、ゲストが
    不安定になることがある。

::

  struct kvm_cpuid_entry {
	__u32 function;
	__u32 eax;
	__u32 ebx;
	__u32 ecx;
	__u32 edx;
	__u32 padding;
  };

  /* for KVM_SET_CPUID */
  struct kvm_cpuid {
	__u32 nent;
	__u32 padding;
	struct kvm_cpuid_entry entries[0];
  };


4.21 KVM_SET_SIGNAL_MASK
------------------------

:Capability: basic
:Architectures: all
:Type: vcpu ioctl
:Parameters: struct kvm_signal_mask (in)
:Returns: 成功時は 0、エラー時は -1

KVM_RUN の実行中にブロックするシグナルを定義する。このシグナルマスクは、
スレッドのシグナルマスクを一時的に上書きする。ブロックされていないシグナルを
受け取ると（従来の動作を保つ SIGKILL と SIGSTOP を除く）、KVM_RUN は -EINTR を
返す。

なお、シグナルは元のシグナルマスクでブロックされていない場合にのみ配送される。

::

  /* for KVM_SET_SIGNAL_MASK */
  struct kvm_signal_mask {
	__u32 len;
	__u8  sigset[0];
  };


4.22 KVM_GET_FPU
----------------

:Capability: basic
:Architectures: x86, loongarch
:Type: vcpu ioctl
:Parameters: struct kvm_fpu (out)
:Returns: 成功時は 0、エラー時は -1

vCPU から浮動小数点の状態を読み出す。

::

  /* x86: for KVM_GET_FPU and KVM_SET_FPU */
  struct kvm_fpu {
	__u8  fpr[8][16];
	__u16 fcw;
	__u16 fsw;
	__u8  ftwx;  /* in fxsave format */
	__u8  pad1;
	__u16 last_opcode;
	__u64 last_ip;
	__u64 last_dp;
	__u8  xmm[16][16];
	__u32 mxcsr;
	__u32 pad2;
  };

  /* LoongArch: for KVM_GET_FPU and KVM_SET_FPU */
  struct kvm_fpu {
	__u32 fcsr;
	__u64 fcc;
	struct kvm_fpureg {
		__u64 val64[4];
	}fpr[32];
  };


4.23 KVM_SET_FPU
----------------

:Capability: basic
:Architectures: x86, loongarch
:Type: vcpu ioctl
:Parameters: struct kvm_fpu (in)
:Returns: 成功時は 0、エラー時は -1

vCPU に浮動小数点の状態を書き込む。

::

  /* x86: for KVM_GET_FPU and KVM_SET_FPU */
  struct kvm_fpu {
	__u8  fpr[8][16];
	__u16 fcw;
	__u16 fsw;
	__u8  ftwx;  /* in fxsave format */
	__u8  pad1;
	__u16 last_opcode;
	__u64 last_ip;
	__u64 last_dp;
	__u8  xmm[16][16];
	__u32 mxcsr;
	__u32 pad2;
  };

  /* LoongArch: for KVM_GET_FPU and KVM_SET_FPU */
  struct kvm_fpu {
	__u32 fcsr;
	__u64 fcc;
	struct kvm_fpureg {
		__u64 val64[4];
	}fpr[32];
  };

4.24 KVM_CREATE_IRQCHIP
-----------------------

:Capability: KVM_CAP_IRQCHIP, KVM_CAP_S390_IRQCHIP (s390)
:Architectures: x86, arm64, s390
:Type: vm ioctl
:Parameters: なし
:Returns: 成功時は 0、エラー時は -1

カーネル内に割り込みコントローラのモデルを作成する。
x86 では、仮想 ioapic と仮想 PIC（入れ子になった 2 つの PIC）を作成し、以降に
作成される vCPU がローカル APIC を持つように設定する。GSI 0〜15 の IRQ
ルーティングは PIC と IOAPIC の両方に設定され、GSI 16〜23 は IOAPIC にのみ
送られる。この ioctl は、vCPU を 1 つも作成する前にしか呼び出せない。
arm64 では、GICv2 が作成される。その他の GIC バージョンでは KVM_CREATE_DEVICE
を使う必要があり、KVM_CREATE_DEVICE は GICv2 の作成にも対応している。GICv2
では、KVM_CREATE_IRQCHIP よりも KVM_CREATE_DEVICE を使うことが推奨される。
s390 では、ダミーの IRQ ルーティングテーブルが作成される。

x86 では、以降の vCPU 作成のときに、デフォルトの APIC ベースアドレス
（0xfee00000）にプライベートな 4 KiB のメモリスロットが設定されることがある。
ユーザメモリ領域はこのアドレスと重なってはならない。重なった場合、vCPU の
作成は ``EEXIST`` で失敗するか、vCPU の作成後にそのメモリ領域を作成すると
メモリ領域が拒否される。これは APIC アクセスの高速化（Intel では APICv、AMD
では AVIC）が有効なときに起こり、対応ハードウェアではこれがデフォルトである。
``KVM_CAP_SPLIT_IRQCHIP`` を使う場合も同じ制約が当てはまる。

s390 では、KVM_CREATE_IRQCHIP を使う前に、vm ケイパビリティ
KVM_CAP_S390_IRQCHIP を有効にする必要がある点に注意する。


4.25 KVM_IRQ_LINE
-----------------

:Capability: KVM_CAP_IRQCHIP
:Architectures: x86, arm64
:Type: vm ioctl
:Parameters: struct kvm_irq_level
:Returns: 成功時は 0、エラー時は -1

カーネル内の割り込みコントローラのモデルへの GSI 入力のレベルを設定する。
一部のアーキテクチャでは、あらかじめ KVM_CREATE_IRQCHIP で割り込みコントローラの
モデルを作成しておく必要がある。エッジトリガ割り込みでは、レベルを 1 に設定して
から 0 に戻す必要がある点に注意する。

実ハードウェアでは、割り込みピンはアクティブローにもアクティブハイにもなりうる。
これは struct kvm_irq_level の level フィールドには関係しない。1 は常にアクティブ
（アサート）を、0 は非アクティブ（デアサート）を意味する。

x86 では、オペレーティングシステムがレベルトリガ割り込みの極性
（アクティブロー／アクティブハイ）をプログラムでき、KVM はかつてその極性を
考慮していた。しかし、アクティブロー割り込みの扱いが劣化したため、上記の規約は
今では x86 でも有効である。これは KVM_CAP_X86_IOAPIC_POLARITY_IGNORED で
通知される。ユーザ空間は、このケイパビリティが存在しない限り（もちろん、
カーネル内 irqchip を使っていない場合を除き）、ゲストへの割り込みを
アクティブローとして提示すべきではない。


arm64 では、CPU レベルとカーネル内 irqchip（GIC）のどちらでも割り込みを通知できる。
カーネル内 irqchip の場合は、特定の CPU 向けに指定された PPI を使うよう GIC に
伝えられる。irq フィールドは次のように解釈される::

  bits:  |  31 ... 28  | 27 ... 24 | 23  ... 16 | 15 ... 0 |
  field: | vcpu2_index | irq_type  | vcpu_index |  irq_id  |

irq_type フィールドの値は次のとおりである。

- KVM_ARM_IRQ_TYPE_CPU:
	       カーネル外 GIC: irq_id 0 は IRQ、irq_id 1 は FIQ
- KVM_ARM_IRQ_TYPE_SPI:
	       カーネル内 GICv2/GICv3: SPI、irq_id は 32〜1019（両端を含む）
               （vcpu_index フィールドは無視される）
	       カーネル内 GICv5: SPI、irq_id は 0 から、設定された SPI の数を
	       1 減らした値まで（最大 1023）
- KVM_ARM_IRQ_TYPE_PPI:
	       カーネル内 GICv2/GICv3: PPI、irq_id は 16〜31（両端を含む）
	       カーネル内 GICv5: PPI、irq_id は 0〜127（両端を含む）

（したがって irq_id フィールドは、ARM GIC 仕様の IRQ ID とよく対応する）

どちらの場合も、level はラインのアサート／デアサートに使われる。

KVM_CAP_ARM_IRQ_LINE_LAYOUT_2 がサポートされている場合、対象の vCPU は
(256 * vcpu2_index + vcpu_index) で識別される。そうでない場合、vcpu2_index は
0 でなければならない。

arm64 では、ケイパビリティ KVM_CAP_IRQCHIP が条件とするのは、カーネル内 irqchip
に対する割り込み注入だけである点に注意する。ユーザ空間の割り込みコントローラに
対しては、KVM_IRQ_LINE を常に使える。

::

  struct kvm_irq_level {
	union {
		__u32 irq;     /* GSI */
		__s32 status;  /* not used for KVM_IRQ_LEVEL */
	};
	__u32 level;           /* 0 or 1 */
  };


4.26 KVM_GET_IRQCHIP
--------------------

:Capability: KVM_CAP_IRQCHIP
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_irqchip (in/out)
:Returns: 成功時は 0、エラー時は -1

KVM_CREATE_IRQCHIP で作成したカーネル内割り込みコントローラの状態を、呼び出し側が
用意したバッファに読み出す。

::

  struct kvm_irqchip {
	__u32 chip_id;  /* 0 = PIC1, 1 = PIC2, 2 = IOAPIC */
	__u32 pad;
        union {
		char dummy[512];  /* reserving space */
		struct kvm_pic_state pic;
		struct kvm_ioapic_state ioapic;
	} chip;
  };


4.27 KVM_SET_IRQCHIP
--------------------

:Capability: KVM_CAP_IRQCHIP
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_irqchip (in)
:Returns: 成功時は 0、エラー時は -1

KVM_CREATE_IRQCHIP で作成したカーネル内割り込みコントローラの状態を、呼び出し側が
用意したバッファから設定する。

::

  struct kvm_irqchip {
	__u32 chip_id;  /* 0 = PIC1, 1 = PIC2, 2 = IOAPIC */
	__u32 pad;
        union {
		char dummy[512];  /* reserving space */
		struct kvm_pic_state pic;
		struct kvm_ioapic_state ioapic;
	} chip;
  };


4.28 KVM_XEN_HVM_CONFIG
-----------------------

:Capability: KVM_CAP_XEN_HVM
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_xen_hvm_config (in)
:Returns: 成功時は 0、エラー時は -1

Xen HVM ゲストがハイパーコールページの初期化に使う MSR を設定し、ユーザ空間に
あるハイパーコール blob の開始アドレスとサイズを指定する。ゲストがその MSR に
書き込むと、kvm は blob の 1 ページ（32 ビットまたは 64 ビット、vCPU モードに
よる）をゲストメモリにコピーする。

MSR のインデックスは [0x40000000, 0x4fffffff] の範囲でなければならない。
つまり、ハイパーバイザでの使用のために非公式に予約された範囲内にある必要がある。
最小値と最大値は KVM_XEN_MSR_MIN_INDEX と KVM_XEN_MSR_MAX_INDEX で列挙されている。

::

  struct kvm_xen_hvm_config {
	__u32 flags;
	__u32 msr;
	__u64 blob_addr_32;
	__u64 blob_addr_64;
	__u8 blob_size_32;
	__u8 blob_size_64;
	__u8 pad2[30];
  };

KVM_CAP_XEN_HVM のチェックで特定のフラグが返された場合、それらをこの ioctl の
flags フィールドに設定できる:

KVM_XEN_HVM_CONFIG_INTERCEPT_HCALL フラグは、ハイパーコールページの内容を KVM が
自動的に生成するよう要求する。ハイパーコールは横取りされ、KVM_EXIT_XEN を通じて
ユーザ空間に渡される。この場合、blob のサイズとアドレスの各フィールドはすべて
0 でなければならない。

KVM_XEN_HVM_CONFIG_EVTCHN_SEND フラグは、ユーザ空間がゲストの shared_info 構造体を
直接操作するのではなく、常に KVM_XEN_HVM_EVTCHN_SEND ioctl を使ってイベント
チャネル割り込みを配送することを KVM に示す。これにより KVM は、たとえば
SCHEDOP_poll ハイパーコールを横取りしてゲストの PV スピンロック操作を高速化すると
いった機能を有効にできる場合がある。ユーザ空間は、この「常にそうする」という表明を
送らなくても、告知されていればその ioctl を使ってイベントを配送してよい

struct kvm_xen_hvm_config では、現在ほかに有効なフラグはない。

4.29 KVM_GET_CLOCK
------------------

:Capability: KVM_CAP_ADJUST_CLOCK
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_clock_data (out)
:Returns: 成功時は 0、エラー時は -1

現在のゲストから見た kvmclock の現在のタイムスタンプを取得する。KVM_SET_CLOCK と
組み合わせて、マイグレーションなどの場面で単調性を保つために使われる。

KVM_CAP_ADJUST_CLOCK を KVM_CHECK_EXTENSION に渡すと、struct kvm_clock_data の
flag メンバで KVM が返せるビットの集合が返る。

次のフラグが定義されている:

KVM_CLOCK_TSC_STABLE
  設定されている場合、返される値は、KVM_GET_CLOCK が呼び出された時点で
  全 VCPU が見る正確な kvmclock の値である。
  クリアされている場合、返される値は単に CLOCK_MONOTONIC に一定のオフセットを
  加えたものになる。オフセットは KVM_SET_CLOCK で変更できる。KVM は全 VCPU を
  このクロックに従わせようとするが、ホストの TSC が安定していないため、
  各 VCPU が読み取る正確な値は異なることがある。

KVM_CLOCK_REALTIME
  設定されている場合、kvm_clock_data 構造体の `realtime` フィールドに、
  KVM_GET_CLOCK が呼び出された時点でのホストのリアルタイムクロックソースの値が
  格納される。クリアされている場合、`realtime` フィールドには値が入らない。

KVM_CLOCK_HOST_TSC
  設定されている場合、kvm_clock_data 構造体の `host_tsc` フィールドに、
  KVM_GET_CLOCK が呼び出された時点でのホストのタイムスタンプカウンタ（TSC）の値が
  格納される。クリアされている場合、`host_tsc` フィールドには値が入らない。

::

  struct kvm_clock_data {
	__u64 clock;  /* kvmclock current value */
	__u32 flags;
	__u32 pad0;
	__u64 realtime;
	__u64 host_tsc;
	__u32 pad[4];
  };


4.30 KVM_SET_CLOCK
------------------

:Capability: KVM_CAP_ADJUST_CLOCK
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_clock_data (in)
:Returns: 成功時は 0、エラー時は -1

kvmclock の現在のタイムスタンプを、引数で指定した値に設定する。KVM_GET_CLOCK と
組み合わせて、マイグレーションなどの場面で単調性を保つために使われる。

次のフラグを渡せる:

KVM_CLOCK_REALTIME
  設定されている場合、KVM は `realtime` フィールドの値を、KVM_SET_CLOCK が
  呼び出された時点でのホストのリアルタイムクロックソースの値と比較する。
  経過時間の差は、ゲストに提供される最終的な kvmclock の値に加算される。

``KVM_GET_CLOCK`` が返すその他のフラグは受け付けられるが無視される。

::

  struct kvm_clock_data {
	__u64 clock;  /* kvmclock current value */
	__u32 flags;
	__u32 pad0;
	__u64 realtime;
	__u64 host_tsc;
	__u32 pad[4];
  };


4.31 KVM_GET_VCPU_EVENTS
------------------------

:Capability: KVM_CAP_VCPU_EVENTS
:Extended by: KVM_CAP_INTR_SHADOW
:Architectures: x86, arm64
:Type: vcpu ioctl
:Parameters: struct kvm_vcpu_events (out)
:Returns: 成功時は 0、エラー時は -1

x86 の場合:
^^^^^^^^^^^

vCPU で現在保留中の例外、割り込み、NMI、および関連する状態を取得する。

::

  struct kvm_vcpu_events {
	struct {
		__u8 injected;
		__u8 nr;
		__u8 has_error_code;
		__u8 pending;
		__u32 error_code;
	} exception;
	struct {
		__u8 injected;
		__u8 nr;
		__u8 soft;
		__u8 shadow;
	} interrupt;
	struct {
		__u8 injected;
		__u8 pending;
		__u8 masked;
		__u8 pad;
	} nmi;
	__u32 sipi_vector;
	__u32 flags;
	struct {
		__u8 smm;
		__u8 pending;
		__u8 smm_inside_nmi;
		__u8 latched_init;
	} smi;
	__u8 reserved[27];
	__u8 exception_has_payload;
	__u64 exception_payload;
  };

flags フィールドには次のビットが定義されている:

- KVM_VCPUEVENT_VALID_SHADOW を設定すると、interrupt.shadow が有効な状態を
  保持していることを示せる。

- KVM_VCPUEVENT_VALID_SMM を設定すると、smi が有効な状態を保持していることを
  示せる。

- KVM_VCPUEVENT_VALID_PAYLOAD を設定すると、exception_has_payload、
  exception_payload、exception.pending の各フィールドが有効な状態を保持して
  いることを示せる。このビットは、KVM_CAP_EXCEPTION_PAYLOAD が有効なときは
  常に設定される。

- KVM_VCPUEVENT_VALID_TRIPLE_FAULT を設定すると、triple_fault_pending フィールドが
  有効な状態を保持していることを示せる。このビットは、
  KVM_CAP_X86_TRIPLE_FAULT_EVENT が有効なときは常に設定される。

arm64 の場合:
^^^^^^^^^^^^^

ゲストがホストカーネルによってエミュレートされているデバイスにアクセスし、それが
実デバイスであれば物理 SError を発生させるようなアクセスだった場合、KVM はその
VCPU に対して仮想 SError を保留にすることがある。このシステムエラー割り込みは、
ゲストが PSTATE.A をアンマスクして例外を処理するまで保留のままである。

VCPU を実行すると、保留中の SError を処理したり、SError が保留になるような
アクセスを行ったりすることがある。このイベントの記述が有効なのは、VCPU が
実行されていない間だけである。

この API は、ゲストから見えない保留中の「イベント」状態を読み書きする手段を
提供する。VCPU を保存、復元、マイグレーションするには、状態を表す構造体を
この GET/SET API で読み出してから書き戻す。これは他のゲスト可視のレジスタと
合わせて行う。保留にされた SError を「キャンセル」することはできない。

ユーザ空間でエミュレートされているデバイスも SError を生成したいことがある。
そのためには、ユーザ空間で events 構造体に値を設定すればよい。既存の SError が
保留になっていないことを確かめるため、まず現在の状態を読み出すべきである。
既存の SError が保留になっている場合は、アーキテクチャの「Multiple SError
interrupts」の規則に従うべきである（DDI0587.a "ARM Reliability, Availability,
and Serviceability (RAS) Specification" の 2.5.3 節）。

SError 例外は常に ESR 値を持つ。仮想 SError の ESR 値を指定できる CPU もある。
そうしたシステムは KVM_CAP_ARM_INJECT_SERROR_ESR を告知する。この場合、
読み出し時に exception.has_esr は常に非ゼロの値を持ち、SError を保留に
しようとする側は ISS フィールドを exception.serror_esr の下位 24 ビットに
指定すべきである。システムが KVM_CAP_ARM_INJECT_SERROR_ESR をサポートしている
のに、ユーザ空間が exception.has_esr を 0 にして events を設定した場合、KVM が
ESR を選ぶ。

サポートしていないシステムで exception.has_esr を指定すると -EINVAL が返る。
exception.serror_esr の下位 24 ビット以外を設定しても -EINVAL が返る。

保留中の外部アボート（KVM_SET_VCPU_EVENTS などで注入されたもの）を読み戻すことは
できない。そのような例外は常に仮想 CPU に直接配送されるためである。

初期化されていない vCPU に対してこの ioctl を呼び出すと -ENOEXEC が返る。

::

  struct kvm_vcpu_events {
	struct {
		__u8 serror_pending;
		__u8 serror_has_esr;
		__u8 ext_dabt_pending;
		/* Align it to 8 bytes */
		__u8 pad[5];
		__u64 serror_esr;
	} exception;
	__u32 reserved[12];
  };

4.32 KVM_SET_VCPU_EVENTS
------------------------

:Capability: KVM_CAP_VCPU_EVENTS
:Extended by: KVM_CAP_INTR_SHADOW
:Architectures: x86, arm64
:Type: vcpu ioctl
:Parameters: struct kvm_vcpu_events (in)
:Returns: 成功時は 0、エラー時は -1

x86 の場合:
^^^^^^^^^^^

vCPU で保留中の例外、割り込み、NMI、および関連する状態を設定する。

データ構造については KVM_GET_VCPU_EVENTS を参照。

実行中の VCPU によって非同期に変更されうるフィールドは、更新から除外できる。
そのフィールドは nmi.pending、sipi_vector、smi.smm、smi.pending である。
現在のカーネル内の状態を上書きしないよう、flags フィールドの対応するビットは
クリアしたままにする。そのビットは次のとおり:

===============================  ==================================
KVM_VCPUEVENT_VALID_NMI_PENDING  transfer nmi.pending to the kernel
KVM_VCPUEVENT_VALID_SIPI_VECTOR  transfer sipi_vector
KVM_VCPUEVENT_VALID_SMM          transfer the smi sub-struct.
===============================  ==================================

KVM_CAP_INTR_SHADOW が利用できる場合、flags フィールドに
KVM_VCPUEVENT_VALID_SHADOW を設定して、interrupt.shadow が有効な状態を保持して
おり、VCPU に書き込まれるべきであることを示せる。

KVM_VCPUEVENT_VALID_SMM は、KVM_CAP_X86_SMM が利用できる場合にのみ設定できる。

KVM_CAP_EXCEPTION_PAYLOAD が有効な場合、flags フィールドに
KVM_VCPUEVENT_VALID_PAYLOAD を設定して、exception_has_payload、
exception_payload、exception.pending の各フィールドが有効な状態を保持しており、
VCPU に書き込まれるべきであることを示せる。

KVM_CAP_X86_TRIPLE_FAULT_EVENT が有効な場合、flags フィールドに
KVM_VCPUEVENT_VALID_TRIPLE_FAULT を設定して、triple_fault フィールドが有効な
状態を保持しており、VCPU に書き込まれるべきであることを示せる。

arm64 の場合:
^^^^^^^^^^^^^

ユーザ空間は、いくつかの種類のイベントをゲストに注入する必要があることがある。

この VCPU の保留中の SError 例外状態を設定する。保留にされた SError を
「キャンセル」することはできない。

ゲストが I/O メモリへのアクセスを行い、それをユーザ空間で処理できなかった場合、
たとえば命令のシンドロームのデコード情報が欠けている、あるいはアクセスされた
IPA にデバイスがマップされていない場合、ユーザ空間は、終了したフォールトの
アドレスを使って VCPU に外部アボートを注入するようカーネルに要求できる。
KVM_EXIT_MMIO、KVM_EXIT_ARM_NISV、KVM_EXIT_ARM_LDST64B のいずれでもない終了の
後に ext_dabt_pending を設定するのはプログラミングエラーである。この機能は、
システムが KVM_CAP_ARM_INJECT_EXT_DABT をサポートしている場合にのみ利用できる。
これは、上記の場合のアクセスをゲストにどう報告するかを、異なるユーザ空間の
実装間で共通化するための補助機能である。とはいえ、ユーザ空間は KVM_SET_ONE_REG
API を使って個々のレジスタを操作することで、すべての Arm 例外を今も
エミュレートできる。

保護 VM では、ext_dabt_pending を設定すると -EPERM が返る。
Documentation/virt/kvm/arm/pkvm.rst を参照。SError の注入は影響を受けない。

データ構造については KVM_GET_VCPU_EVENTS を参照。

初期化されていない vCPU に対してこの ioctl を呼び出すと -ENOEXEC が返る。

4.33 KVM_GET_DEBUGREGS
----------------------

:Capability: KVM_CAP_DEBUGREGS
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_debugregs (out)
:Returns: 成功時は 0、エラー時は -1

vCPU からデバッグレジスタを読み出す。

::

  struct kvm_debugregs {
	__u64 db[4];
	__u64 dr6;
	__u64 dr7;
	__u64 flags;
	__u64 reserved[9];
  };


4.34 KVM_SET_DEBUGREGS
----------------------

:Capability: KVM_CAP_DEBUGREGS
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_debugregs (in)
:Returns: 成功時は 0、エラー時は -1

デバッグレジスタを vCPU に書き込む。

データ構造は KVM_GET_DEBUGREGS を参照。flags フィールドはまだ使われておらず、
渡すときには 0 にクリアされていなければならない。


4.35 KVM_SET_USER_MEMORY_REGION
-------------------------------

:Capability: KVM_CAP_USER_MEMORY
:Architectures: all
:Type: vm ioctl
:Parameters: struct kvm_userspace_memory_region (in)
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_userspace_memory_region {
	__u32 slot;
	__u32 flags;
	__u64 guest_phys_addr;
	__u64 memory_size; /* bytes */
	__u64 userspace_addr; /* start of the userspace allocated memory */
  };

  /* for kvm_userspace_memory_region::flags */
  #define KVM_MEM_LOG_DIRTY_PAGES	(1UL << 0)
  #define KVM_MEM_READONLY	(1UL << 1)

この ioctl を使うと、ユーザはゲスト物理メモリスロットを作成、変更、削除できる。
"slot" のビット 0〜15 がスロット ID を指定し、この値は VM ごとにサポートされる
ユーザメモリスロットの最大数より小さくなければならない。許可されるスロットの
最大数は KVM_CAP_NR_MEMSLOTS で問い合わせできる。スロットはゲスト物理
アドレス空間で重なってはならない。

KVM_CAP_MULTI_ADDRESS_SPACE が利用できる場合、"slot" のビット 16〜31 が変更
対象のアドレス空間を指定する。この値は、KVM_CAP_MULTI_ADDRESS_SPACE
ケイパビリティに対して KVM_CHECK_EXTENSION が返す値より小さくなければ
ならない。別々のアドレス空間にあるスロットは互いに関係がない。スロットの
重なりに関する制限は、各アドレス空間の中でのみ適用される。

スロットの削除は、memory_size に 0 を渡して行う。既存のスロットを変更する
ときは、ゲスト物理メモリ空間内で移動させるか、フラグを変更することはできるが、
サイズは変更できない。

領域のメモリは、userspace_addr フィールドが示すアドレスから取得する。この
アドレスは、メモリスロットのサイズ全体にわたってユーザがアドレス指定できる
メモリを指していなければならない。このメモリのバッキングには、匿名メモリ、
通常のファイル、hugetlbfs など、任意のオブジェクトを使える。メモリ領域の
バッキングの変更は、自動的にゲストに反映される。たとえば、この領域に影響する
mmap() は直ちに可視になる。もう一つの例は madvise(MADV_DROP) である。

何らかの形のアドレスタグ付けをサポートするアーキテクチャでは、userspace_addr
はタグなしのアドレスでなければならない。

guest_phys_addr と userspace_addr の下位 21 ビットを一致させることが推奨される。
こうすると、ゲストのラージページをホストのラージページでバックできる。

flags フィールドは KVM_MEM_LOG_DIRTY_PAGES と KVM_MEM_READONLY の 2 つの
フラグをサポートする。前者を設定すると、スロット内のメモリへの書き込みを
KVM に追跡させることができる。使い方は KVM_GET_DIRTY_LOG ioctl を参照。
後者は、KVM_CAP_READONLY_MEM ケイパビリティが許す場合に設定でき、新しい
スロットを読み取り専用にする。この場合、このメモリへの書き込みは
KVM_EXIT_MMIO エグジットとしてユーザ空間に通知される。

TDX ゲストでは、メモリ領域を削除または移動するとゲストメモリの内容が失われる。
読み取り専用の領域はサポートされない。サポートされるのは as-id 0 だけである。

備考: arm64 では、スロットに KVM_MEM_READONLY フラグが付いている場合、
ページテーブルウォーカが生成する書き込み (たとえば Access フラグと Dirty
フラグを更新するもの) が KVM_EXIT_MMIO エグジットになることはない。これは、
ページテーブルウォーカが書き込むはずのデータを KVM が提供できず、そのアクセスを
エミュレートできないためである。代わりに、アボート (ページテーブルの更新の
原因がロードやストアならデータアボート、命令フェッチなら命令アボート) が
ゲストに注入される。

S390:
^^^^^

VM に KVM_VM_S390_UCONTROL フラグが設定されている場合は -EINVAL または
-EEXIST を返す。保護 VM に対して呼び出した場合は -EINVAL を返す。


4.36 KVM_SET_TSS_ADDR
---------------------

:Capability: KVM_CAP_SET_TSS_ADDR
:Architectures: x86
:Type: vm ioctl
:Parameters: unsigned long tss_address (in)
:Returns: 成功時は 0、エラー時は -1

この ioctl は、ゲスト物理アドレス空間にある 3 ページ分の領域の物理アドレスを
定義する。この領域は、ゲスト物理アドレス空間の先頭 4GB 以内になければならず、
どのメモリスロットや mmio アドレスとも衝突してはならない。ゲストがこのメモリ
領域にアクセスすると、誤動作するおそれがある。

この ioctl は Intel ベースのホストで必要である。Intel ハードウェアで必要なのは、
仮想化の実装にある癖のためである (内部向けドキュメントができたらそちらを参照)。


.. _KVM_ENABLE_CAP:

4.37 KVM_ENABLE_CAP
-------------------

:Capability: KVM_CAP_ENABLE_CAP
:Architectures: mips, ppc, s390, x86, loongarch
:Type: vcpu ioctl
:Parameters: struct kvm_enable_cap (in)
:Returns: 成功時は 0、エラー時は -1

:Capability: KVM_CAP_ENABLE_CAP_VM
:Architectures: all
:Type: vm ioctl
:Parameters: struct kvm_enable_cap (in)
:Returns: 成功時は 0、エラー時は -1

.. note::

   すべての拡張がデフォルトで有効になっているわけではない。この ioctl を
   使うと、アプリケーションは拡張を有効にして、ゲストから利用できるように
   できる。

この ioctl をサポートしないシステムでは、常に失敗する。サポートするシステム
では、有効化がサポートされている拡張に対してのみ動作する。

ケイパビリティを有効化できるかどうかは、KVM_CHECK_EXTENSION ioctl で調べる
べきである。

::

  struct kvm_enable_cap {
       /* in */
       __u32 cap;

有効化しようとするケイパビリティ。

::

       __u32 flags;

将来の拡張を示すビットフィールド。現時点では 0 でなければならない。

::

       __u64 args[4];

機能を有効化するための引数。機能が正しく動作するために初期値が必要な場合は、
ここに格納する。

::

       __u8  pad[64];
  };

vCPU 固有のケイパビリティには vcpu ioctl を、VM 全体のケイパビリティには
vm ioctl を使うべきである。

4.38 KVM_GET_MP_STATE
---------------------

:Capability: KVM_CAP_MP_STATE
:Architectures: x86, s390, arm64, riscv, loongarch
:Type: vcpu ioctl
:Parameters: struct kvm_mp_state (out)
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_mp_state {
	__u32 mp_state;
  };

vCPU の現在の「マルチプロセッシング状態」を返す (単一プロセッサのゲストでも
有効である)。

取りうる値は次のとおり。

   ==============================    ==========================================================================
   KVM_MP_STATE_RUNNABLE             vCPU は現在実行中 [x86,arm64,riscv,loongarch]
   KVM_MP_STATE_UNINITIALIZED        vCPU はまだ INIT シグナルを受け取っていないアプリケーションプロセッサ
                                     (AP) [x86]、またはゲストが電源オフの状態に保っている保護 VM の vCPU
                                     [arm64]
   KVM_MP_STATE_INIT_RECEIVED        vCPU は INIT シグナルを受け取り、SIPI を待ち受けている [x86]
   KVM_MP_STATE_HALTED               vCPU は HLT 命令を実行し、割り込みを待っている [x86]
   KVM_MP_STATE_SIPI_RECEIVED        vCPU はちょうど SIPI を受け取った (ベクタは KVM_GET_VCPU_EVENTS で
                                     取得できる) [x86]
   KVM_MP_STATE_STOPPED              vCPU は停止している [s390,arm64,riscv]
   KVM_MP_STATE_CHECK_STOP           vCPU は特別なエラー状態にある [s390]
   KVM_MP_STATE_OPERATING            vCPU は動作中 (実行中または停止中) [s390]
   KVM_MP_STATE_LOAD                 vCPU は特別なロード/起動状態にある [s390]
   KVM_MP_STATE_SUSPENDED            vCPU はサスペンド状態にあり、ウェイクアップイベントを待っている [arm64]
   ==============================    ==========================================================================

x86 では、この ioctl は KVM_CREATE_IRQCHIP の後でのみ意味がある。カーネル内
irqchip がない場合、これらのアーキテクチャではマルチプロセッシング状態を
ユーザ空間で管理しなければならない。

arm64 の場合:
^^^^^^^^^^^^^

vCPU が KVM_MP_STATE_SUSPENDED 状態にある場合、KVM は WFI 命令のアーキテクチャ
上の実行をエミュレートする。

ウェイクアップイベントを認識すると、KVM はイベント種別が
KVM_SYSTEM_EVENT_WAKEUP である KVM_SYSTEM_EVENT エグジットでユーザ空間に
戻る。ユーザ空間がウェイクアップを受け入れる場合は、vCPU の MP 状態を
KVM_MP_STATE_RUNNABLE に設定しなければならない。そうしないと、KVM は以降の
KVM_RUN の呼び出しでもウェイクアップイベントを待ち続ける。

.. warning::

     ユーザ空間が vCPU を SUSPENDED 状態のままにしておくつもりなら、
     ウェイクアップイベントを抑止する処置 (たとえば割り込みのマスク) を
     取ることが強く推奨される。そうしないと、以降の KVM_RUN の呼び出しは
     直ちに KVM_SYSTEM_EVENT_WAKEUP イベントで戻り、意図せず CPU サイクルを
     浪費する。

     さらに、ユーザ空間がウェイクアップイベントを抑止する処置を取った場合は、
     vCPU を再び RUNNABLE にするときに vCPU を元の状態に戻すことも強く推奨
     される。たとえば、ウェイクアップを抑止するためにペンディング中の
     割り込みをマスクしたなら、ゲストに制御を戻す前にその割り込みのマスクを
     解除すべきである。

riscv の場合:
^^^^^^^^^^^^^

有効な状態は KVM_MP_STATE_STOPPED と KVM_MP_STATE_RUNNABLE だけであり、
これらは vCPU が一時停止しているかどうかを表す。

LoongArch では、vCPU が実行可能かどうかを表すのに KVM_MP_STATE_RUNNABLE
状態だけを使う。

4.39 KVM_SET_MP_STATE
---------------------

:Capability: KVM_CAP_MP_STATE
:Architectures: x86, s390, arm64, riscv, loongarch
:Type: vcpu ioctl
:Parameters: struct kvm_mp_state (in)
:Returns: 成功時は 0、エラー時は -1

vCPU の現在の「マルチプロセッシング状態」を設定する。引数については
KVM_GET_MP_STATE を参照。

x86 では、この ioctl は KVM_CREATE_IRQCHIP の後でのみ意味がある。カーネル内
irqchip がない場合、これらのアーキテクチャではマルチプロセッシング状態を
ユーザ空間で管理しなければならない。

arm64/riscv の場合:
^^^^^^^^^^^^^^^^^^^

有効な状態は KVM_MP_STATE_STOPPED と KVM_MP_STATE_RUNNABLE だけであり、
これらは vCPU を一時停止すべきかどうかを表す。

arm64 では、保護 VM の vCPU が一度実行された後、ゲストが CPU_OFF で、あるいは
CPU_ON でまだオンラインにせずに電源オフの状態に保っている間は、その vCPU は
KVM_MP_STATE_UNINITIALIZED として見える。また、その vCPU に対して
KVM_MP_STATE_RUNNABLE と KVM_MP_STATE_SUSPENDED は -EPERM を返す。電源を
入れられるのはゲストだけである。Documentation/virt/kvm/arm/pkvm.rst を参照。

LoongArch では、vCPU が実行可能かどうかを表すのに KVM_MP_STATE_RUNNABLE
状態だけを使う。

4.40 KVM_SET_IDENTITY_MAP_ADDR
------------------------------

:Capability: KVM_CAP_SET_IDENTITY_MAP_ADDR
:Architectures: x86
:Type: vm ioctl
:Parameters: unsigned long identity (in)
:Returns: 成功時は 0、エラー時は -1

この ioctl は、ゲスト物理アドレス空間にある 1 ページ分の領域の物理アドレスを
定義する。この領域は、ゲスト物理アドレス空間の先頭 4GB 以内になければならず、
どのメモリスロットや mmio アドレスとも衝突してはならない。ゲストがこのメモリ
領域にアクセスすると、誤動作するおそれがある。

アドレスに 0 を設定すると、アドレスはデフォルト (0xfffbc000) にリセットされる。

この ioctl は Intel ベースのホストで必要である。Intel ハードウェアで必要なのは、
仮想化の実装にある癖のためである (内部向けドキュメントができたらそちらを参照)。

VCPU がすでに作成されている場合は失敗する。

4.41 KVM_SET_BOOT_CPU_ID
------------------------

:Capability: KVM_CAP_SET_BOOT_CPU_ID
:Architectures: x86
:Type: vm ioctl
:Parameters: unsigned long vcpu_id
:Returns: 成功時は 0、エラー時は -1

どの vCPU をブートストラッププロセッサ (BSP) にするかを定義する。値は
KVM_CREATE_VCPU の vCPU ID と同じである。この ioctl を呼び出さない場合、
デフォルトは vCPU 0 である。この ioctl は vCPU の作成前に呼び出さなければ
ならない。そうしないと EBUSY エラーを返す。


4.42 KVM_GET_XSAVE
------------------

:Capability: KVM_CAP_XSAVE
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_xsave (out)
:Returns: 成功時は 0、エラー時は -1


::

  struct kvm_xsave {
	__u32 region[1024];
	__u32 extra[0];
  };

この ioctl は、現在の vCPU の xsave 構造体をユーザ空間にコピーする。


4.43 KVM_SET_XSAVE
------------------

:Capability: KVM_CAP_XSAVE and KVM_CAP_XSAVE2
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_xsave (in)
:Returns: 成功時は 0、エラー時は -1

::


  struct kvm_xsave {
	__u32 region[1024];
	__u32 extra[0];
  };

この ioctl は、ユーザ空間の xsave 構造体をカーネルにコピーする。vm ファイル
ディスクリプタに対して呼び出した KVM_CHECK_EXTENSION(KVM_CAP_XSAVE2) が返す
バイト数だけコピーする。KVM_CHECK_EXTENSION(KVM_CAP_XSAVE2) が返すサイズの値は、
常に 4096 以上である。現時点では、``arch_prctl()`` で動的機能が有効になっている
場合にのみ 4096 より大きくなるが、将来は変わるかもしれない。

struct kvm_xsave 内の状態保存領域のオフセットは、ホストの CPUID リーフ 0xD の
内容に従う。


4.44 KVM_GET_XCRS
-----------------

:Capability: KVM_CAP_XCRS
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_xcrs (out)
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_xcr {
	__u32 xcr;
	__u32 reserved;
	__u64 value;
  };

  struct kvm_xcrs {
	__u32 nr_xcrs;
	__u32 flags;
	struct kvm_xcr xcrs[KVM_MAX_XCRS];
	__u64 padding[16];
  };

この ioctl は、現在の vCPU の xcrs をユーザ空間にコピーする。


4.45 KVM_SET_XCRS
-----------------

:Capability: KVM_CAP_XCRS
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_xcrs (in)
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_xcr {
	__u32 xcr;
	__u32 reserved;
	__u64 value;
  };

  struct kvm_xcrs {
	__u32 nr_xcrs;
	__u32 flags;
	struct kvm_xcr xcrs[KVM_MAX_XCRS];
	__u64 padding[16];
  };

この ioctl は、vCPU の xcr をユーザ空間が指定した値に設定する。

4.46 KVM_GET_SUPPORTED_CPUID
----------------------------

:Capability: KVM_CAP_EXT_CPUID
:Architectures: x86
:Type: system ioctl
:Parameters: struct kvm_cpuid2 (in/out)
:Returns: 0 on success, -1 on error

::

  struct kvm_cpuid2 {
	__u32 nent;
	__u32 padding;
	struct kvm_cpuid_entry2 entries[0];
  };

  #define KVM_CPUID_FLAG_SIGNIFCANT_INDEX		BIT(0)
  #define KVM_CPUID_FLAG_STATEFUL_FUNC		BIT(1) /* deprecated */
  #define KVM_CPUID_FLAG_STATE_READ_NEXT		BIT(2) /* deprecated */

  struct kvm_cpuid_entry2 {
	__u32 function;
	__u32 index;
	__u32 flags;
	__u32 eax;
	__u32 ebx;
	__u32 ecx;
	__u32 edx;
	__u32 padding[3];
  };

この ioctl は、ハードウェアと既定設定の kvm の両方がサポートする x86 の
cpuid 機能を返す。ユーザ空間は、この ioctl が返す情報を使って、ハードウェア、
カーネル、ユーザ空間のケイパビリティと、ユーザの要件に整合する cpuid 情報
（KVM_SET_CPUID2 用）を組み立てられる。たとえば、ユーザが古いハードウェアを
エミュレートするために cpuid を制限したい場合や、クラスタ全体で機能を
そろえたい場合がある。

動的に有効化する機能ビットは、この ioctl を呼ぶ前に ``arch_prctl()`` で
要求しておく必要がある。要求していない機能ビットは結果に含まれない。

一部のケイパビリティ（KVM_CAP_X86_DISABLE_EXITS など）は、既定設定の kvm が
サポートしない cpuid 機能（MONITOR など）を公開する場合がある。ユーザ空間が
そのようなケイパビリティを有効にするなら、この ioctl の結果を適切に修正する
のはユーザ空間の責任である。

ユーザ空間は、可変長配列 'entries' のエントリ数を 'nent' フィールドで示した
kvm_cpuid2 構造体を渡して KVM_GET_SUPPORTED_CPUID を呼ぶ。エントリ数が cpu の
ケイパビリティを記述するには少なすぎる場合、エラー（E2BIG）が返る。多すぎる
場合、'nent' フィールドが調整され、エラー（ENOMEM）が返る。ちょうどよい場合、
'nent' フィールドは 'entries' 配列の有効なエントリ数に調整され、配列が
埋められる。

返されるエントリは、cpuid 命令が返すホストの cpuid から、不明または
未サポートの機能をマスクしたものだ。一部の機能（x2apic など）はホストの
cpu に存在しなくても、kvm が効率よくエミュレートできるなら公開される。
各エントリのフィールドは次のとおり。

  function:
         エントリを得るために使った eax の値

  index:
         エントリを得るために使った ecx の値（ecx の影響を受けるエントリの場合）

  flags:
     次のゼロ個以上の OR:

        KVM_CPUID_FLAG_SIGNIFCANT_INDEX:
           index フィールドが有効なら

   eax, ebx, ecx, edx:
         この function/index の組み合わせについて cpuid 命令が返す値

x2APIC（CPUID leaf 1、ecx[21)）と TSC デッドラインタイマー（CPUID leaf 1、
ecx[24]）は true として返る場合があるが、これらは local APIC のカーネル内
エミュレーションのための KVM_CREATE_IRQCHIP に依存する。TSC デッドライン
タイマーのサポートは次のようにも報告される::

  ioctl(KVM_CHECK_EXTENSION, KVM_CAP_TSC_DEADLINE_TIMER)

これが true を返し、かつ KVM_CREATE_IRQCHIP を使う場合、またはユーザ空間で
この機能をエミュレートする場合は、KVM_SET_CPUID2 でこの機能を有効にできる。

KVM_SET_CPUID2 で x2APIC を有効にするには KVM_CREATE_IRQCHIP が必要である。
KVM は x2APIC の MSR アクセスをユーザ空間へ転送することをサポートせず、
すなわち KVM はユーザ空間での x2APIC のエミュレーションをサポートしない。

4.47 KVM_PPC_GET_PVINFO
-----------------------

:Capability: KVM_CAP_PPC_GET_PVINFO
:Architectures: ppc
:Type: vm ioctl
:Parameters: struct kvm_ppc_pvinfo (out)
:Returns: 0 on success, !0 on error

::

  struct kvm_ppc_pvinfo {
	__u32 flags;
	__u32 hcall[4];
	__u8  pad[108];
  };

この ioctl は、デバイスツリーなどの手段でゲストに渡す必要のある PV 固有の
情報を、vm のコンテキストから取得する。

hcall 配列は、ハイパーコールを構成する 4 個の命令を定義する。

将来この構造体にフィールドが追加される場合は、その追加情報に対応するビットが
flags ビットマップに設定される。

flags ビットマップは次のように定義される::


   /* the host supports the ePAPR idle hcall
   #define KVM_PPC_PVINFO_FLAGS_EV_IDLE   (1<<0)

4.52 KVM_SET_GSI_ROUTING
------------------------

:Capability: KVM_CAP_IRQ_ROUTING
:Architectures: x86 s390 arm64
:Type: vm ioctl
:Parameters: struct kvm_irq_routing (in)
:Returns: 0 on success, -1 on error

GSI ルーティングテーブルのエントリを設定し、以前に設定したエントリを上書きする。

arm64 では、GSI ルーティングには次の制限がある。

- GSI ルーティングは KVM_IRQ_LINE には適用されず、KVM_IRQFD にのみ適用される。

::

  struct kvm_irq_routing {
	__u32 nr;
	__u32 flags;
	struct kvm_irq_routing_entry entries[0];
  };

現時点ではフラグは定義されていない。対応するフィールドは 0 にしなければ
ならない。

::

  struct kvm_irq_routing_entry {
	__u32 gsi;
	__u32 type;
	__u32 flags;
	__u32 pad;
	union {
		struct kvm_irq_routing_irqchip irqchip;
		struct kvm_irq_routing_msi msi;
		struct kvm_irq_routing_s390_adapter adapter;
		struct kvm_irq_routing_hv_sint hv_sint;
		struct kvm_irq_routing_xen_evtchn xen_evtchn;
		__u32 pad[8];
	} u;
  };

  /* gsi routing entry types */
  #define KVM_IRQ_ROUTING_IRQCHIP 1
  #define KVM_IRQ_ROUTING_MSI 2
  #define KVM_IRQ_ROUTING_S390_ADAPTER 3
  #define KVM_IRQ_ROUTING_HV_SINT 4
  #define KVM_IRQ_ROUTING_XEN_EVTCHN 5

s390 では、ucontrol VM に KVM_IRQ_ROUTING_S390_ADAPTER を追加すると、
エラー -EINVAL で拒否される。

flags:

- KVM_MSI_VALID_DEVID: KVM_IRQ_ROUTING_MSI ルーティングエントリ種別と
  組み合わせて使い、devid フィールドに有効な値が入っていることを示す。
  VM 単位の KVM_CAP_MSI_DEVID ケイパビリティは、デバイス ID の提供が
  必要であることを通知する。このケイパビリティが利用できない場合、
  ioctl が失敗する可能性があるため、ユーザ空間は KVM_MSI_VALID_DEVID
  フラグを決して設定すべきではない。
- それ以外は 0

::

  struct kvm_irq_routing_irqchip {
	__u32 irqchip;
	__u32 pin;
  };

  struct kvm_irq_routing_msi {
	__u32 address_lo;
	__u32 address_hi;
	__u32 data;
	union {
		__u32 pad;
		__u32 devid;
	};
  };

KVM_MSI_VALID_DEVID が設定されている場合、devid には MSI メッセージを
書き込んだデバイスの一意な識別子が入る。PCI では、通常は下位 16 ビットの
BDF 識別子である。

x86 では、KVM_CAP_X2APIC_API ケイパビリティの
KVM_X2APIC_API_USE_32BIT_IDS 機能が有効でない限り、address_hi は無視される。
有効な場合、address_hi のビット 31-8 が宛先 ID のビット 31-8 になる。
address_hi のビット 7-0 は 0 でなければならない。

::

  struct kvm_irq_routing_s390_adapter {
	__u64 ind_addr;
	__u64 summary_addr;
	__u64 ind_offset;
	__u32 summary_offset;
	__u32 adapter_id;
  };

  struct kvm_irq_routing_hv_sint {
	__u32 vcpu;
	__u32 sint;
  };

  struct kvm_irq_routing_xen_evtchn {
	__u32 port;
	__u32 vcpu;
	__u32 priority;
  };

KVM_CAP_XEN_HVM がサポート機能の通知に KVM_XEN_HVM_CONFIG_EVTCHN_2LEVEL
ビットを含む場合、Xen イベントチャネルへのルーティングがサポートされる。
priority フィールドは存在するが、サポートされる値は
KVM_XEN_HVM_CONFIG_EVTCHN_2LEVEL のみで、これは 2 レベルイベントチャネル
による配信を意味する。FIFO イベントチャネルのサポートは将来追加される
可能性がある。

4.55 KVM_SET_TSC_KHZ
--------------------

:Capability: KVM_CAP_TSC_CONTROL / KVM_CAP_VM_TSC_CONTROL
:Architectures: x86
:Type: vcpu ioctl / vm ioctl
:Parameters: virtual tsc_khz
:Returns: 0 on success, -1 on error

仮想マシンの tsc 周波数を指定する。周波数の単位は KHz。

KVM_CAP_VM_TSC_CONTROL ケイパビリティが通知される場合、これを vm ioctl と
して使い、その後作成する vCPU の初期 tsc 周波数を設定することもできる。
vm ioctl は vCPU を作成する前にのみ許される点に注意。

TSC が保護されたコンフィデンシャルコンピューティング（CoCo）VM では、
TSC 周波数を VM スコープで一度設定し、VM の存続期間中は変更しない。
そのような VM では、TSC 周波数の設定に vm ioctl を使うべきで、vcpu ioctl
はサポートされない。

そのような CoCo VM の例として TDX ゲストがある。

4.56 KVM_GET_TSC_KHZ
--------------------

:Capability: KVM_CAP_GET_TSC_KHZ / KVM_CAP_VM_TSC_CONTROL
:Architectures: x86
:Type: vcpu ioctl / vm ioctl
:Parameters: none
:Returns: virtual tsc-khz on success, negative value on error

ゲストの tsc 周波数を返す。戻り値の単位は KHz。ホストの tsc が不安定な場合、
この ioctl は代わりにエラーとして -EIO を返す。

4.57 KVM_GET_LAPIC
------------------

:Capability: KVM_CAP_IRQCHIP
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_lapic_state (out)
:Returns: 0 on success, -1 on error

::

  #define KVM_APIC_REG_SIZE 0x400
  struct kvm_lapic_state {
	char regs[KVM_APIC_REG_SIZE];
  };

Local APIC のレジスタを読み取り、入力引数にコピーする。データの形式と
レイアウトは、アーキテクチャマニュアルに記載されているものと同じである。

KVM_CAP_X2APIC_API の KVM_X2APIC_API_USE_32BIT_IDS 機能が有効な場合、
APIC_ID レジスタの形式は、その vCPU の APIC モード（MSR_IA32_APICBASE が
通知する）に依存する。x2APIC は APIC ID を APIC_ID レジスタ（バイト 32-35）
に格納する。xAPIC は 8 ビットの APIC ID しか許さず、それは APIC レジスタの
ビット 31-24、すなわち struct kvm_lapic_state の regs フィールドのバイト 35
に格納される。そのため、KVM_SET_MSR で MSR_IA32_APICBASE を設定した後に
KVM_GET_LAPIC を呼ぶ必要がある。

KVM_X2APIC_API_USE_32BIT_IDS 機能が無効な場合、struct kvm_lapic_state は
常に xAPIC 形式を使う。

4.58 KVM_SET_LAPIC
------------------

:Capability: KVM_CAP_IRQCHIP
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_lapic_state (in)
:Returns: 0 on success, -1 on error

::

  #define KVM_APIC_REG_SIZE 0x400
  struct kvm_lapic_state {
	char regs[KVM_APIC_REG_SIZE];
  };

入力引数を Local APIC のレジスタにコピーする。データの形式とレイアウトは、
アーキテクチャマニュアルに記載されているものと同じである。

APIC ID レジスタ（struct kvm_lapic_state の regs フィールドのバイト 32-35）
の形式は、KVM_CAP_X2APIC_API ケイパビリティの状態に依存する。
KVM_GET_LAPIC の注記を参照のこと。

4.59 KVM_IOEVENTFD
------------------

:Capability: KVM_CAP_IOEVENTFD
:Architectures: all
:Type: vm ioctl
:Parameters: struct kvm_ioeventfd (in)
:Returns: 0 on success, !0 on error

この ioctl は、ゲスト内の有効な pio/mmio アドレスに ioeventfd を関連付ける、
または関連付けを解除する。登録したアドレスへのゲストの書き込みは、
エグジットを発生させる代わりに、指定したイベントを通知する。

::

  struct kvm_ioeventfd {
	__u64 datamatch;
	__u64 addr;        /* legal pio/mmio address */
	__u32 len;         /* 0, 1, 2, 4, or 8 bytes    */
	__s32 fd;
	__u32 flags;
	__u8  pad[36];
  };

s390 の virtio-ccw デバイスの特殊なケースでは、ioevent は代わりに
サブチャネルと virtqueue の組に照合される。

次のフラグが定義されている::


  #define KVM_IOEVENTFD_FLAG_DATAMATCH (1 << kvm_ioeventfd_flag_nr_datamatch)
  #define KVM_IOEVENTFD_FLAG_PIO       (1 << kvm_ioeventfd_flag_nr_pio)
  #define KVM_IOEVENTFD_FLAG_DEASSIGN  (1 << kvm_ioeventfd_flag_nr_deassign)
  #define KVM_IOEVENTFD_FLAG_VIRTIO_CCW_NOTIFY \
	(1 << kvm_ioeventfd_flag_nr_virtio_ccw_notify)

datamatch フラグが設定されている場合、登録したアドレスに書き込まれた値が
struct kvm_ioeventfd の datamatch と等しいときにのみ、イベントが通知される。

virtio-ccw デバイスでは、addr にサブチャネル ID が、datamatch に
virtqueue のインデックスが入る。

KVM_CAP_IOEVENTFD_ANY_LENGTH があると、長さ 0 の ioeventfd が許される。
カーネルはゲストの書き込みの長さを無視し、より高速な vmexit を得られる
場合がある。高速化は特定のアーキテクチャにのみ当てはまる場合があるが、
ioeventfd はそれでも動作する。

4.60 KVM_DIRTY_TLB
------------------

:Capability: KVM_CAP_SW_TLB
:Architectures: ppc
:Type: vcpu ioctl
:Parameters: struct kvm_dirty_tlb (in)
:Returns: 0 on success, -1 on error

::

  struct kvm_dirty_tlb {
	__u64 bitmap;
	__u32 num_dirty;
  };

ユーザ空間が共有 TLB のエントリを変更したときは常に、関連する vcpu で
KVM_RUN を呼ぶ前にこれを呼ばなければならない。

"bitmap" フィールドは配列のユーザ空間アドレスである。この配列はビット列
からなり、ビット数は、直前に成功した
``KVM_ENABLE_CAP(KVM_CAP_SW_TLB)`` の呼び出しで決まった TLB エントリの
総数を 64 の倍数に切り上げたものに等しい。

各ビットは 1 個の TLB エントリに対応し、並び順は共有 TLB 配列と同じである。

配列はリトルエンディアンである。ビット 0 は最初のバイトの最下位ビット、
ビット 8 は 2 番目のバイトの最下位ビット、以下同様である。これにより、
ワードサイズの違いによる問題を避けられる。

"num_dirty" フィールドは、ビットマップの処理を省略してすべてを無効化すべき
かを KVM が判断するためのパフォーマンスヒントである。ビットマップ内で
セットされているビット数に設定しなければならない。

4.62 KVM_CREATE_SPAPR_TCE
-------------------------

:Capability: KVM_CAP_SPAPR_TCE
:Architectures: powerpc
:Type: vm ioctl
:Parameters: struct kvm_create_spapr_tce (in)
:Returns: file descriptor for manipulating the created TCE table

これは仮想 TCE（translation control entry）テーブルを作成する。TCE テーブル
は PAPR 形式の仮想 I/O 用の IOMMU である。仮想 I/O で使う論理アドレスを
ゲストの物理アドレスに変換するために使い、PAPR 仮想 I/O に scatter/gather
機能を提供する。

::

  /* for KVM_CAP_SPAPR_TCE */
  struct kvm_create_spapr_tce {
	__u64 liobn;
	__u32 window_size;
  };

liobn フィールドは、TCE テーブルを作成する対象の論理 IO バス番号を与える。
window_size フィールドは、この TCE テーブルが変換する DMA ウィンドウの
サイズを指定する。テーブルには、DMA ウィンドウの 4kiB ごとに 64 ビットの
TCE エントリが 1 個ずつ入る。

この ioctl() で TCE テーブルを作成した liobn に対してゲストが H_PUT_TCE
ハイパーコールを発行すると、カーネルはリアルモードでそれを処理し、
TCE テーブルを更新する。他の liobn への H_PUT_TCE 呼び出しは vm エグジットを
発生させ、ユーザ空間が処理しなければならない。

戻り値はファイルディスクリプタで、mmap(2) に渡すと作成した TCE テーブルを
ユーザ空間にマップできる。これにより、ユーザ空間はカーネルが処理した
H_PUT_TCE 呼び出しが書き込んだエントリを読める。また、状況によっては
有用なことに、ユーザ空間が TCE テーブルを直接更新できる。

4.64 KVM_NMI
------------

:Capability: KVM_CAP_USER_NMI
:Architectures: x86
:Type: vcpu ioctl
:Parameters: none
:Returns: 0 on success, -1 on error

スレッドの vcpu に NMI をキューに入れる。これは仮想 CPU コアと仮想 local APIC
の間のインタフェースなので、KVM_CREATE_IRQCHIP を呼んでいない場合にのみ
明確に定義される点に注意。KVM_CREATE_IRQCHIP を呼んだ後は、このインタフェース
は完全にカーネル内でエミュレートされる。

KVM_CREATE_IRQCHIP と組み合わせてこれを使い LINT1 入力をエミュレートするには、
次の手順を使う。

  - vcpu を一時停止する
  - local APIC の状態を読む（KVM_GET_LAPIC）
  - LINT1 を変更すると NMI がキューに入るかを確認する（LINT1 の LVT エントリを参照）
  - そうなら KVM_NMI を発行する
  - vcpu を再開する

一部のゲストは、デバッグの助けとして、LINT1 NMI 入力がパニックを起こすように
設定する。

4.65 KVM_S390_UCAS_MAP
----------------------

:Capability: KVM_CAP_S390_UCONTROL
:Architectures: s390
:Type: vcpu ioctl
:Parameters: struct kvm_s390_ucas_mapping (in)
:Returns: 0 in case of success

パラメータは次のように定義される::


	struct kvm_s390_ucas_mapping {
		__u64 user_addr;
		__u64 vcpu_addr;
		__u64 length;
	};

この ioctl は、"user_addr" にある長さ "length" のメモリを、"vcpu_addr" から
始まる vcpu のアドレス空間にマップする。すべてのパラメータは 1 メガバイト
単位でアラインされている必要がある。

4.66 KVM_S390_UCAS_UNMAP
------------------------

:Capability: KVM_CAP_S390_UCONTROL
:Architectures: s390
:Type: vcpu ioctl
:Parameters: struct kvm_s390_ucas_mapping (in)
:Returns: 0 in case of success

パラメータは次のように定義される::


	struct kvm_s390_ucas_mapping {
		__u64 user_addr;
		__u64 vcpu_addr;
		__u64 length;
	};

この ioctl は、"vcpu_addr" から始まる長さ "length" のメモリを vcpu の
アドレス空間からアンマップする。"user_addr" フィールドは無視される。
すべてのパラメータは 1 メガバイト単位でアラインされている必要がある。

4.67 KVM_S390_VCPU_FAULT
------------------------

:Capability: KVM_CAP_S390_UCONTROL
:Architectures: s390
:Type: vcpu ioctl
:Parameters: vcpu absolute address (in)
:Returns: 0 in case of success

この呼び出しは、仮想 CPU のアドレス空間（ユーザ制御の仮想マシンの場合）
または仮想マシンのアドレス空間（通常の仮想マシンの場合）にページテーブル
エントリを作成する。マイナーフォールトにのみ機能するため、対象のメモリ
ページにはあらかじめユーザページテーブル経由でアクセスしておくことを
推奨する。ユーザ制御の仮想マシンで、KVM_RUN ioctl を呼ぶ前に仮想 CPU の
lowcore ページをフォールトインするために有効性割り込みを処理するのに
役立つ。


4.68 KVM_SET_ONE_REG
--------------------

:Capability: KVM_CAP_ONE_REG
:Architectures: すべて
:Type: vcpu ioctl
:Parameters: struct kvm_one_reg (in)
:Returns: 成功時は 0、失敗時は負の値

Errors:

  ======   ============================================================
  ENOENT   そのようなレジスタは存在しない
  EINVAL   レジスタ ID が不正、そのようなレジスタが存在しない、または
           s390 の保護仮想化モードの VM で使用された
  EPERM    (arm64) vcpu のファイナライズ前、または保護 VM の vcpu が
           実行された後のレジスタアクセスは許可されない
  EBUSY    (riscv) vcpu が一度でも実行された後のレジスタ値の変更は
           許可されない
  ======   ============================================================

(これらのエラーコードは目安にすぎない。特定の状況で特定のエラーコードが
返ることを前提にしてはならない。)

::

  struct kvm_one_reg {
       __u64 id;
       __u64 addr;
 };

この ioctl を使うと、ユーザ空間が渡した struct kvm_one_reg で指定した
特定の値に、1 つの vcpu レジスタを設定できる。id は後述するレジスタ
識別子を指し、addr は対応するサイズの変数へのポインタである。
アーキテクチャ非依存のレジスタとアーキテクチャ固有のレジスタがある。
それぞれに操作の範囲、独自の定数、幅がある。実装済みのレジスタを
把握するには、以下の一覧を参照する。

  ======= =============================== ============
  アーキテクチャ           レジスタ                  幅 (ビット)
  ======= =============================== ============
  PPC     KVM_REG_PPC_HIOR                64
  PPC     KVM_REG_PPC_IAC1                64
  PPC     KVM_REG_PPC_IAC2                64
  PPC     KVM_REG_PPC_IAC3                64
  PPC     KVM_REG_PPC_IAC4                64
  PPC     KVM_REG_PPC_DAC1                64
  PPC     KVM_REG_PPC_DAC2                64
  PPC     KVM_REG_PPC_DABR                64
  PPC     KVM_REG_PPC_DSCR                64
  PPC     KVM_REG_PPC_PURR                64
  PPC     KVM_REG_PPC_SPURR               64
  PPC     KVM_REG_PPC_DAR                 64
  PPC     KVM_REG_PPC_DSISR               32
  PPC     KVM_REG_PPC_AMR                 64
  PPC     KVM_REG_PPC_UAMOR               64
  PPC     KVM_REG_PPC_MMCR0               64
  PPC     KVM_REG_PPC_MMCR1               64
  PPC     KVM_REG_PPC_MMCRA               64
  PPC     KVM_REG_PPC_MMCR2               64
  PPC     KVM_REG_PPC_MMCRS               64
  PPC     KVM_REG_PPC_MMCR3               64
  PPC     KVM_REG_PPC_SIAR                64
  PPC     KVM_REG_PPC_SDAR                64
  PPC     KVM_REG_PPC_SIER                64
  PPC     KVM_REG_PPC_SIER2               64
  PPC     KVM_REG_PPC_SIER3               64
  PPC     KVM_REG_PPC_PMC1                32
  PPC     KVM_REG_PPC_PMC2                32
  PPC     KVM_REG_PPC_PMC3                32
  PPC     KVM_REG_PPC_PMC4                32
  PPC     KVM_REG_PPC_PMC5                32
  PPC     KVM_REG_PPC_PMC6                32
  PPC     KVM_REG_PPC_PMC7                32
  PPC     KVM_REG_PPC_PMC8                32
  PPC     KVM_REG_PPC_FPR0                64
  ...
  PPC     KVM_REG_PPC_FPR31               64
  PPC     KVM_REG_PPC_VR0                 128
  ...
  PPC     KVM_REG_PPC_VR31                128
  PPC     KVM_REG_PPC_VSR0                128
  ...
  PPC     KVM_REG_PPC_VSR31               128
  PPC     KVM_REG_PPC_FPSCR               64
  PPC     KVM_REG_PPC_VSCR                32
  PPC     KVM_REG_PPC_VPA_ADDR            64
  PPC     KVM_REG_PPC_VPA_SLB             128
  PPC     KVM_REG_PPC_VPA_DTL             128
  PPC     KVM_REG_PPC_EPCR                32
  PPC     KVM_REG_PPC_EPR                 32
  PPC     KVM_REG_PPC_TCR                 32
  PPC     KVM_REG_PPC_TSR                 32
  PPC     KVM_REG_PPC_OR_TSR              32
  PPC     KVM_REG_PPC_CLEAR_TSR           32
  PPC     KVM_REG_PPC_MAS0                32
  PPC     KVM_REG_PPC_MAS1                32
  PPC     KVM_REG_PPC_MAS2                64
  PPC     KVM_REG_PPC_MAS7_3              64
  PPC     KVM_REG_PPC_MAS4                32
  PPC     KVM_REG_PPC_MAS6                32
  PPC     KVM_REG_PPC_MMUCFG              32
  PPC     KVM_REG_PPC_TLB0CFG             32
  PPC     KVM_REG_PPC_TLB1CFG             32
  PPC     KVM_REG_PPC_TLB2CFG             32
  PPC     KVM_REG_PPC_TLB3CFG             32
  PPC     KVM_REG_PPC_TLB0PS              32
  PPC     KVM_REG_PPC_TLB1PS              32
  PPC     KVM_REG_PPC_TLB2PS              32
  PPC     KVM_REG_PPC_TLB3PS              32
  PPC     KVM_REG_PPC_EPTCFG              32
  PPC     KVM_REG_PPC_ICP_STATE           64
  PPC     KVM_REG_PPC_VP_STATE            128
  PPC     KVM_REG_PPC_TB_OFFSET           64
  PPC     KVM_REG_PPC_SPMC1               32
  PPC     KVM_REG_PPC_SPMC2               32
  PPC     KVM_REG_PPC_IAMR                64
  PPC     KVM_REG_PPC_TFHAR               64
  PPC     KVM_REG_PPC_TFIAR               64
  PPC     KVM_REG_PPC_TEXASR              64
  PPC     KVM_REG_PPC_FSCR                64
  PPC     KVM_REG_PPC_PSPB                32
  PPC     KVM_REG_PPC_EBBHR               64
  PPC     KVM_REG_PPC_EBBRR               64
  PPC     KVM_REG_PPC_BESCR               64
  PPC     KVM_REG_PPC_TAR                 64
  PPC     KVM_REG_PPC_DPDES               64
  PPC     KVM_REG_PPC_DAWR                64
  PPC     KVM_REG_PPC_DAWRX               64
  PPC     KVM_REG_PPC_CIABR               64
  PPC     KVM_REG_PPC_IC                  64
  PPC     KVM_REG_PPC_VTB                 64
  PPC     KVM_REG_PPC_CSIGR               64
  PPC     KVM_REG_PPC_TACR                64
  PPC     KVM_REG_PPC_TCSCR               64
  PPC     KVM_REG_PPC_PID                 64
  PPC     KVM_REG_PPC_ACOP                64
  PPC     KVM_REG_PPC_VRSAVE              32
  PPC     KVM_REG_PPC_LPCR                32
  PPC     KVM_REG_PPC_LPCR_64             64
  PPC     KVM_REG_PPC_PPR                 64
  PPC     KVM_REG_PPC_ARCH_COMPAT         32
  PPC     KVM_REG_PPC_DABRX               32
  PPC     KVM_REG_PPC_WORT                64
  PPC	  KVM_REG_PPC_SPRG9               64
  PPC	  KVM_REG_PPC_DBSR                32
  PPC     KVM_REG_PPC_TIDR                64
  PPC     KVM_REG_PPC_PSSCR               64
  PPC     KVM_REG_PPC_DEC_EXPIRY          64
  PPC     KVM_REG_PPC_PTCR                64
  PPC     KVM_REG_PPC_HASHKEYR            64
  PPC     KVM_REG_PPC_HASHPKEYR           64
  PPC     KVM_REG_PPC_DAWR1               64
  PPC     KVM_REG_PPC_DAWRX1              64
  PPC     KVM_REG_PPC_DEXCR               64
  PPC     KVM_REG_PPC_TM_GPR0             64
  ...
  PPC     KVM_REG_PPC_TM_GPR31            64
  PPC     KVM_REG_PPC_TM_VSR0             128
  ...
  PPC     KVM_REG_PPC_TM_VSR63            128
  PPC     KVM_REG_PPC_TM_CR               64
  PPC     KVM_REG_PPC_TM_LR               64
  PPC     KVM_REG_PPC_TM_CTR              64
  PPC     KVM_REG_PPC_TM_FPSCR            64
  PPC     KVM_REG_PPC_TM_AMR              64
  PPC     KVM_REG_PPC_TM_PPR              64
  PPC     KVM_REG_PPC_TM_VRSAVE           64
  PPC     KVM_REG_PPC_TM_VSCR             32
  PPC     KVM_REG_PPC_TM_DSCR             64
  PPC     KVM_REG_PPC_TM_TAR              64
  PPC     KVM_REG_PPC_TM_XER              64

  MIPS    KVM_REG_MIPS_R0                 64
  ...
  MIPS    KVM_REG_MIPS_R31                64
  MIPS    KVM_REG_MIPS_HI                 64
  MIPS    KVM_REG_MIPS_LO                 64
  MIPS    KVM_REG_MIPS_PC                 64
  MIPS    KVM_REG_MIPS_CP0_INDEX          32
  MIPS    KVM_REG_MIPS_CP0_ENTRYLO0       64
  MIPS    KVM_REG_MIPS_CP0_ENTRYLO1       64
  MIPS    KVM_REG_MIPS_CP0_CONTEXT        64
  MIPS    KVM_REG_MIPS_CP0_CONTEXTCONFIG  32
  MIPS    KVM_REG_MIPS_CP0_USERLOCAL      64
  MIPS    KVM_REG_MIPS_CP0_XCONTEXTCONFIG 64
  MIPS    KVM_REG_MIPS_CP0_PAGEMASK       32
  MIPS    KVM_REG_MIPS_CP0_PAGEGRAIN      32
  MIPS    KVM_REG_MIPS_CP0_SEGCTL0        64
  MIPS    KVM_REG_MIPS_CP0_SEGCTL1        64
  MIPS    KVM_REG_MIPS_CP0_SEGCTL2        64
  MIPS    KVM_REG_MIPS_CP0_PWBASE         64
  MIPS    KVM_REG_MIPS_CP0_PWFIELD        64
  MIPS    KVM_REG_MIPS_CP0_PWSIZE         64
  MIPS    KVM_REG_MIPS_CP0_WIRED          32
  MIPS    KVM_REG_MIPS_CP0_PWCTL          32
  MIPS    KVM_REG_MIPS_CP0_HWRENA         32
  MIPS    KVM_REG_MIPS_CP0_BADVADDR       64
  MIPS    KVM_REG_MIPS_CP0_BADINSTR       32
  MIPS    KVM_REG_MIPS_CP0_BADINSTRP      32
  MIPS    KVM_REG_MIPS_CP0_COUNT          32
  MIPS    KVM_REG_MIPS_CP0_ENTRYHI        64
  MIPS    KVM_REG_MIPS_CP0_COMPARE        32
  MIPS    KVM_REG_MIPS_CP0_STATUS         32
  MIPS    KVM_REG_MIPS_CP0_INTCTL         32
  MIPS    KVM_REG_MIPS_CP0_CAUSE          32
  MIPS    KVM_REG_MIPS_CP0_EPC            64
  MIPS    KVM_REG_MIPS_CP0_PRID           32
  MIPS    KVM_REG_MIPS_CP0_EBASE          64
  MIPS    KVM_REG_MIPS_CP0_CONFIG         32
  MIPS    KVM_REG_MIPS_CP0_CONFIG1        32
  MIPS    KVM_REG_MIPS_CP0_CONFIG2        32
  MIPS    KVM_REG_MIPS_CP0_CONFIG3        32
  MIPS    KVM_REG_MIPS_CP0_CONFIG4        32
  MIPS    KVM_REG_MIPS_CP0_CONFIG5        32
  MIPS    KVM_REG_MIPS_CP0_CONFIG7        32
  MIPS    KVM_REG_MIPS_CP0_XCONTEXT       64
  MIPS    KVM_REG_MIPS_CP0_ERROREPC       64
  MIPS    KVM_REG_MIPS_CP0_KSCRATCH1      64
  MIPS    KVM_REG_MIPS_CP0_KSCRATCH2      64
  MIPS    KVM_REG_MIPS_CP0_KSCRATCH3      64
  MIPS    KVM_REG_MIPS_CP0_KSCRATCH4      64
  MIPS    KVM_REG_MIPS_CP0_KSCRATCH5      64
  MIPS    KVM_REG_MIPS_CP0_KSCRATCH6      64
  MIPS    KVM_REG_MIPS_CP0_MAAR(0..63)    64
  MIPS    KVM_REG_MIPS_COUNT_CTL          64
  MIPS    KVM_REG_MIPS_COUNT_RESUME       64
  MIPS    KVM_REG_MIPS_COUNT_HZ           64
  MIPS    KVM_REG_MIPS_FPR_32(0..31)      32
  MIPS    KVM_REG_MIPS_FPR_64(0..31)      64
  MIPS    KVM_REG_MIPS_VEC_128(0..31)     128
  MIPS    KVM_REG_MIPS_FCR_IR             32
  MIPS    KVM_REG_MIPS_FCR_CSR            32
  MIPS    KVM_REG_MIPS_MSA_IR             32
  MIPS    KVM_REG_MIPS_MSA_CSR            32
  ======= =============================== ============

ARM のレジスタは下位 32 ビットを使ってマッピングされる。その上位
16 ビットがレジスタグループ種別、またはコプロセッサ番号である。

ARM コアレジスタの id ビットパターンは次のとおりである::

  0x4020 0000 0010 <index into the kvm_regs struct:16>

ARM 32 ビット CP15 レジスタの id ビットパターンは次のとおりである::

  0x4020 0000 000F <zero:1> <crn:4> <crm:4> <opc1:4> <opc2:3>

ARM 64 ビット CP15 レジスタの id ビットパターンは次のとおりである::

  0x4030 0000 000F <zero:1> <zero:4> <crm:4> <opc1:4> <zero:3>

ARM CCSIDR レジスタは CSSELR の値によって逆多重化される::

  0x4020 0000 0011 00 <csselr:8>

ARM 32 ビット VFP 制御レジスタの id ビットパターンは次のとおりである::

  0x4020 0000 0012 1 <regno:12>

ARM 64 ビット FP レジスタの id ビットパターンは次のとおりである::

  0x4030 0000 0012 0 <regno:12>

ARM ファームウェア擬似レジスタのビットパターンは次のとおりである::

  0x4030 0000 0014 <regno:16>


arm64 のレジスタは下位 32 ビットを使ってマッピングされる。その上位
16 ビットがレジスタグループ種別、またはコプロセッサ番号である。

arm64 のコア/FP-SIMD レジスタの id ビットパターンは次のとおりである。
kvm_regs 構造体には 32 ビットから 128 ビットまでの要素が含まれるため、
アクセスのサイズは可変である。インデックスは、32 ビット配列と
みなした kvm_regs 構造体の 32 ビット値である::

  0x60x0 0000 0010 <index into the kvm_regs struct:16>

具体的には次のとおりである。

======================= ========= ===== =======================================
    エンコーディング            レジスタ      ビット   kvm_regs メンバ
======================= ========= ===== =======================================
  0x6030 0000 0010 0000 X0          64  regs.regs[0]
  0x6030 0000 0010 0002 X1          64  regs.regs[1]
  ...
  0x6030 0000 0010 003c X30         64  regs.regs[30]
  0x6030 0000 0010 003e SP          64  regs.sp
  0x6030 0000 0010 0040 PC          64  regs.pc
  0x6030 0000 0010 0042 PSTATE      64  regs.pstate
  0x6030 0000 0010 0044 SP_EL1      64  sp_el1
  0x6030 0000 0010 0046 ELR_EL1     64  elr_el1
  0x6030 0000 0010 0048 SPSR_EL1    64  spsr[KVM_SPSR_EL1] (alias SPSR_SVC)
  0x6030 0000 0010 004a SPSR_ABT    64  spsr[KVM_SPSR_ABT]
  0x6030 0000 0010 004c SPSR_UND    64  spsr[KVM_SPSR_UND]
  0x6030 0000 0010 004e SPSR_IRQ    64  spsr[KVM_SPSR_IRQ]
  0x6030 0000 0010 0050 SPSR_FIQ    64  spsr[KVM_SPSR_FIQ]
  0x6040 0000 0010 0054 V0         128  fp_regs.vregs[0]    [1]_
  0x6040 0000 0010 0058 V1         128  fp_regs.vregs[1]    [1]_
  ...
  0x6040 0000 0010 00d0 V31        128  fp_regs.vregs[31]   [1]_
  0x6020 0000 0010 00d4 FPSR        32  fp_regs.fpsr
  0x6020 0000 0010 00d5 FPCR        32  fp_regs.fpcr
======================= ========= ===== =======================================

.. [1] これらのエンコーディングは、SVE が有効な vcpu では受け付けられない。
       :ref:`KVM_ARM_VCPU_INIT` を参照。

       代わりに、SVE が有効な vcpu では、対応する SVE Zn レジスタの
       ビット [127:0] から同等のレジスタ内容にアクセスできる (後述)。

arm64 CCSIDR レジスタは CSSELR の値によって逆多重化される::

  0x6020 0000 0011 00 <csselr:8>

arm64 システムレジスタの id ビットパターンは次のとおりである::

  0x6030 0000 0013 <op0:2> <op1:3> <crn:4> <crm:4> <op2:3>

.. warning::

     2 つのシステムレジスタ ID は上記のパターンに従っていない。
     これらは KVM_REG_ARM_TIMER_CVAL と KVM_REG_ARM_TIMER_CNT であり、
     それぞれシステムレジスタ CNTV_CVAL_EL0 と CNTVCT_EL0 に対応する。
     この 2 つは誤って値が入れ替わっており、TIMER_CVAL は CNTVCT_EL0 の
     レジスタエンコーディングから、TIMER_CNT は CNTV_CVAL_EL0 の
     レジスタエンコーディングから導出される。これは API であるため、
     このままにしなければならない。

arm64 ファームウェア擬似レジスタのビットパターンは次のとおりである::

  0x6030 0000 0014 <regno:16>

arm64 SVE レジスタのビットパターンは次のとおりである::

  0x6080 0000 0015 00 <n:5> <slice:5>   Zn bits[2048*slice + 2047 : 2048*slice]
  0x6050 0000 0015 04 <n:4> <slice:5>   Pn bits[256*slice + 255 : 256*slice]
  0x6050 0000 0015 060 <slice:5>        FFR bits[256*slice + 255 : 256*slice]
  0x6060 0000 0015 ffff                 KVM_REG_ARM64_SVE_VLS pseudo-register

2048 * slice >= 128 * max_vq となるレジスタ ID へのアクセスは ENOENT で
失敗する。max_vq は vcpu がサポートする最大ベクトル長を 128 ビットの
クワドワード単位で表したものである。後述の [2]_ を参照。

これらのレジスタは SVE が有効な vcpu でのみアクセスできる。詳細は
KVM_ARM_VCPU_INIT を参照。

さらに KVM_REG_ARM64_SVE_VLS を除き、
KVM_ARM_VCPU_FINALIZE(KVM_ARM_VCPU_SVE) で vcpu の SVE 設定が
ファイナライズされるまで、これらのレジスタにはアクセスできない。
この手順の詳細は KVM_ARM_VCPU_INIT と KVM_ARM_VCPU_FINALIZE を参照。

KVM_REG_ARM64_SVE_VLS は、vcpu がサポートするベクトル長の集合を
ユーザ空間から検出し設定できるようにする擬似レジスタである。
KVM_GET_ONE_REG または KVM_SET_ONE_REG でユーザメモリとの間で
転送されるとき、このレジスタの値は __u64[KVM_ARM64_SVE_VLS_WORDS]
型であり、ベクトル長の集合を次のようにエンコードする::

  __u64 vector_lengths[KVM_ARM64_SVE_VLS_WORDS];

  if (vq >= SVE_VQ_MIN && vq <= SVE_VQ_MAX &&
      ((vector_lengths[(vq - KVM_ARM64_SVE_VQ_MIN) / 64] >>
		((vq - KVM_ARM64_SVE_VQ_MIN) % 64)) & 1))
	/* Vector length vq * 16 bytes supported */
  else
	/* Vector length vq * 16 bytes not supported */

.. [2] 上記の条件が成り立つ vq の最大値が max_vq である。これはこの
       vcpu でゲストが利用できる最大ベクトル長であり、この ioctl
       インタフェースでどのレジスタスライスが見えるかを決める。

("vq" という呼称の説明については Documentation/arch/arm64/sve.rst を
参照。)

KVM_REG_ARM64_SVE_VLS は KVM_ARM_VCPU_INIT の後にのみアクセスできる。
KVM_ARM_VCPU_INIT は、ホストがサポートする最適なベクトル長の集合に
これを初期化する。

その後ユーザ空間は、KVM_ARM_VCPU_FINALIZE(KVM_ARM_VCPU_SVE) で vcpu の
SVE 設定がファイナライズされるまでは、必要に応じてこれを変更できる。

ある値を超えるベクトル長をホストの集合からすべて取り除くだけの場合を
除き、任意に選んだベクトル長の集合のサポートはハードウェアに依存し、
利用できないこともある。KVM_SET_ONE_REG で不正なベクトル長の集合を
設定しようとすると EINVAL で失敗する。

vcpu の SVE 設定がファイナライズされた後、このレジスタへの書き込みを
さらに試みると EPERM で失敗する。

arm64 のビットマップ機能ファームウェア擬似レジスタのビットパターンは次のとおりである::

  0x6030 0000 0016 <regno:16>

ビットマップ機能ファームウェアレジスタは、ユーザ空間が設定できる
ハイパーコールサービスを公開する。セットされているビットは、ゲストが
アクセスできるサービスに対応する。デフォルトでは KVM が VM の初期化時に
サポートするすべてのビットをセットする。ユーザ空間は、利用可能な
サービスを KVM_GET_ONE_REG で検出し、ゲストに見せたい機能に対応する
ビットマップを KVM_SET_ONE_REG で書き戻せる。

備考: VM の vCPU のいずれかが一度でも実行された後、これらのレジスタは
変更できない。そのような状況での KVM_SET_ONE_REG は、ユーザ空間に
-EBUSY を返す。

(詳細は Documentation/virt/kvm/arm/hypercalls.rst を参照。)


MIPS のレジスタは下位 32 ビットを使ってマッピングされる。その上位
16 ビットがレジスタグループ種別である。

MIPS コアレジスタ (前述) の id ビットパターンは次のとおりである::

  0x7030 0000 0000 <reg:16>

MIPS CP0 レジスタ (前述の KVM_REG_MIPS_CP0_*) の id ビットパターンは、
32 ビットレジスタか 64 ビットレジスタかによって次のようになる::

  0x7020 0000 0001 00 <reg:5> <sel:3>   (32-bit)
  0x7030 0000 0001 00 <reg:5> <sel:3>   (64-bit)

備考: KVM_REG_MIPS_CP0_ENTRYLO0 と KVM_REG_MIPS_CP0_ENTRYLO1 は、
ホストハードウェア、ホストカーネル、ゲストのワードサイズや、ゲストに
XPA があるかどうかに関係なく、EntryLo レジスタの MIPS64 版である。
すなわち、RI ビットと XI ビット (存在する場合) がそれぞれビット 63 と
ビット 62 にあり、PFNX フィールドはビット 30 から始まる。

MIPS MAAR (前述の KVM_REG_MIPS_CP0_MAAR(*) を参照) の id ビット
パターンは次のとおりである::

  0x7030 0000 0001 01 <reg:8>

MIPS KVM 制御レジスタ (前述) の id ビットパターンは次のとおりである::

  0x7030 0000 0002 <reg:16>

MIPS FPU レジスタ (前述の KVM_REG_MIPS_FPR_{32,64}() を参照) の id ビット
パターンは、アクセスするレジスタのサイズによって次のようになる。
これらは常に現在のゲスト FPU モード (Status.FR と Config5.FRE) に従って、
つまりゲストから見えるとおりにアクセスされ、ゲスト FPU モードが変更
されると値は不定になる。MIPS SIMD Architecture (MSA) ベクタレジスタ
(前述の KVM_REG_MIPS_VEC_128() を参照) は FPU レジスタと重なるため、
同様のパターンになる::

  0x7020 0000 0003 00 <0:3> <reg:5> (32-bit FPU registers)
  0x7030 0000 0003 00 <0:3> <reg:5> (64-bit FPU registers)
  0x7040 0000 0003 00 <0:3> <reg:5> (128-bit MSA vector registers)

MIPS FPU 制御レジスタ (前述の KVM_REG_MIPS_FCR_{IR,CSR} を参照) の id
ビットパターンは次のとおりである::

  0x7020 0000 0003 01 <0:3> <reg:5>

MIPS MSA 制御レジスタ (前述の KVM_REG_MIPS_MSA_{IR,CSR} を参照) の id
ビットパターンは次のとおりである::

  0x7020 0000 0003 02 <0:3> <reg:5>

RISC-V のレジスタは下位 32 ビットを使ってマッピングされる。その上位
8 ビットがレジスタグループ種別である。

RISC-V config レジスタはゲスト VCPU の設定用であり、id ビットパターンは
次のとおりである::

  0x8020 0000 01 <index into the kvm_riscv_config struct:24> (32bit Host)
  0x8030 0000 01 <index into the kvm_riscv_config struct:24> (64bit Host)

以下は RISC-V config レジスタである:

======================= ========= =============================================
    エンコーディング            レジスタ      説明
======================= ========= =============================================
  0x80x0 0000 0100 0000 isa       ゲスト VCPU の ISA 機能ビットマップ
======================= ========= =============================================

isa config レジスタはいつでも読み出せるが、書き込みはゲスト VCPU が
実行される前のみ可能である。デフォルトでは、基盤となるホストに一致する
ISA 機能ビットがセットされる。

RISC-V コアレジスタはゲスト VCPU の一般的な実行状態を表し、id ビット
パターンは次のとおりである::

  0x8020 0000 02 <index into the kvm_riscv_core struct:24> (32bit Host)
  0x8030 0000 02 <index into the kvm_riscv_core struct:24> (64bit Host)

以下は RISC-V コアレジスタである:

======================= ========= =============================================
    エンコーディング            レジスタ      説明
======================= ========= =============================================
  0x80x0 0000 0200 0000 regs.pc   プログラムカウンタ
  0x80x0 0000 0200 0001 regs.ra   戻りアドレス
  0x80x0 0000 0200 0002 regs.sp   スタックポインタ
  0x80x0 0000 0200 0003 regs.gp   グローバルポインタ
  0x80x0 0000 0200 0004 regs.tp   タスクポインタ
  0x80x0 0000 0200 0005 regs.t0   呼び出し元が保存するレジスタ 0
  0x80x0 0000 0200 0006 regs.t1   呼び出し元が保存するレジスタ 1
  0x80x0 0000 0200 0007 regs.t2   呼び出し元が保存するレジスタ 2
  0x80x0 0000 0200 0008 regs.s0   呼び出し先が保存するレジスタ 0
  0x80x0 0000 0200 0009 regs.s1   呼び出し先が保存するレジスタ 1
  0x80x0 0000 0200 000a regs.a0   関数引数 (または戻り値) 0
  0x80x0 0000 0200 000b regs.a1   関数引数 (または戻り値) 1
  0x80x0 0000 0200 000c regs.a2   関数引数 2
  0x80x0 0000 0200 000d regs.a3   関数引数 3
  0x80x0 0000 0200 000e regs.a4   関数引数 4
  0x80x0 0000 0200 000f regs.a5   関数引数 5
  0x80x0 0000 0200 0010 regs.a6   関数引数 6
  0x80x0 0000 0200 0011 regs.a7   関数引数 7
  0x80x0 0000 0200 0012 regs.s2   呼び出し先が保存するレジスタ 2
  0x80x0 0000 0200 0013 regs.s3   呼び出し先が保存するレジスタ 3
  0x80x0 0000 0200 0014 regs.s4   呼び出し先が保存するレジスタ 4
  0x80x0 0000 0200 0015 regs.s5   呼び出し先が保存するレジスタ 5
  0x80x0 0000 0200 0016 regs.s6   呼び出し先が保存するレジスタ 6
  0x80x0 0000 0200 0017 regs.s7   呼び出し先が保存するレジスタ 7
  0x80x0 0000 0200 0018 regs.s8   呼び出し先が保存するレジスタ 8
  0x80x0 0000 0200 0019 regs.s9   呼び出し先が保存するレジスタ 9
  0x80x0 0000 0200 001a regs.s10  呼び出し先が保存するレジスタ 10
  0x80x0 0000 0200 001b regs.s11  呼び出し先が保存するレジスタ 11
  0x80x0 0000 0200 001c regs.t3   呼び出し元が保存するレジスタ 3
  0x80x0 0000 0200 001d regs.t4   呼び出し元が保存するレジスタ 4
  0x80x0 0000 0200 001e regs.t5   呼び出し元が保存するレジスタ 5
  0x80x0 0000 0200 001f regs.t6   呼び出し元が保存するレジスタ 6
  0x80x0 0000 0200 0020 mode      特権モード (1 = S-mode、0 = U-mode)
======================= ========= =============================================

RISC-V csr レジスタはゲスト VCPU のスーパーバイザモードの制御/ステータス
レジスタを表し、id ビットパターンは次のとおりである::

  0x8020 0000 03 <index into the kvm_riscv_csr struct:24> (32bit Host)
  0x8030 0000 03 <index into the kvm_riscv_csr struct:24> (64bit Host)

以下は RISC-V csr レジスタである:

======================= ========= =============================================
    エンコーディング            レジスタ      説明
======================= ========= =============================================
  0x80x0 0000 0300 0000 sstatus   スーパーバイザステータス
  0x80x0 0000 0300 0001 sie       スーパーバイザ割り込みイネーブル
  0x80x0 0000 0300 0002 stvec     スーパーバイザトラップベクタベース
  0x80x0 0000 0300 0003 sscratch  スーパーバイザスクラッチレジスタ
  0x80x0 0000 0300 0004 sepc      スーパーバイザ例外プログラムカウンタ
  0x80x0 0000 0300 0005 scause    スーパーバイザトラップ原因
  0x80x0 0000 0300 0006 stval     スーパーバイザ不正アドレスまたは命令
  0x80x0 0000 0300 0007 sip       スーパーバイザ保留中の割り込み
  0x80x0 0000 0300 0008 satp      スーパーバイザのアドレス変換と保護
======================= ========= =============================================

RISC-V タイマレジスタはゲスト VCPU のタイマ状態を表し、id ビットパターンは
次のとおりである::

  0x8030 0000 04 <index into the kvm_riscv_timer struct:24>

以下は RISC-V タイマレジスタである:

======================= ========= =============================================
    エンコーディング            レジスタ      説明
======================= ========= =============================================
  0x8030 0000 0400 0000 frequency タイムベース周波数 (読み取り専用)
  0x8030 0000 0400 0001 time      ゲストから見える時間値
  0x8030 0000 0400 0002 compare   ゲストが設定した時間比較値
  0x8030 0000 0400 0003 state     時間比較の状態 (1 = ON、0 = OFF)
======================= ========= =============================================

RISC-V F 拡張レジスタはゲスト VCPU の単精度浮動小数点状態を表し、id ビット
パターンは次のとおりである::

  0x8020 0000 05 <index into the __riscv_f_ext_state struct:24>

以下は RISC-V F 拡張レジスタである:

======================= ========= =============================================
    エンコーディング            レジスタ      説明
======================= ========= =============================================
  0x8020 0000 0500 0000 f[0]      浮動小数点レジスタ 0
  ...
  0x8020 0000 0500 001f f[31]     浮動小数点レジスタ 31
  0x8020 0000 0500 0020 fcsr      浮動小数点制御/ステータスレジスタ
======================= ========= =============================================

RISC-V D 拡張レジスタはゲスト VCPU の倍精度浮動小数点状態を表し、id ビット
パターンは次のとおりである::

  0x8020 0000 06 <index into the __riscv_d_ext_state struct:24> (fcsr)
  0x8030 0000 06 <index into the __riscv_d_ext_state struct:24> (non-fcsr)

以下は RISC-V D 拡張レジスタである:

======================= ========= =============================================
    エンコーディング            レジスタ      説明
======================= ========= =============================================
  0x8030 0000 0600 0000 f[0]      浮動小数点レジスタ 0
  ...
  0x8030 0000 0600 001f f[31]     浮動小数点レジスタ 31
  0x8020 0000 0600 0020 fcsr      浮動小数点制御/ステータスレジスタ
======================= ========= =============================================

LoongArch のレジスタは下位 32 ビットを使ってマッピングされる。その上位
16 ビットがレジスタグループ種別である。

LoongArch csr レジスタはゲスト CPU を制御したり、ゲスト CPU の状態を
取得したりするために使われ、id ビットパターンは次のとおりである::

  0x9030 0000 0001 00 <reg:5> <sel:3>   (64-bit)

LoongArch KVM 制御レジスタは、vcpu カウンタの設定や vcpu のリセットなど、
新たに定義された一部の機能を実装するために使われ、id ビットパターンは
次のとおりである::

  0x9030 0000 0002 <reg:16>

x86 MSR レジスタの id ビットパターンは次のとおりである::
  0x2030 0002 <msr number:32>

以下は x86 向けに KVM が定義したレジスタである:

======================= ========= =============================================
    エンコーディング            レジスタ      説明
======================= ========= =============================================
  0x2030 0003 0000 0000 SSP       シャドウスタックポインタ
======================= ========= =============================================

4.69 KVM_GET_ONE_REG
--------------------

:Capability: KVM_CAP_ONE_REG
:Architectures: すべて
:Type: vcpu ioctl
:Parameters: struct kvm_one_reg（入力と出力）
:Returns: 成功時は 0、失敗時は負の値

エラーは次のとおり:

  ======== ============================================================
  ENOENT   そのようなレジスタは存在しない
  EINVAL   レジスタ ID が不正、またはそのようなレジスタが存在しない。
           s390 の保護仮想化モードの VM で使われることもある
  EPERM    (arm64) vcpu のファイナライズ前、または保護 VM の vcpu が
           実行された後は、レジスタにアクセスできない
  ======== ============================================================

（これらのエラーコードは目安にすぎない。特定の状況で特定のエラーコードが
返ることを前提にしてはならない。）

この ioctl は、vcpu に実装された単一のレジスタの値を受け取れる。読み出す
レジスタは、渡された kvm_one_reg 構造体の "id" フィールドで示す。成功した
場合、レジスタの値は "addr" が指すメモリ位置にある。

このインタフェースでアクセスできるレジスタの一覧は、4.68 の一覧と同じ
である。


4.70 KVM_KVMCLOCK_CTRL
----------------------

:Capability: KVM_CAP_KVMCLOCK_CTRL
:Architectures: pvclock を実装するものすべて（現在は x86 のみ）
:Type: vcpu ioctl
:Parameters: なし
:Returns: 成功時は 0、エラー時は -1

この ioctl は、指定した vCPU がホストのユーザ空間によって一時停止された
ことを示すフラグを、ゲストから参照できるように設定する。

ホストは、soft lockup ウォッチドッグが調べるフラグを pvclock 構造体に
設定する。このフラグは、ゲストとホストで共有される pvclock 構造体の一部
であり、具体的には pvclock_vcpu_time_info 構造体の flags フィールドの第 2
ビットである。設定はホストだけが行い、読み取りとクリアはゲストだけが行う。
ゲストがこのフラグを調べてクリアする処理はアトミックでなければならない。
したがって、load-link/store-conditional または同等の命令を使う必要がある。
ゲストがフラグをクリアするのは 2 つの場合である。soft lockup ウォッチドッグ
のタイマーが自分自身をリセットしたとき、または soft lockup が検出された
ときだ。この ioctl は、vcpu を一時停止した後、再開する前ならいつでも
呼べる。


4.71 KVM_SIGNAL_MSI
-------------------

:Capability: KVM_CAP_SIGNAL_MSI
:Architectures: x86 arm64
:Type: vm ioctl
:Parameters: struct kvm_msi（入力）
:Returns: 配送時は >0、ゲストが MSI をブロックした場合は 0、エラー時は -1

MSI メッセージを直接注入する。MSI メッセージを処理するカーネル内 irqchip が
ある場合にのみ有効である。

::

  struct kvm_msi {
	__u32 address_lo;
	__u32 address_hi;
	__u32 data;
	__u32 flags;
	__u32 devid;
	__u8  pad[12];
  };

flags:
  KVM_MSI_VALID_DEVID: devid に有効な値が入っている。VM ごとの
  KVM_CAP_MSI_DEVID ケイパビリティは、デバイス ID を渡す必要があることを
  示す。このケイパビリティが利用できない場合、ioctl が失敗する可能性が
  あるので、ユーザ空間は KVM_MSI_VALID_DEVID フラグを設定してはならない。

KVM_MSI_VALID_DEVID が設定されている場合、devid には MSI メッセージを
書き込んだデバイスの一意なデバイス識別子が入る。PCI では、通常これは下位
16 ビットの BDF 識別子である。

x86 では、KVM_CAP_X2APIC_API ケイパビリティの KVM_X2APIC_API_USE_32BIT_IDS
機能が有効でない限り、address_hi は無視される。有効な場合、address_hi の
ビット 31〜8 が宛先 ID のビット 31〜8 になる。address_hi のビット 7〜0 は
ゼロでなければならない。


4.71 KVM_CREATE_PIT2
--------------------

:Capability: KVM_CAP_PIT2
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_pit_config（入力）
:Returns: 成功時は 0、エラー時は -1

i8254 PIT のカーネル内デバイスモデルを作成する。この呼び出しは、
KVM_CREATE_IRQCHIP でカーネル内 irqchip サポートを有効にした後にのみ有効で
ある。次のパラメータを渡す必要がある::

  struct kvm_pit_config {
	__u32 flags;
	__u32 pad[15];
  };

有効なフラグは次のとおり::

  #define KVM_PIT_SPEAKER_DUMMY     1 /* emulate speaker port stub */

PIT タイマー割り込みの注入に、VM ごとのカーネルスレッドを使うことがある。
このスレッドが存在する場合、その名前は次のパターンになる::

  kvm-pit/<owner-process-pid>

高い優先度でゲストを実行する場合、このスレッドのスケジューリング
パラメータをそれに合わせて調整する必要があるかもしれない。

この IOCTL は、廃止された KVM_CREATE_PIT を置き換える。


4.72 KVM_GET_PIT2
-----------------

:Capability: KVM_CAP_PIT_STATE2
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_pit_state2（出力）
:Returns: 成功時は 0、エラー時は -1

カーネル内 PIT モデルの状態を取得する。KVM_CREATE_PIT2 の後にのみ有効で
ある。状態は次の構造体で返される::

  struct kvm_pit_state2 {
	struct kvm_pit_channel_state channels[3];
	__u32 flags;
	__u32 reserved[9];
  };

有効なフラグは次のとおり::

  /* disable PIT in HPET legacy mode */
  #define KVM_PIT_FLAGS_HPET_LEGACY     0x00000001
  /* speaker port data bit enabled */
  #define KVM_PIT_FLAGS_SPEAKER_DATA_ON 0x00000002

この IOCTL は、廃止された KVM_GET_PIT を置き換える。


4.73 KVM_SET_PIT2
-----------------

:Capability: KVM_CAP_PIT_STATE2
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_pit_state2（入力）
:Returns: 成功時は 0、エラー時は -1

カーネル内 PIT モデルの状態を設定する。KVM_CREATE_PIT2 の後にのみ有効で
ある。struct kvm_pit_state2 の詳細は KVM_GET_PIT2 を参照。

.. Tip::
  ``KVM_SET_PIT2`` strictly adheres to the spec of Intel 8254 PIT.  For example,
  a ``count`` value of 0 in ``struct kvm_pit_channel_state`` is interpreted as
  65536, which is the maximum count value. Refer to `Intel 8254 programmable
  interval timer <https://www.scs.stanford.edu/10wi-cs140/pintos/specs/8254.pdf>`_.

この IOCTL は、廃止された KVM_SET_PIT を置き換える。


4.74 KVM_PPC_GET_SMMU_INFO
--------------------------

:Capability: KVM_CAP_PPC_GET_SMMU_INFO
:Architectures: powerpc
:Type: vm ioctl
:Parameters: なし
:Returns: 成功時は 0、エラー時は -1

この ioctl は、KVM が対応する "Server" クラスの MMU エミュレーションの
機能を記述した構造体を埋めて返す。ユーザ空間はこれを利用して、ゲスト OS
向けの適切なデバイスツリープロパティを生成できる。

この構造体には、いくつかのグローバルな情報と、それに続く対応するセグメント
ページサイズの配列が含まれる::

      struct kvm_ppc_smmu_info {
	     __u64 flags;
	     __u32 slb_size;
	     __u32 pad;
	     struct kvm_ppc_one_seg_page_size sps[KVM_PPC_PAGE_SIZES_MAX_SZ];
      };

対応するフラグは次のとおり:

    - KVM_PPC_PAGE_SIZES_REAL:
        このフラグが設定されている場合、ゲストのページサイズは
        バッキングストアのページサイズに「合う」必要がある。設定されて
        いない場合は、ユーザ空間でのバッキングのされ方に関係なく、
        一覧にある任意のページサイズを使える。

    - KVM_PPC_1T_SEGMENTS
        エミュレートされる MMU は、標準の 256M セグメントに加えて
        1T セグメントにも対応する。

    - KVM_PPC_NO_HASH
	このフラグは、KVM が HPT ゲストに対応していないことを示す。
	したがって、すべてのゲストは radix MMU モードを使わなければ
	ならない。

"slb_size" フィールドは、対応する SLB エントリの数を示す。

"sps" 配列は 8 個のエントリを持ち、セグメントで対応するベースページサイズ
を昇順に示す。各エントリは次のように定義される::

   struct kvm_ppc_one_seg_page_size {
	__u32 page_shift;	/* Base page shift of segment (or 0) */
	__u32 slb_enc;		/* SLB encoding for BookS */
	struct kvm_ppc_one_page_size enc[KVM_PPC_PAGE_SIZES_MAX_SZ];
   };

"page_shift" が 0 のエントリは未使用である。配列は昇順に並んでいるので、
そのようなエントリに達した時点で探索を止めてよい。

"slb_enc" フィールドは、そのページサイズについて SLB で使うエンコーディング
を与える。ビットの位置は、その値を slbmte 命令の "vsid" 引数にそのまま
OR できるようになっている。

"enc" 配列は、それらのセグメントベースページサイズのそれぞれについて、
対応する実際のページサイズ（ベースページサイズ以上でなければならない）の
一覧と、ハッシュ PTE での対応するエンコーディングを与える。同様に、この
配列はサイズの昇順に並んだ 8 個のエントリからなり、shift が "0" のエントリ
は空のエントリであり終端でもある::

   struct kvm_ppc_one_page_size {
	__u32 page_shift;	/* Page shift (or 0) */
	__u32 pte_enc;		/* Encoding in the HPTE (>>12) */
   };

"pte_enc" フィールドは、ハッシュ PTE の RPN フィールドに OR できる値を
与える（つまり、ハッシュ PTE の第 2 ダブルワードに OR するには、左に 12
ビットシフトする必要がある）。

4.75 KVM_IRQFD
--------------

:Capability: KVM_CAP_IRQFD
:Architectures: x86 s390 arm64
:Type: vm ioctl
:Parameters: struct kvm_irqfd（入力）
:Returns: 成功時は 0、エラー時は -1

eventfd を設定して、ゲストの割り込みを直接トリガーできるようにする。
kvm_irqfd.fd は eventfd として使うファイルディスクリプタを指定し、
kvm_irqfd.gsi はこのイベントでトグルされる irqchip のピンを指定する。
eventfd でイベントがトリガーされると、指定した gsi ピンを使ってゲストに
割り込みが注入される。irqfd は、KVM_IRQFD_FLAG_DEASSIGN フラグを使い、
kvm_irqfd.fd と kvm_irqfd.gsi の両方を指定して削除する。

KVM_CAP_IRQFD_RESAMPLE がある場合、KVM_IRQFD はデアサートと通知の仕組みに
対応し、レベルトリガーの irqfd ベースの割り込みをエミュレートできる。
KVM_IRQFD_FLAG_RESAMPLE が設定されている場合、ユーザは
kvm_irqfd.resamplefd フィールドに追加の eventfd を渡さなければならない。
リサンプルモードで動作しているとき、kvm_irq.fd を通じて割り込みをポスト
すると、irqchip の指定した gsi がアサートされる。EOI などによって irqchip
がリサンプルされると、gsi はデアサートされ、ユーザは kvm_irqfd.resamplefd
を通じて通知を受ける。その割り込みを使うデバイスがまだサービスを必要と
しているなら、割り込みを再度キューに入れるのはユーザの責任である。
resamplefd をクローズしても irqfd を無効にするには不十分である点に注意。
KVM_IRQFD_FLAG_RESAMPLE はアサイン時にのみ必要で、KVM_IRQFD_FLAG_DEASSIGN
と一緒に指定する必要はない。

arm64 では gsi ルーティングが対応しているため、次のことが起こりうる:

- この gsi にルーティングエントリが関連付けられていない場合、注入は
  失敗する
- gsi が irqchip ルーティングエントリに関連付けられている場合、
  irqchip.pin + 32 が注入される SPI ID に対応する。
- gsi が MSI ルーティングエントリに関連付けられている場合、MSI メッセージ
  とデバイス ID は LPI に変換される（対応はカーネル内 GICv3 ITS
  エミュレーションに限られる）。

4.76 KVM_PPC_ALLOCATE_HTAB
--------------------------

:Capability: KVM_CAP_PPC_ALLOC_HTAB
:Architectures: powerpc
:Type: vm ioctl
:Parameters: ハッシュテーブルのオーダーを格納した u32 へのポインタ（入力/出力）
:Returns: 成功時は 0、エラー時は -1

これは、PAPR 準仮想化インタフェースを使うゲストのために、ホストカーネルに
MMU ハッシュテーブルの割り当てを要求する。カーネルが Book 3S HV 方式の
仮想化を使うように設定されている場合にのみ意味がある。それ以外の場合、
このケイパビリティは存在せず、ioctl は ENOTTY エラーを返す。以下の説明は
Book 3S HV を前提とする。

この ioctl を呼ぶとき、実行中の vcpu があってはならない。ある場合、何も
せず EBUSY エラーを返す。

パラメータは 32 ビット符号なし整数変数へのポインタで、ハッシュテーブルの
希望サイズのオーダー（2 を底とする対数）を格納する。値は 18 から 46 の間で
なければならない。ioctl が成功して戻ったとき、カーネルはこの値を変更
しない。

vcpu を実行しようとしたとき（KVM_RUN ioctl で）、ハッシュテーブルがまだ
割り当てられていなければ、ホストカーネルは既定サイズのハッシュテーブル
（16 MB）を割り当てる。

ハッシュテーブルがすでに割り当てられている状態で、既存のハッシュテーブル
と異なるオーダーを指定してこの ioctl を呼ぶと、既存のハッシュテーブルは
解放され、新しいものが割り当てられる。すでに割り当てられているハッシュ
テーブルと同じオーダーを指定して呼ぶと、カーネルは既存のハッシュテーブル
を消去する（すべての HPTE をゼロにする）。どちらの場合も、ゲストが仮想化
リアルモード領域（VRMA）機能を使っているなら、カーネルは次にいずれかの
vcpu を KVM_RUN したときに VMRA HPTE を作り直す。

4.77 KVM_S390_INTERRUPT
-----------------------

:Capability: basic
:Architectures: s390
:Type: vm ioctl, vcpu ioctl
:Parameters: struct kvm_s390_interrupt（入力）
:Returns: 成功時は 0、エラー時は -1

ゲストに割り込みを注入できる。割り込みは、その種類に応じて、フローティング
（vm ioctl）または CPU ごと（vcpu ioctl）である。

割り込みパラメータは kvm_s390_interrupt で渡す::

  struct kvm_s390_interrupt {
	__u32 type;
	__u32 parm;
	__u64 parm64;
  };

type は次のいずれかである:

KVM_S390_SIGP_STOP (vcpu)
    - sigp stop。オプションのフラグは parm に入る
KVM_S390_PROGRAM_INT (vcpu)
    - program check。コードは parm に入る
KVM_S390_SIGP_SET_PREFIX (vcpu)
    - sigp set prefix。プレフィックスアドレスは parm に入る
KVM_S390_RESTART (vcpu)
    - restart
KVM_S390_INT_CLOCK_COMP (vcpu)
    - クロックコンパレータ割り込み
KVM_S390_INT_CPU_TIMER (vcpu)
    - CPU タイマー割り込み
KVM_S390_INT_VIRTIO (vm)
    - virtio 外部割り込み。外部割り込みパラメータは parm と
      parm64 に入る
KVM_S390_INT_SERVICE (vm)
    - sclp 外部割り込み。sclp パラメータは parm に入る
KVM_S390_INT_EMERGENCY (vcpu)
    - sigp emergency。ソース CPU は parm に入る
KVM_S390_INT_EXTERNAL_CALL (vcpu)
    - sigp external call。ソース CPU は parm に入る
KVM_S390_INT_IO(ai,cssid,ssid,schid) (vm)
    - I/O 割り込みを示す複合値（ai - アダプタ割り込み、
      cssid,ssid,schid - サブチャネル）。I/O 割り込みパラメータは
      parm（サブチャネル）と parm64（intparm、割り込みサブクラス）に
      入る
KVM_S390_MCHK (vm, vcpu)
    - machine check 割り込み。cr 14 のビットは parm に、machine check
      割り込みコードは parm64 に入る（さらにペイロードを必要とする
      machine check はこの ioctl では対応していない点に注意）

これは非同期の vcpu ioctl であり、どのスレッドからでも呼べる。

4.78 KVM_PPC_GET_HTAB_FD
------------------------

:Capability: KVM_CAP_PPC_HTAB_FD
:Architectures: powerpc
:Type: vm ioctl
:Parameters: struct kvm_get_htab_fd へのポインタ（入力）
:Returns: 成功時はファイルディスクリプタ番号（>= 0）、エラー時は -1

これは、ゲストのハッシュページテーブル（HPT）のエントリを読み出すため、
または HPT を初期化するためにエントリを書き込むために使えるファイル
ディスクリプタを返す。返された fd に書き込めるのは、引数の flags フィールド
に KVM_GET_HTAB_WRITE ビットが設定されている場合だけで、そのビットが
クリアされている場合だけ読み出せる。引数の構造体は次のとおり::

  /* For KVM_PPC_GET_HTAB_FD */
  struct kvm_get_htab_fd {
	__u64	flags;
	__u64	start_index;
	__u64	reserved[2];
  };

  /* Values for kvm_get_htab_fd.flags */
  #define KVM_GET_HTAB_BOLTED_ONLY	((__u64)0x1)
  #define KVM_GET_HTAB_WRITE		((__u64)0x2)

'start_index' フィールドは、読み出しを開始する HPT 内のエントリの
インデックスを与える。書き込み時には無視される。

fd からの読み出しは、最初はすべての「対象となる」HPT エントリの情報を
返す。対象となるエントリは、KVM_GET_HTAB_BOLTED_ONLY ビットが設定されて
いれば bolted ビットが設定されたエントリ、そうでなければすべてのエントリ
である。HPT の終端に達すると、read() は戻る。fd に対して再び read() を
呼ぶと、HPT の先頭から再び始まるが、前回読み出してから変化した HPT
エントリだけを返す。

読み書きされるデータは、ヘッダ（8 バイト）と、それに続く一連の有効な HPT
エントリ（各 16 バイト）で構成される。ヘッダは、有効な HPT エントリの数と、
有効なエントリの後に続く無効なエントリの数を示す。無効なエントリは
ストリーム中に明示的には現れない。ヘッダの形式は次のとおり::

  struct kvm_get_htab_header {
	__u32	index;
	__u16	n_valid;
	__u16	n_invalid;
  };

fd への書き込みは、ヘッダで与えられたインデックスから HPT エントリを
作成する。まず書き込んだデータの内容を持つ 'n_valid' 個の有効なエントリ、
次に 'n_invalid' 個の無効なエントリを作り、それまで有効だったエントリは
無効にする。

4.79 KVM_CREATE_DEVICE
----------------------

:Capability: KVM_CAP_DEVICE_CTRL
:Architectures: すべて
:Type: vm ioctl
:Parameters: struct kvm_create_device（入力/出力）
:Returns: 成功時は 0、エラー時は -1

Errors:

  ======  =======================================================
  ENODEV  デバイスタイプが不明または未対応
  EEXIST  デバイスがすでに作成済みで、この種のデバイスは複数回
          インスタンス化できない
  ======  =======================================================

  その他のエラー条件は、個々のデバイスタイプが定義するか、通常の
  意味を持つことがある。

カーネル内にエミュレートデバイスを作成する。fd で返されるファイル
ディスクリプタは、KVM_SET/GET/HAS_DEVICE_ATTR で使える。

KVM_CREATE_DEVICE_TEST フラグが設定されている場合、そのデバイスタイプが
対応しているかだけを調べる（現在の vm で作成できるかまでは調べない）。

個々のデバイスはフラグを定義すべきではない。デバイスタイプ番号から自明で
ない振る舞いを指定するには、属性を使うべきである。

::

  struct kvm_create_device {
	__u32	type;	/* in: KVM_DEV_TYPE_xxx */
	__u32	fd;	/* out: device handle */
	__u32	flags;	/* in: KVM_CREATE_DEVICE_xxx */
  };

4.80 KVM_SET_DEVICE_ATTR/KVM_GET_DEVICE_ATTR
--------------------------------------------

:Capability: KVM_CAP_DEVICE_CTRL, KVM_CAP_VM_ATTRIBUTES for vm device,
             KVM_CAP_VCPU_ATTRIBUTES for vcpu device
             KVM_CAP_SYS_ATTRIBUTES for system (/dev/kvm) device (no set)
:Architectures: x86, arm64, s390
:Type: device ioctl, vm ioctl, vcpu ioctl
:Parameters: struct kvm_device_attr
:Returns: 成功時は 0、エラー時は -1

Errors:

  =====   =============================================================
  ENXIO   このデバイスでグループまたは属性が不明/未対応か、
          ハードウェアのサポートがない
  EPERM   (現在) この方法では属性にアクセスできない
          （たとえば読み取り専用属性、またはデバイスが別の状態のとき
          だけ意味を持つ属性）
  =====   =============================================================

  その他のエラー条件は、個々のデバイスタイプが定義することがある。

デバイスの設定や状態の指定した部分を取得または設定する。意味はデバイス
ごとに異なる。"devices" ディレクトリ内の各デバイスのドキュメントを参照。
ONE_REG と同様に、転送されるデータのサイズはその属性ごとに定義される。

::

  struct kvm_device_attr {
	__u32	flags;		/* no flags currently defined */
	__u32	group;		/* device-defined */
	__u64	attr;		/* group-defined */
	__u64	addr;		/* userspace address of attr data */
  };

4.81 KVM_HAS_DEVICE_ATTR
------------------------

:Capability: KVM_CAP_DEVICE_CTRL, KVM_CAP_VM_ATTRIBUTES for vm device,
             KVM_CAP_VCPU_ATTRIBUTES for vcpu device
             KVM_CAP_SYS_ATTRIBUTES for system (/dev/kvm) device
:Type: device ioctl, vm ioctl, vcpu ioctl
:Parameters: struct kvm_device_attr
:Returns: 成功時は 0、エラー時は -1

Errors:

  =====   =============================================================
  ENXIO   このデバイスでグループまたは属性が不明/未対応か、
          ハードウェアのサポートがない
  =====   =============================================================

デバイスが特定の属性に対応しているかを調べる。成功して戻った場合は、その
属性が実装されていることを示す。デバイスの現在の状態でその属性を読み書き
できることまでは示さない。"addr" は無視される。

.. _KVM_ARM_VCPU_INIT:

4.82 KVM_ARM_VCPU_INIT
----------------------

:Capability: basic
:Architectures: arm64
:Type: vcpu ioctl
:Parameters: struct kvm_vcpu_init（入力）
:Returns: 成功時は 0、エラー時は -1

Errors:

  ======     =================================================================
  EINVAL     target が不明、または機能の組み合わせが不正である。
  ENOENT     指定した機能ビットが不明である。
  EPERM      vcpu が保護 VM に属し、すでに実行されている。
  ======     =================================================================

これは、ゲストに提示する CPU の種類と、その CPU が持つべきオプション機能を
KVM に伝える。これにより CPU レジスタが初期値にリセットされる。これを
呼ばない場合、その vcpu に対する KVM_RUN は ENOEXEC を返す。

初期値は次のように定義される:
	- プロセッサ状態:
		* AArch64: EL1h、D、A、I、F ビットが設定される。それ以外の
		  ビットはクリアされる。
		* AArch32: SVC、A、I、F ビットが設定される。それ以外の
		  ビットはクリアされる。
	- PC と SP を含む汎用レジスタ: 0 に設定される
	- FPSIMD/NEON レジスタ: 0 に設定される
	- SVE レジスタ: 0 に設定される
	- システムレジスタ: EL1（または SVC）や EL2（EL2 が有効な場合）への
	  ウォームリセットのときと同じ、アーキテクチャで定義された値に
	  リセットされる。

一部のレジスタはマシンのトポロジを反映するため、この ioctl を呼ぶ前に
すべての vcpu を作成しておくべきである。

ユーザ空間は、ある vcpu に対してこの関数を複数回呼べる。vcpu を実行した
後でも呼べる。呼ぶと vcpu は初期状態にリセットされる。最初の呼び出しより
後の呼び出しはすべて、同じ target と同じ機能フラグの集合を使わなければ
ならない。そうでない場合、EINVAL が返される。

保護 VM では、vcpu を実行した後にこの ioctl を呼ぶと EPERM が返り、受け付ける
機能も制限される。KVM_ARM_VCPU_PSCI_0_2 が必須である。
Documentation/virt/kvm/arm/pkvm.rst を参照。

指定できる機能:

	- KVM_ARM_VCPU_POWER_OFF: CPU を電源オフ状態で起動する。
	  KVM_CAP_ARM_PSCI に依存する。設定しない場合、CPU は電源オンになり、
	  KVM_RUN を呼ぶとゲストコードを実行する。
	- KVM_ARM_VCPU_EL1_32BIT: CPU を 32 ビットモードで起動する。
	  KVM_CAP_ARM_EL1_32BIT に依存する（arm64 のみ）。
	- KVM_ARM_VCPU_PSCI_0_2: CPU 向けに PSCI v0.2（または v0.2 と後方
          互換な将来のリビジョン）をエミュレートする。
	  KVM_CAP_ARM_PSCI_0_2 に依存する。
	- KVM_ARM_VCPU_PMU_V3: CPU 向けに PMUv3 をエミュレートする。
	  KVM_CAP_ARM_PMU_V3 に依存する。
	- KVM_ARM_VCPU_PMU_V3_STRICT: 厳密な PMUv3 UAPI を有効にする。
	  KVM_ARM_VCPU_PMU_V3 が必要。KVM_CAP_ARM_PMU_V3_STRICT に依存する。
	  有効な場合:

	    * ユーザ空間は、PMU を初期化する前、または PMU イベント
	      フィルタを設定する前に、PMU の実装を明示的に選択しなければ
	      ならない

	    * PMU が FEAT_PMUv3p4 を実装している場合、PMMIR_EL1.SLOTS は
	      基盤となる実装のハードウェア値を与える

	    * KVM_SET_ONE_REG による PMCR_EL0.N への書き込みは無視される

	- KVM_ARM_VCPU_PTRAUTH_ADDRESS: アドレスポインタ認証を有効にする
	  （arm64 のみ）。
	  KVM_CAP_ARM_PTRAUTH_ADDRESS に依存する。
	  KVM_CAP_ARM_PTRAUTH_ADDRESS と KVM_CAP_ARM_PTRAUTH_GENERIC の
	  両方がある場合、KVM_ARM_VCPU_PTRAUTH_ADDRESS と
	  KVM_ARM_VCPU_PTRAUTH_GENERIC の両方を要求するか、どちらも
	  要求しないかのどちらかでなければならない。

	- KVM_ARM_VCPU_PTRAUTH_GENERIC: 汎用ポインタ認証を有効にする
	  （arm64 のみ）。
	  KVM_CAP_ARM_PTRAUTH_GENERIC に依存する。
	  KVM_CAP_ARM_PTRAUTH_ADDRESS と KVM_CAP_ARM_PTRAUTH_GENERIC の
	  両方がある場合、KVM_ARM_VCPU_PTRAUTH_ADDRESS と
	  KVM_ARM_VCPU_PTRAUTH_GENERIC の両方を要求するか、どちらも
	  要求しないかのどちらかでなければならない。

	- KVM_ARM_VCPU_SVE: CPU 向けに SVE を有効にする（arm64 のみ）。
	  KVM_CAP_ARM_SVE に依存する。
	  KVM_ARM_VCPU_FINALIZE(KVM_ARM_VCPU_SVE) が必要:

	   * KVM_ARM_VCPU_INIT の後:

	      - KVM_REG_ARM64_SVE_VLS は KVM_GET_ONE_REG で読める。この
	        擬似レジスタの初期値は、このホスト上の vcpu で可能な
	        ベクトル長の最良の集合を示す。

	   * KVM_ARM_VCPU_FINALIZE(KVM_ARM_VCPU_SVE) の前:

	      - KVM_RUN と KVM_GET_REG_LIST は利用できない。

	      - KVM_GET_ONE_REG と KVM_SET_ONE_REG を使って、スケーラブルな
	        アーキテクチャ SVE レジスタ KVM_REG_ARM64_SVE_ZREG()、
	        KVM_REG_ARM64_SVE_PREG()、KVM_REG_ARM64_SVE_FFR に
	        アクセスできない。

	      - KVM_REG_ARM64_SVE_VLS は、vcpu で利用可能なベクトル長の
	        集合を変更するために、KVM_SET_ONE_REG で任意に書き込める。

	   * KVM_ARM_VCPU_FINALIZE(KVM_ARM_VCPU_SVE) の後:

	      - KVM_REG_ARM64_SVE_VLS 擬似レジスタは不変になり、
	        KVM_SET_ONE_REG では書き込めなくなる。

	- KVM_ARM_VCPU_HAS_EL2: ネスト仮想化サポートを有効にし、ゲストを
	  EL1 ではなく EL2 から起動する。
	  KVM_CAP_ARM_EL2 に依存する。
	  KVM_ARM_VCPU_HAS_EL2_E2H0 も設定されていない限り、VM は
	  HCR_EL2.E2H が RES1（VHE）の状態で実行される。

	- KVM_ARM_VCPU_HAS_EL2_E2H0: ネスト仮想化サポートを HCR_EL2.E2H が
	  RES0（非 VHE）の場合に限る。
	  KVM_CAP_ARM_EL2_E2H0 に依存する。
	  KVM_ARM_VCPU_HAS_EL2 も設定しなければならない。

4.83 KVM_ARM_PREFERRED_TARGET
-----------------------------

:Capability: basic
:Architectures: arm64
:Type: vm ioctl
:Parameters: struct kvm_vcpu_init（出力）
:Returns: 成功時は 0、エラー時は -1

基盤となるホスト上で KVM がエミュレートできる、推奨の CPU target タイプを
KVM に問い合わせる。

この ioctl は、推奨の CPU target タイプを含む struct kvm_vcpu_init の
インスタンスを返す。kvm_vcpu_init->features ビットマップは空で返される。
vCPU の機能はユーザ空間自身が選択し、その可用性は KVM_ARM_VCPU_INIT に
挙げられているケイパビリティで通知される。

この ioctl が返す情報は、KVM_ARM_VCPU_INIT ioctl に渡す
struct kvm_vcpu_init のインスタンスを用意するのに使える。そうすると、
基盤となるホストに一致する VCPU になる。


4.84 KVM_GET_REG_LIST
---------------------

:Capability: basic
:Architectures: arm64, mips, riscv, x86（KVM_CAP_ONE_REG がある場合）
:Type: vcpu ioctl
:Parameters: struct kvm_reg_list（入力/出力）
:Returns: 成功時は 0、エラー時は -1

Errors:

  =====      ==============================================================
  E2BIG      reg インデックスの一覧が、ユーザが指定した配列に収まらない
             ほど大きい（必要な数が n に書き込まれる）。
  =====      ==============================================================

::

  struct kvm_reg_list {
	__u64 n; /* number of registers in reg[] */
	__u64 reg[0];
  };

この ioctl は、KVM_GET_ONE_REG/KVM_SET_ONE_REG の呼び出しで対応している
ゲストレジスタを返す。

s390 は歴史的な理由（要するに誰も気にしなかった）により KVM_GET_REG_LIST
に対応していない点に注意。カーネル 4.x 以降のレジスタの集合は次のとおり:

- KVM_REG_S390_TODPR

- KVM_REG_S390_EPOCHDIFF

- KVM_REG_S390_CPU_TIMER

- KVM_REG_S390_CLOCK_COMP

- KVM_REG_S390_PFTOKEN

- KVM_REG_S390_PFCOMPARE

- KVM_REG_S390_PFSELECT

- KVM_REG_S390_PP

- KVM_REG_S390_GBEA

x86 では、KVM_GET_MSR_INDEX_LIST が列挙するすべての MSR は
KVM_X86_REG_TYPE_MSR タイプとして対応しているが、KVM_GET_REG_LIST では
列挙されない点に注意。

4.85 KVM_ARM_SET_DEVICE_ADDR (非推奨)
-------------------------------------

:Capability: KVM_CAP_ARM_SET_DEVICE_ADDR
:Architectures: arm64
:Type: vm ioctl
:Parameters: struct kvm_arm_device_addr（入力）
:Returns: 成功時は 0、エラー時は -1

Errors:

  ======  ============================================
  ENODEV  デバイス ID が不明
  ENXIO   現在のシステムでデバイスが未対応
  EEXIST  アドレスがすでに設定済み
  E2BIG   アドレスがゲストの物理アドレス空間の外
  EBUSY   アドレスが他のデバイスの範囲と重なる
  ======  ============================================

::

  struct kvm_arm_device_addr {
	__u64 id;
	__u64 addr;
  };

ゲストがエミュレートされたデバイスまたは直接公開されたデバイスにアクセス
できる、ゲストの物理アドレス空間内のデバイスアドレスを指定する。ホスト
カーネルはこれを知る必要がある。id フィールドは、特定のデバイスのための
アーキテクチャ固有の識別子である。

arm64 は id フィールドを 2 つの部分に分ける。デバイス ID と、個々の
デバイスに固有のアドレスタイプ ID である::

  bits:  | 63        ...       32 | 31    ...    16 | 15    ...    0 |
  field: |        0x00000000      |     device id   |  addr type id  |

arm64 で現在これが必要なのは、ハードウェア VGIC 機能のためにカーネル内
GIC サポートを使い、デバイス ID として KVM_ARM_DEVICE_VGIC_V2 を使う場合
だけである。VGIC の仮想 CPU インタフェースとディストリビュータインタフェース
をゲストにマッピングするためのベースアドレスを設定するときは、
KVM_CREATE_IRQCHIP を呼んだ後、いずれかの VCPU で KVM_RUN を呼ぶ前に、この
ioctl を呼ばなければならない。いずれかのベースアドレスに対してこの ioctl
を 2 回呼ぶと、-EEXIST が返る。

この IOCTL は非推奨であり、代わりに、より柔軟な SET/GET_DEVICE_ATTR API を
使うべきである。


4.86 KVM_PPC_RTAS_DEFINE_TOKEN
------------------------------

:Capability: KVM_CAP_PPC_RTAS
:Architectures: ppc
:Type: vm ioctl
:Parameters: struct kvm_rtas_token_args
:Returns: 成功時は 0、エラー時は -1

RTAS（Run Time Abstraction Services）サービスのトークン値を定義し、カーネル
内で処理できるようにする。引数の構造体はサービスの名前を与える。これは
カーネル側の実装を持つサービスの名前でなければならない。トークン値が 0
以外の場合、その値はそのサービスに関連付けられ、以降にゲストがそのトークン
を指定して行う RTAS 呼び出しはカーネルが処理する。トークン値が 0 の場合、
そのサービスに関連付けられたトークンは忘れられ、以降にゲストがそのサービス
に対して行う RTAS 呼び出しは、処理のためにユーザ空間に渡される。

4.87 KVM_SET_GUEST_DEBUG
------------------------

:Capability: KVM_CAP_SET_GUEST_DEBUG
:Architectures: x86, s390, ppc, arm64
:Type: vcpu ioctl
:Parameters: struct kvm_guest_debug（入力）
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_guest_debug {
       __u32 control;
       __u32 pad;
       struct kvm_guest_debug_arch arch;
  };

プロセッサ固有のデバッグレジスタを設定し、ゲストのデバッグイベントを処理
するように vcpu を構成する。この構造体は 2 つの部分からなる。1 つ目は制御
ビットフィールドで、実行時に処理するデバッグイベントの種類を示す。共通の
制御ビットは次のとおり:

  - KVM_GUESTDBG_ENABLE:        ゲストのデバッグが有効になる
  - KVM_GUESTDBG_SINGLESTEP:    次の実行でシングルステップする

control フィールドの上位 16 ビットはアーキテクチャ固有の制御フラグで、次の
ものを含みうる:

  - KVM_GUESTDBG_USE_SW_BP:     ソフトウェアブレークポイントを使う [x86, arm64]
  - KVM_GUESTDBG_USE_HW_BP:     ハードウェアブレークポイントを使う [x86, s390]
  - KVM_GUESTDBG_USE_HW:        ハードウェアデバッグイベントを使う [arm64]
  - KVM_GUESTDBG_INJECT_DB:     DB タイプの例外を注入する [x86]
  - KVM_GUESTDBG_INJECT_BP:     BP タイプの例外を注入する [x86]
  - KVM_GUESTDBG_EXIT_PENDING:  即座にゲストエグジットをトリガーする [s390]
  - KVM_GUESTDBG_BLOCKIRQ:      割り込み/NMI/SMI の注入を避ける [x86]

たとえば KVM_GUESTDBG_USE_SW_BP は、メモリ内でソフトウェアブレークポイント
が有効になっていることを示す。そのため、ブレークポイント例外が正しく
トラップされ、KVM の実行ループがブレークポイントで終了して、通常のゲスト
ベクタへ流れ込まないようにする必要がある。KVM_GUESTDBG_USE_HW_BP の場合は、
ゲスト vCPU のアーキテクチャ固有レジスタが正しい（渡された）値に更新される
ようにする必要がある。

構造体の 2 つ目の部分はアーキテクチャ固有で、通常はデバッグレジスタの集合
を含む。

arm64 では、デバッグレジスタの数は実装依存であり、
KVM_CAP_GUEST_DEBUG_HW_BPS と KVM_CAP_GUEST_DEBUG_HW_WPS ケイパビリティを
問い合わせれば分かる。これらは、対応するレジスタの数を示す正の数を返す。

arm64 では、保護 VM に対してこの ioctl は -EPERM を返す。保護ゲストの
デバッグは対応していない。Documentation/virt/kvm/arm/pkvm.rst を参照。

ppc では、KVM_CAP_PPC_GUEST_DEBUG_SSTEP ケイパビリティが、シングルステップ
のデバッグイベント（KVM_GUESTDBG_SINGLESTEP）に対応しているかどうかを示す。

また、対応している場合、KVM_CAP_SET_GUEST_DEBUG2 ケイパビリティが、control
フィールドで対応している KVM_GUESTDBG_* ビットを示す。

デバッグイベントによってメインの実行ループが終了するとき、その理由は
KVM_EXIT_DEBUG で、kvm_run 構造体の kvm_debug_exit_arch の部分に
アーキテクチャ固有のデバッグ情報が入る。

4.88 KVM_GET_EMULATED_CPUID
---------------------------

:Capability: KVM_CAP_EXT_EMUL_CPUID
:Architectures: x86
:Type: system ioctl
:Parameters: struct kvm_cpuid2（入力/出力）
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_cpuid2 {
	__u32 nent;
	__u32 flags;
	struct kvm_cpuid_entry2 entries[0];
  };

'flags' メンバは、ユーザ空間からフラグを渡すために使う。

::

  #define KVM_CPUID_FLAG_SIGNIFCANT_INDEX		BIT(0)
  #define KVM_CPUID_FLAG_STATEFUL_FUNC		BIT(1) /* deprecated */
  #define KVM_CPUID_FLAG_STATE_READ_NEXT		BIT(2) /* deprecated */

  struct kvm_cpuid_entry2 {
	__u32 function;
	__u32 index;
	__u32 flags;
	__u32 eax;
	__u32 ebx;
	__u32 ecx;
	__u32 edx;
	__u32 padding[3];
  };

この ioctl は、kvm がエミュレートする x86 の cpuid 機能を返す。ユーザ空間は、
この ioctl が返す情報を使って、ホストにネイティブに存在するのではなく kvm
がエミュレートしている機能はどれかを調べられる。

ユーザ空間は、可変長配列 'entries' のエントリ数を示す 'nent' フィールドを
持つ kvm_cpuid2 構造体を渡して KVM_GET_EMULATED_CPUID を呼ぶ。エントリ数が
CPU の機能を記述するのに少なすぎる場合、エラー（E2BIG）が返される。
多すぎる場合、'nent' フィールドが調整され、エラー（ENOMEM）が返される。
ちょうどの場合、'nent' フィールドは 'entries' 配列内の有効なエントリ数に
調整され、その後配列が埋められる。

返されるエントリは、kvm がエミュレートする各機能について、CPUID 命令が
返す設定済みの CPUID ビットである。不明または未対応の機能ビットはクリア
される。

たとえば x2apic のような機能は、ホスト CPU に存在しないことがあるが、
効率的にエミュレートできるため kvm が KVM_GET_SUPPORTED_CPUID で公開して
いる。したがってここには含まれない。

各エントリのフィールドは次のように定義される:

  function:
	 エントリを取得するために使う eax の値
  index:
	 エントリを取得するために使う ecx の値（ecx の影響を受ける
	 エントリの場合）
  flags:
    次の 0 個以上の OR:

        KVM_CPUID_FLAG_SIGNIFCANT_INDEX:
           index フィールドが有効な場合

   eax, ebx, ecx, edx:

         cpuid 命令がこの function/index の組み合わせに対して
         返す値

4.89 KVM_S390_MEM_OP
--------------------

:Capability: KVM_CAP_S390_MEM_OP, KVM_CAP_S390_PROTECTED, KVM_CAP_S390_MEM_OP_EXTENSION
:Architectures: s390
:Type: vm ioctl, vcpu ioctl
:Parameters: struct kvm_s390_mem_op (in)
:Returns: 成功時は = 0、
          一般的なエラー（例: -EFAULT や -ENOMEM）の場合は < 0、
          アクセスがそのような例外を引き起こす場合は 16 ビットのプログラム例外コード

VM のメモリに対してデータを読み書きする。KVM_CAP_S390_MEM_OP_EXTENSION
ケイパビリティが、どの機能がサポートされるかを指定する。

パラメータは次の構造体で指定する::

  struct kvm_s390_mem_op {
	__u64 gaddr;		/* the guest address */
	__u64 flags;		/* flags */
	__u32 size;		/* amount of bytes */
	__u32 op;		/* type of operation */
	__u64 buf;		/* buffer in userspace */
	union {
		struct {
			__u8 ar;	/* the access register number */
			__u8 key;	/* access key, ignored if flag unset */
			__u8 pad1[6];	/* ignored */
			__u64 old_addr;	/* ignored if flag unset */
		};
		__u32 sida_offset; /* offset into the sida */
		__u8 reserved[32]; /* ignored */
	};
  };

メモリ領域の開始アドレスは "gaddr" フィールドで、領域の長さは "size" フィールドで
指定しなければならない（0 であってはならない）。"size" の最大値は、
KVM_CAP_S390_MEM_OP ケイパビリティを調べると分かる。"buf" はユーザ空間の
アプリケーションが用意するバッファであり、読み出しアクセスでは読み出したデータを
書き込む先、書き込みアクセスでは書き込むデータを置いておく場所になる。
"reserved" フィールドは将来の拡張用である。予約済みの値と未使用の値は無視される。
メンバを追加する将来の拡張は、新しいフラグを導入しなければならない。

操作の種類は "op" フィールドで指定する。動作を変えるフラグは "flags" フィールドで
設定できる。未定義のフラグビットは 0 に設定しなければならない。

指定できる操作は次のとおりである:
  * ``KVM_S390_MEMOP_LOGICAL_READ``
  * ``KVM_S390_MEMOP_LOGICAL_WRITE``
  * ``KVM_S390_MEMOP_ABSOLUTE_READ``
  * ``KVM_S390_MEMOP_ABSOLUTE_WRITE``
  * ``KVM_S390_MEMOP_SIDA_READ``
  * ``KVM_S390_MEMOP_SIDA_WRITE``
  * ``KVM_S390_MEMOP_ABSOLUTE_CMPXCHG``

論理読み出し/書き込み:
^^^^^^^^^^^^^^^^^^^^^

論理メモリにアクセスする。つまり、指定されたゲストアドレスを、VCPU の状態に応じて
絶対アドレスへ変換し、その絶対アドレスをアクセスの対象とする。"ar" は使用する
アクセスレジスタ番号を指定する。有効な範囲は 0..15 である。
論理アクセスは VCPU ioctl でのみ許可される。
論理アクセスは保護されていないゲストでのみ許可される。

サポートされるフラグ:
  * ``KVM_S390_MEMOP_F_CHECK_ONLY``
  * ``KVM_S390_MEMOP_F_INJECT_EXCEPTION``
  * ``KVM_S390_MEMOP_F_SKEY_PROTECTION``

KVM_S390_MEMOP_F_CHECK_ONLY フラグを設定すると、対応するメモリアクセスがアクセス
例外を引き起こすかどうかを調べられる。ただし、宛先のメモリにあるデータへの実際の
アクセスは行わない。この場合、"buf" は使われず、NULL でもよい。

アクセス中にアクセス例外が発生した場合（または KVM_S390_MEMOP_F_CHECK_ONLY の場合に
発生すると見込まれる場合）、ioctl は例外の種類を表す正のエラー番号を返す。
KVM_S390_MEMOP_F_INJECT_EXCEPTION フラグが設定されていれば、この例外は対応する
VCPU にも直接発生させる。
保護例外では、別途指定がない限り、注入される変換例外識別子（TEID）が抑止を示す。

KVM_S390_MEMOP_F_SKEY_PROTECTION フラグが設定されている場合、ストレージキー保護も
有効になり、"key" で指定したアクセスキーではアクセスが禁止される場合に例外が
発生しうる。有効な範囲は 0..15 である。KVM_S390_MEMOP_F_SKEY_PROTECTION は、
KVM_CAP_S390_MEM_OP_EXTENSION が > 0 の場合に利用できる。
アクセスするメモリが複数のページにまたがり、それらのページのストレージキーが
異なることがあるため、メモリが変更されたあとに保護例外が発生する可能性がある。
この場合、例外を注入しても、TEID は抑止を示さない。

絶対読み出し/書き込み:
^^^^^^^^^^^^^^^^^^^^^

絶対メモリにアクセスする。この操作は KVM_S390_MEMOP_F_SKEY_PROTECTION フラグと
組み合わせて使うことを想定している。メモリへのアクセスと、ストレージキー保護に
必要なチェックを 1 つの操作として行えるようにするためである。これに対し、ユーザ
空間がストレージキーを取得してチェックを行い、そのあとでメモリにアクセスする
方法では、チェックとアクセスのあいだに遅延が生じうる。
KVM_CAP_S390_MEM_OP_EXTENSION に KVM_S390_MEMOP_EXTENSION_CAP_BASE ビットが設定
されていれば、絶対アクセスは VM ioctl で許可される。
現時点では、絶対アクセスは VCPU ioctl では許可されていない。
絶対アクセスは保護されていないゲストでのみ許可される。

サポートされるフラグ:
  * ``KVM_S390_MEMOP_F_CHECK_ONLY``
  * ``KVM_S390_MEMOP_F_SKEY_PROTECTION``

論理アクセスと共通のフラグの意味は、論理アクセスの場合と同じである。

絶対 cmpxchg:
^^^^^^^^^^^^^

絶対ゲストメモリに対して cmpxchg を行う。KVM_S390_MEMOP_F_SKEY_PROTECTION フラグと
組み合わせて使うことを想定している。
無条件の書き込みを行う代わりに、対象の位置が "old_addr" の指す値を持っている
場合にだけアクセスする。これは、"size" パラメータで指定した長さのアトミックな
cmpxchg として実行される。"size" は 16 以下の 2 の冪でなければならない。
対象の値が古い値と一致しないために交換が行われなかった場合、"old_addr" の指す値は
対象の値で置き換えられる。ユーザ空間は、この置き換えが起きたかどうかを見て、
交換が行われたかどうかを判断できる。KVM_CAP_S390_MEM_OP_EXTENSION に
KVM_S390_MEMOP_EXTENSION_CAP_CMPXCHG フラグが設定されていれば、cmpxchg 操作は
VM ioctl で許可される。

サポートされるフラグ:
  * ``KVM_S390_MEMOP_F_SKEY_PROTECTION``

SIDA 読み出し/書き込み:
^^^^^^^^^^^^^^^^^^^^^^

保護ゲストの命令エミュレーションに必要なメモリオペランドを含む secure instruction
data area（SIDA）にアクセスする。
SIDA アクセスは、KVM_CAP_S390_PROTECTED ケイパビリティが利用できる場合に利用できる。
SIDA アクセスは VCPU ioctl でのみ許可される。
SIDA アクセスは保護ゲストでのみ許可される。

サポートされるフラグはない。

4.90 KVM_S390_GET_SKEYS
-----------------------

:Capability: KVM_CAP_S390_SKEYS
:Architectures: s390
:Type: vm ioctl
:Parameters: struct kvm_s390_skeys
:Returns: 成功時は 0、ゲストがストレージキーを使っていない場合は
          KVM_S390_GET_SKEYS_NONE、エラー時は負の値

この ioctl は、s390 アーキテクチャでゲストのストレージキーの値を取得するために
使う。ioctl はパラメータを kvm_s390_skeys 構造体で受け取る::

  struct kvm_s390_skeys {
	__u64 start_gfn;
	__u64 count;
	__u64 skeydata_addr;
	__u32 flags;
	__u32 reserved[9];
  };

start_gfn フィールドは、ストレージキーを取得したい最初のゲストフレームの番号で
ある。

count フィールドは、ストレージキーを取得する連続したフレームの数である
（start_gfn から始まる）。count フィールドは 1 以上でなければならず、許される
最大値は KVM_S390_SKEYS_MAX と定義されている。この範囲外の値では、ioctl は
-EINVAL を返す。

skeydata_addr フィールドは、count バイトを格納できるだけの大きさを持つバッファの
アドレスである。このバッファは、ioctl によってストレージキーのデータで埋められる。

4.91 KVM_S390_SET_SKEYS
-----------------------

:Capability: KVM_CAP_S390_SKEYS
:Architectures: s390
:Type: vm ioctl
:Parameters: struct kvm_s390_skeys
:Returns: 成功時は 0、エラー時は負の値

この ioctl は、s390 アーキテクチャでゲストのストレージキーの値を設定するために
使う。ioctl はパラメータを kvm_s390_skeys 構造体で受け取る。構造体の定義は
KVM_S390_GET_SKEYS の節を参照。

start_gfn フィールドは、ストレージキーを設定したい最初のゲストフレームの番号で
ある。

count フィールドは、ストレージキーを取得する連続したフレームの数である
（start_gfn から始まる）。count フィールドは 1 以上でなければならず、許される
最大値は KVM_S390_SKEYS_MAX と定義されている。この範囲外の値では、ioctl は
-EINVAL を返す。

skeydata_addr フィールドは、count バイトのストレージキーを含むバッファの
アドレスである。バッファ内の各バイトは、start_gfn から count フレームにわたって、
1 つのフレームのストレージキーとして設定される。

備考: 与えられたデータにアーキテクチャ上不正なキー値が 1 つでもあると、ioctl は
-EINVAL を返す。

4.92 KVM_S390_IRQ
-----------------

:Capability: KVM_CAP_S390_INJECT_IRQ
:Architectures: s390
:Type: vcpu ioctl
:Parameters: struct kvm_s390_irq (in)
:Returns: 成功時は 0、エラー時は -1

Errors:


  ======  =================================================================
  EINVAL  割り込みの種類が無効である。種類が KVM_S390_SIGP_STOP で
          フラグパラメータが無効な値である場合、または種類が
          KVM_S390_INT_EXTERNAL_CALL で code が VCPU の最大数を
          超えている場合
  EBUSY   種類が KVM_S390_SIGP_SET_PREFIX で vcpu が停止していない、
          種類が KVM_S390_SIGP_STOP ですでに stop IRQ が保留中である、
          種類が KVM_S390_INT_EXTERNAL_CALL ですでに外部呼び出し
          割り込みが保留中である
  ======  =================================================================

ゲストに割り込みを注入できる。

パラメータとして struct kvm_s390_irq を使うと、KVM_S390_INTERRUPT では注入できない
追加のペイロードを注入できる。

割り込みのパラメータは kvm_s390_irq で渡す::

  struct kvm_s390_irq {
	__u64 type;
	union {
		struct kvm_s390_io_info io;
		struct kvm_s390_ext_info ext;
		struct kvm_s390_pgm_info pgm;
		struct kvm_s390_emerg_info emerg;
		struct kvm_s390_extcall_info extcall;
		struct kvm_s390_prefix_info prefix;
		struct kvm_s390_stop_info stop;
		struct kvm_s390_mchk_info mchk;
		char reserved[64];
	} u;
  };

type は次のいずれかである:

- KVM_S390_SIGP_STOP - sigp stop。パラメータは .stop にある
- KVM_S390_PROGRAM_INT - program check。パラメータは .pgm にある
- KVM_S390_SIGP_SET_PREFIX - sigp set prefix。パラメータは .prefix にある
- KVM_S390_RESTART - restart。パラメータなし
- KVM_S390_INT_CLOCK_COMP - クロックコンパレータ割り込み。パラメータなし
- KVM_S390_INT_CPU_TIMER - CPU タイマー割り込み。パラメータなし
- KVM_S390_INT_EMERGENCY - sigp emergency。パラメータは .emerg にある
- KVM_S390_INT_EXTERNAL_CALL - sigp external call。パラメータは .extcall にある
- KVM_S390_MCHK - マシンチェック割り込み。パラメータは .mchk にある

これは非同期の vcpu ioctl であり、任意のスレッドから呼び出せる。

4.94 KVM_S390_GET_IRQ_STATE
---------------------------

:Capability: KVM_CAP_S390_IRQ_STATE
:Architectures: s390
:Type: vcpu ioctl
:Parameters: struct kvm_s390_irq_state (out)
:Returns: バッファにコピーしたバイト数以上、
          バッファサイズが 0 の場合は -EINVAL、
          保留中の割り込みをすべて格納するにはバッファサイズが小さすぎる場合は
          -ENOBUFS、バッファアドレスが無効だった場合は -EFAULT

この ioctl を使うと、ユーザ空間は現在保留中のすべての割り込みの状態を 1 つの
バッファにまとめて取得できる。用途にはマイグレーションやゲストの状態の調査がある。
パラメータ構造体は、ユーザ空間のバッファのアドレスとその長さを保持する::

  struct kvm_s390_irq_state {
	__u64 buf;
	__u32 flags;        /* will stay unused for compatibility reasons */
	__u32 len;
	__u32 reserved[4];  /* will stay unused for compatibility reasons */
  };

ユーザ空間は上記の構造体を渡し、保留中の割り込みごとに struct kvm_s390_irq が
用意したバッファにコピーされる。

この構造体には、将来の拡張用に flags フィールドと reserved フィールドがある。
カーネルが flags == 0 を検査したことはなく、QEMU が flags と reserved を
あらかじめゼロで埋めたこともないため、これらのフィールドは互換性を壊さずに
将来使うことはできない。

-ENOBUFS が返された場合、用意したバッファが小さすぎたことを表す。ユーザ空間は
より大きなバッファで再試行してよい。

4.95 KVM_S390_SET_IRQ_STATE
---------------------------

:Capability: KVM_CAP_S390_IRQ_STATE
:Architectures: s390
:Type: vcpu ioctl
:Parameters: struct kvm_s390_irq_state (in)
:Returns: 成功時は 0、
          バッファアドレスが無効だった場合は -EFAULT、
          バッファの長さが無効な場合は -EINVAL（後述）、
          すでに保留中の割り込みがあった場合は -EBUSY、
          実際に割り込みを注入するときに発生したエラー。KVM_S390_IRQ を参照。

この ioctl を使うと、ユーザ空間は vcpu に対して現在保留中のすべての CPU ローカル
割り込みの状態をまとめて設定できる。マイグレーション後に割り込みの状態を復元する
ためのものである。入力パラメータは、struct kvm_s390_irq_state を含むユーザ空間の
バッファである::

  struct kvm_s390_irq_state {
	__u64 buf;
	__u32 flags;        /* will stay unused for compatibility reasons */
	__u32 len;
	__u32 reserved[4];  /* will stay unused for compatibility reasons */
  };

flags と reserved の制限も同様に適用される。
（KVM_S390_GET_IRQ_STATE を参照）

buf が参照するユーザ空間のメモリには、ゲストに注入する割り込みごとに
struct kvm_s390_irq が入っている。何らかの理由で割り込みの 1 つを注入できなかった
場合、ioctl は中断する。

len は sizeof(struct kvm_s390_irq) の倍数でなければならない。0 より大きい必要が
あり、(max_vcpus + 32) * sizeof(struct kvm_s390_irq) を超えてはならない。これは、
保留になりうる CPU ローカル割り込みの最大数である。

4.96 KVM_SMI
------------

:Capability: KVM_CAP_X86_SMM
:Architectures: x86
:Type: vcpu ioctl
:Parameters: none
:Returns: 成功時は 0、エラー時は -1

そのスレッドの vcpu に SMI をキューに入れる。

4.97 KVM_X86_SET_MSR_FILTER
-----------------------------

:Capability: KVM_CAP_X86_MSR_FILTER
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_msr_filter
:Returns: 成功時は 0、エラー時は < 0

::

  struct kvm_msr_filter_range {
  #define KVM_MSR_FILTER_READ  (1 << 0)
  #define KVM_MSR_FILTER_WRITE (1 << 1)
	__u32 flags;
	__u32 nmsrs; /* number of msrs in bitmap */
	__u32 base;  /* MSR index the bitmap starts at */
	__u8 *bitmap; /* a 1 bit allows the operations in flags, 0 denies */
  };

  #define KVM_MSR_FILTER_MAX_RANGES 16
  struct kvm_msr_filter {
  #define KVM_MSR_FILTER_DEFAULT_ALLOW (0 << 0)
  #define KVM_MSR_FILTER_DEFAULT_DENY  (1 << 0)
	__u32 flags;
	struct kvm_msr_filter_range ranges[KVM_MSR_FILTER_MAX_RANGES];
  };

``struct kvm_msr_filter_range`` の flags の値:

``KVM_MSR_FILTER_READ``

  指定したビットマップを使って MSR への読み出しアクセスをフィルタリングする。
  ビットマップの 0 は読み出しアクセスを拒否すべきことを表し、1 は特定の MSR への
  読み出しが、デフォルトのフィルタ動作にかかわらず許可されるべきことを表す。

``KVM_MSR_FILTER_WRITE``

  指定したビットマップを使って MSR への書き込みアクセスをフィルタリングする。
  ビットマップの 0 は書き込みアクセスを拒否すべきことを表し、1 は特定の MSR への
  書き込みが、デフォルトのフィルタ動作にかかわらず許可されるべきことを表す。

``struct kvm_msr_filter`` の flags の値:

``KVM_MSR_FILTER_DEFAULT_ALLOW``

  アクセスされる MSR インデックスに一致するフィルタ範囲がない場合、KVM は
  デフォルトですべての MSR へのアクセスを許可する。

``KVM_MSR_FILTER_DEFAULT_DENY``

  アクセスされる MSR インデックスに一致するフィルタ範囲がない場合、KVM は
  デフォルトですべての MSR へのアクセスを拒否する。

この ioctl を使うと、ユーザ空間は最大 16 個の MSR 範囲のビットマップを定義し、
KVM なら通常は許可されるゲストの MSR アクセスを拒否できる。ある MSR がどの範囲にも
含まれない場合は、"default" のフィルタ動作が適用される。各ビットマップ範囲は
[base .. base+nmsrs) の MSR を対象とする。

ユーザ空間が MSR アクセスを拒否した場合の KVM の動作は、KVM_CAP_X86_USER_SPACE_MSR
の KVM_MSR_EXIT_REASON_FILTER が有効かどうかで変わる。KVM_MSR_EXIT_REASON_FILTER が
有効なら、拒否されたアクセスで KVM はユーザ空間へエグジットする。つまり、ユーザ
空間が MSR アクセスを実質的に横取りする。KVM_MSR_EXIT_REASON_FILTER が有効で
なければ、拒否されたアクセスで KVM はゲストに #GP を注入する。なお、VMX 遷移中の
MSR ロード/ストアのエミュレーション中に MSR アクセスが拒否された場合、KVM は
KVM_MSR_EXIT_REASON_FILTER を無視する。詳細は後述の警告を参照。

ユーザ空間が MSR アクセスを許可した場合、KVM は vCPU モデルに従ってそのアクセスを
エミュレートまたは仮想化する（あるいはその両方を行う）。なお、ユーザ空間がアクセス
を許可しても、KVM が最終的に #GP を注入することはある。たとえば、KVM がその MSR を
サポートしていない場合や、その MSR のアーキテクチャ上の動作に従う場合である。

デフォルトでは、KVM は MSR 範囲フィルタを 1 つも持たない
KVM_MSR_FILTER_DEFAULT_ALLOW モードで動作する。

範囲を 1 つも設定せずに（すべての nmsrs == 0 で）この ioctl を呼び出すと、
MSR フィルタリングが無効になる。このモードでは ``KVM_MSR_FILTER_DEFAULT_DENY`` は
無効であり、エラーの原因になる。

.. warning::
   命令実行（エミュレーションまたはネイティブ）の副作用として起きる MSR アクセスは
   フィルタリングされない。ハードウェアが RDMSR と WRMSR 以外では MSR ビットマップに
   従わないためであり、KVM は命令をエミュレートするときも、ハードウェアとの
   無意味な差異を避けるために同じ動作をまねる。たとえば、RDPID は MSR_TSC_AUX を
   読み出し、SYSENTER は SYSENTER の MSR を読み出す。

   専用の VMCS フィールドでロード/ストアされる MSR は、VM エントリ/VM エグジットの
   エミュレーションの一部としてフィルタリングされない。

   VMX のロード/ストアリストでロード/ストアされる MSR は、VM エントリ/VM エグジット
   のエミュレーションの一部として、*フィルタリングされる*。VM エントリで MSR
   アクセスが拒否されると、KVM は一貫性チェックの
   VM エグジット(EXIT_REASON_MSR_LOAD_FAIL)を生成する。VM エグジットで MSR アクセス
   が拒否されると、KVM は VM-Abort を生成する。要するに、KVM は、VM エントリ/
   VM エグジットの MSR リストではロード/セーブできない MSR についての Intel の
   アーキテクチャ上の一覧を広げる。このような制限をエンドユーザーに伝えるのは
   プラットフォーム所有者の責任である。

   x2APIC の MSR アクセスはフィルタリングできない（x2APIC の MSR を含むフィルタは
   KVM が黙って無視する）。

なお、vCPU の実行中にこの ioctl を呼び出すと、本質的に競合が避けられない。
ただし、KVM は vCPU が以前のフィルタか新しいフィルタのどちらかを見ることを保証する。
たとえば、古いフィルタと新しいフィルタで同じ設定になっている MSR の動作は
決定的である。

同様に、拒否されたアクセスをユーザ空間で横取りしたい場合は、フィルタを有効にする
前に KVM_MSR_EXIT_REASON_FILTER を有効にし、すべてのフィルタを無効にしたあとまで
有効なままにしておかなければならない。これを守らないと、KVM がユーザ空間へ
エグジットする代わりに #GP を注入することがある。

4.98 KVM_CREATE_SPAPR_TCE_64
----------------------------

:Capability: KVM_CAP_SPAPR_TCE_64
:Architectures: powerpc
:Type: vm ioctl
:Parameters: struct kvm_create_spapr_tce_64 (in)
:Returns: 作成した TCE テーブルを操作するためのファイルディスクリプタ

これは、32 ビットウィンドウしかサポートしない KVM_CAP_SPAPR_TCE の拡張であり、
4.62 KVM_CREATE_SPAPR_TCE で説明する。

このケイパビリティは、ioctl インタフェースで拡張された構造体を使う::

  /* for KVM_CAP_SPAPR_TCE_64 */
  struct kvm_create_spapr_tce_64 {
	__u64 liobn;
	__u32 page_shift;
	__u32 flags;
	__u64 offset;	/* in pages */
	__u64 size; 	/* in pages */
  };

この拡張の目的は、可変のページサイズを持つ、より大きな DMA ウィンドウをもう 1 つ
サポートすることである。KVM_CREATE_SPAPR_TCE_64 は、64 ビットのウィンドウサイズ、
IOMMU のページシフト、対応する DMA ウィンドウのバスオフセットを受け取る。
@size と @offset は IOMMU ページの数である。

@flags は現時点では使われない。

その他の機能は KVM_CREATE_SPAPR_TCE と同じである。

4.99 KVM_REINJECT_CONTROL
-------------------------

:Capability: KVM_CAP_REINJECT_CONTROL
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_reinject_control (in)
:Returns: 成功時は 0、
          struct kvm_reinject_control を読み出せなかった場合は -EFAULT、
          以前に KVM_CREATE_PIT または KVM_CREATE_PIT2 が成功しなかった場合は
          -ENXIO。

i8254（PIT）には reinject と !reinject の 2 つのモードがある。デフォルトは
reinject である。このモードでは、KVM は経過した i8254 のティックをキューに入れ、
i8254 が注入するベクタからの割り込みの完了を監視する。reinject モードは、i8254
からの保留中の割り込みがないときにティックをキューから取り出し、その割り込みを
注入する。!reinject モードは、ティックが届くとすぐに割り込みを注入する。

::

  struct kvm_reinject_control {
	__u8 pit_reinject;
	__u8 reserved[31];
  };

pit_reinject = 0（!reinject モード）は、タイミングの計測に PIT を使う古い
オペレーティングシステム（例: Linux 2.4.x）を動かす場合を除いて推奨する。

4.100 KVM_PPC_CONFIGURE_V3_MMU
------------------------------

:Capability: KVM_CAP_PPC_MMU_RADIX または KVM_CAP_PPC_MMU_HASH_V3
:Architectures: ppc
:Type: vm ioctl
:Parameters: struct kvm_ppc_mmuv3_cfg (入力)
:Returns: 成功した場合は 0、
         struct kvm_ppc_mmuv3_cfg を読み取れない場合は -EFAULT、
         設定が不正な場合は -EINVAL

この ioctl は、ゲストが radix 変換と HPT（hashed page table）変換のどちらを
使うかを制御し、ゲストのプロセステーブルへのポインタを設定する。

::

  struct kvm_ppc_mmuv3_cfg {
	__u64	flags;
	__u64	process_table;
  };

flags には 2 つのビットを設定できる。KVM_PPC_MMUV3_RADIX と
KVM_PPC_MMUV3_GTSE である。KVM_PPC_MMUV3_RADIX を設定すると、ゲストは
radix ツリー変換を使うように構成され、クリアすると HPT 変換を使う。
KVM_PPC_MMUV3_GTSE を設定し、かつ KVM が許可する場合、ゲストはグローバル
TLB と SLB の無効化命令を使えるようになる。クリアすると、ゲストはこれらの
命令を使えない。

process_table フィールドは、ゲストの空間にあるゲストプロセステーブルの
アドレスとサイズを指定する。このフィールドの形式は、Power ISA V3.00 の
Book III 5.7.6.1 節で定義されているパーティションテーブルエントリの
2 番目のダブルワードと同じである。

4.101 KVM_PPC_GET_RMMU_INFO
---------------------------

:Capability: KVM_CAP_PPC_MMU_RADIX
:Architectures: ppc
:Type: vm ioctl
:Parameters: struct kvm_ppc_rmmu_info (出力)
:Returns: 成功した場合は 0、
	 struct kvm_ppc_rmmu_info を書き込めない場合は -EFAULT、
	 有用な情報を返せない場合は -EINVAL

この ioctl は、2 つのものを含む構造体を返す。(a) サポートされる radix
ツリーのジオメトリのリスト、(b) tlbie（TLB invalidate entry）命令の
"AP"（actual page size）フィールドに入れるページサイズを対応付ける
リストである。

::

  struct kvm_ppc_rmmu_info {
	struct kvm_ppc_radix_geom {
		__u8	page_shift;
		__u8	level_bits[4];
		__u8	pad[3];
	}	geometries[8];
	__u32	ap_encodings[8];
  };

geometries[] フィールドは、radix ページテーブルでサポートされる最大 8 個の
ジオメトリを表す。最小ページサイズの 2 を底とする対数と、ツリーの各レベル
（PTE レベルから PGD レベルまで、この順）でインデックスに使うビット数で
示す。未使用のエントリでは、page_shift フィールドが 0 になる。

ap_encodings は、サポートされるページサイズとその AP フィールドの
エンコーディングを示す。上位 3 ビットに AP 値を、下位 6 ビットに
ページサイズの 2 を底とする対数を入れてエンコードする。

4.102 KVM_PPC_RESIZE_HPT_PREPARE
--------------------------------

:Capability: KVM_CAP_SPAPR_RESIZE_HPT
:Architectures: powerpc
:Type: vm ioctl
:Parameters: struct kvm_ppc_resize_hpt (入力)
:Returns: 正常に完了した場合は 0、
	 新しい HPT を準備中の場合は >0。値は準備が完了するまでの推定ミリ秒数、
         struct kvm_reinject_control を読み取れない場合は -EFAULT、
	 指定した shift または flags が不正な場合は -EINVAL、
	 新しい HPT を確保できない場合は -ENOMEM

ゲストのハッシュページテーブル（HPT）を実行時にリサイズする PAPR 拡張を
実装するために使う。具体的には、ゲスト用の新しい候補 HPT の準備を開始・
停止・監視する。実質的に H_RESIZE_HPT_PREPARE ハイパーコールを実装する
ものである。

::

  struct kvm_ppc_resize_hpt {
	__u64 flags;
	__u32 shift;
	__u32 pad;
  };

ゲストに保留中の HPT がない状態で shift > 0 を指定して呼び出すと、
サイズ 2^(shift) バイトの新しい保留 HPT の準備を開始する。そして、準備が
完了するまでの推定ミリ秒数を正の整数で返す。

保留中の HPT があり、そのサイズがパラメータで要求したものと一致しない
場合に呼び出すと、既存の保留 HPT を破棄し、上記と同様に新しいものを作成する。

要求したサイズの保留 HPT がある場合に呼び出すと、次のようになる。

  * 保留 HPT の準備がすでに完了している場合は、0 を返す
  * 保留 HPT の準備が失敗した場合は、エラーコードを返し、その後で保留 HPT を
    破棄する
  * 保留 HPT の準備がまだ進行中の場合は、準備が完了するまでの推定ミリ秒数を
    返す

shift == 0 で呼び出すと、現在保留中の HPT を破棄して 0 を返す
（つまり、進行中の準備をキャンセルする）。

flags は将来の拡張用に予約されている。現在は flags にいずれかのビットを
設定すると -EINVAL になる。

通常は、0 以下を返すまで同じパラメータで繰り返し呼び出す。最初の呼び出しで
準備を開始し、以降の呼び出しで準備が完了または失敗するまで監視する。

4.103 KVM_PPC_RESIZE_HPT_COMMIT
-------------------------------

:Capability: KVM_CAP_SPAPR_RESIZE_HPT
:Architectures: powerpc
:Type: vm ioctl
:Parameters: struct kvm_ppc_resize_hpt (入力)
:Returns: 正常に完了した場合は 0、
         struct kvm_reinject_control を読み取れない場合は -EFAULT、
	 指定した shift または flags が不正な場合は -EINVAL、
	 保留中の HPT がない場合、または保留中の HPT が要求されたサイズでない場合は -ENXIO、
	 保留中の HPT の準備が完全に完了していない場合は -EBUSY、
	 既存の HPT エントリを新しい HPT に移す際にハッシュ衝突が起きた場合は -ENOSPC、
	 その他のエラー状態では -EIO

ゲストのハッシュページテーブル（HPT）を実行時にリサイズする PAPR 拡張を
実装するために使う。具体的には、ゲストを新しい HPT での動作に切り替えるよう
要求する。実質的に H_RESIZE_HPT_COMMIT ハイパーコールを実装するものである。

::

  struct kvm_ppc_resize_hpt {
	__u64 flags;
	__u32 shift;
	__u32 pad;
  };

これは、同じパラメータで KVM_PPC_RESIZE_HPT_PREPARE が 0 を返した後にだけ
呼び出すべきである。それ以外の場合、KVM_PPC_RESIZE_HPT_COMMIT はエラーを
返す（通常は -ENXIO か -EBUSY だが、準備を開始した後に失敗した場合は
別のエラーになることもある）。

ゲストがまだ静止状態（どの vCPU も MMU 有効なメモリアクセスを行わない状態）
になっていない場合、これがゲストに与える影響は不定である。

正常に完了すると、保留中の HPT がゲストのアクティブな HPT になり、
以前の HPT は破棄される。

失敗した場合、ゲストは引き続き以前の HPT で動作する。

4.104 KVM_X86_GET_MCE_CAP_SUPPORTED
-----------------------------------

:Capability: KVM_CAP_MCE
:Architectures: x86
:Type: system ioctl
:Parameters: u64 mce_cap (出力)
:Returns: 成功した場合は 0、エラー時は -1

サポートされる MCE ケイパビリティを返す。u64 mce_cap パラメータは
MSR_IA32_MCG_CAP レジスタと同じ形式である。サポートされるケイパビリティには、
対応するビットが設定される。

4.105 KVM_X86_SETUP_MCE
-----------------------

:Capability: KVM_CAP_MCE
:Architectures: x86
:Type: vcpu ioctl
:Parameters: u64 mcg_cap (入力)
:Returns: 成功した場合は 0、
         u64 mcg_cap を読み取れない場合は -EFAULT、
         要求したバンク数が不正な場合は -EINVAL、
         要求した MCE ケイパビリティがサポートされていない場合は -EINVAL

MCE サポートを使用可能な状態に初期化する。u64 mcg_cap パラメータは
MSR_IA32_MCG_CAP レジスタと同じ形式で、どのケイパビリティを有効にするかを
指定する。サポートされるエラー報告バンクの最大数は、KVM_CAP_MCE を確認する
際に取得できる。サポートされるケイパビリティは
KVM_X86_GET_MCE_CAP_SUPPORTED で取得できる。

4.106 KVM_X86_SET_MCE
---------------------

:Capability: KVM_CAP_MCE
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_x86_mce (入力)
:Returns: 成功した場合は 0、
         struct kvm_x86_mce を読み取れない場合は -EFAULT、
         バンク番号が不正な場合は -EINVAL、
         status フィールドに VAL ビットが設定されていない場合は -EINVAL

ゲストにマシンチェックエラー（MCE）を注入する。入力パラメータは
次のとおり::

  struct kvm_x86_mce {
	__u64 status;
	__u64 addr;
	__u64 misc;
	__u64 mcg_status;
	__u8 bank;
	__u8 pad1[7];
	__u64 pad2[3];
  };

報告される MCE が訂正不能エラーの場合、KVM はそれを MCE 例外としてゲストに
注入する。ゲストの MCG_STATUS レジスタが MCE が進行中であることを示している
場合、KVM は KVM_EXIT_SHUTDOWN の VM エグジットを発生させる。

そうでなく、MCE が訂正済みエラーの場合、KVM は対応するバンクにそれを格納する
だけである（ただし、そのバンクが以前に報告された訂正不能エラーを保持して
いない場合に限る）。

4.107 KVM_S390_GET_CMMA_BITS
----------------------------

:Capability: KVM_CAP_S390_CMMA_MIGRATION
:Architectures: s390
:Type: vm ioctl
:Parameters: struct kvm_s390_cmma_log (入力、出力)
:Returns: 成功した場合は 0、エラー時は負の値

Errors:

  ======     ==================================================================
  ENOMEM     処理を完了するために必要なメモリを確保できない
  ENXIO      CMMA が有効になっていない
  EINVAL     KVM_S390_CMMA_PEEK が設定されていないが、マイグレーションモードが
             有効になっていない
  EINVAL     KVM_S390_CMMA_PEEK が設定されていないが、ダーティトラッキングが
             無効になっている（そのためマイグレーションモードも自動的に無効になった）
  EFAULT     ユーザ空間のアドレスが不正か、そのアドレスに対応するページテーブルが
             存在しない（たとえば hugepage を使っている場合）。
  ======     ==================================================================

この ioctl は、s390 アーキテクチャで CMMA ビットの値を取得するために使う。
次の 2 つの場面での使用を想定している。

- ライブマイグレーション中に CMMA 値を保存する。ライブマイグレーションは、
  VM プロパティ KVM_REQ_START_MIGRATION で有効にする必要がある。
- フラグ KVM_S390_CMMA_PEEK を設定して、CMMA 値を破壊せずにのぞき見る。

この ioctl は kvm_s390_cmma_log 構造体を介してパラメータを受け取る。
取得したい値は、kvm_s390_cmma_log 構造体の "values" メンバで位置を示す
バッファに書き込まれる。入力構造体の値も必要に応じて更新される。

各 CMMA 値は 1 バイトを占める。

::

  struct kvm_s390_cmma_log {
	__u64 start_gfn;
	__u32 count;
	__u32 flags;
	union {
		__u64 remaining;
		__u64 mask;
	};
	__u64 values;
  };

start_gfn は、CMMA 値を取得する最初のゲストフレームの番号であり、

count はバッファの長さ（バイト単位）であり、

values は結果の書き込み先バッファを指す。

count が KVM_S390_SKEYS_MAX より大きい場合、KVM_S390_SKEYS_MAX とみなされる。
KVM_S390_SKEYS_MAX は、他の ioctl との一貫性のために流用している。

結果はフィールド values が指すバッファに書き込まれ、入力パラメータの値は
次のように更新される。

flags に応じて異なる動作を行う。これまでにサポートされているフラグは
KVM_S390_CMMA_PEEK だけである。

KVM_S390_CMMA_PEEK が設定されていない場合の既定の動作は次のとおりである。
start_gfn は、CMMA ビットがダーティだった最初のページフレームを示す。
クリーンなページはスキップされるため、入力で渡したものと同じとは限らない。

count は、実際にバッファに書き込まれたバイト数を示す。バッファはクリーンな値が
16 バイト見つかるまでしか埋められない（見つかったクリーンな値はバッファに
コピーされない）ため、入力値より小さくなることができる（そして実際にしばしば
小さくなる）。CMMA のマイグレーションブロックにはベースアドレスと長さが必要で
合計 16 バイトになるため、その後ろにダーティなデータがある場合は、クリーンな
データのサイズがヘッダのサイズを超えない範囲で、クリーンなデータをいくらか
返す。これにより、ユーザ空間とのやり取りが増える代わりに、保存または
ネットワーク経由で転送するデータ量を最小限にできる。次に ioctl を呼び出すと、
クリーンな値はすべてスキップされるので、見つかった 16 バイトより多くのデータを
節約できる可能性がある。

KVM_S390_CMMA_PEEK が設定されている場合は、マイグレーションモードでなくても
既存のストレージ属性を読み取り、それ以外の動作は行わない。

出力の start_gfn は入力の start_gfn と等しくなる。

出力の count は入力の count と等しくなる。ただし、メモリの末尾に達した場合を除く。

どちらの場合も、フィールド "remaining" はまだ残っているダーティな CMMA 値の
総数を示す。KVM_S390_CMMA_PEEK が設定されていてマイグレーションモードが
有効でない場合は 0 になる。

mask は使用しない。

values は結果を格納するユーザ空間のバッファを指す。

4.108 KVM_S390_SET_CMMA_BITS
----------------------------

:Capability: KVM_CAP_S390_CMMA_MIGRATION
:Architectures: s390
:Type: vm ioctl
:Parameters: struct kvm_s390_cmma_log (入力)
:Returns: 成功した場合は 0、エラー時は負の値

この ioctl は、s390 アーキテクチャで CMMA ビットの値を設定するために使う。
ライブマイグレーション中に CMMA 値を復元する用途を想定しているが、使い方に
制限はない。この ioctl は kvm_s390_cmma_values 構造体を介してパラメータを
受け取る。各 CMMA 値は 1 バイトを占める。

::

  struct kvm_s390_cmma_log {
	__u64 start_gfn;
	__u32 count;
	__u32 flags;
	union {
		__u64 remaining;
		__u64 mask;
 	};
	__u64 values;
  };

start_gfn は開始ゲストフレーム番号を示し、

count はバッファ内で対象とする値の個数を示し、

flags は使用せず、0 でなければならない。

mask は対象とする PGSTE ビットを示す。

remaining は使用しない。

values は値を格納するユーザ空間のバッファを指す。

この ioctl は、処理を完了するために必要なメモリを確保できない場合は -ENOMEM で、
CMMA が有効になっていない場合は -ENXIO で、count フィールドが大きすぎる場合
（たとえば KVM_S390_CMMA_SIZE_MAX を超える場合）または flags フィールドが 0 で
なかった場合は -EINVAL で、ユーザ空間のアドレスが不正な場合、不正なページに
書き込もうとした場合（たとえばメモリの末尾より後）、またはそのアドレスに
対応するページテーブルが存在しない場合（たとえば hugepage を使っている場合）は
-EFAULT で失敗することがある。

4.109 KVM_PPC_GET_CPU_CHAR
--------------------------

:Capability: KVM_CAP_PPC_GET_CPU_CHAR
:Architectures: powerpc
:Type: vm ioctl
:Parameters: struct kvm_ppc_cpu_char (出力)
:Returns: 正常に完了した場合は 0、
	 struct kvm_ppc_cpu_char を書き込めない場合は -EFAULT

この ioctl は、命令の投機的実行と、投機的実行に起因する情報漏えいの可能性に
関係する CPU の特定の特性についての情報をユーザ空間に与える
（CVE-2017-5715、CVE-2017-5753、CVE-2017-5754 を参照）。情報は
struct kvm_ppc_cpu_char で返され、その内容は次のとおり::

  struct kvm_ppc_cpu_char {
	__u64	character;		/* characteristics of the CPU */
	__u64	behaviour;		/* recommended software behaviour */
	__u64	character_mask;		/* valid bits in character */
	__u64	behaviour_mask;		/* valid bits in behaviour */
  };

拡張性のために、character_mask と behaviour_mask フィールドは、character と
behaviour のどのビットをカーネルが埋めたかを示す。将来、定義されるビットの
集合が拡張された場合、ユーザ空間は自分が新しいビットを知っているカーネル上で
動いているかどうかを判別できる。

character フィールドは、意図しない情報漏えいの防止に役立つ CPU の属性を表す。
具体的には、L1 データキャッシュをフラッシュ無効化する命令
（ori 30,30,0 または mtspr SPRN_TRIG2,rN）があるかどうか、L1 データキャッシュが、
エントリを作成したスレッドだけが使えるモードになっているかどうか、
bcctr[l] 命令が投機的実行を防ぐかどうか、投機的実行のバリア命令
（ori 31,31,0）が提供されているかどうかである。

behaviour フィールドは、意図しない情報漏えいを防ぐためにソフトウェアが取るべき
動作を表し、したがってハードウェアがどの脆弱性の影響を受けるかを表す。
具体的には、カーネルからユーザモードに戻る際に L1 データキャッシュを
フラッシュすべきかどうか、配列の境界チェックと配列アクセスの間に投機的実行の
バリアを置くべきかどうかである。

これらのフィールドは、新しい H_GET_CPU_CHARACTERISTICS ハイパーコールと
同じビット定義を使う。

4.110 KVM_MEMORY_ENCRYPT_OP
---------------------------

:Capability: basic
:Architectures: x86
:Type: vm ioctl, vcpu ioctl
:Parameters: 不透明なプラットフォーム固有の構造体（入力/出力）
:Returns: 成功した場合は 0、エラー時は -1

プラットフォームが暗号化された VM の作成をサポートしている場合、この ioctl は、
それらの暗号化 VM を管理するためのプラットフォーム固有のメモリ暗号化コマンドを
発行するために使える。

現在、この ioctl は、AMD プロセッサの Secure Encrypted Virtualization（SEV）
コマンドと、Intel プロセッサの Trusted Domain Extensions（TDX）コマンドの
両方を発行するために使われている。コマンドの詳細は
Documentation/virt/kvm/x86/amd-memory-encryption.rst と
Documentation/virt/kvm/x86/intel-tdx.rst で定義されている。

4.111 KVM_MEMORY_ENCRYPT_REG_REGION
-----------------------------------

:Capability: basic
:Architectures: x86
:Type: system
:Parameters: struct kvm_enc_region (入力)
:Returns: 成功した場合は 0、エラー時は -1

この ioctl は、暗号化されたデータを含む可能性のあるゲストメモリ領域
（たとえばゲスト RAM、SMRAM など）を登録するために使える。

これは SEV を有効にしたゲストで使う。暗号化が有効な場合、ゲストメモリ領域は
暗号化されたデータを含むことがある。SEV のメモリ暗号化エンジンは tweak を
使うため、異なる位置にある同一の平文ページはそれぞれ異なる暗号文になる。
したがって、それらのページの暗号文を入れ替えたり移動したりしても、平文が
入れ替わることはない。そのため、SEV ゲストの物理バッキングページを移動
（またはマイグレーション）するには、いくつか追加の手順が必要になる。

備考: 現在の SEV 鍵管理仕様には、暗号文ページを入れ替えたりマイグレーション
（移動）したりするコマンドがない。そのため、今のところ、この ioctl で登録された
ゲストメモリ領域はピン留めする。

4.112 KVM_MEMORY_ENCRYPT_UNREG_REGION
-------------------------------------

:Capability: basic
:Architectures: x86
:Type: system
:Parameters: struct kvm_enc_region (入力)
:Returns: 成功した場合は 0、エラー時は -1

この ioctl は、上記の KVM_MEMORY_ENCRYPT_REG_REGION ioctl で登録した
ゲストメモリ領域の登録を解除するために使える。

4.113 KVM_HYPERV_EVENTFD
------------------------

:Capability: KVM_CAP_HYPERV_EVENTFD
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_hyperv_eventfd (入力)

この ioctl は、指定した Hyper-V 接続 ID について、SIGNAL_EVENT ハイパーコールを
通じてゲストから通知を受け取るための eventfd を登録（または登録解除）する。
このときユーザエグジットは発生しない。イベントフラグ番号（ビット 24〜31）が
0 でない SIGNAL_EVENT ハイパーコールは、依然として KVM_EXIT_HYPERV_HCALL の
ユーザエグジットを発生させる。

::

  struct kvm_hyperv_eventfd {
	__u32 conn_id;
	__s32 fd;
	__u32 flags;
	__u32 padding[3];
  };

conn_id フィールドは 24 ビットに収まる必要がある::

  #define KVM_HYPERV_CONN_ID_MASK		0x00ffffff

flags フィールドに指定できる値は次のとおり::

  #define KVM_HYPERV_EVENTFD_DEASSIGN	(1 << 0)

:Returns: 成功した場合は 0、
 	  conn_id または flags が許容範囲外の場合は -EINVAL、
	  登録解除時に conn_id が登録されていない場合は -ENOENT、
	  登録時に conn_id がすでに登録されている場合は -EEXIST

4.114 KVM_GET_NESTED_STATE
--------------------------

:Capability: KVM_CAP_NESTED_STATE
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_nested_state (in/out)
:Returns: 成功時は 0、エラー時は -1

Errors:

  =====      =============================================================
  E2BIG      状態の合計サイズが、ユーザが指定した 'size' の値を超えている。
             必要なサイズが size に書き込まれる。
  =====      =============================================================

::

  struct kvm_nested_state {
	__u16 flags;
	__u16 format;
	__u32 size;

	union {
		struct kvm_vmx_nested_state_hdr vmx;
		struct kvm_svm_nested_state_hdr svm;

		/* Pad the header to 128 bytes.  */
		__u8 pad[120];
	} hdr;

	union {
		struct kvm_vmx_nested_state_data vmx[0];
		struct kvm_svm_nested_state_data svm[0];
	} data;
  };

  #define KVM_STATE_NESTED_GUEST_MODE		0x00000001
  #define KVM_STATE_NESTED_RUN_PENDING		0x00000002
  #define KVM_STATE_NESTED_EVMCS		0x00000004

  #define KVM_STATE_NESTED_FORMAT_VMX		0
  #define KVM_STATE_NESTED_FORMAT_SVM		1

  #define KVM_STATE_NESTED_VMX_VMCS_SIZE	0x1000
  #define KVM_STATE_NESTED_SVM_VMCB_SIZE	0x1000

  #define KVM_STATE_NESTED_VMX_SMM_GUEST_MODE	0x00000001
  #define KVM_STATE_NESTED_VMX_SMM_VMXON	0x00000002

  #define KVM_STATE_NESTED_GIF_SET		0x00000100

  #define KVM_STATE_VMX_PREEMPTION_TIMER_DEADLINE 0x00000001

  struct kvm_vmx_nested_state_hdr {
	__u64 vmxon_pa;
	__u64 vmcs12_pa;

	struct {
		__u16 flags;
	} smm;

	__u32 flags;
	__u64 preemption_timer_deadline;
  };

  struct kvm_svm_nested_state_hdr {
	__u64 vmcb_pa;
	__u64 gpat;
  };

  struct kvm_vmx_nested_state_data {
	__u8 vmcs12[KVM_STATE_NESTED_VMX_VMCS_SIZE];
	__u8 shadow_vmcs12[KVM_STATE_NESTED_VMX_VMCS_SIZE];
  };

  struct kvm_svm_nested_state_data {
	__u8 vmcb12[KVM_STATE_NESTED_SVM_VMCB_SIZE];
  };

この ioctl は、vCPU のネスト仮想化状態をカーネルからユーザ空間へコピーする。

状態の最大サイズは、KVM_CHECK_EXTENSION ioctl() に KVM_CAP_NESTED_STATE を渡すこ
とで取得できる。

4.115 KVM_SET_NESTED_STATE
--------------------------

:Capability: KVM_CAP_NESTED_STATE
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_nested_state (in)
:Returns: 成功時は 0、エラー時は -1

これは vCPU の kvm_nested_state 構造体をユーザ空間からカーネルへコピーする。
struct kvm_nested_state の定義は KVM_GET_NESTED_STATE を参照。

4.116 KVM_(UN)REGISTER_COALESCED_MMIO
-------------------------------------

:Capability: KVM_CAP_COALESCED_MMIO (for coalesced mmio)
	     KVM_CAP_COALESCED_PIO (for coalesced pio)
:Architectures: all
:Type: vm ioctl
:Parameters: struct kvm_coalesced_mmio_zone
:Returns: 成功時は 0、エラー時は 0 未満

coalesced I/O は、ハードウェアレジスタへの書き込みのエミュレーションを遅延させて
ユーザ空間へのエグジットを避ける、性能最適化である。ふつうは、頻繁にアクセスされ
るハードウェアレジスタのエミュレーションのオーバーヘッドを減らすために使う。

ハードウェアレジスタが coalesced I/O 用に設定されていると、書き込みアクセスはユ
ーザ空間へエグジットせず、その値はカーネルとユーザ空間で共有されるリングバッファ
に記録される。

coalesced I/O は、あるハードウェアレジスタへの 1 回以上の書き込みアクセスを、同
じデバイス上の別のハードウェアレジスタへの読み出しまたは書き込みまで遅延できる場
合に使う。この最後のアクセスが vmexit を引き起こし、ユーザ空間はそれをエミュレー
トする前にリングバッファからのアクセスを処理する。これにより、繰り返しの書き込み
でユーザ空間へエグジットするのを避けられる。

coalesced PIO は coalesced MMIO を基にしている。coalesced MMIO と PIO の違いはほ
とんどなく、coalesced PIO が I/O ポートへのアクセスを記録する点だけが異なる。

4.117 KVM_CLEAR_DIRTY_LOG
-------------------------

:Capability: KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2
:Architectures: x86, arm64, mips
:Type: vm ioctl
:Parameters: struct kvm_clear_dirty_log (in)
:Returns: 成功時は 0、エラー時は -1

::

  /* for KVM_CLEAR_DIRTY_LOG */
  struct kvm_clear_dirty_log {
	__u32 slot;
	__u32 num_pages;
	__u64 first_page;
	union {
		void __user *dirty_bitmap; /* one bit per page */
		__u64 padding;
	};
  };

この ioctl は、struct kvm_clear_dirty_log の dirty_bitmap フィールドで渡されたビ
ットマップに従って、メモリスロット内のページのダーティ状態をクリアする。ビットマ
ップのビット 0 はメモリスロット内のページ "first_page" に対応し、num_pages は入
力ビットマップのビット単位のサイズである。first_page は 64 の倍数でなければなら
ない。num_pages も 64 の倍数でなければならないが、first_page + num_pages がメモ
リスロットのサイズになる場合は例外である。入力ビットマップでセットされている各ビ
ットについて、対応するページが KVM のダーティビットマップで「クリーン」とマーク
され、そのページでダーティトラッキングが再度有効になる (たとえば書き込み保護によ
って、またはページテーブルエントリのダーティビットをクリアすることによって)。

KVM_CAP_MULTI_ADDRESS_SPACE が利用できる場合、slot フィールドのビット 16〜31 が、
ダーティ状態をクリアしたいアドレス空間を指定する。slot フィールドの使い方の詳細
は KVM_SET_USER_MEMORY_REGION を参照。

この ioctl は主に、KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2 が有効なときに役立つ。詳し
くはこのケイパビリティの説明を参照。ただし、KVM_CHECK_EXTENSION が
KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2 の存在を確認できる限り、常に使える。

4.118 KVM_GET_SUPPORTED_HV_CPUID
--------------------------------

:Capability: KVM_CAP_HYPERV_CPUID (vcpu), KVM_CAP_SYS_HYPERV_CPUID (system)
:Architectures: x86
:Type: system ioctl, vcpu ioctl
:Parameters: struct kvm_cpuid2 (in/out)
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_cpuid2 {
	__u32 nent;
	__u32 padding;
	struct kvm_cpuid_entry2 entries[0];
  };

  struct kvm_cpuid_entry2 {
	__u32 function;
	__u32 index;
	__u32 flags;
	__u32 eax;
	__u32 ebx;
	__u32 ecx;
	__u32 edx;
	__u32 padding[3];
  };

この ioctl は、KVM における Hyper-V エミュレーションに関連する x86 の CPUID 機能
リーフを返す。ユーザ空間は、この ioctl が返す情報を使って、Hyper-V の
enlightenment を利用するゲスト (たとえば Windows や Hyper-V のゲスト) に提示する
CPUID 情報を組み立てられる。

この ioctl が返す CPUID 機能リーフは、Hyper-V Top Level Functional Specification
(TLFS) で定義されている。これらのリーフは KVM_GET_SUPPORTED_CPUID ioctl では取得
できない。一部が KVM の機能リーフ (0x40000000, 0x40000001) と重なるためである。

現在、以下の CPUID リーフのリストが返される:

 - HYPERV_CPUID_VENDOR_AND_MAX_FUNCTIONS
 - HYPERV_CPUID_INTERFACE
 - HYPERV_CPUID_VERSION
 - HYPERV_CPUID_FEATURES
 - HYPERV_CPUID_ENLIGHTMENT_INFO
 - HYPERV_CPUID_IMPLEMENT_LIMITS
 - HYPERV_CPUID_NESTED_FEATURES
 - HYPERV_CPUID_SYNDBG_VENDOR_AND_MAX_FUNCTIONS
 - HYPERV_CPUID_SYNDBG_INTERFACE
 - HYPERV_CPUID_SYNDBG_PLATFORM_CAPABILITIES

ユーザ空間は、可変サイズの配列 'entries' のエントリ数を 'nent' フィールドで示し
た kvm_cpuid2 構造体を渡して KVM_GET_SUPPORTED_HV_CPUID を呼び出す。エントリ数が
すべての Hyper-V 機能リーフを記述するには少なすぎる場合、エラー (E2BIG) が返され
る。エントリ数が Hyper-V 機能リーフの数以上であれば、'nent' フィールドは
'entries' 配列内の有効なエントリ数に調整され、その後配列が埋められる。

'struct kvm_cpuid_entry2' の 'index' フィールドと 'flags' フィールドは現在予約済
みであり、ユーザ空間はそこに特定の値を期待すべきではない。

備考: KVM_GET_SUPPORTED_HV_CPUID の vCPU 版は現在非推奨である。サポートするすべ
ての機能ビットを無条件に公開するシステム ioctl と違い、vCPU 版には次の癖がある:

- HYPERV_CPUID_NESTED_FEATURES リーフと HV_X64_ENLIGHTENED_VMCS_RECOMMENDED 機能
  ビットは、対応する vCPU で以前に Enlightened VMCS が有効にされていた場合
  (KVM_CAP_HYPERV_ENLIGHTENED_VMCS) にのみ公開される。
- HV_STIMER_DIRECT_MODE_AVAILABLE ビットは、カーネル内 LAPIC の場合にのみ公開さ
  れる (KVM_CREATE_IRQCHIP がすでに呼ばれていることを前提とする)。

4.119 KVM_ARM_VCPU_FINALIZE
---------------------------

:Architectures: arm64
:Type: vcpu ioctl
:Parameters: int feature (in)
:Returns: 成功時は 0、エラー時は -1

Errors:

  ======     ==============================================================
  EPERM      機能が有効でない、設定が必要、またはすでに確定済み
  EINVAL     機能が未知、または存在しない
  ======     ==============================================================

feature に指定できる値:

  =====      ===========================================
  arm64      KVM_ARM_VCPU_SVE (KVM_CAP_ARM_SVE が必要)
  =====      ===========================================

指定した vCPU 機能の設定を確定する。

対象の機能を有効にして vCPU がすでに初期化されている必要がある。これは、
features[] に適切なフラグをセットして
:ref:`KVM_ARM_VCPU_INIT <KVM_ARM_VCPU_INIT>` 呼び出しを成功させることで行う。

影響を受ける vCPU 機能では、vCPU が完全に使えるようになる前に必ず実行しなければ
ならない手順である。

KVM_ARM_VCPU_INIT と KVM_ARM_VCPU_FINALIZE の間では、KVM_SET_ONE_REG などの
ioctl を使って機能を設定できる。実行すべき正確な設定とその方法は機能によって異な
る。

KVM_RUN、KVM_GET_REG_LIST、KVM_GET_ONE_REG、KVM_SET_ONE_REG など、特定の機能が確
定していることに依存する他の呼び出しは、KVM_ARM_VCPU_FINALIZE 呼び出しによって機
能がすでに確定していない限り、-EPERM で失敗する。

この ioctl を使って確定する必要がある vCPU 機能の詳細は KVM_ARM_VCPU_INIT を参照。

4.120 KVM_SET_PMU_EVENT_FILTER
------------------------------

:Capability: KVM_CAP_PMU_EVENT_FILTER
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_pmu_event_filter (in)
:Returns: 成功時は 0、エラー時は -1

Errors:

  ======     ============================================================
  EFAULT     args[0] にアクセスできない
  EINVAL     args[0] に、フィルタまたはフィルタイベントの不正なデータが含まれる
  E2BIG      nevents が大きすぎる
  EBUSY      フィルタを割り当てるのに十分なメモリがない
  ======     ============================================================

::

  struct kvm_pmu_event_filter {
	__u32 action;
	__u32 nevents;
	__u32 fixed_counter_bitmap;
	__u32 flags;
	__u32 pad[4];
	__u64 events[0];
  };

この ioctl は、許可する event select と unit mask の組み合わせを制限することで、
ゲストがプログラムできる PMU イベントの集合を制限する。

引数には、許可または拒否するフィルタイベントのリストを保持する。

フィルタイベントは汎用カウンタのみを制御する。固定カウンタは
fixed_counter_bitmap で制御する。

'flags' に指定できる値::

``0``

このモードを使うには、'flags' フィールドをクリアする。

このモードでは、各イベントが event select + unit mask を含む。

ゲストが PMU をプログラムしようとすると、ゲストの event select + unit mask がフ
ィルタイベントと比較され、ゲストにアクセスを許可すべきかが判定される。

``KVM_PMU_EVENT_FLAG_MASKED_EVENTS``
:Capability: KVM_CAP_PMU_EVENT_MASKED_EVENTS

このモードでは、各フィルタイベントが event select、mask、match、exclude の値を持
つ。マスクされたイベントをエンコードするには次を使う::

  KVM_PMU_ENCODE_MASKED_ENTRY()

エンコードされたイベントは次のレイアウトに従う::

  Bits   Description
  ----   -----------
  7:0    event select (low bits)
  15:8   umask match
  31:16  unused
  35:32  event select (high bits)
  36:54  unused
  55     exclude bit
  63:56  umask mask

ゲストが PMU をプログラムしようとすると、ゲストにアクセスを許可すべきかを判定す
るために次の手順を踏む:

 1. ゲストの event select をフィルタイベントと照合する。
 2. 一致が見つかった場合、ゲストの unit mask を、含めるフィルタイベントの
    mask と match の値と照合する。
    すなわち (unit mask & mask) == match && !exclude。
 3. 一致が見つかった場合、ゲストの unit mask を、除外するフィルタイベントの
    mask と match の値と照合する。
    すなわち (unit mask & mask) == match && exclude。
 4.
   a. 含める側で一致が見つかり、除外する側で一致が見つからなければ、
      そのイベントをフィルタする。
   b. それ以外の場合は、そのイベントをフィルタしない。
 5.
   a. イベントがフィルタされ、それが許可リストであれば、ゲストに
      そのイベントのプログラムを許可する。
   b. イベントがフィルタされ、それが拒否リストであれば、ゲストに
      そのイベントのプログラムを許可しない。

新しい PMU イベントフィルタを設定するとき、未使用のフィールドが設定されている場
合、または Intel で呼び出したときに event select の上位ビット (35:32) が設定され
ている場合、-EINVAL が返される。

'action' に指定できる値::

  #define KVM_PMU_EVENT_ALLOW 0
  #define KVM_PMU_EVENT_DENY 1

この API を通じて、KVM のユーザ空間は "action" フィールドと
"fixed_counter_bitmap" フィールドを設定することで、VM の固定カウンタ (存在する場
合) の動作も制御できる。

具体的には、ゲストの FixCtr[i] に定義済みの固定イベントをカウントさせるかどうか
を判定するとき、KVM は次の擬似コードに従う::

  FixCtr[i]_is_allowed = (action == ALLOW) && (bitmap & BIT(i)) ||
    (action == DENY) && !(bitmap & BIT(i));
  FixCtr[i]_is_denied = !FixCtr[i]_is_allowed;

KVM は常に fixed_counter_bitmap を消費する。fixed_counter_bitmap が正しく設定さ
れていることを保証するのはユーザ空間の責任である。たとえば、汎用カウンタのみに作
用するフィルタをユーザ空間が定義したい場合などである。

備考: "events" フィールドは、固定カウンタにハードコードされた event_select と
unit_mask の値にも適用される。両者が矛盾する場合、"fixed_counter_bitmap" は
"events" より優先度が高い。

4.121 KVM_PPC_SVM_OFF
---------------------

:Capability: basic
:Architectures: powerpc
:Type: vm ioctl
:Parameters: none
:Returns: 正常終了時は 0、

Errors:

  ======     ================================================================
  EINVAL     ultravisor が保護ゲストの終了に失敗した場合
  ENOMEM     ハイパーバイザがゲスト用の新しい radix ページテーブルの割り当てに失敗した場合
  ======     ================================================================

この ioctl は、ゲストのセキュアモードをオフにする、またはゲストをセキュアモード
から通常モードへ移行させるために使う。ゲストがリセットされるときに呼び出される。
通常のゲストに対して呼び出しても効果はない。

この ioctl は、保護ゲストを終了させるために ultravisor 呼び出しを発行し、VPA ペ
ージのピン留めを解除し、ハイパーバイザが保護ページを追跡するために使うすべてのデ
バイスページを解放する。

4.122 KVM_S390_NORMAL_RESET
---------------------------

:Capability: KVM_CAP_S390_VCPU_RESETS
:Architectures: s390
:Type: vcpu ioctl
:Parameters: none
:Returns: 0

この ioctl は、POP (Principles Of Operation) の cpu reset の定義に従って vCPU レ
ジスタと制御構造をリセットする。

4.123 KVM_S390_INITIAL_RESET
----------------------------

:Capability: basic
:Architectures: s390
:Type: vcpu ioctl
:Parameters: none
:Returns: 0

この ioctl は、POP の initial cpu reset の定義に従って vCPU レジスタと制御構造を
リセットする。ただし、cpu は ESA モードにはならない。このリセットは通常リセット
のスーパーセットである。

4.124 KVM_S390_CLEAR_RESET
--------------------------

:Capability: KVM_CAP_S390_VCPU_RESETS
:Architectures: s390
:Type: vcpu ioctl
:Parameters: none
:Returns: 0

この ioctl は、POP の clear cpu reset の定義に従って vCPU レジスタと制御構造をリ
セットする。ただし、cpu は ESA モードにはならない。このリセットは初期リセットの
スーパーセットである。


4.125 KVM_S390_PV_COMMAND
-------------------------

:Capability: KVM_CAP_S390_PROTECTED
:Architectures: s390
:Type: vm ioctl
:Parameters: struct kvm_pv_cmd
:Returns: 成功時は 0、エラー時は 0 未満

::

  struct kvm_pv_cmd {
	__u32 cmd;	/* Command to be executed */
	__u16 rc;	/* Ultravisor return code */
	__u16 rrc;	/* Ultravisor return reason code */
	__u64 data;	/* Data or address */
	__u32 flags;    /* flags for future extensions. Must be 0 for now */
	__u32 reserved[3];
  };

**Ultravisor の戻りコード**
Ultravisor の戻り (理由) コードは、コマンドが期待する結果を得るために Ultravisor
呼び出しが実行された場合にカーネルが提供する。したがって、これらは IOCTL の戻り
コードとは独立である。KVM が `rc` を変更する場合、その値は常に 0 より大きくなる。
そのため、`rc` の変化を検出できるように、PV コマンドを発行する前に `rc` を 0 に
設定しておくことを勧める。

**cmd の値:**

KVM_PV_ENABLE
  メモリを割り当て、Ultravisor に VM を登録する。これにより、Ultravisor にメモリを
  提供し、そのメモリは KVM からアクセスできなくなる。既存のすべての CPU は保護 CPU
  に変換される。このコマンドが成功した後にホットプラグで追加された CPU も、その作
  成中に保護される。

  Errors:

  =====      =============================
  EINTR      マスクされていないシグナルが保留中である
  =====      =============================

KVM_PV_DISABLE
  Ultravisor から VM の登録を解除し、Ultravisor に提供していたメモリを回収して、カ
  ーネルが再び使えるようにする。登録済みのすべての vCPU は非保護のものに戻される。
  以前の保護 VM が KVM_PV_ASYNC_CLEANUP_PREPARE で非同期の破棄の準備をされ、その後
  KVM_PV_ASYNC_CLEANUP_PERFORM で破棄されていない場合、その VM はこの呼び出しで現
  在の保護 VM とともに破棄される。

KVM_PV_VM_SET_SEC_PARMS
  イメージの展開と検証の準備として、VM メモリから Ultravisor へイメージヘッダを渡
  す。

KVM_PV_VM_UNPACK
  暗号化されたブートイメージの 1 ページを展開する (保護し、復号する)。

KVM_PV_VM_VERIFY
  展開されたイメージの完全性を検証する。これが成功した場合にのみ、KVM は保護 vCPU
  を起動できる。

KVM_PV_INFO
  :Capability: KVM_CAP_S390_PROTECTED_DUMP

  Ultravisor 関連のデータをサブコマンド経由でユーザ空間に提供する API を提示する。
  len_max はユーザ空間バッファのサイズ、len_written はそのバッファのうち実際に書き
  込まれたバイト数を KVM が示したものである。将来さらに応答フィールドが追加された
  場合、len_written を使って有効なフィールドを判定できる。

  ::

     enum pv_cmd_info_id {
	KVM_PV_INFO_VM,
	KVM_PV_INFO_DUMP,
     };

     struct kvm_s390_pv_info_header {
	__u32 id;
	__u32 len_max;
	__u32 len_written;
	__u32 reserved;
     };

     struct kvm_s390_pv_info {
	struct kvm_s390_pv_info_header header;
	struct kvm_s390_pv_info_dump dump;
	struct kvm_s390_pv_info_vm vm;
     };

**サブコマンド:**

  KVM_PV_INFO_VM
    このサブコマンドは、PV ホスト向けの基本的な Ultravisor 情報を提供する。これらの
    値は sysfs の firmware UV クエリインタフェースでファイルとしても公開されている可
    能性が高いが、この API のほうがプログラムから簡単に取得できる。

    installed calls および feature_indication メンバは、インストール済みの UV 呼び出
    しと、UV のその他の機能表示を提供する。

    max_* メンバは、PV vCPU の最大数、PV ゲストの最大数、PV ゲストメモリの最大サイズ
    に関する情報を提供する。

    ::

      struct kvm_s390_pv_info_vm {
	__u64 inst_calls_list[4];
	__u64 max_cpus;
	__u64 max_guests;
	__u64 max_guest_addr;
	__u64 feature_indication;
      };


  KVM_PV_INFO_DUMP
    このサブコマンドは、PV ゲストのダンプに関する情報を提供する。

    ::

      struct kvm_s390_pv_info_dump {
	__u64 dump_cpu_buffer_len;
	__u64 dump_config_mem_buffer_per_1m;
	__u64 dump_config_finalize_len;
      };

KVM_PV_DUMP
  :Capability: KVM_CAP_S390_PROTECTED_DUMP

  保護 VM のダンプを容易にする呼び出しを提供する API を提示する。

  ::

    struct kvm_s390_pv_dmp {
      __u64 subcmd;
      __u64 buff_addr;
      __u64 buff_len;
      __u64 gaddr;		/* For dump storage state */
    };

  **サブコマンド:**

  KVM_PV_DUMP_INIT
    保護 VM のダンプ処理を初期化する。この呼び出しが成功しない場合、他のすべてのサブ
    コマンドは -EINVAL で失敗する。ダンプ処理がまだ完了していない場合、このサブコマ
    ンドは -EINVAL を返す。

    すべての PV VM をダンプできるわけではない。ダンプを許可するには、オーナーが SE
    ヘッダの `dump
    allowed` PCF ビット 34 を設定する必要がある。

  KVM_PV_DUMP_CONFIG_STOR_STATE
    絶対ゲストアドレス (`gaddr`) で指定された 1MB ブロックから始まる、`buff_len` バ
    イトの tweak 成分値を格納する。`buff_len` は `conf_dump_storage_state_len` に整
    列されている必要があり、かつダンプ用 uv_info データが提供する
    `conf_dump_storage_state_len` の値以上でなければならない。エラーの rc が返された
    場合でも buff_user に書き込まれることがある。たとえば、最初のページのデータを書
    き込んだ後にフォールトが発生した場合である。

  KVM_PV_DUMP_COMPLETE
    このサブコマンドが成功すると、ダンプ処理が完了し、KVM_PV_DUMP_INIT を再び呼び出
    せるようになる。

    成功時には、`conf_dump_finalize_len` バイトの完了データが `buff_addr` に格納され
    る。完了データには、鍵導出のシード、IV、tweak nonce、暗号鍵、および認証タグが含
    まれ、これらはすべて後でダンプを復号するために必要である。

KVM_PV_ASYNC_CLEANUP_PREPARE
  :Capability: KVM_CAP_S390_PROTECTED_ASYNC_DISABLE

  現在の保護 VM を非同期の破棄に備えさせる。現在の保護 VM が使うほとんどのリソース
  は、後続の非同期の破棄のために取り分けられる。現在の保護 VM はその後、非保護とし
  て直ちに実行を再開する。非同期の破棄に備えられた保護 VM は、同時に最大 1 つまで
  しか存在できない。保護 VM が破棄に備えられたまま、その後
  KVM_PV_ASYNC_CLEANUP_PERFORM を呼び出していない場合、この呼び出しは失敗する。そ
  の場合、ユーザ空間のプロセスは通常の KVM_PV_DISABLE を発行すべきである。この呼び
  出しで取り分けられたリソースは、後続の KVM_PV_ASYNC_CLEANUP_PERFORM または
  KVM_PV_DISABLE の呼び出しでクリーンアップする必要がある。そうしない場合は、KVM
  の終了時にクリーンアップされる。KVM_PV_ASYNC_CLEANUP_PREPARE は、クリーンアップ
  が始まり次第、つまり KVM_PV_ASYNC_CLEANUP_PERFORM が完了する前にも、再び呼び出せ
  る。

KVM_PV_ASYNC_CLEANUP_PERFORM
  :Capability: KVM_CAP_S390_PROTECTED_ASYNC_DISABLE

  KVM_PV_ASYNC_CLEANUP_PREPARE で破棄に備えられた保護 VM を破棄する。取り分けられ
  ていたリソースは、このコマンドの実行中に解放される。この PV コマンドは、理想的に
  はユーザ空間が別のスレッドから発行する。致命的なシグナルを受信した場合 (またはプ
  ロセスが自然に終了した場合)、コマンドは完了せずに直ちに終了し、通常の KVM シャッ
  トダウン手順が残りのすべての保護 VM のクリーンアップを行う。これには、プロセスの
  終了によって破棄が中断されたものも含まれる。

4.126 KVM_XEN_HVM_SET_ATTR
--------------------------

:Capability: KVM_CAP_XEN_HVM / KVM_XEN_HVM_CONFIG_SHARED_INFO
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_xen_hvm_attr
:Returns: 成功時は 0、エラー時は 0 未満

::

  struct kvm_xen_hvm_attr {
	__u16 type;
	__u16 pad[3];
	union {
		__u8 long_mode;
		__u8 vector;
		__u8 runstate_update_flag;
		union {
			__u64 gfn;
			__u64 hva;
		} shared_info;
		struct {
			__u32 send_port;
			__u32 type; /* EVTCHNSTAT_ipi / EVTCHNSTAT_interdomain */
			__u32 flags;
			union {
				struct {
					__u32 port;
					__u32 vcpu;
					__u32 priority;
				} port;
				struct {
					__u32 port; /* Zero for eventfd */
					__s32 fd;
				} eventfd;
				__u32 padding[4];
			} deliver;
		} evtchn;
		__u32 xen_version;
		__u64 pad[8];
	} u;
  };

type の値:

KVM_XEN_ATTR_TYPE_LONG_MODE
  VM の ABI モードを 32 ビットまたは 64 ビット (ロングモード) に設定する。これによ
  り、VM に公開される shared_info ページのレイアウトが決まる。

KVM_XEN_ATTR_TYPE_SHARED_INFO
  Xen の shared_info ページが存在するゲスト物理フレーム番号を設定する。Xen は最初
  の 32 個の vCPU の vcpu_info を shared_info ページに置くが、KVM はこれを自動では
  行わない。代わりに、ある vCPU の vcpu_info が shared_info ページの「デフォルト」
  の位置にある場合でも、KVM_XEN_VCPU_ATTR_TYPE_VCPU_INFO または
  KVM_XEN_VCPU_ATTR_TYPE_VCPU_INFO_HVA を明示的に使う必要がある。これは、KVM が
  vcpu_info[] 配列の添字として使われる Xen の CPU ID を把握していないことがあり、
  正しいデフォルト位置を知らない可能性があるためである。

  shared_info ページは KVM によって絶えず書き込まれる可能性がある。このページには、
  とりわけ Xen ゲストへ割り込みを配送するために使うイベントチャネルビットマップが
  含まれる。このページはダーティトラッキングの仕組みから除外されている。つまり、
  KVM はイベントチャネル割り込みをゲストへ配送するたびに、明示的にページをダーティ
  にするわけではない。したがって、いずれかの vCPU が実行されていたか、ゲストへ配送
  できるイベントチャネル割り込みが存在する場合、ユーザ空間は指定された GFN がダー
  ティであると常にみなすべきである。

  gfn を KVM_XEN_INVALID_GFN に設定すると、shared_info ページが無効になる。

KVM_XEN_ATTR_TYPE_SHARED_INFO_HVA
  Xen のケイパビリティで KVM_XEN_HVM_CONFIG_SHARED_INFO_HVA フラグも設定されている
  場合、この属性を使って、shared_info ページが存在するユーザ空間アドレスを設定でき
  る。このアドレスは、ゲスト物理アドレス空間のどこにマップされるかにかかわらず、
  VMM では常に固定である。この属性は KVM_XEN_ATTR_TYPE_SHARED_INFO より優先して使
  うべきである。ページがゲスト物理アドレス空間で再マップされるときに、内部キャッシ
  ュが不要に無効化されるのを避けられるためである。

  hva を 0 に設定すると、shared_info ページが無効になる。

KVM_XEN_ATTR_TYPE_UPCALL_VECTOR
  Xen のイベントチャネルの upcall を配送するために使う例外ベクタを設定する。これは
  ハイパーバイザが直接注入する HVM 全体のベクタであり (ローカル APIC 経由ではない)、
  ふつうはゲストが HVM_PARAM_CALLBACK_IRQ で設定する。これを 0 に設定すると再び無
  効にできる (たとえばゲストの SHUTDOWN_soft_reset 用)。

KVM_XEN_ATTR_TYPE_EVTCHN
  この属性は、KVM_CAP_XEN_HVM ioctl が KVM_XEN_HVM_CONFIG_EVTCHN_SEND 機能のサポー
  トを示す場合に利用できる。ゲストからの EVTCHNOP_send 要求を横取りするための送信
  ポート番号を設定する。ある送信ポート番号は、ゲスト上の指定した vCPU (APIC ID に
  よる) / ポート / 優先度へ戻すか、eventfd でイベントをトリガするようにできる。
  vCPU と優先度は、後続の呼び出しで KVM_XEN_EVTCHN_UPDATE を設定することで変更でき
  るが、ある送信ポートでは他のフィールドは変更できない。ポートのマッピングは、
  flags フィールドに KVM_XEN_EVTCHN_DEASSIGN を使うと削除される。flags フィールド
  に KVM_XEN_EVTCHN_RESET を渡すと、送信側イベントチャネルの横取りがすべて削除され
  る。flags フィールドの値は互いに排他的で、ビットマスクとして組み合わせることはで
  きない。

KVM_XEN_ATTR_TYPE_XEN_VERSION
  この属性は、KVM_CAP_XEN_HVM ioctl が KVM_XEN_HVM_CONFIG_EVTCHN_SEND 機能のサポー
  トを示す場合に利用できる。ゲストが XENVER_version 呼び出しを呼び出したときに返す
  32 ビットのバージョンコードを設定する。ふつうは (XEN_MAJOR << 16 | XEN_MINOR) で
  ある。PV Xen ゲストは、イベントチャネルの配送をトリガするためのダミーのハイパー
  コールとしてこれを使うことが多い。そのため、ユーザ空間へエグジットせずにカーネル
  内で応答するのが有益である。

KVM_XEN_ATTR_TYPE_RUNSTATE_UPDATE_FLAG
  この属性は、KVM_CAP_XEN_HVM ioctl が KVM_XEN_HVM_CONFIG_RUNSTATE_UPDATE_FLAG の
  サポートを示す場合に利用できる。ゲストの vCPU が他の vCPU の vcpu_runstate_info
  を安全に読めるようにする XEN_RUNSTATE_UPDATE フラグを有効にする。Xen ゲストは、
  HYPERVISOR_vm_assist ハイパーコールの VMASST_TYPE_runstate_update_flag によって
  この機能を有効にする。

4.127 KVM_XEN_HVM_GET_ATTR
--------------------------

:Capability: KVM_CAP_XEN_HVM / KVM_XEN_HVM_CONFIG_SHARED_INFO
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_xen_hvm_attr
:Returns: 成功時は 0、エラー時は 0 未満

Xen VM の属性を読み取れるようにする。構造体と型については上記の
KVM_XEN_HVM_SET_ATTR を参照。KVM_XEN_ATTR_TYPE_EVTCHN 属性は読み取れない。

4.128 KVM_XEN_VCPU_SET_ATTR
---------------------------

:Capability: KVM_CAP_XEN_HVM / KVM_XEN_HVM_CONFIG_SHARED_INFO
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_xen_vcpu_attr
:Returns: 成功時は 0、エラー時は 0 未満

::

  struct kvm_xen_vcpu_attr {
	__u16 type;
	__u16 pad[3];
	union {
		__u64 gpa;
		__u64 pad[4];
		struct {
			__u64 state;
			__u64 state_entry_time;
			__u64 time_running;
			__u64 time_runnable;
			__u64 time_blocked;
			__u64 time_offline;
		} runstate;
		__u32 vcpu_id;
		struct {
			__u32 port;
			__u32 priority;
			__u64 expires_ns;
		} timer;
		__u8 vector;
	} u;
  };

type の値:

KVM_XEN_VCPU_ATTR_TYPE_VCPU_INFO
  ある vCPU の vcpu_info のゲスト物理アドレスを設定する。VM の shared_info ページ
  と同様に、イベントチャネル割り込みの配送が有効な場合、対応するページはいつでもダ
  ーティになりうる。そのためユーザ空間は、ダーティログに頼らず、常にそのページがダ
  ーティであるとみなすべきである。gpa を KVM_XEN_INVALID_GPA に設定すると
  vcpu_info が無効になる。

KVM_XEN_VCPU_ATTR_TYPE_VCPU_INFO_HVA
  Xen のケイパビリティで KVM_XEN_HVM_CONFIG_SHARED_INFO_HVA フラグも設定されている
  場合、この属性を使って、ある vCPU の vcpu_info のユーザ空間アドレスを設定できる。
  これは、vcpu_info が shared_info ページの「デフォルト」の位置にある場合にのみ使
  うべきである。この場合、ユーザ空間アドレスは変化しないとみなしてよい。
  shared_info ページはゲストメモリ上のオーバレイであり、ゲスト物理アドレス空間のど
  こにマップされるかにかかわらずホストアドレスは固定だからである。したがって、ゲス
  トメモリのレイアウトが変更されても、内部キャッシュを不要に無効化せずに済む。
  vcpu_info が「デフォルト」の位置にない場合、同じホストアドレスにとどまることは保
  証されないため、前述のキャッシュの無効化が必要になる。

KVM_XEN_VCPU_ATTR_TYPE_VCPU_TIME_INFO
  ある vCPU 用の追加の pvclock 構造体のゲスト物理アドレスを設定する。ふつうはゲス
  トの vsyscall サポートに使う。gpa を KVM_XEN_INVALID_GPA に設定するとこの構造体
  が無効になる。

KVM_XEN_VCPU_ATTR_TYPE_RUNSTATE_ADDR
  ある vCPU の vcpu_runstate_info のゲスト物理アドレスを設定する。これは Xen ゲス
  トが steal time などの CPU 状態を追跡する方法である。gpa を KVM_XEN_INVALID_GPA
  に設定すると runstate 領域が無効になる。

KVM_XEN_VCPU_ATTR_TYPE_RUNSTATE_CURRENT
  構造体の .u.runstate.state メンバから、指定した vCPU の runstate
  (RUNSTATE_running/_runnable/_blocked/_offline) を設定する。KVM は running と
  runnable の時間を自動で計上するが、blocked と offline の状態は明示的にしか入らな
  い。

KVM_XEN_VCPU_ATTR_TYPE_RUNSTATE_DATA
  構造体の .u.runstate メンバから、現在の runstate を含む vCPU の runstate データ
  のすべてのフィールドを設定する。state_entry_time は他の 4 つの時間の合計と等しく
  なければならない。

KVM_XEN_VCPU_ATTR_TYPE_RUNSTATE_ADJUST
  構造体の .u.runstate メンバの内容を、指定した vCPU の runstate データの対応する
  メンバに*加算する*。これにより、runstate の時間をアトミックに調整できる。
  state_entry_time への調整分は、他の 4 つの時間への調整分の合計と等しくなければな
  らない。state フィールドは -1 か、有効な runstate の値 (RUNSTATE_running、
  RUNSTATE_runnable、RUNSTATE_blocked、RUNSTATE_offline) のいずれかに設定し、調整
  後の state_entry_time 時点での現在の計上状態を設定する。

KVM_XEN_VCPU_ATTR_TYPE_VCPU_ID
  この属性は、KVM_CAP_XEN_HVM ioctl が KVM_XEN_HVM_CONFIG_EVTCHN_SEND 機能のサポー
  トを示す場合に利用できる。指定した vCPU の Xen vCPU ID を設定し、タイマ関連の
  vCPU 操作を KVM が横取りできるようにする。

KVM_XEN_VCPU_ATTR_TYPE_TIMER
  この属性は、KVM_CAP_XEN_HVM ioctl が KVM_XEN_HVM_CONFIG_EVTCHN_SEND 機能のサポー
  トを示す場合に利用できる。vCPU の VIRQ_TIMER に対するイベントチャネルのポートと
  優先度を設定し、保留中のタイマを保存/復元できるようにする。タイマポートを 0 に設
  定すると、シングルショットタイマのカーネルによる処理が無効になる。

KVM_XEN_VCPU_ATTR_TYPE_UPCALL_VECTOR
  この属性は、KVM_CAP_XEN_HVM ioctl が KVM_XEN_HVM_CONFIG_EVTCHN_SEND 機能のサポー
  トを示す場合に利用できる。vCPU ごとのローカル APIC の upcall ベクタを設定する。
  これは Xen ゲストが HVMOP_set_evtchn_upcall_vector ハイパーコールで設定する。ふ
  つうは Windows ゲストが使い、HVM_PARAM_CALLBACK_IRQ で設定する HVM 全体の upcall
  ベクタとは別のものである。ベクタを 0 に設定すると無効になる。

4.129 KVM_XEN_VCPU_GET_ATTR
---------------------------

:Capability: KVM_CAP_XEN_HVM / KVM_XEN_HVM_CONFIG_SHARED_INFO
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_xen_vcpu_attr
:Returns: 成功時は 0、エラー時は 0 未満

Xen vCPU の属性を読み取れるようにする。構造体と型については上記の
KVM_XEN_VCPU_SET_ATTR を参照。

KVM_XEN_VCPU_ATTR_TYPE_RUNSTATE_ADJUST 型は KVM_XEN_VCPU_GET_ATTR ioctl では使え
ない。

4.130 KVM_ARM_MTE_COPY_TAGS
---------------------------

:Capability: KVM_CAP_ARM_MTE
:Architectures: arm64
:Type: vm ioctl
:Parameters: struct kvm_arm_copy_mte_tags
:Returns: コピーしたバイト数。エラー時は 0 未満
          （引数が不正な場合は -EINVAL、メモリにアクセスできない場合は -EFAULT）。

::

  struct kvm_arm_copy_mte_tags {
	__u64 guest_ipa;
	__u64 length;
	void __user *addr;
	__u64 flags;
	__u64 reserved[2];
  };

Memory Tagging Extension (MTE) のタグを、ゲストのタグメモリとの間でコピーする。
``guest_ipa`` フィールドと ``length`` フィールドは ``PAGE_SIZE`` に整列していなければ
ならない。``length`` は 2^31 - PAGE_SIZE バイトより大きくてはならない。``addr``
フィールドは、タグのコピー先またはコピー元となるバッファを指さなければならない。

``flags`` はコピーの向きを指定する。値は ``KVM_ARM_TAGS_TO_GUEST`` か
``KVM_ARM_TAGS_FROM_GUEST`` のいずれかである。

タグを格納するバッファのサイズは ``(length / 16)`` バイトである（MTE のグラニュールは
16 バイト長である）。各バイトにはタグ値が1つ入る。これは ``PTRACE_PEEKMTETAGS`` と
``PTRACE_POKEMTETAGS`` の形式と一致する。

データを1バイトもコピーする前にエラーが起きた場合は、負のエラーコードが返る。エラーが
起きる前に一部のタグをコピーしていた場合は、コピーに成功したバイト数が返る。呼び出しが
正常に完了した場合は ``length`` が返る。

4.131 KVM_GET_SREGS2
--------------------

:Capability: KVM_CAP_SREGS2
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_sregs2 (out)
:Returns: 成功時は 0、エラー時は -1

vCPU から特殊レジスタを読み出す。
この ioctl は（対応していれば）KVM_GET_SREGS を置き換える。

::

        struct kvm_sregs2 {
                /* out (KVM_GET_SREGS2) / in (KVM_SET_SREGS2) */
                struct kvm_segment cs, ds, es, fs, gs, ss;
                struct kvm_segment tr, ldt;
                struct kvm_dtable gdt, idt;
                __u64 cr0, cr2, cr3, cr4, cr8;
                __u64 efer;
                __u64 apic_base;
                __u64 flags;
                __u64 pdptrs[4];
        };

``kvm_sregs2`` の flags の値:

``KVM_SREGS2_FLAGS_PDPTRS_VALID``

  この構造体が有効な PDPTR 値を含むことを示す。


4.132 KVM_SET_SREGS2
--------------------

:Capability: KVM_CAP_SREGS2
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_sregs2 (in)
:Returns: 成功時は 0、エラー時は -1

vCPU に特殊レジスタを書き込む。
データ構造については KVM_GET_SREGS2 を参照。
この ioctl は（対応していれば）KVM_SET_SREGS を置き換える。

4.133 KVM_GET_STATS_FD
----------------------

:Capability: KVM_CAP_STATS_BINARY_FD
:Architectures: all
:Type: vm ioctl, vcpu ioctl
:Parameters: なし
:Returns: 成功時は統計のファイルディスクリプタ、エラー時は 0 未満

Errors:

  ======     ======================================================
  ENOMEM     メモリ不足のため fd を作成できなかった場合
  EMFILE     オープンしているファイル数が上限を超えた場合
  ======     ======================================================

返されるファイルディスクリプタを使うと、VM/vCPU の統計データをバイナリ形式で
読み出せる。ファイルディスクリプタ内のデータは、次のように並んだ4つのブロックから
なる。

+-------------+
|   Header    |
+-------------+
|  id string  |
+-------------+
| Descriptors |
+-------------+
| Stats Data  |
+-------------+

オフセット 0 から始まるヘッダを除き、4つのブロックが隣接していることや上記の順序で
あることは保証されない点に注意すること。id、descriptors、data ブロックのオフセットは
ヘッダに入っている。ただし、4つのブロックはすべてファイル内で 64 ビットのオフセットに
整列しており、重なり合うことはない。

data ブロック以外のすべてのブロックは不変である。ユーザ空間はファイルディスクリプタを
取得した後に一度だけこれらを読むことができ、その後は ``pread`` や ``lseek`` を使って
統計を繰り返し読める。

データはすべてシステムのエンディアンである。

ヘッダの形式は次のとおり::

	struct kvm_stats_header {
		__u32 flags;
		__u32 name_size;
		__u32 num_desc;
		__u32 id_offset;
		__u32 desc_offset;
		__u32 data_offset;
	};

``flags`` フィールドは現在使われていない。常に 0 として読まれる。

``name_size`` フィールドは統計名の文字列のサイズ（バイト単位）である。この文字列には
末尾の '\0' も含み、"id string" ブロックに入っていて、各ディスクリプタの末尾にも
付加される。

``num_desc`` フィールドはディスクリプタブロックに含まれるディスクリプタの数である。
（ディスクリプタは複数の値からなることがあるため、data ブロックの実際の値の数は
もっと多い場合がある）。

``id_offset`` フィールドは、id 文字列の、ファイルディスクリプタが指すファイルの先頭
からのオフセットである。8 の倍数である。

``desc_offset`` フィールドは、Descriptors ブロックの、ファイルディスクリプタが指す
ファイルの先頭からのオフセットである。8 の倍数である。

``data_offset`` フィールドは、Stats Data ブロックの、ファイルディスクリプタが指す
ファイルの先頭からのオフセットである。8 の倍数である。

id 文字列ブロックには、KVM_GET_STATS_FD を呼び出したファイルディスクリプタを識別する
文字列が入る。このブロックのサイズは、末尾の ``'\0'`` を含めて、ヘッダの ``name_size``
フィールドで示される。

ディスクリプタブロックは、ファイルディスクリプタの存続期間中に一度だけ読めばよい。
``struct kvm_stats_desc`` の並びからなり、それぞれの後ろに ``name_size`` のサイズの
文字列が続く。
::

	#define KVM_STATS_TYPE_SHIFT		0
	#define KVM_STATS_TYPE_MASK		(0xF << KVM_STATS_TYPE_SHIFT)
	#define KVM_STATS_TYPE_CUMULATIVE	(0x0 << KVM_STATS_TYPE_SHIFT)
	#define KVM_STATS_TYPE_INSTANT		(0x1 << KVM_STATS_TYPE_SHIFT)
	#define KVM_STATS_TYPE_PEAK		(0x2 << KVM_STATS_TYPE_SHIFT)
	#define KVM_STATS_TYPE_LINEAR_HIST	(0x3 << KVM_STATS_TYPE_SHIFT)
	#define KVM_STATS_TYPE_LOG_HIST		(0x4 << KVM_STATS_TYPE_SHIFT)
	#define KVM_STATS_TYPE_MAX		KVM_STATS_TYPE_LOG_HIST

	#define KVM_STATS_UNIT_SHIFT		4
	#define KVM_STATS_UNIT_MASK		(0xF << KVM_STATS_UNIT_SHIFT)
	#define KVM_STATS_UNIT_NONE		(0x0 << KVM_STATS_UNIT_SHIFT)
	#define KVM_STATS_UNIT_BYTES		(0x1 << KVM_STATS_UNIT_SHIFT)
	#define KVM_STATS_UNIT_SECONDS		(0x2 << KVM_STATS_UNIT_SHIFT)
	#define KVM_STATS_UNIT_CYCLES		(0x3 << KVM_STATS_UNIT_SHIFT)
	#define KVM_STATS_UNIT_BOOLEAN		(0x4 << KVM_STATS_UNIT_SHIFT)
	#define KVM_STATS_UNIT_MAX		KVM_STATS_UNIT_BOOLEAN

	#define KVM_STATS_BASE_SHIFT		8
	#define KVM_STATS_BASE_MASK		(0xF << KVM_STATS_BASE_SHIFT)
	#define KVM_STATS_BASE_POW10		(0x0 << KVM_STATS_BASE_SHIFT)
	#define KVM_STATS_BASE_POW2		(0x1 << KVM_STATS_BASE_SHIFT)
	#define KVM_STATS_BASE_MAX		KVM_STATS_BASE_POW2

	struct kvm_stats_desc {
		__u32 flags;
		__s16 exponent;
		__u16 size;
		__u32 offset;
		__u32 bucket_size;
		char name[];
	};

``flags`` フィールドには、このディスクリプタが表す統計データの種別と単位が入る。
エンディアンは CPU ネイティブである。
次のフラグがサポートされる:

``flags`` のビット 0-3 が種別を表す:

  * ``KVM_STATS_TYPE_CUMULATIVE``
    統計は累積カウントを報告する。データの値は増加するだけである。
    KVM で使われるカウンタのほとんどはこの種別である。
    この種別に対応する ``size`` フィールドは常に 1 である。
    累積統計のデータはすべて読み書き可能である。
  * ``KVM_STATS_TYPE_INSTANT``
    統計は瞬時値を報告する。値は増加も減少もする。この種別は通常、ダーティページ数や
    ラージページ数など、何らかのリソースの計測に使われる。
    瞬時統計はすべて読み取り専用である。
    この種別に対応する ``size`` フィールドは常に 1 である。
  * ``KVM_STATS_TYPE_PEAK``
    統計データはピーク値を報告する。たとえばハッシュテーブルのバケット内の項目数の
    最大値や、待ち時間の最大値などである。
    データの値は増加するだけである。
    この種別に対応する ``size`` フィールドは常に 1 である。
  * ``KVM_STATS_TYPE_LINEAR_HIST``
    統計は線形ヒストグラムとして報告される。バケット数は ``size`` フィールドで
    指定する。バケットの幅は ``hist_param`` フィールドで指定する。N 番目のバケット
    (1 <= N < ``size``) の範囲は [``hist_param``*(N-1), ``hist_param``*N) であり、
    最後のバケットの範囲は [``hist_param``*(``size``-1), +INF) である。
    （+INF は正の無限大を表す。）
  * ``KVM_STATS_TYPE_LOG_HIST``
    統計は対数ヒストグラムとして報告される。バケット数は ``size`` フィールドで
    指定する。最初のバケットの範囲は [0, 1) であり、最後のバケットの範囲は
    [pow(2, ``size``-2), +INF) である。それ以外の N 番目のバケット
    (1 < N < ``size``) は [pow(2, N-2), pow(2, N-1)) を覆う。

``flags`` のビット 4-7 が単位を表す:

  * ``KVM_STATS_UNIT_NONE``
    統計データの値に単位はない。通常、その値はある事象の単純なカウンタであることを
    意味する。
  * ``KVM_STATS_UNIT_BYTES``
    統計データがメモリサイズの計測に使われることを示す。単位は Byte、KiByte、
    MiByte、GiByte などである。データの単位はディスクリプタの ``exponent``
    フィールドで決まる。
  * ``KVM_STATS_UNIT_SECONDS``
    統計データが時間やレイテンシの計測に使われることを示す。
  * ``KVM_STATS_UNIT_CYCLES``
    統計データが CPU クロックサイクルの計測に使われることを示す。
  * ``KVM_STATS_UNIT_BOOLEAN``
    統計が常に 0 か 1 のいずれかであることを示す。"peak" 種別のブール統計は 1 から
    0 に戻ることはない。ブール統計は線形ヒストグラム（バケット2つ）にはできるが、
    対数ヒストグラムにはできない。

ヒストグラムの場合、単位はバケットの範囲に適用される。一方、バケットの値はその
バケットの範囲に入ったサンプル数を表す。

``flags`` のビット 8-11 が ``exponent`` とともに単位のスケールを表す:

  * ``KVM_STATS_BASE_POW10``
    スケールは 10 の累乗に基づく。時間と CPU クロックサイクルの計測に使われる。
    たとえば ``KVM_STATS_UNIT_SECONDS`` と組み合わせて exponent に -9 を使うと、
    単位がナノ秒であることを表せる。
  * ``KVM_STATS_BASE_POW2``
    スケールは 2 の累乗に基づく。メモリサイズの計測に使われる。たとえば
    ``KVM_STATS_UNIT_BYTES`` と組み合わせて exponent に 20 を使うと、単位が MiB
    であることを表せる。

``size`` フィールドはこの統計データの値の数である。単純な統計のほとんどでは 1 で
ある。1 は符号なし 64 ビットのデータを1つ含むことを意味する。

``offset`` フィールドは、Data ブロックの先頭から、対応する統計データの先頭までの
オフセットである。

``bucket_size`` フィールドはヒストグラム統計データのパラメータとして使う。線形
ヒストグラム統計データでのみ使われ、``flags`` のビット 4-11 と ``exponent`` が表す
単位でバケットの幅を指定する。

``name`` フィールドは統計データの名前の文字列である。名前の文字列は
``struct kvm_stats_desc`` の末尾から始まる。末尾の ``'\0'`` を含む最大長は、ヘッダの
``name_size`` で示される。

Stats Data ブロックには 64 ビット値の配列が入り、順序は Descriptors ブロックの
ディスクリプタと同じである。

4.134 KVM_GET_XSAVE2
--------------------

:Capability: KVM_CAP_XSAVE2
:Architectures: x86
:Type: vcpu ioctl
:Parameters: struct kvm_xsave (out)
:Returns: 成功時は 0、エラー時は -1


::

  struct kvm_xsave {
	__u32 region[1024];
	__u32 extra[0];
  };

この ioctl は現在の vCPU の xsave 構造体をユーザ空間にコピーする。コピーするバイト数
は、vm ファイルディスクリプタに対して KVM_CHECK_EXTENSION(KVM_CAP_XSAVE2) を呼び出して
返される値と同じである。KVM_CHECK_EXTENSION(KVM_CAP_XSAVE2) が返すサイズの値は常に
4096 以上である。現時点では、``arch_prctl()`` で動的機能が有効になっている場合にのみ
4096 を超えるが、将来変わるかもしれない。

struct kvm_xsave 内の状態保存領域のオフセットは、ホストの CPUID リーフ 0xD の内容に
従う。

4.135 KVM_XEN_HVM_EVTCHN_SEND
-----------------------------

:Capability: KVM_CAP_XEN_HVM / KVM_XEN_HVM_CONFIG_EVTCHN_SEND
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_irq_routing_xen_evtchn
:Returns: 成功時は 0、エラー時は 0 未満


::

   struct kvm_irq_routing_xen_evtchn {
	__u32 port;
	__u32 vcpu;
	__u32 priority;
   };

この ioctl はイベントチャネルの割り込みをゲストの vCPU に直接注入する。

4.136 KVM_S390_PV_CPU_COMMAND
-----------------------------

:Capability: KVM_CAP_S390_PROTECTED_DUMP
:Architectures: s390
:Type: vcpu ioctl
:Parameters: なし
:Returns: 成功時は 0、エラー時は 0 未満

この ioctl は `KVM_S390_PV_COMMAND` とほぼ同じだが、vCPU 向けの要求を扱う。
kvm_s390_pv_dmp 構造体を再利用するため、コマンド id も共通である。

**コマンド:**

KVM_PV_DUMP
  保護 VM の vCPU をダンプしやすくする呼び出しを提供する API を提示する。

**サブコマンド:**

KVM_PV_DUMP_CPU
  レジスタ値のような暗号化されたダンプデータを提供する。
  返されるデータの長さは uv_info.guest_cpu_stor_len で与えられる。

4.137 KVM_S390_ZPCI_OP
----------------------

:Capability: KVM_CAP_S390_ZPCI_OP
:Architectures: s390
:Type: vm ioctl
:Parameters: struct kvm_s390_zpci_op (in)
:Returns: 成功時は 0、エラー時は 0 未満

zPCI デバイスのハードウェア支援仮想化機能を管理するために使う。

パラメータは次の構造体で指定する::

  struct kvm_s390_zpci_op {
	/* in */
	__u32 fh;		/* target device */
	__u8  op;		/* operation to perform */
	__u8  pad[3];
	union {
		/* for KVM_S390_ZPCIOP_REG_AEN */
		struct {
			__u64 ibv;	/* Guest addr of interrupt bit vector */
			__u64 sb;	/* Guest addr of summary bit */
			__u32 flags;
			__u32 noi;	/* Number of interrupts */
			__u8 isc;	/* Guest interrupt subclass */
			__u8 sbo;	/* Offset of guest summary bit vector */
			__u16 pad;
		} reg_aen;
		__u64 reserved[8];
	} u;
  };

操作の種別は "op" フィールドで指定する。
KVM_S390_ZPCIOP_REG_AEN は、アダプタイベント通知の解釈に VM を登録するために使う。
これによりファームウェアがアダプタイベントを VM に直接配送できるようになり、KVM は
バックアップの配送機構を提供する。KVM_S390_ZPCIOP_DEREG_AEN は、その後でアダプタ
イベント通知の解釈を無効にするために使う。

対象の zPCI ファンクションも "fh" フィールドで指定しなければならない。
KVM_S390_ZPCIOP_REG_AEN 操作では、ファームウェア配送を確立するための追加情報を
"reg_aen" 構造体で与えなければならない。

"pad" フィールドと "reserved" フィールドは将来の拡張に使われる可能性があり、ユーザ空間は
0 を設定すべきである。

4.138 KVM_ARM_SET_COUNTER_OFFSET
--------------------------------

:Capability: KVM_CAP_COUNTER_OFFSET
:Architectures: arm64
:Type: vm ioctl
:Parameters: struct kvm_arm_counter_offset (in)
:Returns: 成功時は 0、エラー時は 0 未満

このケイパビリティは、ユーザ空間が KVM_ARM_SET_CNT_OFFSET ioctl と次のデータ構造を
使って、ゲストから見た仮想カウンタと物理カウンタの両方に VM 全体で1つのオフセットを
適用できることを示す:

::

	struct kvm_arm_counter_offset {
		__u64 counter_offset;
		__u64 reserved;
	};

オフセットは、仮想カウンタと物理カウンタの両方の値から差し引かれるカウンタサイクル数を
表す（CNTVOFF_EL2 と CNTPOFF_EL2 システムレジスタの効果に似ているが、グローバルに
限られる）。オフセットはこの VM のすべての vCPU（すでに作成済みのものも、この ioctl の
後に作成されるものも）に常に適用される。

ゲストカウンタの以前の値などに基づいてオフセットを計算するのはユーザ空間の責任である。

"reserved" フィールドに 0 以外の値を設定すると、エラー (-EINVAL) が返る場合がある。
この ioctl は、vCPU の ioctl が同時に発行されると -EBUSY を返すこともある。

この ioctl を使うと、以降にユーザ空間が SET_ONE_REG インタフェースで CNTVCT_EL0 と
CNTPCT_EL0 レジスタに書き込んでも、KVM はそれを無視する。エラーは返らないが、その
結果のオフセットは適用されない。

.. _KVM_ARM_GET_REG_WRITABLE_MASKS:

4.139 KVM_ARM_GET_REG_WRITABLE_MASKS
------------------------------------

:Capability: KVM_CAP_ARM_SUPPORTED_REG_MASK_RANGES
:Architectures: arm64
:Type: vm ioctl
:Parameters: struct reg_mask_range (in/out)
:Returns: 成功時は 0、エラー時は 0 未満


::

        #define KVM_ARM_FEATURE_ID_RANGE	0
        #define KVM_ARM_FEATURE_ID_RANGE_SIZE	(3 * 8 * 8)

        struct reg_mask_range {
                __u64 addr;             /* Pointer to mask array */
                __u32 range;            /* Requested range */
                __u32 reserved[13];
        };

この ioctl は、選択したレジスタ範囲の書き込み可能マスクをユーザ空間にコピーする。

``addr`` フィールドは、KVM が書き込み可能マスクをコピーする先の配列を指すポインタで
ある。

``range`` フィールドは要求するレジスタ範囲を指定する。
``KVM_CAP_ARM_SUPPORTED_REG_MASK_RANGES`` ケイパビリティに対する
``KVM_CHECK_EXTENSION`` は、サポートされる範囲をフラグの集合として返す。各フラグの
ビット位置が ``range`` フィールドに指定できる値を表す。それ以外の値は将来用に予約
されており、KVM はエラーを返す場合がある。

``reserved[13]`` 配列は将来用に予約されており、0 にすべきである。そうでなければ
KVM はエラーを返す場合がある。

KVM_ARM_FEATURE_ID_RANGE (0)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Feature ID 範囲は、op0==3、op1=={0, 1, 3}、CRn==0、CRm=={0-7}、op2=={0-7} の
AArch64 システムレジスタ空間として定義される。

``addr`` が指す、返されるマスク配列は、マクロ
``ARM64_FEATURE_ID_RANGE_IDX(op0, op1, crn, crm, op2)`` で添字付けされる。これにより、
ユーザ空間は ``op0, op1, crn, crm, op2`` で表されるシステムレジスタについて、どの
フィールドを変更できるかを知ることができる。システムがサポートする機能の上位集合を
表す ID レジスタ値は、KVM が拒否する。

4.140 KVM_SET_USER_MEMORY_REGION2
---------------------------------

:Capability: KVM_CAP_USER_MEMORY2
:Architectures: all
:Type: vm ioctl
:Parameters: struct kvm_userspace_memory_region2 (in)
:Returns: 成功時は 0、エラー時は -1

KVM_SET_USER_MEMORY_REGION2 は KVM_SET_USER_MEMORY_REGION の拡張で、guest_memfd の
メモリをゲストにマッピングできる。KVM_SET_USER_MEMORY_REGION と共通のフィールドは
すべて同じ意味である。ユーザ空間が flags に KVM_MEM_GUEST_MEMFD を設定すると、KVM は
メモリ領域を [guest_memfd_offset, guest_memfd_offset + memory_size] の guest_memfd
範囲に結び付ける。対象の guest_memfd は、現在の VM 上で KVM_CREATE_GUEST_MEMFD で
作成したファイルを指していなければならず、対象範囲が他のメモリ領域に結び付いていては
ならない。通常の境界チェックはすべて適用される（常識的に使うこと）。

::

  struct kvm_userspace_memory_region2 {
	__u32 slot;
	__u32 flags;
	__u64 guest_phys_addr;
	__u64 memory_size; /* bytes */
	__u64 userspace_addr; /* start of the userspace allocated memory */
	__u64 guest_memfd_offset;
	__u32 guest_memfd;
	__u32 pad1;
	__u64 pad2[14];
  };

KVM_MEM_GUEST_MEMFD の領域は、有効な guest_memfd（プライベートメモリ）と userspace_addr
（共有メモリ）を _持たなければならない_。ただし userspace_addr についての「有効」とは、
そのアドレス自体が正当なユーザ空間アドレスであればよいという意味である。userspace_addr
のバッキングマッピングは、KVM_SET_USER_MEMORY_REGION2 の時点で有効／構築済みである
必要はない。たとえば共有メモリはオンデマンドで遅延マッピング／割り当てできる。

gfn をゲストにマッピングするとき、メモリが共有かプライベートかにかかわらず、ゲストの
フォールトは常に guest_memfd から処理される。共有かプライベートかは KVM が guest_memfd
の状態に基づいて判断する。guest_memfd が共有とプライベートを決める唯一のものである。
作成時の共有／プライベート状態については :ref:`KVM_CREATE_GUEST_MEMFD` を参照。ユーザ
空間は、必要に応じて :ref:`KVM_SET_MEMORY_ATTRIBUTES2` 経由で
KVM_MEMORY_ATTRIBUTE_PRIVATE を切り替えることで、メモリを共有にするかプライベートに
するかを制御できる。

userspace_addr は、guest_memfd 内の正しいオフセットに対応する mmap() 済みアドレスで
あることが期待される。userspace_addr と guest_memfd の不一致は検証されず、ユーザの
誤りである。userspace_addr は kvm_read_guest() のようなホスト側のゲストアクセスにのみ
使われる。

インプレース変換が無効な場合、KVM は gfn の KVM_MEMORY_ATTRIBUTE_PRIVATE 状態に基づいて
共有かプライベートかを選ぶ。VM の作成時点では、すべてのメモリは共有である。つまり
すべての gfn で PRIVATE 属性は '0' である。ユーザ空間は、必要に応じて
KVM_SET_MEMORY_ATTRIBUTES 経由で KVM_MEMORY_ATTRIBUTE_PRIVATE を切り替えることで、
メモリを共有にするかプライベートにするかを制御できる。

S390:
^^^^^

VM に KVM_VM_S390_UCONTROL フラグが設定されている場合は -EINVAL を返す。
保護 VM に対して呼び出した場合は -EINVAL を返す。

.. _KVM_SET_MEMORY_ATTRIBUTES:

4.141 KVM_SET_MEMORY_ATTRIBUTES
-------------------------------

:Capability: KVM_CAP_MEMORY_ATTRIBUTES
:Architectures: x86
:Type: vm ioctl
:Parameters: struct kvm_memory_attributes (in)
:Returns: 成功時は 0、エラー時は 0 未満

KVM_SET_MEMORY_ATTRIBUTES を使うと、ユーザ空間はゲスト物理メモリの範囲にメモリ属性を
設定できる。

::

  struct kvm_memory_attributes {
	__u64 address;
	__u64 size;
	__u64 attributes;
	__u64 flags;
  };

  #define KVM_MEMORY_ATTRIBUTE_PRIVATE           (1ULL << 3)

address と size はページ境界に整列していなければならない。サポートされる属性は、
KVM_CAP_MEMORY_ATTRIBUTES に対して ioctl(KVM_CHECK_EXTENSION) を実行して取得できる。
VM に対して実行すると、KVM_CAP_MEMORY_ATTRIBUTES はその VM がサポートする属性を正確に
返す。システムスコープで実行すると、KVM_CAP_MEMORY_ATTRIBUTES は KVM がサポートする
すべての属性を返す。現時点で定義されている属性は KVM_MEMORY_ATTRIBUTE_PRIVATE のみで、
これは対応する gfn をゲストのプライベートメモリとして印付ける。

"get" API は存在しない点に注意。ユーザ空間が、必要に応じて gfn／ページの状態を明示的に
追跡する責任を負う。

"flags" フィールドは将来の拡張用に予約されており、'0' でなければならない。

関連項目: :ref:`KVM_SET_MEMORY_ATTRIBUTES2`。

.. _KVM_CREATE_GUEST_MEMFD:

4.142 KVM_CREATE_GUEST_MEMFD
----------------------------

:Capability: KVM_CAP_GUEST_MEMFD
:Architectures: none
:Type: vm ioctl
:Parameters: struct kvm_create_guest_memfd(in)
:Returns: 成功時はファイルディスクリプタ、エラー時は 0 未満

KVM_CREATE_GUEST_MEMFD は無名ファイルを作成し、それを参照するファイルディスクリプタを
返す。guest_memfd ファイルは memfd_create() で作成したファイルとほぼ同様である。
たとえば guest_memfd ファイルは RAM 上にあり、揮発性のストレージを持ち、最後の参照が
破棄されると自動的に解放される。ただし「通常の」memfd_create() ファイルと違い、
guest_memfd ファイルは所有元の仮想マシンに結び付き（後述）、ユーザ空間からマッピング、
読み出し、書き込みができず、サイズも変更できない（ただし guest_memfd ファイルは
PUNCH_HOLE をサポートする）。

::

  struct kvm_create_guest_memfd {
	__u64 size;
	__u64 flags;
	__u64 reserved[6];
  };

概念上、guest_memfd ファイルを支える inode は物理メモリを表す。つまり "struct kvm"
ではなく、モノとしての仮想マシンに結び付く。ファイル自体は "struct kvm" に結び付き、
そのインスタンスから見た下位メモリを表す。実質的にゲストアドレスからホストメモリへの
変換を提供する。これにより、複数の KVM 構造体で1つの仮想マシンを管理する用途、たとえば
仮想マシンのホスト内マイグレーションを行える。

現時点で KVM は guest_memfd のマッピングを KVM_SET_USER_MEMORY_REGION2 経由でのみ
サポートし、より具体的には "struct kvm_userspace_memory_region2" の guest_memfd と
guest_memfd_offset フィールド経由でサポートする。guest_memfd_offset は guest_memfd
インスタンス内のオフセットである。ある guest_memfd ファイルについて、1ページにつき
マッピングは1つだけである。つまり、複数のメモリ領域を1つの guest_memfd 範囲に
結び付けることはできない（1つの guest_memfd ファイルにいくつでもメモリ領域を
結び付けられるが、結び付ける範囲は重なってはならない）。

ケイパビリティ KVM_CAP_GUEST_MEMFD_FLAGS は、KVM_CREATE_GUEST_MEMFD で指定できる
`flags` を列挙する。現在定義されているフラグ:

  ============================ ================================================
  GUEST_MEMFD_FLAG_MMAP        guest_memfd ファイルディスクリプタに対して
                               mmap() を使えるようにする。
  GUEST_MEMFD_FLAG_INIT_SHARED KVM_CREATE_GUEST_MEMFD の間、ファイル内の
                               すべてのメモリを共有にする（INIT_SHARED を
                               付けずに作成したメモリファイルはプライベート
                               として印付けられる）。共有メモリはホストの
                               ユーザ空間ページテーブルにフォールトできる。
                               プライベートメモリはできない。
  ============================ ================================================

KVM の MMU がゲストのフォールトを処理するために PFN 検索を行うと、そのフォールトが
共有のフォールトでもプライベートのフォールトでも、常に guest_memfd から処理される
（インプレース変換が無効で、バッキングの guest_memfd に GUEST_MEMFD_FLAG_MMAP フラグが
設定されていない場合を除く）。

詳細は KVM_SET_USER_MEMORY_REGION2 を参照。

4.143 KVM_PRE_FAULT_MEMORY
---------------------------

:Capability: KVM_CAP_PRE_FAULT_MEMORY
:Architectures: x86, s390, arm64
:Type: vcpu ioctl
:Parameters: struct kvm_pre_fault_memory (in/out)
:Returns: 少なくとも1ページを処理した場合は 0、エラー時は 0 未満

Errors:

  ========== ===============================================================
  EAGAIN     処理が進む前に競合が起きたが、再試行すれば成功するかもしれない。
  EINVAL     指定した `gpa` と `size` が不正だった（たとえばページ整列
             されていない、オーバーフローする、size が 0 など）、または
             VM が UCONTROL（s390）である。
  ENOENT     指定した `gpa` が定義済みのメモリスロットの外にある。
  ENOEXEC    vCPU が初期化されていない（arm64）。
  EINTR      マスクされていないシグナルが保留中で、処理されたページがない。
  EFAULT     パラメータのアドレスが不正だった。
  EHWPOISON  ポイズンされたホストページに遭遇した。
  EOPNOTSUPP GPA に対するメモリのマッピングが、ハイパーバイザで、または
             現在の vCPU の状態／モードでサポートされていない。
  EIO        想定外のエラー状態（WARN も発生させる）
  ========== ===============================================================

::

  struct kvm_pre_fault_memory {
	/* in/out */
	__u64 gpa;
	__u64 size;
	/* in */
	__u64 flags;
	__u64 padding[5];
  };

KVM_PRE_FAULT_MEMORY は、現在の vCPU の状態に合わせてメモリをマッピングするために KVM が
使うステージ 2 ページテーブルを用意する。KVM は、vCPU がステージ 2 の読み取りページ
フォールトを起こしたときと同じようにメモリをマッピングする。つまり必要に応じてメモリを
フォールトインするが、CoW は壊さない。arm64 では、KVM はステージ 2 のフォールト一般に
対してそうするのと同じく、新しく作成したステージ 2 PTE を Accessed として印付けるが、
既存の PTE の Accessed 状態は変えない。x86 では、KVM は新しく作成したステージ 2 PTE を
Accessed として印付けず、s390 では該当しない。

arm64 では、GPA は IPA として解釈され、ネストゲストの IPA としては解釈されない。
プリフォールトが用意するのは正規のステージ 2 ページテーブルだけである。

arm64 で保護 KVM（pKVM）機能が有効な場合、この機能はサポートされない。

ゲストを「ファイナライズ」／計測する前にプライベートなゲストメモリを初期設定する
コンフィデンシャル VM 種別では、この ioctl は、ゲストを「ファイナライズ」状態にする
ために必要な設定をすべて終えた後にのみ発行すべきである。そうして初めて上記の意味を
確実に保証できる。

vCPU が複数あり、ページテーブルを共有している場合がある。その場合は、この ioctl を
並行して呼び出せる。

ioctl が戻ると、入力の値は残りの範囲を指すように更新される。戻り時に `size` > 0 なら、
呼び出し側は同じ `struct kvm_map_memory` 引数でこの ioctl をもう一度発行すればよい。

x86 では、シャドウページテーブルは仮想アドレスまたはネストゲスト物理アドレスで
添字付けされるため、この ioctl をサポートできない。ゲストがシャドウページテーブルを
使っている場合（たとえばページテーブルを使うネストゲストを実行している場合）にこの
ioctl を呼び出すと、`KVM_CHECK_EXTENSION` がこのケイパビリティの存在を報告していても
`EOPNOTSUPP` で失敗する。

`flags` は現在のところ 0 でなければならない。

4.144 KVM_S390_KEYOP
--------------------

:Capability: KVM_CAP_S390_KEYOP
:Architectures: s390
:Type: vm ioctl
:Parameters: struct kvm_s390_keyop (in/out)
:Returns: 成功時は 0、エラー時は 0 未満

指定したキー操作を、与えられたゲストアドレスに対して実行する。以前のストレージキー
（またはその該当部分）が `key` に返される。

::

  struct kvm_s390_keyop {
	__u64 guest_addr;
	__u8  key;
	__u8  operation;
  };

現在 ``operation`` に指定できる値:

KVM_S390_KEYOP_ISKE
  ゲストアドレス ``guest_addr`` のストレージキーを ``key`` に返す。

KVM_S390_KEYOP_RRBE
  ゲストアドレス ``guest_addr`` の参照ビットをリセットし、以前のストレージキーの
  R ビットと C ビットを ``key`` に返す。ストレージキーの残りのフィールドは 0 に
  設定される。

KVM_S390_KEYOP_SSKE
  ゲストアドレス ``guest_addr`` のストレージキーを ``key`` で指定したキーに設定し、
  以前の値を ``key`` に返す。

4.145 KVM_PPC_GET_COMPAT_CAPS
-----------------------------
:Capability: KVM_CAP_PPC_COMPAT_CAPS
:Architectures: powerpc
:Type: vm ioctl
:Parameters: struct kvm_ppc_compat_caps (in/out)
:Returns: 成功時は 0、失敗時は負の値

エラーには次のものがある:

  ======== ============================================================
  EFAULT   ``struct kvm_ppc_compat_caps`` をユーザ空間から読み出せない、
           またはユーザ空間に書き込めない場合
  EINVAL   ``size`` フィールドが ``KVM_PPC_COMPAT_CAPS_SIZE_VER0`` より
           小さい場合、``flags`` フィールドが 0 でない場合、または
           バックエンドが CPU 互換ケイパビリティの取得やマッピングに
           失敗した場合
  E2BIG    ``size`` が ``PAGE_SIZE`` を超える場合（病的な入力への防御）、
           または ``size`` がカーネルの構造体サイズより大きく、未知の
           末尾バイトが 0 でない場合（既定以外のフィールドを設定した
           新しいユーザ空間を古いカーネルで動かす場合）。後者の場合、
           カーネルは自身の構造体サイズを ``size`` フィールドに書き戻す
           ので、ユーザ空間は正しいサイズで再試行できる
  ENOTTY   バックエンドが ``get_compat_caps`` 操作を実装していない場合
           （たとえば、必要な KVM 操作が利用できない非 HV の KVM 実装）
  ======== ============================================================

IBM POWER のシステムサーバ向けプロセッサには互換モード機能があり、第 N 世代の
プロセッサを (N-1) や (N-2) といった以前の世代と整合するモードで動作させられる。

この ioctl は、KVM on PowerNV（ネスト API v1）と KVM on PowerVM（ネスト API v2）の
各プラットフォームでネスト KVM ゲストを起動するために現在のホストプロセッサが
サポートする CPU 互換モードの情報を、ユーザ空間に提供する。

::

  struct kvm_ppc_compat_caps {
	__u64	size;			/* Size of this structure */
	__u64	flags;			/* Reserved for future use, must be 0 */
	__u64	compat_capabilities;	/* Capabilities supported by the host */
  };

この ioctl を呼び出す前に、ユーザ空間は ``size`` フィールドを
``sizeof(struct kvm_ppc_compat_caps)`` に設定し、``flags`` フィールドを 0 にしなければ
ならない。カーネルは、0 でない ``flags`` を ``-EINVAL`` で拒否する。初期化されていない
スタックの値が黙って受け入れられるのを防ぎ、ABI のあいまいさなしにこのフィールドを
将来の用途に使えるようにしておくためである。

この ioctl は、拡張可能なバージョニングをサポートするために
``copy_struct_from_user()`` と ``copy_struct_to_user()`` を使う。

``KVM_PPC_COMPAT_CAPS_SIZE_VER0`` (24) は、最初の構造体バージョンのサイズを示す
固定された定数である。

``compat_capabilities`` ビットフィールドは、ホストがサポートするプロセッサ互換モードを
表す。次のビットが特定のプロセッサモードのサポートを示す（IBM の MSB-0 表記を使い、
ビット 0 が最上位ビットである）:

- ``KVM_PPC_COMPAT_CAP_POWER9``  (bit 1) -- KVM ゲストを Power9 プロセッサモードで実行できる
- ``KVM_PPC_COMPAT_CAP_POWER10`` (bit 2) -- KVM ゲストを Power10 プロセッサモードで実行できる
- ``KVM_PPC_COMPAT_CAP_POWER11`` (bit 3) -- KVM ゲストを Power11 プロセッサモードで実行できる

.. note::

   上のビット番号は IBM の MSB-0 表記（ビット 0 が最上位ビット）を使っている。
   実際の実装では次のように定義されている:

   - ``KVM_PPC_COMPAT_CAP_POWER9``  = ``(1ULL << 62)``
   - ``KVM_PPC_COMPAT_CAP_POWER10`` = ``(1ULL << 61)``
   - ``KVM_PPC_COMPAT_CAP_POWER11`` = ``(1ULL << 60)``

   ユーザ空間は、ビット位置を直書きするのではなく ``<linux/kvm.h>`` で定義されている
   定数を使うべきである。

.. _KVM_SET_MEMORY_ATTRIBUTES2:

4.146 KVM_SET_MEMORY_ATTRIBUTES2
---------------------------------

:Capability: KVM_CAP_GUEST_MEMFD_MEMORY_ATTRIBUTES
:Architectures: all
:Type: guest_memfd ioctl
:Parameters: struct kvm_memory_attributes2 (in/out)
:Returns: 成功時は 0、エラー時は 0 未満

Errors:

  ========== ===============================================================
  EINVAL     指定した `offset` または `size` が不正だった（たとえば
             ページ整列されていない、オーバーフローする、size が 0 など）。
  EFAULT     パラメータのアドレスが不正だった。
  ENOMEM     プライベート／共有の状態を追跡しようとしてメモリが不足した
  EAGAIN     範囲内のページに未解放の参照がある。後述の ``error_offset``
             を参照。
  ========== ===============================================================

KVM_SET_MEMORY_ATTRIBUTES2 は KVM_SET_MEMORY_ATTRIBUTES の拡張で、ユーザ空間への値の
返却（書き込み）をサポートする。拡張前からあるフィールドは KVM_SET_MEMORY_ATTRIBUTES と
すべて同じ意味である。

属性の値は KVM_SET_MEMORY_ATTRIBUTES と共通である。

::

  struct kvm_memory_attributes2 {
	union {
		__u64 address;
		__u64 offset;
	};
	__u64 size;
	__u64 attributes;
	__u64 flags;
	__u64 error_offset;
	__u64 reserved[11];
  };

  #define KVM_MEMORY_ATTRIBUTE_PRIVATE           (1ULL << 3)

ケイパビリティ KVM_CAP_GUEST_MEMFD_MEMORY_ATTRIBUTES は、
KVM_SET_MEMORY_ATTRIBUTES2 で設定できる属性を列挙する。

guest_memfd 内のオフセット範囲の属性を KVM_MEMORY_ATTRIBUTE_PRIVATE に設定すると、
指定した guest_memfd に裏打ちされたメモリ範囲をゲスト専用に制限できる。guest_memfd が
GUEST_MEMFD_FLAG_MMAP 付きで作成されていても、KVM_MEMORY_ATTRIBUTE_PRIVATE の設定が
成功した後は、要求した範囲をホストのユーザ空間にマッピングできなくなり、ゲストだけが
マッピングできるようになる。

再びその範囲をホストのユーザ空間にマッピングできるようにするには、
KVM_MEMORY_ATTRIBUTE_PRIVATE を解除して、その guest_memfd に対して
KVM_SET_MEMORY_ATTRIBUTES2 をもう一度呼び出す。

KVM は属性の更新中にページのメモリ内容を直接操作しない。ただし、これらの属性を設定する
処理には、ホストやステージ 2 ページテーブルからのページのマッピング解除といった操作が
含まれ、信頼済みファームウェアの実装によって異なるメモリ内容への副作用が生じる場合が
ある。

この ioctl が -EAGAIN を返した場合、想定外の参照カウントを持つページのオフセットが
``error_offset`` に返される。これは、カーネルの他の部分がページに対して一時的な
参照カウントを取得している場合に起こりうる。

ユーザ空間は、get_user_pages() が取得した参照カウントなど、共有ページに対する既知の
参照カウントをすべて取り除く方法を考えて、この ioctl を再試行することが期待される。
こうした長期間の参照カウントの原因になりうるのは、guest_memfd のメモリが IOMMU
ページテーブルにピン留めされた場合である。

関連項目: :ref:`KVM_SET_MEMORY_ATTRIBUTES`。

.. _kvm_run:


5. kvm_run 構造体
========================

アプリケーションコードは、vcpu の fd を mmap() して kvm_run 構造体への
ポインタを得る。ここからアプリケーションコードは、KVM_RUN ioctl を呼ぶ前に
kvm_run のフィールドを変更することで実行を制御し、KVM_RUN が返った理由を
構造体のメンバを参照して調べることができる。

::

  struct kvm_run {
	/* in */
	__u8 request_interrupt_window;

ゲストに外部割り込みを注入できるようになった時点で KVM_RUN を返すよう要求する。
KVM_INTERRUPT と組み合わせて使うと有用である。

::

	__u8 immediate_exit;

このフィールドは KVM_RUN の開始時に 1 回だけ参照される。0 以外なら、KVM_RUN は
ただちに終了し、-EINTR を返す。シグナルを使って vCPU を KVM_RUN から抜けさせると
いう一般的な場面では、このフィールドを使うと KVM_SET_SIGNAL_MASK の使用を避けられる。
KVM_SET_SIGNAL_MASK はスケーラビリティが劣る。KVM_RUN の外でシグナルをブロック
する代わりに、ユーザ空間は run->immediate_exit を 0 以外に設定するシグナル
ハンドラを用意すればよい。

このフィールドは、KVM_CAP_IMMEDIATE_EXIT が利用できない場合は無視される。

::

	__u8 padding1[6];

	/* out */
	__u32 exit_reason;

KVM_RUN が成功して返った（戻り値 0）とき、これが KVM_RUN の戻った理由を
アプリケーションコードに伝える。このフィールドに指定できる値は後述する。

::

	__u8 ready_for_interrupt_injection;

request_interrupt_window が指定されている場合、このフィールドは、いま
KVM_INTERRUPT で割り込みを注入できることを示す。

::

	__u8 if_flag;

現在の割り込みフラグの値。カーネル内のローカル APIC を使っていない場合に
のみ有効である。

::

	__u16 flags;

アーキテクチャ固有のフラグで、デバイスの動作に影響しうる VCPU の状態を詳しく示す。
現在定義されているフラグは次のとおり::

  /* x86, set if the VCPU is in system management mode */
  #define KVM_RUN_X86_SMM          (1 << 0)
  /* x86, set if bus lock detected in VM */
  #define KVM_RUN_X86_BUS_LOCK     (1 << 1)
  /* x86, set if the VCPU is executing a nested (L2) guest */
  #define KVM_RUN_X86_GUEST_MODE   (1 << 2)

  /* arm64, set for KVM_EXIT_DEBUG */
  #define KVM_DEBUG_ARCH_HSR_HIGH_VALID  (1 << 0)

::

	/* in (pre_kvm_run), out (post_kvm_run) */
	__u64 cr8;

cr8 レジスタの値。カーネル内のローカル APIC を使っていない場合にのみ有効で
ある。入力と出力の両方で使う。

::

	__u64 apic_base;

APIC BASE msr の値。カーネル内のローカル APIC を使っていない場合にのみ
有効である。入力と出力の両方で使う。

::

	union {
		/* KVM_EXIT_UNKNOWN */
		struct {
			__u64 hardware_exit_reason;
		} hw;

exit_reason が KVM_EXIT_UNKNOWN なら、vcpu は不明な理由で終了した。
アーキテクチャ固有の詳しい情報は hardware_exit_reason にある。

::

		/* KVM_EXIT_FAIL_ENTRY */
		struct {
			__u64 hardware_entry_failure_reason;
			__u32 cpu; /* if KVM_LAST_CPU */
		} fail_entry;

exit_reason が KVM_EXIT_FAIL_ENTRY なら、vcpu は不明な理由で実行できなかった。
アーキテクチャ固有の詳しい情報は hardware_entry_failure_reason にある。

::

		/* KVM_EXIT_EXCEPTION */
		struct {
			__u32 exception;
			__u32 error_code;
		} ex;

未使用。

::

		/* KVM_EXIT_IO */
		struct {
  #define KVM_EXIT_IO_IN  0
  #define KVM_EXIT_IO_OUT 1
			__u8 direction;
			__u8 size; /* bytes */
			__u16 port;
			__u32 count;
			__u64 data_offset; /* relative to kvm_run start */
		} io;

exit_reason が KVM_EXIT_IO なら、vcpu が実行したポート I/O 命令を kvm が
処理できなかった。data_offset は、データのある場所（KVM_EXIT_IO_OUT）、
または次の KVM_RUN 呼び出しのためにアプリケーションコードがデータを置く
べき場所（KVM_EXIT_IO_IN）を表す。データの形式はパックされた配列である。

::

		/* KVM_EXIT_DEBUG */
		struct {
			struct kvm_debug_exit_arch arch;
		} debug;

exit_reason が KVM_EXIT_DEBUG なら、vcpu はデバッグイベントを処理しており、
そのイベントについてアーキテクチャ固有の情報が返される。

::

		/* KVM_EXIT_MMIO */
		struct {
			__u64 phys_addr;
			__u8  data[8];
			__u32 len;
			__u8  is_write;
		} mmio;

exit_reason が KVM_EXIT_MMIO なら、vcpu が実行したメモリマップド I/O 命令を
kvm が処理できなかった。'is_write' が真なら 'data' メンバに書き込まれた
データが入っており、そうでなければアプリケーションコードが 'data' を
埋める必要がある。

'data' メンバの先頭 'len' バイトには、VCPU が適切な幅でこのバイト配列へ
直接ロードまたはストアした場合と同じ値が入る。

.. note::

      KVM_EXIT_IO、KVM_EXIT_MMIO、KVM_EXIT_OSI、KVM_EXIT_PAPR、KVM_EXIT_XEN、
      KVM_EXIT_EPR、KVM_EXIT_HYPERCALL、KVM_EXIT_TDX、
      KVM_EXIT_X86_RDMSR、KVM_EXIT_X86_WRMSR では、対応する操作が完了し、
      ゲストの状態が一貫するのは、ユーザ空間が KVM_RUN でカーネルに再入したあとだけである。
      カーネル側はまず未完了の操作を終わらせ、そのあと保留中のシグナルを調べる。

      操作の保留状態は、ユーザ空間から見える状態としては保存されない。したがって、
      ユーザ空間は、ライブマイグレーションを行う前に操作が完了していることを確認すべきである。
      ユーザ空間は、マスクされていないシグナルを保留させたまま、または immediate_exit
      フィールドを設定した状態でゲストに再入すれば、以降の命令を実行させずに
      保留中の操作を完了させられる。

::

		/* KVM_EXIT_HYPERCALL */
		struct {
			__u64 nr;
			__u64 args[6];
			__u64 ret;
			__u64 flags;
		} hypercall;


ゲストがホストのユーザ空間とやり取りする必要がある機能を実装するには、
ユーザ空間が ``KVM_EXIT_IO`` (x86) または ``KVM_EXIT_MMIO`` (s390 以外の
すべて) を使うことを強く推奨する。

.. note:: KVM_EXIT_IO は KVM_EXIT_MMIO よりかなり高速である。

arm64 の場合
------------

SMCCC エグジットは、SMCCC フィルタの設定に応じて有効にできる。詳しくは
Documentation/virt/kvm/devices/vm.rst の ``KVM_ARM_SMCCC_FILTER`` を参照。

``nr`` には、ゲストの SMCCC 呼び出しのファンクション ID が入る。ユーザ空間は
``KVM_GET_ONE_REG`` ioctl を使って、呼び出しパラメータを vCPU の GPR から
取り出すことになっている。

``flags`` の定義は次のとおり。
 - ``KVM_HYPERCALL_EXIT_SMC``: ゲストが SMCCC 呼び出しを開始するのに SMC
   コンジットを使ったことを示す。このビットが 0 なら、ゲストは SMCCC 呼び出しに
   HVC コンジットを使った。

 - ``KVM_HYPERCALL_EXIT_16BIT``: ゲストが SMCCC 呼び出しを開始するのに 16 ビット
   命令を使ったことを示す。このビットが 0 なら、ゲストは 32 ビット命令を使った。
   AArch64 ゲストでは、このビットは常に 0 である。

エグジットした時点で、PC はトラップした命令の直後の命令を指している。

::

		/* KVM_EXIT_TPR_ACCESS */
		struct {
			__u64 rip;
			__u32 is_write;
			__u32 pad;
		} tpr_access;

文書化予定（KVM_TPR_ACCESS_REPORTING）。

::

		/* KVM_EXIT_S390_SIEIC */
		struct {
			__u8 icptcode;
			__u64 mask; /* psw upper half */
			__u64 addr; /* psw lower half */
			__u16 ipa;
			__u32 ipb;
		} s390_sieic;

s390 固有。

::

		/* KVM_EXIT_S390_RESET */
  #define KVM_S390_RESET_POR       1
  #define KVM_S390_RESET_CLEAR     2
  #define KVM_S390_RESET_SUBSYSTEM 4
  #define KVM_S390_RESET_CPU_INIT  8
  #define KVM_S390_RESET_IPL       16
		__u64 s390_reset_flags;

s390 固有。

::

		/* KVM_EXIT_S390_UCONTROL */
		struct {
			__u64 trans_exc_code;
			__u32 pgm_code;
		} s390_ucontrol;

s390 固有。ユーザ制御の仮想マシン（KVM_VM_S390_UCONTROL）で、そのホスト
ページテーブル上にカーネルが解決できないページフォールトが発生した。
cpu の lowcore に置かれたプログラムコードとアドレス変換例外コードが、
z Architecture Principles of Operation Book の Dynamic Address Translation
（DAT）の章の定義に従ってここに示される。

::

		/* KVM_EXIT_DCR */
		struct {
			__u32 dcrn;
			__u32 data;
			__u8  is_write;
		} dcr;

非推奨。440 KVM 用に使われていた。

::

		/* KVM_EXIT_OSI */
		struct {
			__u64 gprs[32];
		} osi;

MOL は 'OSI' と呼ぶ独自のハイパーコールインターフェースを使う。これを有効に
するため、ハイパーコールを捕まえて、ゲストの gpr をすべて含むこの exit
構造体とともにエグジットする。

exit_reason が KVM_EXIT_OSI なら、vcpu はそのようなハイパーコールを起こした。
ユーザ空間はそのハイパーコールを処理でき、終わったら必要に応じて gpr を
変更する。ゲストエントリの際、ゲストの GPR はすべてこの構造体の値で
置き換えられる。

::

		/* KVM_EXIT_PAPR_HCALL */
		struct {
			__u64 nr;
			__u64 ret;
			__u64 args[9];
		} papr_hcall;

これは 64 ビット PowerPC で pSeries パーティションをエミュレートするとき、
たとえば qemu の 'pseries' マシンタイプで使う。ゲストが 'sc 1' 命令で
ハイパーコールを行ったときに発生する。'nr' フィールドにはハイパーコール番号が
（ゲストの R3 から）入り、'args' には引数が（ゲストの R4〜R12 から）入る。
ユーザ空間は戻りコードを 'ret' に、追加の戻り値を args[] に入れるべきである。
使用できるハイパーコールは、www.power.org から入手できる Power Architecture
Platform Requirements（PAPR）文書で定義されている（入手には無償の開発者
登録が必要）。

::

		/* KVM_EXIT_S390_TSCH */
		struct {
			__u16 subchannel_id;
			__u16 subchannel_nr;
			__u32 io_int_parm;
			__u32 io_int_word;
			__u32 ipb;
			__u8 dequeued;
		} s390_tsch;

s390 固有。このエグジットは、KVM_CAP_S390_CSS_SUPPORT が有効で TEST
SUBCHANNEL がインターセプトされたときに発生する。dequeued が設定されて
いれば、対象サブチャネルの保留中の I/O 割り込みが 1 つ取り出されており、
subchannel_id、subchannel_nr、io_int_parm、io_int_word にその割り込みの
パラメータが入る。ipb は命令パラメータのデコードに必要である。

::

		/* KVM_EXIT_EPR */
		struct {
			__u32 epr;
		} epr;

FSL BookE PowerPC チップでは、割り込みコントローラにコアへの高速な割り込み
アクノリッジ経路がある。コアが割り込みの配送に成功すると、EPR レジスタに
割り込みベクタ番号を自動的に設定し、割り込みコントローラ内でその割り込みを
アクノリッジする。

割り込みコントローラがユーザ空間にある場合は、このエグジットを使って次に
配送すべき割り込みベクタを取得するため、それを介して割り込みアクノリッジ
サイクルを行う必要がある。

これは、KVM_CAP_PPC_EPR が有効で、かつ外部割り込みがゲストに配送された
直後に発生する。ユーザ空間はアクノリッジした割り込みベクタを 'epr'
フィールドに入れるべきである。

::

		/* KVM_EXIT_SYSTEM_EVENT */
		struct {
  #define KVM_SYSTEM_EVENT_SHUTDOWN       1
  #define KVM_SYSTEM_EVENT_RESET          2
  #define KVM_SYSTEM_EVENT_CRASH          3
  #define KVM_SYSTEM_EVENT_WAKEUP         4
  #define KVM_SYSTEM_EVENT_SUSPEND        5
  #define KVM_SYSTEM_EVENT_SEV_TERM       6
  #define KVM_SYSTEM_EVENT_TDX_FATAL      7
			__u32 type;
                        __u32 ndata;
                        __u64 data[16];
		} system_event;

exit_reason が KVM_EXIT_SYSTEM_EVENT なら、vcpu が何らかのアーキテクチャ
固有の仕組み（ハイパーコールや特別な命令）を使ってシステムレベルのイベントを
起こした。ARM64 の場合、これは vcpu からの HVC 命令による PSCI 呼び出しで
発生する。

'type' フィールドはシステムレベルイベントの種別を表す。
'type' に指定できる値は次のとおり。

 - KVM_SYSTEM_EVENT_SHUTDOWN -- ゲストが VM のシャットダウンを要求した。
   ユーザ空間はこれに従う義務はない。従う場合も、VM を同期的に破棄する必要は
   ない（つまり、シャットダウンが最終的に起きる前に KVM_RUN を再度呼んでよい）。
 - KVM_SYSTEM_EVENT_RESET -- ゲストが VM のリセットを要求した。
   SHUTDOWN と同様、ユーザ空間は要求を無視してもよいし、リセットを将来実行
   するよう予定してもよく、KVM_RUN を再度呼んでもよい。
 - KVM_SYSTEM_EVENT_CRASH -- ゲストがクラッシュし、ゲストがクラッシュ状態の
   維持を要求した。ユーザ空間は要求を無視してもよいし、VM メモリのコアダンプを
   取得したり、VM をリセットまたはシャットダウンしたりしてもよい。
 - KVM_SYSTEM_EVENT_SEV_TERM -- AMD SEV ゲストが終了を要求した。
   ゲストの GHCB のゲスト物理アドレスが `data[0]` に格納される。
 - KVM_SYSTEM_EVENT_TDX_FATAL -- TDX ゲストが致命的なエラー状態を報告した。
   KVM は解析も変換も行わず、Intel SDM で定義されている命令エンコーディング上の
   x86-64 汎用レジスタの 4 ビットインデックスの昇順で、16 個の汎用レジスタを
   そのままユーザ空間に渡す。
 - KVM_SYSTEM_EVENT_WAKEUP -- エグジットする vCPU がサスペンド状態にあり、
   KVM がウェイクアップイベントを認識した。ユーザ空間は、このイベントに従って
   エグジットする vCPU を実行可能とマークしてもよいし、拒否して KVM_RUN を
   再度呼んでもよい。
 - KVM_SYSTEM_EVENT_SUSPEND -- ゲストが VM のサスペンドを要求した。

KVM_CAP_SYSTEM_EVENT_DATA が存在する場合、'data' フィールドにはその
システムレベルイベントのアーキテクチャ固有の情報を格納できる。data 配列の
うち先頭 `ndata` 個（0 の場合もある）だけが有効である。

 - arm64 の場合、ゲストが PSCI 仕様 v1.1 に従って SYSTEM_RESET2 呼び出しを
   行ったとき、data[0] に KVM_SYSTEM_EVENT_RESET_FLAG_PSCI_RESET2 が設定される。

 - arm64 の場合、ゲストが PSCI 仕様 v1.3 に従って SYSTEM_OFF2 呼び出しを
   行ったとき、data[0] に KVM_SYSTEM_EVENT_SHUTDOWN_FLAG_PSCI_OFF2 が設定される。

 - RISC-V の場合、data[0] に ``sbi_system_reset`` 呼び出しの 2 番目の引数の値が
   設定される。

以前のバージョンの Linux では、この構造体に `flags` メンバが定義されていた。
このフィールドは現在 `data[0]` の別名になっている。ユーザ空間は、ndata が
0 より大きい場合にのみ書き込まれると想定してよい。

arm/arm64 の場合
------------------

KVM_SYSTEM_EVENT_SUSPEND エグジットは、VM ケイパビリティ
KVM_CAP_ARM_SYSTEM_SUSPEND で有効になる。ゲストが PSCI の SYSTEM_SUSPEND
ファンクションを呼び出すと、KVM はこのイベント種別でユーザ空間にエグジットする。

ARM DEN0022D.b 5.19 "SYSTEM_SUSPEND" に従って PSCI の SYSTEM_SUSPEND 呼び出しを
実装するのは、もっぱらユーザ空間の責任である。KVM はユーザ空間にエグジットする
前に vCPU の状態を変えないので、呼び出しパラメータは vCPU のレジスタに
そのまま残る。

ユーザ空間は、このようなエグジットに対して対処を_しなければならない_。
次のいずれかを行う必要がある。

 - ゲストの VM サスペンド要求に従う。ユーザ空間は、呼び出し元の vCPU の状態を
   KVM_MP_STATE_SUSPENDED に設定することで、サスペンドのカーネル内
   エミュレーションを要求できる。ユーザ空間は、呼び出し元の vCPU を再開する
   とき、PSCI ファンクションに渡されたパラメータに従って vCPU の状態を設定
   しなければならない。ファンクションパラメータの詳細は ARM DEN0022D.b 5.19.1
   "Intended use" を参照。

 - ゲストの VM サスペンド要求を拒否する。取りうる戻り値については
   ARM DEN0022D.b 5.19.2 "Caller responsibilities" を参照。

PSCI SYSTEM_OFF2 呼び出しを使うハイバネーションは、PSCI v1.3 が有効なときに
有効になる。ゲストが PSCI の SYSTEM_OFF2 ファンクションを呼び出すと、KVM は
KVM_SYSTEM_EVENT_SHUTDOWN イベント種別で、data[0] に
KVM_SYSTEM_EVENT_SHUTDOWN_FLAG_PSCI_OFF2 を設定してユーザ空間にエグジットする。
SYSTEM_OFF2 ファンクションでサポートされるハイバネーション種別は
HIBERNATE_OFF だけである。

::

		/* KVM_EXIT_IOAPIC_EOI */
		struct {
			__u8 vector;
		} eoi;

VCPU のカーネル内のローカル APIC が、レベルトリガの IOAPIC 割り込みの
EOI を受け取ったことを示す。このエグジットは、IOAPIC がユーザ空間に
実装されている場合（すなわち KVM_CAP_SPLIT_IRQCHIP が有効な場合）にのみ
発生する。ユーザ空間の IOAPIC は EOI を処理し、割り込みがまだアサートされて
いるなら再び発生させるべきである。Vector は、EOI を受け取った LAPIC の
割り込みベクタである。

::

		struct kvm_hyperv_exit {
  #define KVM_EXIT_HYPERV_SYNIC          1
  #define KVM_EXIT_HYPERV_HCALL          2
  #define KVM_EXIT_HYPERV_SYNDBG         3
			__u32 type;
			__u32 pad1;
			union {
				struct {
					__u32 msr;
					__u32 pad2;
					__u64 control;
					__u64 evt_page;
					__u64 msg_page;
				} synic;
				struct {
					__u64 input;
					__u64 result;
					__u64 params[2];
				} hcall;
				struct {
					__u32 msr;
					__u32 pad2;
					__u64 control;
					__u64 status;
					__u64 send_page;
					__u64 recv_page;
					__u64 pending_page;
				} syndbg;
			} u;
		};
		/* KVM_EXIT_HYPERV */
                struct kvm_hyperv_exit hyperv;

VCPU が Hyper-V エミュレーションに関連するいくつかの処理を行うために
ユーザ空間にエグジットすることを示す。

'type' に指定できる値は次のとおり。

	- KVM_EXIT_HYPERV_SYNIC -- Hyper-V SynIC の状態変化をユーザ空間に同期的に通知する

通知は、SynIC のイベントページ／メッセージページを再マップし、ユーザ空間での
SynIC メッセージ／イベント処理を有効化／無効化するために使われる。

	- KVM_EXIT_HYPERV_SYNDBG -- Hyper-V の合成デバッガの状態変化をユーザ空間に同期的に通知する

通知は、pending_page の位置を更新するか、制御コマンドを送る（send_page に
あるバッファを送る、または recv_page にバッファを受け取る）ために使われる。

::

		/* KVM_EXIT_ARM_NISV / KVM_EXIT_ARM_LDST64B */
		struct {
			__u64 esr_iss;
			__u64 fault_ipa;
		} arm_nisv;

- KVM_EXIT_ARM_NISV:

arm64 システムで使う。ゲストがメモリスロットにないメモリにアクセスすると、
KVM は通常ユーザ空間に戻り、代わりに MMIO エミュレーションを行うよう求める。
しかし一部の命令クラスでは、命令デコード（アクセスの方向、メモリアクセスの
長さ）が提供されず、VM から命令を取得してデコードするのはカーネルに置くには
複雑すぎる。

以前は、この状況が起きると KVM は警告を出力し、VM を終了させていた。KVM は、
ゲストがメモリスロット外のメモリにアクセスしたのは I/O を行おうとしており、
それが単にエミュレートできないのだと想定し、警告メッセージもそれに合わせた
表現になっていた。しかし実際にもっと多く起きたのは、ゲストのバグによる
ゲストメモリ領域外へのアクセスであり、アクセスが I/O ウィンドウ内でない場合は、
より意味のある警告メッセージとゲスト内の外部アボートにつながるべきものであった。

ユーザ空間の実装は、KVM_CAP_ARM_NISV_TO_USER を問い合わせ、VM の作成時に
このケイパビリティを有効にできる。これを有効にすると、この種のエラーは
代わりに KVM_EXIT_ARM_NISV でユーザ空間に返り、esr_iss フィールドに ESR_EL2 の
有効ビットが、fault_ipa フィールドにフォールトした IPA が入る。ユーザ空間は、
実際に I/O アクセスであれば、ゲストメモリから命令をデコードして（度胸があるなら）
アクセスを修正し、ゲストの実行を続けることもできるし、ゲストをサスペンド、
ダンプ、再起動すると決めることもできる。

KVM は KVM_EXIT_MMIO の場合のようにフォールトした命令をスキップしない点に
注意。ユーザ空間が命令をデコードしてエミュレートすると決めた場合、処理状態の
変化はユーザ空間がエミュレートしなければならない。

この機能は保護ゲストでは利用できない。エミュレーションに必要な状態に
ユーザ空間がアクセスできないためである。代わりに、データアボート例外が
ゲストに直接注入される。保護 VM のコンテキスト外で問い合わせれば
KVM_CAP_ARM_NISV_TO_USER は報告されるが、保護 VM のファイルディスクリプタで
問い合わせてもこの機能は公開されない点に注意。

- KVM_EXIT_ARM_LDST64B:

arm64 システムで使う。ゲストがメモリスロット外で LD64B、ST64B、ST64BV、
ST64BV0 を使うと、KVM は KVM_EXIT_ARM_LDST64B でユーザ空間に戻り、
KVM_EXIT_ARM_NISV と同様に、関連する ESR_EL2 の情報とフォールトした IPA を
公開する。

ユーザ空間はこれらの命令を完全にエミュレートすることになっている。内容は
次のとおり。

	- ストアのオペランドの取得（ST64BV0 命令の場合は ACCDATA_EL1 を含む）
	- ゲストがビッグエンディアンならエンディアンを扱う
	- アクセスのエミュレート（アクセスが成功しなかった場合の例外の配送を含む）
	- ST64BV/ST64BV0 の場合は戻り値を提供する
	- ロードの場合はデータを返す
	- 命令が正常に実行されたなら PC を進める

このエミュレーションはゲスト状態とのやり取りが多く、性能は期待されていない
点に注意。ただし命令の意味が保たれること、とくに 64 バイトアクセスの
シングルコピーアトミック性は期待される。

ユーザ空間が ID_AA64ISAR1_EL1.LS64 を 0 以外に設定し、FEAT_LS64* が有効で
あることを示している場合は、このエグジット理由を処理しなければならない。

::

		/* KVM_EXIT_X86_RDMSR / KVM_EXIT_X86_WRMSR */
		struct {
			__u8 error; /* user -> kernel */
			__u8 pad[7];
			__u32 reason; /* kernel -> user */
			__u32 index; /* kernel -> user */
			__u64 data; /* kernel <-> user */
		} msr;

x86 システムで使う。VM ケイパビリティ KVM_CAP_X86_USER_SPACE_MSR が有効な
場合、KVM カーネルコードが #GP を起こすようなレジスタへの MSR アクセスは、
代わりに読み取りで KVM_EXIT_X86_RDMSR エグジット、書き込みで
KVM_EXIT_X86_WRMSR エグジットを発生させることがある。

"reason" フィールドは、MSR のインターセプトが起きた理由を表す。ユーザ空間が
MSR エグジットを受け取るのは、ENABLE_CAP で特定の理由を指定した場合だけ
である。現在有効なエグジット理由は次のとおり。

============================ ========================================
 KVM_MSR_EXIT_REASON_UNKNOWN KVM にとって未知の MSR へのアクセス
 KVM_MSR_EXIT_REASON_INVAL   無効な MSR または予約済みビットへのアクセス
 KVM_MSR_EXIT_REASON_FILTER  KVM_X86_SET_MSR_FILTER によってブロックされたアクセス
============================ ========================================

KVM_EXIT_X86_RDMSR では、"index" フィールドが、ゲストが読み取ろうとしている
MSR をユーザ空間に伝える。この要求に成功として応答するには、ユーザ空間は
該当するデータを "data" フィールドに書き込み、読み取ったデータがゲストの
レジスタ状態に反映されるよう、ゲストの実行を続けなければならない。

RDMSR 要求が失敗した場合、ユーザ空間は "error" フィールドに "1" を設定して
示す。VCPU を再度実行すると、これにより #GP がゲストに注入される。

KVM_EXIT_X86_WRMSR では、"index" フィールドが、ゲストが書き込もうとしている
MSR をユーザ空間に伝える。イベントの処理を終えたら、ユーザ空間は vCPU の
実行を続けなければならない。MSR の書き込みが失敗した場合も、ユーザ空間は
"error" フィールドに "1" を設定する。

MSR フィルタリングとの関係の詳細は KVM_X86_SET_MSR_FILTER を参照。

::


		struct kvm_xen_exit {
  #define KVM_EXIT_XEN_HCALL          1
			__u32 type;
			union {
				struct {
					__u32 longmode;
					__u32 cpl;
					__u64 input;
					__u64 result;
					__u64 params[6];
				} hcall;
			} u;
		};
		/* KVM_EXIT_XEN */
                struct kvm_hyperv_exit xen;

VCPU が Xen エミュレーションに関連するいくつかの処理を行うために
ユーザ空間にエグジットすることを示す。

'type' に指定できる値は次のとおり。

  - KVM_EXIT_XEN_HCALL -- Xen ハイパーコールをユーザ空間に同期的に通知する。
    ユーザ空間は、KVM_RUN を再度呼ぶ前に、ハイパーコールの結果を適切な
    フィールドに入れることになっている。

::

		/* KVM_EXIT_RISCV_SBI */
		struct {
			unsigned long extension_id;
			unsigned long function_id;
			unsigned long args[6];
			unsigned long ret[2];
		} riscv_sbi;

exit reason が KVM_EXIT_RISCV_SBI なら、VCPU が KVM RISC-V カーネルモジュール
で処理されない SBI 呼び出しを行ったことを示す。SBI 呼び出しの詳細は kvm_run
構造体の 'riscv_sbi' メンバにある。'riscv_sbi' の 'extension_id' フィールドは
SBI 拡張 ID を表し、'function_id' フィールドはその SBI 拡張のファンクション ID を
表す。'riscv_sbi' の 'args' 配列フィールドは SBI 呼び出しのパラメータを表し、
'ret' 配列フィールドは戻り値を表す。ユーザ空間は、VCPU を再開する前に SBI
呼び出しの戻り値を更新すべきである。RISC-V SBI 仕様の詳細は
https://github.com/riscv/riscv-sbi-doc を参照。

::

		/* KVM_EXIT_MEMORY_FAULT */
		struct {
  #define KVM_MEMORY_EXIT_FLAG_PRIVATE	(1ULL << 3)
			__u64 flags;
			__u64 gpa;
			__u64 size;
		} memory_fault;

KVM_EXIT_MEMORY_FAULT は、vCPU が KVM では解決できないメモリフォールトに
遭遇したことを示す。'gpa' と 'size'（バイト単位）は、フォールトしたゲスト
物理アドレス範囲 [gpa, gpa + size) を表す。'flags' フィールドは、フォールト
したアクセスの関連しそうな性質を表す。

 - KVM_MEMORY_EXIT_FLAG_PRIVATE - 設定されていれば、メモリフォールトが
   プライベートメモリアクセスで起きたことを示す。クリアされていれば、
   フォールトが共有アクセスで起きたことを示す。

注意! KVM_EXIT_MEMORY_FAULT は、すべての KVM エグジット理由の中で唯一、
戻り値 '0' ではなく '-1' を伴う。KVM が KVM_EXIT_MEMORY_FAULT でエグジット
するとき、errno は常に EFAULT か EHWPOISON に設定される。それ以外の
エラー番号では、ユーザ空間は kvm_run.exit_reason が古いか未定義だと
想定すべきである。

::

    /* KVM_EXIT_NOTIFY */
    struct {
  #define KVM_NOTIFY_CONTEXT_INVALID	(1 << 0)
      __u32 flags;
    } notify;

x86 システムで使う。VM ケイパビリティ KVM_CAP_X86_NOTIFY_VMEXIT が有効な
場合、VM 非ルートモードで一定時間イベントウィンドウが発生しないと VM エグジット
が生成される。ケイパビリティを有効にする際に KVM_X86_NOTIFY_VMEXIT_USER を
設定すると、さらに処理するためエグジット理由 KVM_EXIT_NOTIFY でユーザ空間に
エグジットする。"flags" フィールドにはより詳しい情報が入る。

'flags' の有効な値は次のとおり。

  - KVM_NOTIFY_CONTEXT_INVALID -- VM コンテキストが壊れており、VMCS 内で
    有効でない。対象の VM を再開すると、不明な結果になる。

::

		/* KVM_EXIT_TDX */
		struct {
			__u64 flags;
			__u64 nr;
			union {
				struct {
					u64 ret;
					u64 data[5];
				} unknown;
				struct {
					u64 ret;
					u64 gpa;
					u64 size;
				} get_quote;
				struct {
					u64 ret;
					u64 leaf;
					u64 r11, r12, r13, r14;
				} get_tdvmcall_info;
				struct {
					u64 ret;
					u64 vector;
				} setup_event_notify;
			};
		} tdx;

ゲストからの TDVMCALL を処理する。KVM は Guest-Hypervisor
Communication Interface（GHCI）仕様に基づいて一部の TDVMCALL を転送する。
KVM はこれらの要求を最小限の変更でユーザ空間の VMM に橋渡しし、入力を共用体に
入れ、再入時にゲストへコピーし戻す。

フラグは現在常に 0 で、``nr`` にはレジスタ R11 からの TDVMCALL 番号が入る。
共用体の残りのフィールドが TDVMCALL の入力と出力を提供する。現在定義されて
いる ``nr`` の値は次のとおり。

 * ``TDVMCALL_GET_QUOTE``: ゲストが、ホスト上で動作する TD-Quoting Enclave を
   ホストするサービスが署名する TD-Quote の生成を要求した。パラメータと
   戻り値は共用体の ``get_quote`` フィールドにある。``gpa`` フィールドと
   ``size`` は、TDX ゲストが TD Report を渡す共有メモリバッファのゲスト物理
   アドレス（共有ビットを立てていないもの）とサイズを指定する。``ret``
   フィールドは GetQuote 要求の戻り値を表す。要求が正常にキューに入ると、
   TDX ゲストは共有メモリ領域のステータスフィールドをポーリングして、Quote の
   生成が完了したかどうかを確認できる。完了すると、生成された Quote が同じ
   バッファを通じて返される。

 * ``TDVMCALL_GET_TD_VM_CALL_INFO``: ゲストが TDVMCALL のサポート状況を
   要求した。指定されたリーフに対する出力値は、共用体の ``get_tdvmcall_info``
   フィールドの ``r11`` から ``r14`` までのフィールドに入れるべきである。

 * ``TDVMCALL_SETUP_EVENT_NOTIFY_INTERRUPT``: ゲストが、ベクタ ``vector`` に
   対する通知割り込みの設定を要求した。

KVM は将来さらに多くの値のサポートを追加する可能性があり、``KVM_ENABLE_CAP``
などの呼び出しがなくてもユーザ空間へのエグジットを起こすことがある。この
場合、KVM は出力フィールドをすでに有効にして入る。通常は共用体の
``unknown.ret`` フィールドが ``TDVMCALL_STATUS_SUBFUNC_UNSUPPORTED`` になる。
TDVMCALL をサポートするつもりがなければ、ユーザ空間は何もする必要はない。

::

		/* KVM_EXIT_ARM_SEA */
		struct {
  #define KVM_EXIT_ARM_SEA_FLAG_GPA_VALID   (1ULL << 0)
			__u64 flags;
			__u64 esr;
			__u64 gva;
			__u64 gpa;
		} arm_sea;

arm64 システムで使う。VM ケイパビリティ ``KVM_CAP_ARM_SEA_TO_USER`` が有効な
場合、ゲストのアクセスが同期外部アボート（SEA）を引き起こし、ホストの APEI が
その SEA の処理に失敗すると、KVM はユーザ空間にエグジットする。

``esr`` には、KVM にトラップされた例外の ESR_EL2 をサニタイズした値が設定
される。内容は次のフィールドからなる。

 - ``ESR_EL2.EC``
 - ``ESR_EL2.IL``
 - ``ESR_EL2.FnV``
 - ``ESR_EL2.EA``
 - ``ESR_EL2.CM``
 - ``ESR_EL2.WNR``
 - ``ESR_EL2.FSC``
 - ``ESR_EL2.SET`` (VM で FEAT_RAS が実装されている場合)

``ESR_EL2.FnV == 0`` のとき、``gva`` には KVM にトラップされた例外の FAR_EL2 の
値が設定される。それ以外の場合、``gva`` の値は不明である。

``KVM_EXIT_ARM_SEA_FLAG_GPA_VALID`` フラグが設定されているとき、``gpa`` には
KVM にトラップされた例外のフォールトした IPA が設定される。それ以外の場合、
``gpa`` の値は不明である。

::

		/* Fix the size of the union. */
		char padding[256];
	};

	/*
	 * shared registers between kvm and userspace.
	 * kvm_valid_regs specifies the register classes set by the host
	 * kvm_dirty_regs specified the register classes dirtied by userspace
	 * struct kvm_sync_regs is architecture specific, as well as the
	 * bits for kvm_valid_regs and kvm_dirty_regs
	 */
	__u64 kvm_valid_regs;
	__u64 kvm_dirty_regs;
	union {
		struct kvm_sync_regs regs;
		char padding[SYNC_REGS_SIZE_BYTES];
	} s;

KVM_CAP_SYNC_REGS が定義されている場合、これらのフィールドを使うと、
ユーザ空間は SET/GET_*REGS を呼ばずに特定のゲストレジスタへアクセスできる。
したがって、ユーザ空間がエグジットを処理しなければならないときに、システム
コールのオーバーヘッドをいくらか避けられる。ユーザ空間は、kvm_valid_regs の
特定のビットを調べて構造体の有効性を確認できる。これらのビットは
アーキテクチャ固有で、通常はレジスタ群の有効性を定義する（たとえば
汎用レジスタ用のビットが 1 つ）。

カーネルは、特定の種別のレジスタの主たる格納先として kvm_run 構造体を
使ってよい点に注意。そのため、kvm_dirty_regs の対応するビットが設定されて
いなくても、カーネルは kvm_run の値を使うことがある。

::

		/* KVM_EXIT_SNP_REQ_CERTS */
		struct kvm_exit_snp_req_certs {
			__u64 gpa;
			__u64 npages;
			__u64 ret;
		};

KVM_EXIT_SNP_REQ_CERTS は、証明書取得が有効な SEV-SNP ゲスト
（KVM_SEV_SNP_ENABLE_REQ_CERTS を参照）が、メッセージ種別 MSG_REPORT_REQ で
Extended Guest Request NAE #VMGEXIT（SNP_GUEST_REQUEST）を生成したこと、
すなわちファームウェアにアテステーションレポートを要求し、その要求の一部と
してアテステーションレポートの署名に対応する証明書データをハイパーバイザが
提供することを望んでいることを示す。

ユーザ空間が証明書を提供できるようにするため、'gpa' と 'npages' はゲストの
要求からそのまま転送される（それぞれ GHCB の RAX フィールドと RBX フィールド）。
'ret' は KVM からの "output" ではなく、エグジット時は常に '0' である。KVM は
ユーザ空間にエグジットする前に 'gpa' が 4KiB に整列していることを確認するが、
それ以外にゲストからの情報は検証しない。

次の KVM_RUN で、たとえばユーザ空間が要求を処理した（または処理しなかった）
あと、KVM は #VMGEXIT を完了する。その際、'ret' フィールドを使ってゲストに
成功を伝えるか失敗を伝えるか、失敗ならどの理由コードを SW_EXITINFO2 で
伝えるかを決める。'ret' がサポートされない値（下の表を参照）なら、KVM_RUN は
-EINVAL で失敗する。'ret' が 'ENOSPC' の場合、KVM は 'npages' フィールドも
消費する。すなわちユーザ空間は、すべての証明書データを格納するのに必要な
ページ数をこのフィールドでゲストに伝えられる。

サポートされる 'ret' の値と、それぞれの SW_EXITINFO2 エンコーディングは
次のとおり。

  ======     =============================================================
  0          0x0、すなわち成功。KVM は SNP ファームウェアに SNP_GUEST_REQUEST
             コマンドを発行する。
  ENOSPC     0x0000000100000000、すなわち証明書テーブルと証明書データを
             格納するのにゲストページが足りない。KVM は GHBC の RBX
             フィールドにも 'npages' を設定する。
  EAGAIN     0x0000000200000000、すなわちホストがビジーで、ゲストは要求を
             再試行すべきである。
  EIO        0xffffffff00000000、その他すべてのエラー（この戻りコードは
             GHCB で許されているとおり、KVM 定義のハイパーバイザ値である）
  ======     =============================================================


.. _cap_enable:

6. vCPU で有効化できるケイパビリティ
====================================

有効化すると vCPU や仮想マシン（VM）の動作を変えるケイパビリティがある。有効化する
方法は :ref:`KVM_ENABLE_CAP` を参照。

以下にケイパビリティの一覧と、有効化したときに vCPU や VM に与える影響を示す。

各項目の説明には、次の情報を添えている。

  Architectures:
      この ioctl を提供する命令セットアーキテクチャ。
      x86 には i386 と x86_64 の両方が含まれる。

  Target:
      これが vCPU 単位か VM 単位のどちらのケイパビリティか。

  Parameters:
      このケイパビリティが受け付けるパラメータ。

  Returns:
      戻り値。一般的なエラー番号（EBADF、ENOMEM、EINVAL）の詳細は
      述べないが、固有の意味を持つエラーは述べる。


6.1 KVM_CAP_PPC_OSI
-------------------

:Architectures: ppc
:Target: vCPU
:Parameters: なし
:Returns: 成功時は 0、エラー時は -1

このケイパビリティを有効にすると、OSI ハイパーコールを横取りできる。そうしなければ、
OSI ハイパーコールはゲストに注入する通常のシステムコールとして扱われる。OSI
ハイパーコールは、ゲストとホストの間で標準化された通信手段を持たせるために
Mac-on-Linux が考案した。

このケイパビリティを有効にすると、KVM_EXIT_OSI が発生しうる。


6.2 KVM_CAP_PPC_PAPR
--------------------

:Architectures: ppc
:Target: vCPU
:Parameters: なし
:Returns: 成功時は 0、エラー時は -1

このケイパビリティを有効にすると、PAPR ハイパーコールを横取りできる。PAPR
ハイパーコールはハイパーコール命令 "sc 1" で行う。

また、ゲストの特権レベルを "supervisor" モードに設定する。通常、ゲストは
"hypervisor" 特権モードで動作し、いくつかの機能が欠けている。

さらに、SDR1 の意味も変える。このモードでは、PAPR は HTAB をゲストから見えない
ようにするため、SDR1 の HTAB アドレス部分には GPA ではなく HVA が入る。

このケイパビリティを有効にすると、KVM_EXIT_PAPR_HCALL が発生しうる。


6.3 KVM_CAP_SW_TLB
------------------

:Architectures: ppc
:Target: vCPU
:Parameters: args[0] は struct kvm_config_tlb のアドレス
:Returns: 成功時は 0、エラー時は -1

::

  struct kvm_config_tlb {
	__u64 params;
	__u64 array;
	__u32 mmu_type;
	__u32 array_len;
  };

vCPU の TLB 配列を設定し、ユーザ空間と KVM の間に共有メモリ領域を確立する。
"params" と "array" フィールドは、mmu タイプ固有のデータ構造のユーザ空間アドレス
である。"array_len" フィールドは安全機構であり、ユーザ空間が配列用に確保したメモリ
のサイズ（バイト単位）を設定すべきである。これは少なくとも "mmu_type" と "params"
が定めるサイズでなければならない。

KVM_RUN の実行中、共有領域は KVM の管理下にある。その内容は不定であり、ユーザ空間
が変更を加えると、結果は限られた範囲で不定な動作になる。

KVM_RUN から戻ると、共有領域はゲスト TLB の現在の状態を反映する。ユーザ空間が変更
を加えた場合は、この vCPU で再び KVM_RUN を呼ぶ前に、KVM_DIRTY_TLB を呼んで、どの
エントリを変更したかを KVM に伝えなければならない。

mmu タイプ KVM_MMU_FSL_BOOKE_NOHV と KVM_MMU_FSL_BOOKE_HV では、次のとおり。

 - "params" フィールドの型は "struct kvm_book3e_206_tlb_params" である。
 - "array" フィールドは "struct kvm_book3e_206_tlb_entry" 型の配列を指す。
 - 配列は、第1 TLB の全エントリに続けて第2 TLB の全エントリを並べたものである。
 - TLB 内では、エントリはまずセット番号の昇順で並ぶ。セット内では、エントリは
   ウェイ順（ESEL の昇順）で並ぶ。
 - TLB0 でセット番号を決めるハッシュは (MAS2 >> 12) & (num_sets - 1) である。
   ここで "num_sets" は tlb_sizes[] の値を tlb_ways[] の値で割ったものである。
 - mas1 の tsize フィールドは、ハードウェアが TLB0 ではこの値を無視するとしても、
   TLB0 では 4K に設定しなければならない。

6.4 KVM_CAP_S390_CSS_SUPPORT
----------------------------

:Architectures: s390
:Target: vCPU
:Parameters: なし
:Returns: 成功時は 0、エラー時は -1

このケイパビリティは、チャネル I/O 命令の処理を有効にする。

TEST PENDING INTERRUPTION と TEST SUBCHANNEL の割り込み部分はカーネル内で処理し、
その他の I/O 命令はユーザ空間に渡す。

このケイパビリティを有効にすると、TEST SUBCHANNEL の横取り時に
KVM_EXIT_S390_TSCH が発生する。

このケイパビリティは vCPU 単位で有効化するが、VM 全体に影響することに注意。

6.5 KVM_CAP_PPC_EPR
-------------------

:Architectures: ppc
:Target: vCPU
:Parameters: args[0] はプロキシ機能を有効にするかどうかを指定する
:Returns: 成功時は 0、エラー時は -1

このケイパビリティは、外部プロキシ機能を通じた割り込みの配送を有効または無効に
する。

有効にすると（args[0] != 0）、ゲストが外部割り込みを配送されるたびに、最上位の
割り込みベクタを受け取るために、自動的に KVM_EXIT_EPR エグジットでユーザ空間へ
抜ける。

無効にすると（args[0] == 0）、この機能が未対応であるかのように動作する。

このケイパビリティを有効にすると、KVM_EXIT_EPR が発生しうる。

6.6 KVM_CAP_IRQ_MPIC
--------------------

:Architectures: ppc
:Parameters: args[0] は MPIC デバイスの fd、
             args[1] はこの vCPU の MPIC CPU 番号

このケイパビリティは、vCPU をカーネル内の MPIC デバイスに接続する。

6.7 KVM_CAP_IRQ_XICS
--------------------

:Architectures: ppc
:Target: vCPU
:Parameters: args[0] は XICS デバイスの fd、
             args[1] はこの vCPU の XICS CPU 番号（サーバ ID）

このケイパビリティは、vCPU をカーネル内の XICS デバイスに接続する。

6.8 KVM_CAP_S390_IRQCHIP
------------------------

:Architectures: s390
:Target: VM
:Parameters: なし

このケイパビリティは s390 でカーネル内 irqchip を有効にする。詳細は
「4.24 KVM_CREATE_IRQCHIP」を参照。

6.9 KVM_CAP_MIPS_FPU
--------------------

:Architectures: mips
:Target: vCPU
:Parameters: args[0] は将来の使用のために予約済み（0 にすべき）。

このケイパビリティは、ゲストがホストの浮動小数点ユニット（FPU）を使えるように
する。ゲストで FPU を有効にするには、Config1.FP ビットを設定できる。これを設定
すると、現在のゲスト FPU レジスタモードに応じて ``KVM_REG_MIPS_FPR_*`` と
``KVM_REG_MIPS_FCR_*`` レジスタにアクセスでき、Status.FR と Config5.FRE ビットは、
FPU が対応していれば KVM API 経由でもゲストからもアクセスできる。

6.10 KVM_CAP_MIPS_MSA
---------------------

:Architectures: mips
:Target: vCPU
:Parameters: args[0] は将来の使用のために予約済み（0 にすべき）。

このケイパビリティは、ゲストが MIPS SIMD アーキテクチャ（MSA）を使えるように
する。ゲストが MSA を使えるようにするには、Config3.MSAP ビットを設定できる。
これを設定すると、``KVM_REG_MIPS_VEC_*`` と ``KVM_REG_MIPS_MSA_*`` レジスタに
アクセスでき、Config5.MSAEn ビットは KVM API 経由でもゲストからもアクセスできる。

6.74 KVM_CAP_SYNC_REGS
----------------------

:Architectures: s390, x86
:Target: s390 は常に有効、x86 は vCPU
:Parameters: なし
:Returns: x86: KVM_CHECK_EXTENSION は、対応するレジスタセットを示すビット配列を
          返す（ビットフィールドは arch/x86/include/uapi/asm/kvm.h で定義されて
          いる）。

前述の :ref:`kvm_run` 節にある kvm_sync_regs 構造体の説明のとおり、
KVM_CAP_SYNC_REGS は「ユーザ空間が SET/GET_*REGS を呼ばずに特定のゲストレジスタに
アクセスできるようにする」。これにより、レジスタ値の設定や取得のための ioctl
呼び出しの繰り返しをなくし、オーバーヘッドを減らす。ユーザ空間がゲスト状態を
同期的に変更するとき、たとえばユーザ空間で命令をエミュレートしたり横取りしたり
するときには、特に重要である。

s390 の詳細はソースコードを参照。

x86 では次のとおり。

- kvm_run にコピーするレジスタセットはユーザ空間が選択できる（毎回のエグジットで
  すべてのセットをコピーするのではない）。
- regs と sregs に加えて vcpu_events も利用できる。

x86 では、struct kvm_run の 'kvm_valid_regs' フィールドを流用し、次のエグジットで
コピーする特定のレジスタセットをユーザ空間が指定する入力ビット配列フィールドと
して機能させる。

ユーザ空間が vCPU にコピーすべき値を変更したことを示すには、全アーキテクチャ共通
のビット配列フィールド 'kvm_dirty_regs' を設定しなければならない。設定には
'kvm_valid_regs' フィールドと同じビットフラグを使う。ダーティビットを設定して
いないと、レジスタセットの値が変更されていても vCPU にはコピーされない。

ビット配列の未使用のビットフィールドは 0 に設定しなければならない。

::

  struct kvm_sync_regs {
        struct kvm_regs regs;
        struct kvm_sregs sregs;
        struct kvm_vcpu_events events;
  };

6.75 KVM_CAP_PPC_IRQ_XIVE
-------------------------

:Architectures: ppc
:Target: vCPU
:Parameters: args[0] は XIVE デバイスの fd、
             args[1] はこの vCPU の XIVE CPU 番号（サーバ ID）

このケイパビリティは、vCPU をカーネル内の XIVE デバイスに接続する。

6.76 KVM_CAP_HYPERV_SYNIC
-------------------------

:Architectures: x86
:Target: vCPU

KVM_CHECK_EXTENSION が利用可能と示せば、このケイパビリティは、カーネルに
Hyper-V Synthetic interrupt controller（SynIC）の実装があることを意味する。
Hyper-V SynIC は、Windows の Hyper-V ベースのゲスト準仮想化ドライバ（VMBus）を
支えるために使う。

SynIC を使うには、vCPU の fd に対して KVM_ENABLE_CAP ioctl でこのケイパビリティ
を設定して有効化する必要がある。この設定は、CPU が対応していても APIC ハードウェア
仮想化を無効にする点に注意。SynIC の auto-EOI の動作と両立しないためである。

6.77 KVM_CAP_HYPERV_SYNIC2
--------------------------

:Architectures: x86
:Target: vCPU

このケイパビリティは、Hyper-V Synthetic interrupt controller（SynIC）の新しい
バージョンを有効にする。KVM_CAP_HYPERV_SYNIC との違いは、対応する MSR に書き込んで
SynIC のメッセージページとイベントフラグページを有効にしたときに、KVM がこれらの
ページをクリアしない点だけである。

6.78 KVM_CAP_HYPERV_DIRECT_TLBFLUSH
-----------------------------------

:Architectures: x86
:Target: vCPU

このケイパビリティは、Hyper-V ハイパーバイザ上で動作する KVM が、ゲストに対して
Direct TLB flush を有効にすることを示す。これは、TLB フラッシュのハイパーコールを
KVM を経由せずにレベル 0 ハイパーバイザ（Hyper-V）が処理することを意味する。
Hyper-V と KVM ではハイパーコールの引数の ABI が異なるため、このケイパビリティを
有効にすると、KVM によるハイパーコール処理が実質的にすべて無効になる（KVM の
ハイパーコールの一部が Hyper-V に TLB フラッシュのハイパーコールと誤認されること
があるため）。したがってユーザ空間は、CPUID で KVM の識別を無効にし、Hyper-V の
識別だけを公開すべきである。この場合、ゲストは Hyper-V 上で動作していると認識し、
Hyper-V のハイパーコールだけを使う。

6.79 KVM_CAP_HYPERV_ENFORCE_CPUID
---------------------------------

:Architectures: x86
:Target: vCPU

有効にすると、KVM は、ゲストに提供するエミュレート済みの Hyper-V 機能を、
Hyper-V CPUID 機能リーフのビットに従って無効にする。そうでなければ、
HYPERV_CPUID_INTERFACE（0x40000001）リーフで Hyper-V の識別を設定すると、現在
実装されているすべての Hyper-V 機能が無条件に提供される。

6.80 KVM_CAP_ENFORCE_PV_FEATURE_CPUID
-------------------------------------

:Architectures: x86
:Target: vCPU

有効にすると、KVM は、ゲストに提供する準仮想化機能を、KVM_CPUID_FEATURES CPUID
リーフ（0x40000001）のビットに従って無効にする。そうでなければ、CPUID リーフで
実際に公開された内容にかかわらず、ゲストが準仮想化機能を使えることがある。

.. _KVM_CAP_DIRTY_LOG_RING:


.. _cap_enable_vm:

7. VM で有効化できるケイパビリティ
==========================================

有効化すると仮想マシンの動作を変えるケイパビリティがある。
有効化する方法は :ref:`KVM_ENABLE_CAP` の節を参照されたい。
以下に、ケイパビリティの一覧と、それらを有効化したときの VM への影響を示す。

説明と合わせて、以下の情報を記載する。

  アーキテクチャ:
      この ioctl を提供する命令セットアーキテクチャ。
      x86 は i386 と x86_64 の両方を含む。

  パラメータ:
      ケイパビリティが受け付けるパラメータ。

  戻り値:
      返される値。一般的なエラー番号（EBADF、ENOMEM、EINVAL）については
      詳細を述べないが、固有の意味を持つエラーについては述べる。


7.1 KVM_CAP_PPC_ENABLE_HCALL
----------------------------

:Architectures: ppc
:Parameters: args[0] は sPAPR hcall 番号。args[1] は 0 で無効化、
             1 でカーネル内処理を有効化する。

このケイパビリティは、個々の sPAPR ハイパーコール（hcall）を
カーネルが処理するかどうかを制御する。
hcall のカーネル内処理を有効化または無効化すると、VM 全体に影響する。
作成時には、このケイパビリティが実装される前にカーネル内ハンドラが
実装されていた hcall の初期セットが、カーネル内処理のために有効化される。
無効化すると、カーネルは hcall の処理を試みず、常にユーザ空間へ処理を委ねる。
関連する hcall のグループの一部を有効化し、別の一部を無効化することが
意味をなさない場合があるが、KVM はユーザ空間がそうすることを妨げない。

指定された hcall 番号にカーネル内実装がない場合、
KVM_ENABLE_CAP ioctl は EINVAL エラーで失敗する。

7.2 KVM_CAP_S390_USER_SIGP
--------------------------

:Architectures: s390
:Parameters: なし

このケイパビリティは、どの SIGP 命令が完全にユーザ空間で
処理されるかを制御する。
このケイパビリティを有効化すると、すべての高速命令が
完全にカーネルで処理される:

- SENSE
- SENSE RUNNING
- EXTERNAL CALL
- EMERGENCY SIGNAL
- CONDITIONAL EMERGENCY SIGNAL

他のすべての命令は完全にユーザ空間で処理される。

特権操作の例外のみがカーネル（あるいは横取り前のハードウェア）で
チェックされる。
このケイパビリティが有効でない場合、SIGP 命令の処理には
古い方法（カーネルとユーザ空間で部分的に処理）が使われる。

7.3 KVM_CAP_S390_VECTOR_REGISTERS
---------------------------------

:Architectures: s390
:Parameters: なし
:Returns: 成功時は 0、エラー時は負の値

z13 プロセッサで導入されたベクタレジスタの使用を可能にし、
ホストとユーザ空間間の同期を提供する。
マシンがベクタをサポートしていない場合は -EINVAL を返す。

7.4 KVM_CAP_S390_USER_STSI
--------------------------

:Architectures: s390
:Parameters: なし

このケイパビリティは、STSI 命令のポストハンドラを可能にする。
カーネルでの初期処理の後、KVM はユーザ空間がさらなるデータを
挿入できるように、KVM_EXIT_S390_STSI でユーザ空間へ終了する。

ユーザ空間へ終了する前に、kvm ハンドラは
vcpu->run の s390_stsi フィールドを埋めるべきである::

  struct {
	__u64 addr;
	__u8 ar;
	__u8 reserved;
	__u8 fc;
	__u8 sel1;
	__u16 sel2;
  } s390_stsi;

  @addr - guest address of STSI SYSIB
  @fc   - function code
  @sel1 - selector 1
  @sel2 - selector 2
  @ar   - access register number

KVM ハンドラは rc = -EREMOTE でユーザ空間へ終了するべきである。

7.5 KVM_CAP_SPLIT_IRQCHIP
-------------------------

:Architectures: x86
:Parameters: args[0] - ユーザ空間の IOAPIC 用に予約するルート数
:Returns: 成功時は 0、エラー時は -1

カーネル内の各プロセッサ用にローカル APIC を作成する。
ユーザ空間の VMM が IOAPIC と PIC（さらに、別途有効化が必要な PIT も）を
エミュレートしたい場合は、KVM_CREATE_IRQCHIP の代わりにこれを使用できる。

このケイパビリティはカーネル内での割り込み要求のルーティングも
有効化する。
KVM_CAP_SPLIT_IRQCHIP が有効な場合、IRQ ルーティングテーブルでは
KVM_IRQ_ROUTING_MSI タイプのルートのみが使用される。
最初の args[0] 個の MSI ルートは IOAPIC ピン用に予約される。
LAPIC がこれらのルートに対して EOI を受信すると、
KVM_EXIT_IOAPIC_EOI vmexit がユーザ空間へ報告される。

``KVM_CREATE_IRQCHIP`` と同様に、後続の vCPU 作成では
APIC ベースアドレス (0xfee00000) にプライベートなメモリスロットを
設置する場合があり、これはユーザメモリ領域と重複してはならない。
詳細は ``KVM_CREATE_IRQCHIP`` を参照されたい。

vCPU がすでに作成されている場合、または irqchip がすでにカーネル内にある場合
（すなわち KVM_CREATE_IRQCHIP がすでに呼ばれている場合）は失敗する。

7.6 KVM_CAP_S390_RI
-------------------

:Architectures: s390
:Parameters: なし

zEC12 プロセッサで導入されたランタイム・インストルメンテーションの
使用を可能にする。
マシンがランタイム・インストルメンテーションをサポートしていない場合は
-EINVAL を返す。
vCPU がすでに作成されている場合は -EBUSY を返す。

7.7 KVM_CAP_X2APIC_API
----------------------

:Architectures: x86
:Parameters: args[0] - 有効化すべき機能
:Returns: 成功時は 0、args[0] に無効な機能が含まれる場合は -EINVAL

args[0] で有効な機能フラグは次のとおりである::

  #define KVM_X2APIC_API_USE_32BIT_IDS                          (1ULL << 0)
  #define KVM_X2APIC_API_DISABLE_BROADCAST_QUIRK                (1ULL << 1)
  #define KVM_X2APIC_ENABLE_SUPPRESS_EOI_BROADCAST              (1ULL << 2)
  #define KVM_X2APIC_DISABLE_SUPPRESS_EOI_BROADCAST             (1ULL << 3)

KVM_X2APIC_API_USE_32BIT_IDS を有効化すると、
KVM_SET_GSI_ROUTING、KVM_SIGNAL_MSI、KVM_SET_LAPIC、KVM_GET_LAPIC の
動作が変わり、32 ビットの APIC ID を使用できるようになる。
それぞれの節の KVM_CAP_X2APIC_API を参照されたい。

論理モードまたは 255 個を超える vCPU で x2APIC を動作させるには、
KVM_X2APIC_API_DISABLE_BROADCAST_QUIRK を有効化する必要がある。
そうしない場合、KVM は割り込みリマッピングなしの物理 x2APIC を
サポートするため、x2APIC モードでも 0xff をブロードキャストとして扱う。
これは論理モードでは望ましくない。
論理モードでは 0xff はクラスタ 0 の CPU 0-7 を表す。

KVM_X2APIC_ENABLE_SUPPRESS_EOI_BROADCAST を設定すると、
KVM に EOI ブロードキャストの抑制を有効化するよう指示する。
KVM はゲストに EOI ブロードキャストの抑制のサポートを通知し、
ゲストが SPIV レジスタで EOI ブロードキャスト抑制ビットを設定したときに
LAPIC の EOI ブロードキャストを抑制する。
このフラグは分割 IRQCHIP を使用している場合にのみサポートされる。

KVM_X2APIC_DISABLE_SUPPRESS_EOI_BROADCAST を設定すると、
EOI ブロードキャストの抑制のサポートが完全に無効化される。
すなわち、KVM にゲストへのサポートの通知を行わないよう指示する。

現代の VMM は KVM_X2APIC_ENABLE_SUPPRESS_EOI_BROADCAST または
KVM_X2APIC_DISABLE_SUPPRESS_EOI_BROADCAST のいずれかを
有効化すべきである。
そうしない場合、KVM は従来の奇異な動作をする。
分割 IRQCHIP モードでは、KVM は EOI ブロードキャストの抑制の
サポートを通知するが、実際には EOI ブロードキャストを抑制しない。
カーネル内 IRQCHIP モードでは、KVM は EOI ブロードキャストの抑制の
サポートを通知しない。

KVM_X2APIC_ENABLE_SUPPRESS_EOI_BROADCAST と
KVM_X2APIC_DISABLE_SUPPRESS_EOI_BROADCAST の両方を設定すると
EINVAL エラーで失敗する。
分割 IRCHIP なしで KVM_X2APIC_ENABLE_SUPPRESS_EOI_BROADCAST を
設定した場合も同様である。

7.8 KVM_CAP_S390_USER_INSTR0
----------------------------

:Architectures: s390
:Parameters: なし

このケイパビリティを有効化すると、不正命令 0x0000（2 バイト）が
横取りされ、ユーザ空間へ転送される。
ユーザ空間はこの仕組みを利用して、たとえば 2 バイトの
ソフトウェアブレークポイントを実現できる。
カーネルはこれらの命令に対して操作例外を注入しない。
ユーザ空間がその処理を行う必要がある。

このケイパビリティは、vCPU がすでに作成され実行中であっても
動的に有効化できる。

7.9 KVM_CAP_S390_GS
-------------------

:Architectures: s390
:Parameters: なし
:Returns: 成功時は 0、マシンがガード付きストレージをサポートしていない場合は
          -EINVAL、vCPU がすでに作成されている場合は -EBUSY。

KVM ゲストのガード付きストレージの使用を可能にする。

7.10 KVM_CAP_S390_AIS
---------------------

:Architectures: s390
:Parameters: なし

アダプタ割り込みの抑制の使用を可能にする。
:Returns: 成功時は 0、vCPU がすでに作成されている場合は -EBUSY。

7.11 KVM_CAP_PPC_SMT
--------------------

:Architectures: ppc
:Parameters: vsmt_mode、flags

このケイパビリティを VM で有効化すると、ユーザ空間は所望の仮想 SMT モード
（すなわち仮想コアあたりの仮想 CPU 数）を設定できるようになる。
仮想 SMT モード vsmt_mode は 1 以上 8 以下の 2 の累乗でなければならない。
POWER8 では、vsmt_mode はホストのサブコアあたりのスレッド数以下で
なければならない。
現時点では flags は 0 でなければならない。
このケイパビリティの有効化に成功すると、その後 VM に対して
KVM_CAP_PPC_SMT ケイパビリティを問い合わせたときに vsmt_mode が返される。
このケイパビリティは HV KVM でのみサポートされ、
vCPU が作成される前でのみ設定できる。
KVM_CAP_PPC_SMT_POSSIBLE ケイパビリティは、利用可能な仮想 SMT モードを示す。

7.12 KVM_CAP_PPC_FWNMI
----------------------

:Architectures: ppc
:Parameters: なし

このケイパビリティを有効化すると、ゲストアドレス空間での
マシンチェック例外が、NMI 終了理由で KVM にゲストを終了させる。
これにより QEMU はエラーログを構築し、ゲストカーネルが登録した
マシンチェック処理ルーチンへ分岐できる。
このケイパビリティがない場合、KVM はゲストの 0x200 割り込みベクタへ
分岐する。

7.13 KVM_CAP_X86_DISABLE_EXITS
------------------------------

:Architectures: x86
:Parameters: args[0] は無効化する終了を定義する
:Returns: 成功時は 0、args[0] に無効な終了が含まれる場合、
          または vCPU がすでに作成されている場合は -EINVAL

args[0] で有効なビットは次のとおりである::

  #define KVM_X86_DISABLE_EXITS_MWAIT            (1 << 0)
  #define KVM_X86_DISABLE_EXITS_HLT              (1 << 1)
  #define KVM_X86_DISABLE_EXITS_PAUSE            (1 << 2)
  #define KVM_X86_DISABLE_EXITS_CSTATE           (1 << 3)
  #define KVM_X86_DISABLE_EXITS_APERFMPERF       (1 << 4)

このケイパビリティを VM で有効化すると、ユーザ空間は一部の命令の
横取りを行わなくなり、一部のワークロードでのレイテンシを改善できる。
vCPU を専用の物理 CPU に関連付ける場合に推奨される。
将来さらにビットが追加される可能性がある。
ユーザ空間は KVM_CHECK_EXTENSION の結果を KVM_ENABLE_CAP に渡すだけで、
そうした vmexit をすべて無効化できる。

HLT 終了を無効化する場合は KVM_FEATURE_PV_UNHALT を有効化してはならない。

``IA32_APERF`` と ``IA32_MPERF`` MSR の仮想化には、
APERF/MPERF 終了を無効化するだけでは不十分である。
Intel と AMD の両方がこれらの MSR の厳格な使用条件を文書化しており、
時間間隔（T0 から T1）におけるデルタの比率のみが
アーキテクチャ的に定義されていることを強調しているが、
MSR を単にパススルーするだけでも誤った比率が生じる可能性がある。

この誤った比率は、T0 と T1 の間で次のことが起こると
発生する可能性がある:

1. vCPU スレッドが論理プロセッサ間をマイグレートする。
2. ライブマイグレーションまたはサスペンド/レジューム操作が行われる。
3. 別のタスクが vCPU の論理プロセッサを共有する。
4. C0 より低い C ステートがエミュレートされる（例: HLT 横取りによる）。
5. ゲストの TSC 周波数がホストの TSC 周波数と一致しない。

これらの複雑さのため、KVM はこのパススルー機能をゲストの CPUID ビット
``CPUID.6:ECX.APERFMPERF[bit 0]`` に自動的に関連付けない。
この仕組みが ``IA32_APERF`` と ``IA32_MPERF`` MSR の仮想化に
適切だと判断するユーザ空間の VMM は、
ゲストの CPUID ビットを明示的に設定する必要がある。


7.14 KVM_CAP_S390_HPAGE_1M
--------------------------

:Architectures: s390
:Parameters: なし
:Returns: 成功時は 0、hpage モジュールパラメータが設定されていない場合、
          cmma が有効な場合、または VM に KVM_VM_S390_UCONTROL フラグが
          設定されている場合は -EINVAL

このケイパビリティにより、VM に対して hugetlbfs 経由の 1m ページによる
メモリバッキングの KVM サポートを有効化できる。
ケイパビリティを有効化した後は、cmma を有効化できなくなり、
pfmfi とストレージキーの解釈が無効化される。
cmma がすでに有効な場合、または hpage モジュールパラメータが 1 に
設定されていない場合は、-EINVAL が返される。

このケイパビリティなしでも巨大ページでバッキングされた VM を
一般的に作成できるが、その VM は実行できない。

7.15 KVM_CAP_MSR_PLATFORM_INFO
------------------------------

:Architectures: x86
:Parameters: args[0] は機能を有効化するかどうか

このケイパビリティにより、ゲストは MSR_PLATFORM_INFO MSR を読み取れる。
そうでない場合、ゲストがアクセスしようとすると #GP が発生する。
現時点では、このケイパビリティはゲストに対するこの MSR の
書き込み許可を有効化しない。

7.16 KVM_CAP_PPC_NESTED_HV
--------------------------

:Architectures: ppc
:Parameters: なし
:Returns: 成功時は 0、実装がネスト HV 仮想化をサポートしていない場合は
          -EINVAL。

POWER9 以降のシステム上の HV-KVM では「ネスト HV」仮想化が可能であり、
ゲスト VM が CPU のスーパーバイザモード（特権非ハイパーバイザ状態）を
使用して実行されるゲストを実行する方法を提供する。
このケイパビリティを VM で有効化するには、CPU が必要な機能を
備えていることと、kvm-hv モジュールパラメータでその機能が
有効化されていることが条件となる。

7.17 KVM_CAP_EXCEPTION_PAYLOAD
------------------------------

:Architectures: x86
:Parameters: args[0] は機能を有効化するかどうか

このケイパビリティを有効化すると、L1 が L2 で発生した #PF 例外を
横取りしたとき、エミュレートされた VM エグジットの前に CR2 は
変更されない。
同様に、kvm-intel に限り、L1 が L2 で発生した #DB 例外を横取りしたとき、
エミュレートされた VM エグジットの前に DR6 は変更されない。
その結果、KVM_GET_VCPU_EVENTS が L2 の保留中の #PF（または #DB）例外を
報告するとき、exception.has_payload が設定され、
フォールトアドレス（または新しい DR6 ビット*）が
exception_payload フィールドに報告される。
同様に、ユーザ空間が KVM_SET_VCPU_EVENTS を使用して L2 に #PF（または #DB）を
注入するとき、exception.has_payload を設定し、
フォールトアドレス - または新しい DR6 ビット\ [#]_ - を
exception_payload フィールドに設定することが期待される。

このケイパビリティは構造体 kvm_vcpu_events の exception.pending も
有効化し、ユーザ空間が保留中の例外と注入された例外を
区別できるようにする。


.. [#] 新しい DR6 ビットについて、ビット 16 は #DB 例外が DR6.RTM を
       クリアする場合に限り設定されることに注意されたい。

7.18 KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2
--------------------------------------

:Architectures: x86, arm64, mips
:Parameters: args[0] は機能を有効化するかどうか

有効なフラグは次のとおりである::

  #define KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE   (1 << 0)
  #define KVM_DIRTY_LOG_INITIALLY_SET           (1 << 1)

KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE が設定されている場合、
KVM_GET_DIRTY_LOG はダーティとして返されたすべてのページを
自動的にクリアして書き込み保護しない。
代わりに、ユーザ空間が KVM_CLEAR_DIRTY_LOG を使用して
この操作を別途行う必要がある。

操作がやや複雑になる代わりに、2 つの理由から
スケーラビリティと応答性が向上する。
第一に、KVM_CLEAR_DIRTY_LOG ioctl はメモリスロット全体を同期するのではなく、
64 ページの粒度で動作できる。
これにより、KVM がスピンロックを長時間保持しないことが保証される。
第二に、KVM_GET_DIRTY_LOG の呼び出しとユーザ空間が実際に
ページ内のデータを使用するまでの間に、多大な時間が経過する場合がある。
この間にページが変更される可能性があり、
ゲストとユーザ空間の両方にとって非効率である。
ゲストは書き込み保護フォールトにより高いペナルティを受け、
ユーザ空間はダーティページの誤った報告を目にする可能性がある。
手動の再保護はこの時間を短縮し、ゲストのパフォーマンスを向上させ、
ダーティログの誤検出の数を減らすのに役立つ。

KVM_DIRTY_LOG_INITIALLY_SET が設定されている場合、
ダーティビットマップのすべてのビットが作成時に 1 に初期化される。
これもパフォーマンスを向上させる。
最初の KVM_CLEAR_DIRTY_LOG 呼び出しでダーティログを
小さなチャンクで徐々に有効化できるからである。
KVM_DIRTY_LOG_INITIALLY_SET は KVM_DIRTY_LOG_MANUAL_PROTECT_ENABLE に
依存する（また、現時点では x86、arm64、riscv でのみ利用可能である）。

KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2 は以前
KVM_CAP_MANUAL_DIRTY_LOG_PROTECT という名前で提供されていたが、
実装にバグがあり、正しく使用することが困難または不可能であった。
KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2 が利用可能であることは、
それらのバグが修正されたことを示す。
ユーザ空間は KVM_CAP_MANUAL_DIRTY_LOG_PROTECT を
使用しようとすべきではない。

7.19 KVM_CAP_PPC_SECURE_GUEST
------------------------------

:Architectures: ppc

このケイパビリティは、KVM がウルトラバイザファームウェアを備えた
ホスト上で実行されており、保護ゲストをサポートできることを示す。
そのようなシステムでは、ゲストはウルトラバイザに対して、
自分自身を保護ゲストにするよう要求できる。
保護ゲストのメモリは、明示的にホストと共有するよう要求された
ページを除いて、ホストからアクセスできない。
ゲストが保護ゲストになることを要求すると、
ウルトラバイザは KVM に通知し、KVM はその移行を拒否する機会を得る。

このケイパビリティが存在する場合、VM に対して有効化できる。
これは KVM が保護ゲストモードへの移行を許可することを意味する。
そうでない場合、KVM は移行を拒否する。

7.20 KVM_CAP_HALT_POLL
----------------------

:Architectures: all
:Target: VM
:Parameters: args[0] はナノ秒単位の最大ポーリング時間
:Returns: 成功時は 0、エラー時は -1

KVM_CAP_HALT_POLL は kvm.halt_poll_ns モジュールパラメータを上書きし、
対象 VM のすべての vCPU の最大ハルトポーリング時間を設定する。
このケイパビリティはいつでも何回でも呼び出すことができ、
最大ハルトポーリング時間を動的に変更できる。

ハルトポーリングの詳細については
Documentation/virt/kvm/halt-polling.rst を参照されたい。

7.21 KVM_CAP_X86_USER_SPACE_MSR
-------------------------------

:Architectures: x86
:Target: VM
:Parameters: args[0] は報告する KVM_MSR_EXIT_REASON_* イベントの
             マスクを含む
:Returns: 成功時は 0、エラー時は -1

このケイパビリティにより、ユーザ空間は MSR へのアクセスが拒否された場合に
RDMSR および WRMSR 命令を横取りできる。
デフォルトでは、KVM は拒否されたアクセスに #GP を注入する。

ゲストが MSR の読み取りまたは書き込みを要求したとき、
KVM はそれぞれのシステムに関連するすべての MSR を
実装していない場合がある。
また、CPU タイプによる区別も行わない。

MSR 処理をより細かく制御できるようにするため、
ユーザ空間はこのケイパビリティを有効化できる。
有効化すると、args[0] で指定されたマスクに一致し、
ゲスト内で #GP を発生させる MSR アクセスは、
代わりに KVM_EXIT_X86_RDMSR および KVM_EXIT_X86_WRMSR 終了通知を
発生させる。
ユーザ空間はその後、モデル固有の MSR 処理を実装したり、
MSR が KVM によってエミュレート/仮想化されなかったことを
ユーザに通知したりできる。

有効なマスクフラグは次のとおりである:

============================ ==================================================
 KVM_MSR_EXIT_REASON_UNKNOWN KVM にとって未知の MSR へのアクセスを横取りする
 KVM_MSR_EXIT_REASON_INVAL   vCPU モデルおよび/またはモードに従ってアーキテクチャ的に
                             無効なアクセスを横取りする
 KVM_MSR_EXIT_REASON_FILTER  ユーザ空間が KVM_X86_SET_MSR_FILTER を介して拒否した
                             アクセスを横取りする
============================ ==================================================

7.22 KVM_CAP_X86_BUS_LOCK_EXIT
-------------------------------

:Architectures: x86
:Target: VM
:Parameters: args[0] はゲストでバスロックが検出されたときに
             使用するポリシーを定義する
:Returns: 成功時は 0、args[0] に無効なビットが含まれる場合は -EINVAL

args[0] で有効なビットは次のとおりである::

  #define KVM_BUS_LOCK_DETECTION_OFF      (1 << 0)
  #define KVM_BUS_LOCK_DETECTION_EXIT     (1 << 1)

このケイパビリティを VM で有効化すると、ユーザ空間は
ゲストで検出されたバスロックを処理するポリシーを選択できる。
ユーザ空間は KVM_CHECK_EXTENSION の結果から
サポートされるモードを取得し、KVM_ENABLE_CAP を介して定義できる。
サポートされるモードは相互に排他的である。

このケイパビリティにより、ユーザ空間はホストが分割ロック検出
（KVM が横取りする #AC 例外を発生させる）を有効化しているかどうかに
関係なく、ゲストで検出されたバスロックに対して VM エグジットを
強制できる。
このケイパビリティは、悪意のある/バグのあるゲストがバスロックを
悪用してシステム全体のパフォーマンスを低下させる攻撃を
軽減することを目的としている。

KVM_BUS_LOCK_DETECTION_OFF が設定されている場合、
KVM はゲストのバスロックを VM エグジットに強制しないが、
ホストカーネルの分割ロック #AC 検出は有効な場合は
依然として適用される。

KVM_BUS_LOCK_DETECTION_EXIT が設定されている場合、
KVM はゲストのバスロックが VM エグジットを発生させることを保証する
CPU 機能を有効化し、そのようなすべての VM エグジットで
ユーザ空間へ終了する。
たとえば、ユーザ空間が問題のあるゲストをスロットルしたり、
その他のポリシーベースの軽減策を適用したりできるようにするためである。
ユーザ空間へ終了するとき、KVM は vcpu-run->flags に
KVM_RUN_X86_BUS_LOCK を設定し、条件付きで exit_reason を
KVM_EXIT_X86_BUS_LOCK に設定する。

基盤となるハードウェア実装の違いにより、
終了時の vCPU の RIP は Intel と AMD で異なる。
Intel ホストでは、RIP は次の命令を指す。
すなわち、終了はトラップに似ている。
AMD ホストでは、RIP は問題のある命令を指す。
すなわち、終了はフォールトに似ている。

注意！検出されたバスロックは、ユーザ空間への他の終了と
同時に発生する可能性がある。
すなわち、ユーザ空間が検出されたすべてのバスロックに対して
アクションを実行したい場合は、プライマリ終了理由に関係なく
KVM_RUN_X86_BUS_LOCK をチェックすべきである。

7.23 KVM_CAP_PPC_DAWR1
----------------------

:Architectures: ppc
:Parameters: なし
:Returns: 成功時は 0、CPU が第 2 DAWR をサポートしていない場合は -EINVAL

このケイパビリティは、POWER10 プロセッサが提供する
第 2 DAWR 機能を確認/有効化するために使用できる。


7.24 KVM_CAP_VM_COPY_ENC_CONTEXT_FROM
-------------------------------------

:Architectures: x86 SEV 有効
:Type: vm
:Parameters: args[0] はソース VM の fd
:Returns: 成功時は 0、エラー時は ENOTTY

このケイパビリティにより、ユーザ空間は fd で示される VM から、
呼び出し対象の VM へ暗号化コンテキストをコピーできる。

これは、ホストによってスケジュールされるゲスト内ワークロードを
サポートすることを目的としている。
これにより、ゲスト内ワークロードは独自の NPT を維持でき、
2 つの VM が割り込みなど（別々の APIC/MSR など）で
互いを誤って上書きするのを防ぐ。

7.25 KVM_CAP_SGX_ATTRIBUTE
--------------------------

:Architectures: x86
:Target: VM
:Parameters: args[0] は securityfs 内の SGX 属性ファイルの
             ファイルハンドル
:Returns: 成功時は 0、ファイルハンドルが無効な場合、
          または要求された属性が KVM でサポートされていない場合は -EINVAL。

KVM_CAP_SGX_ATTRIBUTE により、ユーザ空間の VMM は VM に
1 つ以上の特権エンクレーブ属性へのアクセスを許可できる。
args[0] は、KVM によってサポート/制限されている属性
（現在は PROVISIONKEY のみ）に対応する有効な SGX 属性ファイルへの
ファイルハンドルを保持していなければならない。

SGX サブシステムは、侵害されていないカーネルに追加のセキュリティを
提供するため、エンクレーブ属性のサブセットへのアクセスを制限している。
たとえば、PROVISIONKEY の使用は、マルウェアが PROVISIONKEY を使用して
安定したシステムフィンガープリントを取得するのを阻止するために
制限されている。
ユーザ空間が VM でエンクレーブを実行してそのような制限を
回避するのを防ぐため、KVM はデフォルトで特権属性へのアクセスを
禁止する。

詳細は Documentation/arch/x86/sgx.rst を参照されたい。

7.27 KVM_CAP_EXIT_ON_EMULATION_FAILURE
--------------------------------------

:Architectures: x86
:Parameters: args[0] この機能を有効にするかどうか

このケイパビリティを有効にすると、エミュレーションの失敗は、ユーザ空間への
KVM_INTERNAL_ERROR による終了を引き起こす（ただし、VMware バックドア命令を
処理するためにエミュレータが呼び出された場合は除く）。さらに KVM は、
エミュレーションの失敗によるユーザ空間への終了に対して、最大 15 バイトの命令
バイトを提供するようになる。これらのユーザ空間への終了が起きたときは、internal
構造体ではなく emulation_failure 構造体を使う。両者は同じレイアウトだが、
emulation_failure 構造体のほうが内容によく合っている。また、構造体のうち
どのフィールドが有効かを表す 'flags' フィールドが明示的に定義されている
（すなわち、'flags' フィールドに
KVM_INTERNAL_ERROR_EMULATION_FLAG_INSTRUCTION_BYTES が設定されていれば、
'insn_size' と 'insn_bytes' のどちらにも有効なデータが入っている）。

7.28 KVM_CAP_ARM_MTE
--------------------

:Architectures: arm64
:Parameters: なし

このケイパビリティは、KVM（およびハードウェア）が Memory Tagging Extensions
(MTE) をゲストに公開することを示す。ゲストにアクセスを許可するには、VCPU を
作成する前に VMM 側でも有効にしなければならない。MTE は AArch64 モードで
動作するゲストに対してのみ利用でき、このケイパビリティを有効にすると AArch32
VCPU の作成が失敗する。

有効にすると、ゲストはゲストに与えられた任意のメモリに付随するタグに
アクセスできる。KVM はホストのスワップやハイバネーションのあいだもタグが
保持されることを保証する。ただし VM をマイグレーションする場合は、VMM が
必要に応じてタグを手動で保存／復元する必要がある。

このケイパビリティを有効にすると、メモリスロット内のすべてのメモリは
``MAP_ANONYMOUS`` として、または RAM ベースのファイルマッピング（``tmpfs``、
``memfd``）でマップされなければならない。無効な mmap でメモリスロットを
作成しようとすると -EINVAL が返る。

``guest_memfd`` は匿名ファイルではあるが、MTE ではサポートされない。MTE
ケイパビリティが有効なときに ``guest_memfd`` をバッキングとするメモリスロットを
作成しようとした場合、あるいは ``guest_memfd`` ベースのメモリスロットを
作成したあとに MTE ケイパビリティを有効にしようとした場合、-EINVAL が返る。

有効にすると、VMM は ``KVM_ARM_MTE_COPY_TAGS`` ioctl を使って、ゲストとの
あいだでタグを一括コピーできる。

7.29 KVM_CAP_VM_MOVE_ENC_CONTEXT_FROM
-------------------------------------

:Architectures: x86 SEV enabled
:Type: vm
:Parameters: args[0] 移行元 vm の fd
:Returns: 成功時は 0

このケイパビリティを使うと、ユーザ空間は fd で示される VM から、呼び出し先の
VM へ暗号化コンテキストをマイグレーションできる。

これは、ホスト内でユーザ空間 VMM 間を VM がマイグレーションする、つまりゲストを
中断せずに VMM プロセスを更新することを支えることを目的とする。

7.31 KVM_CAP_DISABLE_QUIRKS2
----------------------------

:Parameters: args[0] - 無効にする KVM のクワークの集合
:Architectures: x86
:Type: vm

このケイパビリティを有効にすると、KVM は一部の挙動のクワークを無効にする。

このケイパビリティに対して KVM_CHECK_EXTENSION を呼ぶと、KVM で無効にできる
クワークのビットマスクが返る。

このケイパビリティに対する KVM_ENABLE_CAP の引数は、無効にするクワークの
ビットマスクであり、KVM_CHECK_EXTENSION が返すビットマスクの部分集合で
なければならない。

cap.args[0] で有効なビットは次のとおり:

.. list-table::
   :widths: 40 60

   * - KVM_X86_QUIRK_LINT0_REENABLED
     - 既定では、LVT LINT0 レジスタのリセット値は 0x700
       (APIC_MODE_EXTINT) である。このクワークを無効にすると、リセット値は
       0x10000 (APIC_LVT_MASKED) になる。

   * - KVM_X86_QUIRK_CD_NW_CLEARED
     - 既定では、KVM は AMD CPU 上で CR0.CD と CR0.NW をクリアする。これは
       CR0.CD のまま、つまりキャッシュを "no fill" モードにしたまま動き続ける
       不具合のあるゲストファームウェアを回避するためである。

       このクワークを無効にすると、KVM は CR0.CD と CR0.NW の値を変更しない。

   * - KVM_X86_QUIRK_LAPIC_MMIO_HOLE
     - 既定では、x2APIC モードに設定されていても MMIO LAPIC インターフェースが
       利用できる。このクワークを無効にすると、LAPIC が x2APIC モードのとき
       KVM は MMIO LAPIC インターフェースを無効にする。

   * - KVM_X86_QUIRK_OUT_7E_INC_RIP
     - 既定では、ポート 0x7e への OUT 命令でユーザ空間へ終了する前に、KVM は
       %rip を事前インクリメントする。このクワークを無効にすると、KVM は
       ユーザ空間へ終了する前に %rip を事前インクリメントしない。

   * - KVM_X86_QUIRK_MISC_ENABLE_NO_MWAIT
     - このクワークを無効にすると、IA32_MISC_ENABLE[bit 18] (MWAIT) が
       設定されていれば KVM は CPUID.01H:ECX[bit 3] (MONITOR/MWAIT) を
       設定する。また、このクワークを無効にすると、IA32_MISC_ENABLE[bit 18]
       がクリアされていれば KVM は CPUID.01H:ECX[bit 3] をクリアする。

   * - KVM_X86_QUIRK_FIX_HYPERCALL_INSN
     - 既定では、KVM はゲストの VMMCALL/VMCALL 命令を、そのシステムの
       ベンダーのハイパーコール命令に合うように書き換える。このクワークを
       無効にすると、KVM は無効なゲストハイパーコール命令を書き換えなくなる。
       不正なハイパーコール命令を実行すると、ゲスト内で #UD が発生する。

   * - KVM_X86_QUIRK_MWAIT_NEVER_UD_FAULTS
     - 既定では、KVM は MONITOR/MWAIT を（インターセプトされるなら）ゲスト
       CPUID で MONITOR/MWAIT がサポートされているかどうかによらず NOP として
       エミュレートする。このクワークを無効にし、かつ
       KVM_X86_DISABLE_EXITS_MWAIT が設定されていない（MONITOR/MWAIT が
       インターセプトされる）場合、ゲスト CPUID でサポートされていなければ
       KVM は MONITOR/MWAIT に対して #UD を注入する。なお、
       KVM_X86_QUIRK_MISC_ENABLE_NO_MWAIT が無効なときは、MISC_ENABLE への
       書き込み時に KVM はゲスト CPUID の MONITOR/MWAIT サポートを変更する。

   * - KVM_X86_QUIRK_SLOT_ZAP_ALL
     - 既定では、KVM_X86_DEFAULT_VM の VM について、KVM はメモリスロットの
       削除や移動のときに、すべてのメモリスロットとアドレス空間にあるすべての
       SPTE を無効化する。このクワークを無効にした場合（または VM タイプが
       KVM_X86_DEFAULT_VM でない場合）、KVM は削除または移動したメモリスロットの
       バッキングメモリに到達できないことだけを保証する。つまり KVM は、その
       メモリスロットに関係する SPTE だけを無効化_してもよい_。

   * - KVM_X86_QUIRK_STUFF_FEATURE_MSRS
     - 既定では、vCPU の作成時に、KVM はその vCPU の
       MSR_IA32_PERF_CAPABILITIES (0x345)、MSR_IA32_ARCH_CAPABILITIES (0x10a)、
       MSR_PLATFORM_INFO (0xce)、およびすべての VMX MSR (0x480..0x492) を、
       KVM がサポートする最大の機能に設定する。また KVM は
       MSR_IA32_UCODE_REV (0x8b) を任意の値（Intel と AMD で異なる）に設定する。
       最後に、（ユーザ空間によって）ゲスト CPUID が設定されると、KVM は
       選んだ VMX MSR のフィールドを変更し、ゲスト CPUID と L2 の有効な ISA の
       あいだの一貫性を強制する。このクワークを無効にすると、KVM は vCPU の
       MSR 値をゼロにする（2 つの例外については後述）。つまり、機能 MSR を
       CPUID リーフのように扱い、vCPU モデルの定義を完全にユーザ空間の管理下に
       置く。このクワークは VMX MSR の CR0/CR4_FIXED1 (0x487 と 0x489) には
       影響しない。KVM が現在それらをユーザ空間から設定できるようにしている
       ためである（KVM は安全性のため、ゲスト CPUID に基づいてそれらを設定する）。

   * - KVM_X86_QUIRK_IGNORE_GUEST_PAT
     - 既定では、Intel プラットフォーム上で KVM はゲスト PAT を無視し、EPT の
       実効メモリタイプを WB に強制する。このクワークは、ゲスト PAT を安全に
       尊重できない Intel プラットフォームでは利用できない（すなわち、CPU
       self-snoop がなければ、KVM は常にゲスト PAT を無視し、実効メモリタイプを
       WB に強制する）。また、AMD プラットフォームでは、あるいは Intel で
       一貫性のない DMA デバイスが VM に割り当てられている場合は無視される。
       そのような場合、KVM は常にゲスト PAT を尊重する。このクワークは、特定の
       Intel Xeon プラットフォーム（例: ICX、SPR）での速度低下を避けるために
       必要である。これらのプラットフォームでは self-snoop 機能はサポートされて
       いるものの UC が遅く、ビデオ RAM のマップに WC ではなく UC を使う古い
       ゲストで問題が起きる。ユーザ空間は、そのようなゲストソフトウェアが
       ないと分かっている場合、たとえば bochs グラフィックスデバイスを公開
       していない場合に、このクワークを無効にしてゲスト PAT を尊重できる
       （このドライバには不具合があったことが知られている）。

   * - KVM_X86_QUIRK_VMCS12_ALLOW_FREEZE_IN_SMM
     - 既定では、KVM は vmcs12 の GUEST_IA32_DEBUGCTL に対する一貫性チェックを
       緩め、FREEZE_IN_SMM を設定できるようにする。このクワークを無効にすると、
       KVM はこのビットがクリアされていることを要求する。なお、クワークの設定に
       かかわらず、vmcs02 のこのビットは依然として完全にホストが制御する。

   * - KVM_X86_QUIRK_NESTED_SVM_SHARED_PAT
     - 既定では、ネスト SVM ゲスト向けの KVM は IA32_PAT MSR を L1 と L2 で
       共有する。これは従来の挙動であり、AMD のアーキテクチャ仕様に一致しない。
       このクワークを無効にし、かつ L2 でネストページング (NPT) が有効な場合、
       KVM は VMCB の g_pat フィールドを使って L2 専用のゲスト PAT レジスタを
       正しく仮想化する。L2 で NPT が無効な場合は、クワークの設定にかかわらず
       L1 と L2 は IA32_PAT MSR を共有し続ける。

7.32 KVM_CAP_MAX_VCPU_ID
------------------------

:Architectures: x86
:Target: VM
:Parameters: args[0] - 現在の VM に設定する APIC ID の最大値
:Returns: 成功時は 0、args[0] が KVM でサポートされる KVM_MAX_VCPU_IDS を
          超えている場合、またはすでに設定されている場合は -EINVAL

このケイパビリティを使うと、ユーザ空間は vCPU の作成前に、現在の VM セッションに
割り当てる APIC ID の最大値を指定できる。これにより、APIC ID で添字付けされる
データ構造のメモリを節約できる。ユーザ空間は、決めた CPU トポロジから APIC ID
の上限を計算できる。

値は、KVM_ENABLE_CAP に 0 以外の値を設定するまで、または vCPU が作成される
までしか変更できない。最初の vCPU を作成するとき、値が 0 のままか
KVM_ENABLE_CAP が呼ばれていなければ、KVM は
KVM_CHECK_EXTENSION(KVM_CAP_MAX_VCPU_ID) の戻り値を最大 APIC ID として使う。

7.33 KVM_CAP_X86_NOTIFY_VMEXIT
------------------------------

:Architectures: x86
:Target: VM
:Parameters: args[0] は notify window の値といくつかのフラグ
:Returns: 成功時は 0、args[0] に無効なフラグが含まれる場合、または
          notify VM exit がサポートされない場合は -EINVAL

args[0] のビット 63:32 は notify window に使う。args[0] のビット 31:0 は
いくつかのフラグに使う。有効なビットは次のとおり::

  #define KVM_X86_NOTIFY_VMEXIT_ENABLED    (1 << 0)
  #define KVM_X86_NOTIFY_VMEXIT_USER       (1 << 1)

このケイパビリティを使うと、ユーザ空間は VM 作成時に VM 単位で notify VM exit
のオン／オフを設定できる。notify VM exit は既定で無効である。ユーザ空間が
args[0] に KVM_X86_NOTIFY_VMEXIT_ENABLED ビットを設定すると、VMM は指定された
notify window 付きでこの機能を有効にする。これは、VM が非 root モードのときに
指定された時間（notify window）のあいだイベントウィンドウが発生しないと、
VM エグジットを発生させる。

args[0] に KVM_X86_NOTIFY_VMEXIT_USER が設定されていると、notify VM exit が
起きたときに KVM は処理のためにユーザ空間へ終了する。

このケイパビリティは、悪意のある VM が（イベントウィンドウが開かないために）
CPU をスタックさせ、ホストや他の VM がその CPU を使えなくする、という脅威を
緩和することを狙っている。

7.35 KVM_CAP_X86_APIC_BUS_CYCLES_NS
-----------------------------------

:Architectures: x86
:Target: VM
:Parameters: args[0] は望む APIC バスクロックレート（ナノ秒単位）
:Returns: 成功時は 0、args[0] に周波数として無効な値が入っている場合、または
          すでに vCPU が作成されている場合は -EINVAL、
          KVM_CREATE_IRQCHIP で仮想ローカル APIC が作成されていない場合は -ENXIO

このケイパビリティは VM の APIC バスクロック周波数を設定する。KVM のカーネル内
仮想 APIC が APIC タイマーをエミュレートするときに使う。KVM の既定値は
KVM_CHECK_EXTENSION で取得できる。

備考: 0 以外の CPUID 0x15 をゲストに公開する場合、ユーザ空間が CPUID 0x15
（コアクリスタルクロック周波数）を正しく設定する責任を負う。

7.36 KVM_CAP_DIRTY_LOG_RING/KVM_CAP_DIRTY_LOG_RING_ACQ_REL
----------------------------------------------------------

:Architectures: x86, arm64, riscv
:Type: vm
:Parameters: args[0] - ダーティログリングのサイズ

KVM はユーザ空間に mmap されるリングバッファを使ってダーティメモリを追跡できる。
ダーティリングは vCPU ごとに 1 つある。

ダーティリングは ``struct kvm_dirty_gfn`` の配列としてユーザ空間から利用できる。
各ダーティエントリは次のように定義される::

  struct kvm_dirty_gfn {
          __u32 flags;
          __u32 slot; /* as_id | slot_id */
          __u64 offset;
  };

flags フィールドには、エントリの現在の状態を表す次の値が定義されている::

  #define KVM_DIRTY_GFN_F_DIRTY           BIT(0)
  #define KVM_DIRTY_GFN_F_RESET           BIT(1)
  #define KVM_DIRTY_GFN_F_MASK            0x3

ユーザ空間は、KVM_CREATE_VM ioctl の直後に KVM_ENABLE_CAP ioctl を呼び、
新しいゲストに対してこのケイパビリティを有効にしてリングのサイズを設定する。
ケイパビリティを有効にできるのは vCPU を作成する前だけで、リングのサイズは
2 のべき乗でなければならない。リングバッファが大きいほど、リングが満杯になって
VM がユーザ空間へ強制終了される可能性が低くなる。最適なサイズはワークロードに
よるが、少なくとも 64 KiB（4096 エントリ）を推奨する。

ダーティページビットマップと同じように、バッファは KVM_SET_USER_MEMORY_REGION
で KVM_MEM_LOG_DIRTY_PAGES フラグを設定したすべてのユーザメモリ領域への
書き込みを追跡する。フラグを設定してメモリ領域を登録すると、ユーザ空間は
リングバッファからダーティページの回収を始められる。

リングバッファのエントリは、未使用（フラグビット ``00``）、ダーティ（フラグ
ビット ``01``）、回収済み（フラグビット ``1X``）のいずれかになる。エントリの
状態遷移は次のとおり::

          dirtied         harvested        reset
     00 -----------> 01 -------------> 1X -------+
      ^                                          |
      |                                          |
      +------------------------------------------+

ダーティページを回収するには、ユーザ空間は mmap したリングバッファにアクセスして
ダーティな GFN を読み取る。フラグに DIRTY ビットが設定されていれば（この段階では
RESET ビットはクリアされていなければならない）、その GFN はダーティな GFN で
ある。ユーザ空間はその GFN を回収し、フラグを状態 ``01b`` から ``1Xb`` に変更
する（ビット 0 は KVM には無視されるが、ビット 1 はこの GFN が回収済みでリセット
待ちであることを示すために設定しなければならない）。そして次の GFN に進む。
GFN のフラグの DIRTY ビットがクリアになるまで、つまり回収可能だったダーティ
GFN をすべて回収し終えるまで、これを続ける。

弱い順序付けのアーキテクチャでは、ユーザ空間によるリングバッファへのアクセス
（より正確には 'flags' フィールド）は順序付けされなければならない。利用可能なら
load-acquire/store-release アクセサを使うか、この順序を保証するほかのメモリ
バリアを使う。

ユーザ空間がダーティ GFN のすべてを一度に回収する必要はない。ただしダーティ
GFN は順番に集めなければならない。つまり、あるダーティ GFN を飛ばして隣の
ものを集めることはできない。

リングバッファの 1 つ以上のエントリを処理したあと、ユーザ空間は VM ioctl の
KVM_RESET_DIRTY_RINGS を呼んでカーネルに通知し、カーネルが回収済みの GFN を
再び保護するようにする。そのためこの ioctl は、ダーティページの内容を読む
*前に*呼ばなければならない。

ダーティリングは満杯になりうる。そうなると vCPU の KVM_RUN は、終了理由
KVM_EXIT_DIRTY_RING_FULL で戻る。

ダーティリングインターフェースは KVM_GET_DIRTY_LOG インターフェースと大きく
異なる点がある。ユーザ空間がダーティリングを読むとき、カーネルがまだ
プロセッサのダーティページバッファをカーネルバッファにフラッシュしていない
可能性がある（ダーティビットマップの場合、フラッシュは KVM_GET_DIRTY_LOG
ioctl が行う）。それを確実にするには、シグナルを使って vCPU を KVM_RUN から
追い出す必要がある。その結果生じる vmexit により、すべてのダーティ GFN が
ダーティリングへフラッシュされることが保証される。

備考: KVM_CAP_DIRTY_LOG_RING_ACQ_REL は、弱い順序付けのアーキテクチャが公開
すべき唯一のケイパビリティである。これは、エントリの状態を読んで DIRTY から
HARVESTED へ変更するときにユーザ空間に課される追加のメモリ順序付けの要件を
示すためである。TSO のような順序付けを持つアーキテクチャ（x86 など）は、
KVM_CAP_DIRTY_LOG_RING と KVM_CAP_DIRTY_LOG_RING_ACQ_REL の両方をユーザ空間に
公開してよい。

ダーティリングを有効にしたあと、ユーザ空間は
KVM_CAP_DIRTY_LOG_RING_WITH_BITMAP のケイパビリティを検出し、リング構造を
スロット単位のビットマップでバッキングできるかどうかを調べる必要がある。この
ケイパビリティが公開されていれば、そのアーキテクチャは vCPU／リングの
コンテキストなしでゲストページをダーティにできる。そのため一部のダーティ情報は
ビットマップ構造にも保持される。KVM_CAP_DIRTY_LOG_RING_WITH_BITMAP は、
KVM_CAP_DIRTY_LOG_RING_ACQ_REL のケイパビリティが有効になっていない場合、または
既存のメモリスロットがある場合は有効にできない。

ここでのビットマップはリング構造のバックアップにすぎないことに注意。リングと
ビットマップの組み合わせが役立つのは、vCPU／リングのコンテキスト外でダーティに
なるメモリがごくわずかな場合だけである。そうでなければ、独立したスロット単位の
ビットマップの仕組みを検討する必要がある。

バックアップビットマップのダーティビットを集めるには、ユーザ空間は同じ
KVM_GET_DIRTY_LOG ioctl を使える。ダーティビットの生成がすべて 1 回のパスで
行われる限り、KVM_CLEAR_DIRTY_LOG は不要である。ダーティビットマップの回収は、
VMM が状態を完了とみなす前に最後に行うべき処理である。VMM はダーティ状態が
最終であることを保証し、ビットマップの回収より後に順序付けられた別の ioctl
によるダーティページを取りこぼさないようにする必要がある。

備考: バックアップビットマップの使用例をいくつか挙げる。(1) KVM デバイス
"kvm-arm-vgic-its" でコマンド KVM_DEV_ARM_{VGIC_GRP_CTRL, ITS_SAVE_TABLES}
により vgic/its テーブルを保存する。(2) KVM デバイス "kvm-arm-vgic-its" で
コマンド KVM_DEV_ARM_{VGIC_GRP_CTRL, ITS_RESTORE_TABLES} により vgic/its
テーブルを復元する。VGICv3 LPI の保留状態が復元される。(3) KVM デバイス
"kvm-arm-vgic-v3" でコマンド
KVM_DEV_ARM_VGIC_{GRP_CTRL, SAVE_PENDING_TABLES} により vgic3 の保留テーブルを
保存する。

7.37 KVM_CAP_PMU_CAPABILITY
---------------------------

:Architectures: x86
:Type: vm
:Parameters: arg[0] は PMU 仮想化ケイパビリティのビットマスク
:Returns: 成功時は 0、arg[0] に無効なビットが含まれる場合は -EINVAL

このケイパビリティは KVM の PMU 仮想化を変更する。

このケイパビリティに対して KVM_CHECK_EXTENSION を呼ぶと、VM で調整できる PMU
仮想化ケイパビリティのビットマスクが返る。

KVM_ENABLE_CAP の引数もビットマスクであり、VM に適用する PMU 仮想化
ケイパビリティを選択する。これは VCPU の作成前の VM に対してのみ呼び出せる。

現時点で KVM_PMU_CAP_DISABLE が唯一のケイパビリティである。これを設定すると
その VM の PMU 仮想化が無効になる。ユーザモードは、PMU が無効であることを
反映するように CPUID リーフ 0xA を調整すべきである。

7.38 KVM_CAP_VM_DISABLE_NX_HUGE_PAGES
-------------------------------------

:Architectures: x86
:Type: vm
:Parameters: arg[0] は 0 でなければならない
:Returns: 成功時は 0、ユーザ空間プロセスが CAP_SYS_BOOT を持たない場合は
          -EPERM、args[0] が 0 でない場合、または vCPU が作成されている場合は
          -EINVAL

このケイパビリティは、iTLB MULTIHIT に対する NX ヒュージページの緩和を無効に
する。

nx_huge_pages モジュールパラメータが設定されていない場合、このケイパビリティは
効果がない。

このケイパビリティは、vCPU を作成する前にのみ設定できる。

7.39 KVM_CAP_ARM_EAGER_SPLIT_CHUNK_SIZE
---------------------------------------

:Architectures: arm64
:Type: vm
:Parameters: arg[0] は新しい分割チャンクサイズ
:Returns: 成功時は 0、すでにメモリスロットが作成されている場合は -EINVAL

このケイパビリティは、Eager Page Splitting で使うチャンクサイズを設定する。

Eager Page Splitting は、ゲストメモリがヒュージページでバッキングされている
ときのダーティログ（ライブマイグレーションで使う）の性能を向上させる。これは、
（メモリ領域の KVM_MEM_LOG_DIRTY_PAGES フラグで）ダーティログを有効にしたとき、
または KVM_CLEAR_DIRTY_LOG を使ったときに、ヒュージページの分割（PAGE_SIZE
ページへの分割）をフォールト時にではなく先回りして行うことで、フォールト時の
分割を避ける。

チャンクサイズは、一度に何ページを分割するかを指定し、チャンクごとに 1 回の
アロケーションを使う。チャンクサイズが大きいほど、事前に確保するページが
増える。

チャンクサイズは有効なブロックサイズでなければならない。受け付けられるブロック
サイズの一覧は KVM_CAP_ARM_SUPPORTED_BLOCK_SIZES に 64 ビットのビットマップ
として公開される（各ビットが 1 つのブロックサイズを表す）。既定値は 0 で、
eager page splitting が無効になる。

7.40 KVM_CAP_EXIT_HYPERCALL
---------------------------

:Architectures: x86
:Type: vm

このケイパビリティを有効にすると、KVM は一部のハイパーコールを処理するために、
終了理由 KVM_EXIT_HYPERCALL でユーザ空間へ終了する。ユーザ空間は hypercall.ret
を EINVAL に設定してハイパーコールを失敗させることも、hypercall.ret を EAGAIN
に設定して次にゲストが実行するときにハイパーコールを再試行させることもできる。

このケイパビリティに対して KVM_CHECK_EXTENSION を呼ぶと、ユーザ空間へ終了する
ように設定できるハイパーコールのビットマスクが返る。現時点でそのような
ハイパーコールは KVM_HC_MAP_GPA_RANGE だけである。

KVM_ENABLE_CAP の引数もビットマスクであり、KVM_CHECK_EXTENSION の結果の部分
集合でなければならない。KVM は、引数で対応するビットが立っているハイパーコール
をユーザ空間へ転送し、それ以外には ENOSYS を返す。

7.41 KVM_CAP_ARM_SYSTEM_SUSPEND
-------------------------------

:Architectures: arm64
:Type: vm

有効にすると、KVM はゲストのサスペンド要求を処理するために、タイプ
KVM_SYSTEM_EVENT_SUSPEND の KVM_EXIT_SYSTEM_EVENT でユーザ空間へ終了する。

7.42 KVM_CAP_ARM_WRITABLE_IMP_ID_REGS
-------------------------------------

:Architectures: arm64
:Target: VM
:Parameters: なし
:Returns: 成功時は 0、このケイパビリティを有効にする前に vCPU が作成されている
          場合は -EINVAL

このケイパビリティは、Arm アーキテクチャの PE 実装を識別するレジスタの挙動を
変更する。対象は MIDR_EL1、REVIDR_EL1、AIDR_EL1 である。既定では、これらの
レジスタはユーザ空間から参照できるが、不変として扱われる。

このケイパビリティを有効にすると、KVM は最初の KVM_RUN より前に、ユーザ空間が
これらのレジスタを変更することを許可する。これらのレジスタは VM スコープであり、
ある VM のすべての vCPU で同じ値の組が提示される。

7.43 KVM_CAP_RISCV_MP_STATE_RESET
---------------------------------

:Architectures: riscv
:Type: VM
:Parameters: なし
:Returns: 成功時は 0、arg[0] が 0 でない場合は -EINVAL

このケイパビリティを有効にすると、IOCTL を通じて MP_STATE_INIT_RECEIVED を設定
するときに、KVM は VCPU をリセットする。元の MP_STATE は保持される。

7.44 KVM_CAP_ARM_CACHEABLE_PFNMAP_SUPPORTED
-------------------------------------------

:Architectures: arm64
:Target: VM
:Parameters: なし

このケイパビリティは、PFNMAP のメモリ領域をキャッシュ可能として安全にマップ
できるかどうかをユーザ空間に示す。これはハードウェアの force write back (FWB)
機能のサポートに依存する。

7.45 KVM_CAP_ARM_SEA_TO_USER
----------------------------

:Architecture: arm64
:Target: VM
:Parameters: なし
:Returns: 成功時は 0、サポートされない場合は -EINVAL

このケイパビリティを有効にすると、ゲストのアクセスによって EL2 にトラップされた
SEA について、KVM がユーザ空間へ終了することがある。詳しくは
``KVM_EXIT_ARM_SEA`` を参照。

7.46 KVM_CAP_S390_USER_OPEREXEC
-------------------------------

:Architectures: s390
:Parameters: なし

このケイパビリティを有効にすると、KVM は自身で処理しないすべての操作例外を
ユーザ空間へ転送する。これには KVM_CAP_S390_USER_INSTR0 が扱う 0x0000 命令も
含まれる。これは、ハードウェアで（まだ）実装されていない命令をユーザ空間が
エミュレートしたい場合に役立つ。

このケイパビリティは、VCPU がすでに作成されて実行中であっても動的に有効に
できる。

7.47 KVM_CAP_S390_HPAGE_2G
--------------------------

:Architectures: s390
:Parameters: なし
:Returns: 成功時は 0。hpage_2g モジュールパラメータが設定されていない場合、
          cmma が有効な場合、または VM に KVM_VM_S390_UCONTROL フラグが
          設定されている場合は -EINVAL。VM に vCPU がすでに作成されている
          場合は -EBUSY。

このケイパビリティを使うと、hugetlbfs を通じた 2g ページでのメモリバッキングに
対する KVM のサポートを VM で有効にできる。ケイパビリティを有効にしたあとは、
cmma を有効にできなくなり、pfmfi とストレージキーの解釈が無効になる。cmma が
すでに有効な場合、または hpage_2g モジュールパラメータが 1 に設定されていない
場合は、-EINVAL が返る。

8. その他のケイパビリティ
==========================

この節では、KVM 実装のその他の機能についての情報を与えるケイパビリティを
列挙する。

8.1 KVM_CAP_PPC_HWRNG
---------------------

:Architectures: ppc

KVM_CHECK_EXTENSION が利用可能と示した場合、このケイパビリティは、
カーネルがハードウェア乱数生成器を利用する H_RANDOM ハイパーコールの実装を
持つことを意味する。存在する場合、カーネルの H_RANDOM ハンドラは
KVM_CAP_PPC_ENABLE_HCALL ケイパビリティでゲストが使えるように有効化できる。

8.3 KVM_CAP_PPC_MMU_RADIX
-------------------------

:Architectures: ppc

KVM_CHECK_EXTENSION が利用可能と示した場合、このケイパビリティは、
カーネルが Power ISA V3.00 で定義された radix MMU(POWER9 プロセッサで
実装されているもの)を使うゲストをサポートできることを意味する。

8.4 KVM_CAP_PPC_MMU_HASH_V3
---------------------------

:Architectures: ppc

KVM_CHECK_EXTENSION が利用可能と示した場合、このケイパビリティは、
カーネルが Power ISA V3.00 で定義されたハッシュページテーブル MMU
(POWER9 プロセッサで実装されているもの)を使うゲストをサポートできることを
意味する。これにはインメモリのセグメントテーブルも含まれる。

8.5 KVM_CAP_MIPS_VZ
-------------------

:Architectures: mips

メインの kvm ハンドルに対する KVM_CHECK_EXTENSION が利用可能と示した場合、
このケイパビリティは、ハードウェアの完全なハードウェア支援仮想化機能を
KVM 経由で利用できることを意味する。これを利用する VM を作成するには、
適切な KVM_VM_MIPS_* タイプを KVM_CREATE_VM に渡さなければならない。

kvm VM ハンドルに対する KVM_CHECK_EXTENSION がこのケイパビリティが利用可能と
示した場合、その VM がハードウェアの完全なハードウェア支援仮想化機能を
使っていることを意味する。これは KVM_VM_MIPS_DEFAULT で VM を作成した後に
確認するのに役立つ。

KVM_CHECK_EXTENSION が返す値は既知の値(下記参照)と比較すべきである。
それ以外の値は予約済みである。これは、MIPS VZ ASE と互換でない可能性のある
別のハードウェア支援仮想化実装の可能性を認めるためである。

==  ==========================================================================
 0  トラップ & エミュレート実装を使い、ゲストコードをユーザモードで実行する。
    ゲストの仮想メモリセグメントは、ゲストがユーザモードのアドレス空間に
    収まるように並べ替えられる。

 1  MIPS VZ ASE が使われ、標準のゲスト仮想メモリセグメントを含む完全な
    ハードウェア支援仮想化を提供する。
==  ==========================================================================

8.7 KVM_CAP_MIPS_64BIT
----------------------

:Architectures: mips

このケイパビリティは、サポートされるゲストのアーキテクチャタイプ、
すなわちサポートされるレジスタ幅とアドレス幅を示す。

kvm VM ハンドルに対する KVM_CHECK_EXTENSION でこのケイパビリティを確認した
ときに返る値は、おおよそ CP0_Config.AT レジスタフィールドに対応し、既知の値
(下記参照)と個別に比較すべきである。それ以外の値は予約済みである。

==  ========================================================================
 0  MIPS32 または microMIPS32。
    レジスタもアドレスも 32 ビット幅である。
    32 ビットのゲストコードしか実行できない。

 1  MIPS64 または microMIPS64 で、32 ビット互換セグメントにのみアクセス
    できる。
    レジスタは 64 ビット幅だが、アドレスは 32 ビット幅である。
    64 ビットのゲストコードは実行できるが、MIPS64 メモリセグメントには
    アクセスできない。
    32 ビットのゲストコードも実行できる。

 2  MIPS64 または microMIPS64 で、すべてのアドレスセグメントにアクセス
    できる。
    レジスタもアドレスも 64 ビット幅である。
    64 ビットまたは 32 ビットのゲストコードを実行できる。
==  ========================================================================

8.9 KVM_CAP_ARM_USER_IRQ
------------------------

:Architectures: arm64

KVM_CHECK_EXTENSION が利用可能と示した場合、このケイパビリティは、
ユーザ空間がカーネル内の割り込みコントローラなしで VM を作成すると、
VM に提示される仮想割り込みを生成しうるカーネル内エミュレートデバイスの
出力レベルの変化が通知されることを意味する。
そのような VM では、ユーザ空間に戻るたびに、カーネルは vcpu の
run->s.regs.device_irq_level フィールドを更新し、デバイスの実際の出力
レベルを表す。

kvm がデバイス出力レベルの変化を検出すると、kvm は VM を実行する前に
少なくとも 1 回ユーザ空間に戻ることを保証する。この終了は KVM_EXIT_INTR でも
KVM_EXIT_MMIO のような他の終了イベントでもよい。こうすることで、ユーザ空間は
常にデバイス出力レベルをサンプリングし、ユーザ空間の割り込みコントローラの
状態を再計算できる。ユーザ空間は kvm の終了のたびに
run->s.regs.device_irq_level の状態を常に確認すべきである。
run->s.regs.device_irq_level の値は、デバイスに応じてレベルトリガと
エッジトリガの両方の割り込み信号を表せる。エッジトリガの割り込み信号は、
run->s.regs.device_irq_level のビットがエッジ信号ごとにちょうど 1 回
セットされた状態でユーザ空間に終了する。

フィールド run->s.regs.device_irq_level は、run->kvm_valid_regs や
run->kvm_dirty_regs のビットとは無関係に利用できる。

KVM_CAP_ARM_USER_IRQ がサポートされている場合、KVM_CHECK_EXTENSION ioctl は
0 より大きい数を返し、このケイパビリティのどのバージョンが実装されているか、
したがって run->s.regs.device_irq_level のどのビットが値を通知できるかを
示す。

現在、device_irq_level ビットマップには次のビットが定義されている::

  KVM_CAP_ARM_USER_IRQ >= 1:

    KVM_ARM_DEV_EL1_VTIMER -  EL1 virtual timer
    KVM_ARM_DEV_EL1_PTIMER -  EL1 physical timer
    KVM_ARM_DEV_PMU        -  ARM PMU overflow interrupt signal

kvm の将来のバージョンでは追加のイベントが実装されるかもしれない。それらは
KVM_CHECK_EXTENSION がより大きい数を返すことで示され、上に列挙される。

8.10 KVM_CAP_PPC_SMT_POSSIBLE
-----------------------------

:Architectures: ppc

このケイパビリティを問い合わせると、KVM_CAP_PPC_SMT で設定できる仮想 SMT
モードの候補を表すビットマップが返る。右から数えて N 番目のビットがセット
されていれば、2^N の仮想 SMT モードが利用できる。

8.12 KVM_CAP_HYPERV_VP_INDEX
----------------------------

:Architectures: x86

このケイパビリティは、ユーザ空間が HV_X64_MSR_VP_INDEX msr をロードできる
ことを示す。この値は SynIC 割り込みの対象 vcpu を表すのに使う。互換性のため、
KVM はこの msr を KVM 内部の vcpu インデックスで初期化する。このケイパビリティ
がない場合でも、ユーザ空間はこの msr の値を問い合わせられる。

8.13 KVM_CAP_S390_AIS_MIGRATION
-------------------------------

:Architectures: s390

このケイパビリティは、flic デバイスが KVM_DEV_FLIC_AISM_ALL 属性を使って
マイグレーション用の AIS 状態を取得・設定できるかどうかを示す。flic デバイスを
作成しなくても、これを知ることができる。

8.14 KVM_CAP_S390_PSW
---------------------

:Architectures: s390

このケイパビリティは、PSW が kvm_run 構造体経由で公開されることを示す。

8.15 KVM_CAP_S390_GMAP
----------------------

:Architectures: s390

このケイパビリティは、ゲストマッピングとして使うユーザ空間メモリが、
メモリスロットがセグメント(1MB)境界に整列され、そのサイズになっていれば、
ユーザメモリのアドレス空間のどこにあってもよいことを示す。

8.16 KVM_CAP_S390_COW
---------------------

:Architectures: s390

このケイパビリティは、ゲストマッピングとして使うユーザ空間メモリが、
コピーオンライトのセマンティクスと、読み取り専用ページテーブルによる
ダーティページ追跡を使えることを示す。

8.17 KVM_CAP_S390_BPB
---------------------

:Architectures: s390

このケイパビリティは、kvm が分岐予測ブロッキングのリセット、マイグレーション、
ネスト KVM を扱うインタフェースを実装することを示す。このケイパビリティが
ない状態で stfle 機能 82 をゲストに提供すべきではない。

8.18 KVM_CAP_HYPERV_TLBFLUSH
----------------------------

:Architectures: x86

このケイパビリティは、KVM が準仮想化された Hyper-V の TLB Flush
ハイパーコールをサポートすることを示す:
HvFlushVirtualAddressSpace, HvFlushVirtualAddressSpaceEx,
HvFlushVirtualAddressList, HvFlushVirtualAddressListEx。

8.19 KVM_CAP_ARM_INJECT_SERROR_ESR
----------------------------------

:Architectures: arm64

このケイパビリティは、ユーザ空間が(KVM_SET_VCPU_EVENTS ioctl 経由で)
ゲストが仮想 SError 割り込み例外を取るときに報告されるシンドローム値を
指定できることを示す。
KVM がこのケイパビリティを通知する場合、ユーザ空間は ESR シンドロームの
ISS フィールドしか指定できない。EC のような ESR の他の部分は、例外を取る
ときに CPU が生成する。この仮想 SError が AArch64 を使って EL1 に取られる
場合、この値は ESR_ELx の ISS フィールドに報告される。

詳細は KVM_CAP_VCPU_EVENTS を参照。

8.20 KVM_CAP_HYPERV_SEND_IPI
----------------------------

:Architectures: x86

このケイパビリティは、KVM が準仮想化された Hyper-V の IPI 送信
ハイパーコールをサポートすることを示す:
HvCallSendSyntheticClusterIpi, HvCallSendSyntheticClusterIpiEx。

8.22 KVM_CAP_S390_VCPU_RESETS
-----------------------------

:Architectures: s390

このケイパビリティは、KVM_S390_NORMAL_RESET と KVM_S390_CLEAR_RESET ioctl が
利用できることを示す。

8.23 KVM_CAP_S390_PROTECTED
---------------------------

:Architectures: s390

このケイパビリティは、Ultravisor が初期化済みで、KVM が保護 VM を開始できる
ことを示す。
このケイパビリティは KVM_S390_PV_COMMAND ioctl と KVM_MP_STATE_LOAD
MP_STATE を司る。保護ゲストでは、状態変化が不正な場合に KVM_SET_MP_STATE が
失敗することがある。

8.24 KVM_CAP_STEAL_TIME
-----------------------

:Architectures: arm64, x86

このケイパビリティは、KVM が steal time アカウンティングをサポートすることを
示す。
steal time アカウンティングがサポートされている場合、アーキテクチャ固有の
インタフェースで有効化できる。このケイパビリティとアーキテクチャ固有の
インタフェースは一致していなければならない。つまり、一方が機能をサポート
すると言えば、他方もサポートすると言うべきであり、その逆も同じである。
arm64 については Documentation/virt/kvm/devices/vcpu.rst の
"KVM_ARM_VCPU_PVTIME_CTRL" を参照。x86 については
Documentation/virt/kvm/x86/msr.rst の "MSR_KVM_STEAL_TIME" を参照。

8.25 KVM_CAP_S390_DIAG318
-------------------------

:Architectures: s390

このケイパビリティを使うと、ゲストは自身の制御プログラム(すなわちゲスト
カーネルの種類とバージョン)に関する情報を設定できる。この情報は
システム/ファームウェアのサービスイベントのときに役立ち、マシン上で動く
ゲスト環境に関する追加データを提供する。

この情報は DIAGNOSE 0x318 命令に関連付けられ、1 バイトの Control Program
Name Code (CPNC)と 7 バイトの Control Program Version Code (CPVC)からなる
8 バイトの値を設定する。CPNC は制御プログラムがどの環境で動いているか
(例: Linux、z/VM など)を決め、CPVC は OS に固有の情報(例: Linux の
バージョン、Linux ディストリビューションなど)に使う。

このケイパビリティが利用できる場合、CPNC と CPVC は sync regs の仕組み
(KVM_SYNC_DIAG318)で KVM とユーザ空間の間で同期できる。

8.26 KVM_CAP_X86_USER_SPACE_MSR
-------------------------------

:Architectures: x86

このケイパビリティは、KVM が MSR の読み書きをユーザ空間へ転送することを
サポートすることを示す。VM 単位で有効化できる。有効にすると、通常なら
KVM がゲストに #GP を発生させる MSR アクセスが、代わりに
KVM_EXIT_X86_RDMSR と KVM_EXIT_X86_WRMSR の終了通知を通じてユーザ空間へ
回される。

8.27 KVM_CAP_X86_MSR_FILTER
---------------------------

:Architectures: x86

このケイパビリティは、KVM がユーザ定義の MSR へのアクセスを拒否できることを
サポートすることを示す。このケイパビリティが公開されると、KVM は新しい VM
ioctl である KVM_X86_SET_MSR_FILTER を提供し、ユーザ空間はこれを呼び出して、
KVM がアクセスを拒否すべき MSR 範囲のビットマップを指定できる。

KVM_CAP_X86_USER_SPACE_MSR と組み合わせると、ユーザ空間は KVM の対象外にある
MSR をトラップしてエミュレートできるだけでなく、KVM の MSR エミュレーション
コードの攻撃面も制限できる。

8.30 KVM_CAP_XEN_HVM
--------------------

:Architectures: x86

このケイパビリティは、Xen が Xen PVHVM ゲストをホストするためにサポートする
機能を示す。有効なフラグは次のとおり::

  #define KVM_XEN_HVM_CONFIG_HYPERCALL_MSR		(1 << 0)
  #define KVM_XEN_HVM_CONFIG_INTERCEPT_HCALL		(1 << 1)
  #define KVM_XEN_HVM_CONFIG_SHARED_INFO		(1 << 2)
  #define KVM_XEN_HVM_CONFIG_RUNSTATE			(1 << 3)
  #define KVM_XEN_HVM_CONFIG_EVTCHN_2LEVEL		(1 << 4)
  #define KVM_XEN_HVM_CONFIG_EVTCHN_SEND		(1 << 5)
  #define KVM_XEN_HVM_CONFIG_RUNSTATE_UPDATE_FLAG	(1 << 6)
  #define KVM_XEN_HVM_CONFIG_PVCLOCK_TSC_UNSTABLE	(1 << 7)

KVM_XEN_HVM_CONFIG_HYPERCALL_MSR フラグは、ゲストが自身のハイパーコールページを
設定するための KVM_XEN_HVM_CONFIG ioctl が利用できることを示す。

KVM_XEN_HVM_CONFIG_INTERCEPT_HCALL もセットされている場合、同じフラグを
ハイパーコールページの内容を渡さずに KVM_XEN_HVM_CONFIG のフラグに指定できる。
これは、KVM にハイパーコールページの内容を自動生成させ、あわせてゲストの
ハイパーコールの傍受を KVM_EXIT_XEN で有効にするよう求めるものである。

KVM_XEN_HVM_CONFIG_SHARED_INFO フラグは、KVM_XEN_HVM_SET_ATTR、
KVM_XEN_HVM_GET_ATTR、KVM_XEN_VCPU_SET_ATTR、KVM_XEN_VCPU_GET_ATTR ioctl が
利用できること、および vcpu の vcpu_info の evtchn_upcall_pending フィールドが
セットされたときにイベントチャネルの upcall 用の例外ベクタが配送されることを
示す。

KVM_XEN_HVM_CONFIG_RUNSTATE フラグは、runstate 関連の機能
KVM_XEN_VCPU_ATTR_TYPE_RUNSTATE_ADDR/_CURRENT/_DATA/_ADJUST が
KVM_XEN_VCPU_SET_ATTR/KVM_XEN_VCPU_GET_ATTR ioctl でサポートされることを示す。

KVM_XEN_HVM_CONFIG_EVTCHN_2LEVEL フラグは、priority フィールドを 2 レベル
イベントチャネル配送を示すように設定した、KVM_IRQ_ROUTING_XEN_EVTCHN タイプの
IRQ ルーティングエントリがサポートされることを示す。

KVM_XEN_HVM_CONFIG_EVTCHN_SEND フラグは、KVM が KVM_XEN_HVM_EVTCHN_SEND ioctl
でイベントチャネルイベントをゲストに直接注入することをサポートすることを示す。
あわせて、イベントチャネル配送、タイマー、XENVER_version の傍受に関連する
KVM_XEN_ATTR_TYPE_EVTCHN/XEN_VERSION HVM 属性と
KVM_XEN_VCPU_ATTR_TYPE_VCPU_ID/TIMER/UPCALL_VECTOR vCPU 属性のサポートも示す。

KVM_XEN_HVM_CONFIG_RUNSTATE_UPDATE_FLAG フラグは、KVM が KVM_XEN_SET_ATTR と
KVM_XEN_GET_ATTR ioctl の KVM_XEN_ATTR_TYPE_RUNSTATE_UPDATE_FLAG 属性を
サポートすることを示す。これは、runstate 情報の更新中に、KVM がゲストメモリに
マップされた vcpu_runstate_info に XEN_RUNSTATE_UPDATE フラグをセットするか
どうかを制御する。上の RUNSTATE 機能はサポートするが
RUNSTATE_UPDATE_FLAG 機能はサポートしないバージョンの KVM は、ゲスト構造体を
更新するときに常に XEN_RUNSTATE_UPDATE フラグをセットする点に注意する。
これはおそらく直感に反する。このフラグが通知される場合、KVM はより正しく
振る舞い、明示的に有効化される(ゲストがハイパーコールを発行し、それによって
VMM が KVM_XEN_ATTR_TYPE_RUNSTATE_UPDATE_FLAG 属性を有効にする)までは
XEN_RUNSTATE_UPDATE フラグを使わない。

KVM_XEN_HVM_CONFIG_PVCLOCK_TSC_UNSTABLE フラグは、KVM が Xen pvclock
ソースの PVCLOCK_TSC_STABLE_BIT フラグをクリアすることをサポートすることを
示す。これは、KVM_CAP_XEN_HVM ioctl が
KVM_XEN_HVM_CONFIG_PVCLOCK_TSC_UNSTABLE フラグをセットしたときに行われる。

8.31 KVM_CAP_SPAPR_MULTITCE
---------------------------

:Architectures: ppc
:Type: vm

このケイパビリティは、カーネルがハイパーコール H_PUT_TCE_INDIRECT と
H_STUFF_TCE をユーザ空間に渡さずに扱えることを意味する。これは PPC KVM
ゲストの DMA 操作を大幅に高速化する。ユーザ空間が以前に LIOBN を KVM に
登録した場合(KVM_CREATE_SPAPR_TCE または同様の呼び出し経由)、ユーザ空間は
これらのハイパーコールのハンドラが呼ばれないことを想定すべきである。

ゲストで H_PUT_TCE_INDIRECT と H_STUFF_TCE を使えるようにするには、ユーザ空間が
ゲストに対してそれを通知しなければならないことがある。例えば、IBM pSeries
(sPAPR)ゲストは、"ibm,hypertas-functions" デバイスツリープロパティに
"hcall-multi-tce" があるとこれらを使い始める。

上記のハイパーコールは、カーネル内の高速パスで処理できることもあれば、
そうでないこともある。カーネルで扱えない場合は、ユーザ空間に渡される。
そのため、カーネル内の高速化があるにもかかわらず、ユーザ空間はこれらに
ついて実装を持たなければならない。

このケイパビリティは常に有効である。

8.32 KVM_CAP_PTP_KVM
--------------------

:Architectures: arm64

このケイパビリティは、KVM の仮想 PTP サービスがホストでサポートされることを
示す。VMM は、マイグレーション時にそのサービスをゲストが利用できるかどうかを
確認できる。

8.37 KVM_CAP_S390_PROTECTED_DUMP
--------------------------------

:Architectures: s390
:Type: vm

このケイパビリティは、KVM と Ultravisor が PV ゲストのダンプをサポートする
ことを示す。`KVM_PV_DUMP` コマンドは `KVM_S390_PV_COMMAND` ioctl で利用でき、
`KVM_PV_INFO` コマンドはダンプ関連の UV データを提供する。また、vcpu ioctl
`KVM_S390_PV_CPU_COMMAND` が利用でき、`KVM_PV_DUMP_CPU` サブコマンドを
サポートする。

8.39 KVM_CAP_S390_CPU_TOPOLOGY
------------------------------

:Architectures: s390
:Type: vm

このケイパビリティは、KVM が S390 CPU Topology 機能を提供することを示す。
この機能は、ファンクションコード 2 の PTF 命令の解釈と、ファンクションコード
0 または 1 の PTF 命令および STSI(15,1,x)命令の両方をユーザランドの
ハイパーバイザへ傍受して転送することで成り立つ。

このケイパビリティがない状態で stfle 機能 11(CPU Topology 機能)をゲストに
通知すべきではない。

このケイパビリティがある場合、KVM は vm fd に新しい属性グループ
KVM_S390_VM_CPU_TOPOLOGY を提供する。
この新しい属性を使うと、kvm_device_attr 構造体を通じて SCA の Modified Change
Topology Report (MTCR)ビットを取得、設定、クリアできる。

Modified Change Topology Report の値を取得するとき、attr->addr は値の格納先
または取得元のバイトを指していなければならない。

8.41 KVM_CAP_VM_TYPES
---------------------

:Architectures: x86
:Type: system ioctl

このケイパビリティは、サポートされる VM タイプのビットマップを返す。ビット @n
が 1 であることは、値 @n の VM タイプがサポートされることを意味する。@n と
して取りうる値は次のとおり::

  #define KVM_X86_DEFAULT_VM	0
  #define KVM_X86_SW_PROTECTED_VM	1
  #define KVM_X86_SEV_VM	2
  #define KVM_X86_SEV_ES_VM	3
  #define KVM_X86_SNP_VM	4
  #define KVM_X86_TDX_VM	5

KVM_X86_SW_PROTECTED_VM は現在のところ開発とテスト専用である点に注意する。
KVM_X86_SW_PROTECTED_VM を「実際の」VM に使ってはならず、特に本番環境では
使ってはならない。ソフトウェア保護 VM の振る舞いと有効な ABI は安定して
いない。

8.42 KVM_CAP_PPC_RPT_INVALIDATE
-------------------------------

:Architectures: ppc

このケイパビリティは、カーネルが H_RPT_INVALIDATE ハイパーコールを扱える
ことを示す。

ゲストで H_RPT_INVALIDATE を使えるようにするには、ユーザ空間がゲストに対して
それを通知しなければならないことがある。例えば、IBM pSeries (sPAPR)ゲストは、
"ibm,hypertas-functions" デバイスツリープロパティに "hcall-rpt-invalidate" が
あるとこれを使い始める。

このケイパビリティは、radix MMU をサポートする POWER9 のようなプラットフォーム
のハイパーバイザで有効になる。

8.43 KVM_CAP_PPC_AIL_MODE_3
---------------------------

:Architectures: ppc

このケイパビリティは、カーネルが H_SET_MODE ハイパーコールで制御される
"Address Translation Mode on Interrupt" すなわち "Alternate Interrupt
Location" リソースのモード 3 設定をサポートすることを示す。

このケイパビリティにより、ゲストカーネルは割り込みとシステムコールを扱う
ためにより性能のよいモードを使える。

8.44 KVM_CAP_MEMORY_FAULT_INFO
------------------------------

:Architectures: x86

このケイパビリティの存在は、KVM がゲストのページフォールトの VM エグジットを
解決できない場合、例えば有効なメモリスロットはあるが対応するホスト仮想
アドレスのバッキング VMA がない場合に、KVM_RUN が kvm_run.memory_fault を
埋めることを示す。

kvm_run.memory_fault の情報は、KVM_RUN が errno=EFAULT または errno=EHWPOISON
のエラーを返し、*かつ* kvm_run.exit_reason が KVM_EXIT_MEMORY_FAULT に
セットされている場合に限り有効である。

備考: メモリフォールトを解決して KVM_RUN を再試行しようとするユーザ空間は、
同じエラーや注釈付きフォールトを繰り返し受け取らないように備えることが
望ましい。

詳細は KVM_EXIT_MEMORY_FAULT を参照。

8.45 KVM_CAP_X86_GUEST_MODE
---------------------------

:Architectures: x86

このケイパビリティの存在は、KVM_RUN が kvm_run.flags の
KVM_RUN_X86_GUEST_MODE ビットを更新し、終了時に vCPU がネストゲストのコードを
実行していたかどうかを示すことを意味する。

8.46 KVM_CAP_S390_KEYOP
-----------------------

:Architectures: s390

このケイパビリティの存在は、KVM_S390_KEYOP ioctl が利用できることを示す。

終了の時点で実行していたのが L1 と L2 のどちらのゲストかに応じて、KVM は
そのゲストのレジスタ状態で終了する。ユーザ空間はこれらのケースを区別する
よう注意しなければならない。

8.47 KVM_CAP_S390_VSIE_ESAMODE
------------------------------

:Architectures: s390

このケイパビリティの存在は、ネストした KVM ゲストが ESA モードで起動できる
ことを示す。

9. 既知の KVM API の問題
========================

KVM の API には、ユーザ空間が知っておく必要のある一貫性のなさや、よくある
落とし穴がある。この節ではそのようないくつかの問題を詳しく説明する。

そのほとんどはアーキテクチャ固有なので、節はアーキテクチャごとに分ける。

9.1. x86
--------

``KVM_GET_SUPPORTED_CPUID`` の問題
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

一般に、``KVM_GET_SUPPORTED_CPUID`` は、その結果をそのまま
``KVM_SET_CPUID2`` に渡せるように設計されている。この節では、そうするのに
注意が要るいくつかのケースを記述する。

ローカル APIC の機能
~~~~~~~~~~~~~~~~~~~~

CPU[EAX=1]:ECX[21] (X2APIC)は ``KVM_GET_SUPPORTED_CPUID`` で報告されるが、
ローカル APIC のカーネル内エミュレーションを有効にするために
``KVM_CREATE_IRQCHIP`` または ``KVM_ENABLE_CAP(KVM_CAP_IRQCHIP_SPLIT)`` を
使った場合にしか有効化できない。

準仮想化機能の ``KVM_FEATURE_PV_UNHALT`` についても同じである。

古いバージョンの Linux では、CPU[EAX=1]:ECX[24] (TSC_DEADLINE)は
``KVM_GET_SUPPORTED_CPUID`` で報告されないが、``KVM_CAP_TSC_DEADLINE_TIMER`` が
存在し、カーネルがローカル APIC のカーネル内エミュレーションを有効にしていれば
有効化できる。新しいバージョンでは、``KVM_GET_SUPPORTED_CPUID`` はそのビットを
利用可能として報告する。

ロングモードのセグメントリミット
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CPU[EAX=0x80000008]:EBX[20] (EFER_LMSLE_MBZ)は "defeature" ビットである。
CPU がロングモードのセグメントリミットをサポート*しない*ときにセットされ、
EFER.LMSLE を 0 にすることを要求する。KVM は、KVM が EFER.LMSLE の設定を
拒否する場合、すなわち CPU がロングモードのセグメントリミットをサポートして
いないか、ネスト SVM がサポートされていない場合に限り、このビットを
``KVM_GET_SUPPORTED_CPUID`` で報告する。したがって KVM は、ネスト SVM が
有効なときにしか EFER.LMSLE を許可しないため、すべての Intel ホストでこの
ビットを報告する。

KVM は ``KVM_GET_EMULATED_CPUID`` でこのビットを報告することは決してないが、
KVM が報告しないホストでも、ユーザ空間は ``KVM_SET_CPUID2`` でこのビットを
セットできる。KVM はゲストの列挙を尊重し、それに応じて EFER.LMSLE=1 を拒否する。
これにより、ユーザ空間はロングモードのセグメントリミットを*サポートする*
ホスト上で vCPU の機能を無効化でき、その vCPU を後でそれをサポートしない
ホストへマイグレーションできる。例えば、AMD Rome で作成した vCPU を、
ロングモードのセグメントリミットのサポートを落とした Milan 以降へ
マイグレーションできる。逆方向にはエミュレーションが要らない。ロングモードの
セグメントリミットを持たないホストはすでにこの defeature を列挙しているから
である。

注意として、``KVM_SET_MSRS`` はこのチェックの対象外である。ホスト側から開始
される MSR 書き込みはゲスト CPUID のチェックを飛ばすので、ユーザ空間はゲスト
CPUID を設定する前に MSR を設定できる。``KVM_SET_SREGS`` とネスト VMRUN は
対象外ではない。

CPU トポロジ
~~~~~~~~~~~~

いくつかの CPUID 値にはホスト CPU のトポロジ情報が含まれる。Intel システム
では 0x0b と 0x1f、AMD システムでは 0x8000001e である。KVM のバージョンに
よってこの情報に対して返す値が異なるので、ユーザ空間はこれを当てにしては
ならない。現在はすべて 0 を返す。

ユーザ空間がゲストのトポロジを設定したい場合、これら 3 つのリーフの値が CPU
ごとに異なることに注意しなければならない。特に、APIC ID は 0x0b と 0x1f の
すべてのサブリーフでは EDX にあり、0x8000001e では EAX にある。後者はさらに
コア ID とノード ID をそれぞれ EBX と ECX のビット 7:0 に格納する。

廃止された ioctl とケイパビリティ
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

KVM_CAP_DISABLE_QUIRKS は、どの quirk が実際に利用できるかをユーザ空間に
知らせない。利用できるなら ``KVM_CHECK_EXTENSION(KVM_CAP_DISABLE_QUIRKS2)`` を
代わりに使う。

KVM_GET_*/KVM_SET_* ioctl の順序
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TBD
