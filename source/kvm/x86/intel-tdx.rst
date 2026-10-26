.. SPDX-License-Identifier: GPL-2.0

===================================
Intel Trust Domain Extensions（TDX）
===================================

概要
====
Intel の Trust Domain Extensions（TDX）は、保護ゲスト VM をホストおよび
物理攻撃から守る。CPU によるアテステーションを受けた「TDX モジュール」と
呼ばれるソフトウェアモジュールが、新しい CPU の分離領域内で動き、保護 VM
（TDX ゲストまたは TD とも呼ばれる）を管理・実行する機能を提供する。

ホワイトペーパー、仕様書などの資料は [1] を参照。

本書では TDX 固有の KVM ABI を説明する。TDX モジュールは、KVM が TDX ゲ
ストを実行するために使う前に初期化する必要がある。TDX モジュールを初期化
するためのサポートはホストの core カーネルが提供しており、その内容は Documentation/arch/x86/tdx.rst
に書かれている。

API の説明
===========

KVM_MEMORY_ENCRYPT_OP
---------------------
:Type: vm ioctl、vcpu ioctl

TDX の操作では、KVM_MEMORY_ENCRYPT_OP は TDX 固有の sub-ioctl() コマンド
を持つ汎用 ioctl として使われる。

::

  /* Trust Domain Extensions sub-ioctl() commands. */
  enum kvm_tdx_cmd_id {
          KVM_TDX_CAPABILITIES = 0,
          KVM_TDX_INIT_VM,
          KVM_TDX_INIT_VCPU,
          KVM_TDX_INIT_MEM_REGION,
          KVM_TDX_FINALIZE_VM,
          KVM_TDX_GET_CPUID,

          KVM_TDX_CMD_NR_MAX,
  };

  struct kvm_tdx_cmd {
        /* enum kvm_tdx_cmd_id */
        __u32 id;
        /* flags for sub-command. If sub-command doesn't use this, set zero. */
        __u32 flags;
        /*
         * data for each sub-command. An immediate or a pointer to the actual
         * data in process virtual address.  If sub-command doesn't use it,
         * set zero.
         */
        __u64 data;
        /*
         * Auxiliary error code.  The sub-command may return TDX SEAMCALL
         * status code in addition to -Exxx.
         */
        __u64 hw_error;
  };

KVM_TDX_CAPABILITIES
--------------------
:Type: vm ioctl
:Returns: 成功時は 0、エラー時は 0 未満

システムにロードされた特定の TDX モジュールのもとで、現在の KVM が対応す
る TDX ケイパビリティを返す。TDX ゲストに設定できる機能／ケイパビリティ
を報告する。

- id: KVM_TDX_CAPABILITIES
- flags: 0 でなければならない
- data: struct kvm_tdx_capabilities へのポインタ
- hw_error: 0 でなければならない

::

  struct kvm_tdx_capabilities {
        __u64 supported_attrs;
        __u64 supported_xfam;

        /* TDG.VP.VMCALL hypercalls executed in kernel and forwarded to
         * userspace, respectively
         */
        __u64 kernel_tdvmcallinfo_1_r11;
        __u64 user_tdvmcallinfo_1_r11;

        /* TDG.VP.VMCALL instruction executions subfunctions executed in kernel
         * and forwarded to userspace, respectively
         */
        __u64 kernel_tdvmcallinfo_1_r12;
        __u64 user_tdvmcallinfo_1_r12;

        __u64 reserved[250];

        /* Configurable CPUID bits for userspace */
        struct kvm_cpuid2 cpuid;
  };


KVM_TDX_INIT_VM
---------------
:Type: vm ioctl
:Returns: 成功時は 0、エラー時は 0 未満

TDX 固有の VM 初期化を行う。これは KVM_CREATE_VM のあと、vCPU を作成する
前に呼ぶ必要がある。

- id: KVM_TDX_INIT_VM
- flags: 0 でなければならない
- data: struct kvm_tdx_init_vm へのポインタ
- hw_error: 0 でなければならない

::

  struct kvm_tdx_init_vm {
          __u64 attributes;
          __u64 xfam;
          __u64 mrconfigid[6];          /* sha384 digest */
          __u64 mrowner[6];             /* sha384 digest */
          __u64 mrownerconfig[6];       /* sha384 digest */

          /* The total space for TD_PARAMS before the CPUIDs is 256 bytes */
          __u64 reserved[12];

        /*
         * Call KVM_TDX_INIT_VM before vcpu creation, thus before
         * KVM_SET_CPUID2.
         * This configuration supersedes KVM_SET_CPUID2s for VCPUs because the
         * TDX module directly virtualizes those CPUIDs without VMM.  The user
         * space VMM, e.g. qemu, should make KVM_SET_CPUID2 consistent with
         * those values.  If it doesn't, KVM may have wrong idea of vCPUIDs of
         * the guest, and KVM may wrongly emulate CPUIDs or MSRs that the TDX
         * module doesn't virtualize.
         */
          struct kvm_cpuid2 cpuid;
  };


KVM_TDX_INIT_VCPU
-----------------
:Type: vcpu ioctl
:Returns: 成功時は 0、エラー時は 0 未満

TDX 固有の vCPU 初期化を行う。

- id: KVM_TDX_INIT_VCPU
- flags: 0 でなければならない
- data: ゲスト TD の vCPU RCX の初期値
- hw_error: 0 でなければならない

KVM_TDX_INIT_MEM_REGION
-----------------------
:Type: vcpu ioctl
:Returns: 成功時は 0、エラー時は 0 未満

@source_addr から与えられたユーザ空間のデータで、@gpa から始まる @nr_pages
ページ分の TDX ゲストプライベートメモリを初期化する。@source_addr は PAGE_SIZE
にアラインされていなければならない。

guest_memfd のインプレース変換が有効な場合は、@source_addr に 0 を渡して
「ソースページなし」を表す。インプレース変換が有効でないか対応していない
場合は、ソースページが必要である。

なお、このサブコマンドを呼ぶ前に、範囲 [gpa, gpa + nr_pages] のメモリ属
性を private にしておく必要がある。ユーザ空間は KVM_SET_MEMORY_ATTRIBUTES
で属性を設定できる。

KVM_TDX_MEASURE_MEMORY_REGION フラグを指定すると、計測も拡張される。

- id: KVM_TDX_INIT_MEM_REGION
- flags: 現在定義されているのは KVM_TDX_MEASURE_MEMORY_REGION だけである
- data: struct kvm_tdx_init_mem_region へのポインタ
- hw_error: 0 でなければならない

::

  #define KVM_TDX_MEASURE_MEMORY_REGION   (1UL << 0)

  struct kvm_tdx_init_mem_region {
          __u64 source_addr;
          __u64 gpa;
          __u64 nr_pages;
  };


KVM_TDX_FINALIZE_VM
-------------------
:Type: vm ioctl
:Returns: 成功時は 0、エラー時は 0 未満

初期 TD の内容の計測を完了し、実行可能としてマークする。

- id: KVM_TDX_FINALIZE_VM
- flags: 0 でなければならない
- data: 0 でなければならない
- hw_error: 0 でなければならない


KVM_TDX_GET_CPUID
-----------------
:Type: vcpu ioctl
:Returns: 成功時は 0、エラー時は 0 未満

TDX モジュールが TD ゲスト向けに仮想化する CPUID の値を取得する。-E2BIG
が返った場合、ユーザ空間はより大きなバッファを確保して再試行すべきである。
最小バッファサイズは struct kvm_cpuid2 の nent フィールドに更新される。

- id: KVM_TDX_GET_CPUID
- flags: 0 でなければならない
- data: struct kvm_cpuid2 へのポインタ（in/out）
- hw_error: 0 でなければならない（out）

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

KVM TDX の作成手順
=====================
標準の KVM の手順に加えて、新しい TDX ioctl を呼ぶ必要がある。制御の流れ
は次のとおりである:

#. システム全体のケイパビリティを確認する

   * KVM_CAP_VM_TYPES: VM タイプが対応しているか、KVM_X86_TDX_VM が対応しているかを確認する。

#. VM を作成する

   * KVM_CREATE_VM
   * KVM_TDX_CAPABILITIES: TDX ゲストを作成するための TDX ケイパビリティを問い合わせる。
   * KVM_CHECK_EXTENSION(KVM_CAP_MAX_VCPUS): VM レベルで TD が対応する最大 vCPU 数を問い合わせる（TDX にはこの点に関する独自の制限がある）。
   * KVM_SET_TSC_KHZ: ホストと異なる TSC 周波数にしたい場合に TD の TSC 周波数を設定する。これは任意である。
   * KVM_TDX_INIT_VM: TDX 固有の VM パラメータを渡す。

#. vCPU を作成する

   * KVM_CREATE_VCPU
   * KVM_TDX_INIT_VCPU: TDX 固有の vCPU パラメータを渡す。
   * KVM_SET_CPUID2: TD の CPUID を設定する。
   * KVM_SET_MSRS: TD の MSR を設定する。

#. 初期ゲストメモリを初期化する

   * 初期ゲストメモリの内容を用意する。
   * KVM_TDX_INIT_MEM_REGION: 初期ゲストメモリを追加する。
   * KVM_TDX_FINALIZE_VM: TDX ゲストの計測を完了する。

#. vCPU を実行する

参照
====

https://www.intel.com/content/www/us/en/developer/tools/trust-domain-extensions/documentation.html
