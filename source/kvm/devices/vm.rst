.. SPDX-License-Identifier: GPL-2.0

======================
汎用 VM インタフェース
======================

仮想マシン（VM）の「デバイス」は、ioctl の KVM_SET_DEVICE_ATTR、
KVM_GET_DEVICE_ATTR、KVM_HAS_DEVICE_ATTR も受け付ける。このインタフェースは、
他のデバイスと同じ struct kvm_device_attr を使うが、VM 全体の設定と制御を
対象とする。

仮想マシンごとのグループと属性は、存在する場合はアーキテクチャ固有である。

1. グループ: KVM_S390_VM_MEM_CTRL
=================================

:Architectures: s390

1.1. 属性: KVM_S390_VM_MEM_ENABLE_CMMA
--------------------------------------

:Parameters: なし
:Returns: vCPU がすでに定義されている場合は -EBUSY、それ以外は 0

仮想マシン（VM）で Collaborative Memory Management Assist（CMMA）を有効にする。

1.2. 属性: KVM_S390_VM_MEM_CLR_CMMA
-----------------------------------

:Parameters: なし
:Returns: CMMA が有効になっていない場合は -EINVAL;
          それ以外は 0

すべてのゲストページの CMMA 状態をクリアする。これにより、ゲストが未使用と
マークしたページは再び使われ、ホストに回収されない。

1.3. 属性 KVM_S390_VM_MEM_LIMIT_SIZE
------------------------------------

:Parameters: attr->addr にゲストメモリの新しい上限のアドレスを指定する
:Returns: 指定したアドレスにアクセスできない場合は -EFAULT;
          仮想マシンの種別が UCONTROL の場合は -EINVAL;
          指定したゲストメモリがそのマシンに対して大きすぎる場合は -E2BIG;
          vCPU がすでに定義されている場合は -EBUSY;
          新しいシャドウゲストマッピング用のメモリが足りない場合は -ENOMEM;
          それ以外は 0。

ユーザ空間が実際の上限を問い合わせ、ゲストメモリの最大サイズの新しい上限を
設定できる。この上限はページテーブルの段数で決まるため、それぞれ 2048 MB、
4096 GB、8192 TB に切り上げられる。上限がない場合、上限は
KVM_S390_NO_MEM_LIMIT（U64_MAX）に設定される。

2. グループ: KVM_S390_VM_CPU_MODEL
==================================

:Architectures: s390

2.1. 属性: KVM_S390_VM_CPU_MACHINE (r/o)
----------------------------------------

ユーザ空間が、マシンと KVM に固有の CPU 関連情報を取得できる::

  struct kvm_s390_vm_cpu_machine {
       __u64 cpuid;           # CPUID of host
       __u32 ibc;             # IBC level range offered by host
       __u8  pad[4];
       __u64 fac_mask[256];   # set of cpu facilities enabled by KVM
       __u64 fac_list[256];   # set of cpu facilities offered by host
  }

:Parameters: マシン関連の CPU データ（struct kvm_s390_vm_cpu_machine* 型）を
             格納するバッファのアドレス
:Returns:   指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
            この ioctl を処理するためのメモリが足りない場合は -ENOMEM;
            成功した場合は 0。

2.2. 属性: KVM_S390_VM_CPU_PROCESSOR (r/w)
==========================================

ユーザ空間が、vCPU の CPU 関連情報を取得、または変更を要求できる::

  struct kvm_s390_vm_cpu_processor {
       __u64 cpuid;           # CPUID currently (to be) used by this vcpu
       __u16 ibc;             # IBC level currently (to be) used by this vcpu
       __u8  pad[6];
       __u64 fac_list[256];   # set of cpu facilities currently (to be) used
                              # by this vcpu
  }

KVM は CPU モデルのデータを一切強制も制限もしない。KVM_S390_VM_CPU_MACHINE で
取得した情報は、妥当な構成を設定するためのヒントとして使う。追加で設定した
facility ビットによって発生し、KVM が処理しない命令のインターセプトは、
VM ドライバのコードで実装する必要がある。

:Parameters: プロセッサ関連の CPU データ（struct kvm_s390_vm_cpu_processor* 型）を
             格納または設定するバッファのアドレス。
:Returns:  vCPU が 1 つ以上すでに起動されている場合（書き込みの場合のみ）-EBUSY;
          指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
          この ioctl を処理するためのメモリが足りない場合は -ENOMEM;
          成功した場合は 0。

.. _KVM_S390_VM_CPU_MACHINE_FEAT:

2.3. 属性: KVM_S390_VM_CPU_MACHINE_FEAT (r/o)
---------------------------------------------

ユーザ空間が利用可能な CPU 機能を取得できる。機能は、ハードウェアが提供し、
KVM がサポートしていれば利用可能である。理論上は、CPU 機能を KVM が完全に
エミュレートすることもあり得る。

::

  struct kvm_s390_vm_cpu_feat {
        __u64 feat[16]; # Bitmap (1 = feature available), MSB 0 bit numbering
  };

:Parameters: 機能一覧を読み込むバッファのアドレス。
:Returns:  指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
           成功した場合は 0。

2.4. 属性: KVM_S390_VM_CPU_PROCESSOR_FEAT (r/w)
-----------------------------------------------

ユーザ空間が、ある VM のすべての VCPU について有効な CPU 機能を取得または
変更できる。利用できない機能は有効にできない。

パラメータの構造体の説明は :ref:`KVM_S390_VM_CPU_MACHINE_FEAT` を参照。

:Parameters: 機能一覧を格納または読み込むバッファのアドレス。
:Returns:   指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
            利用できない CPU 機能を有効にしようとした場合は -EINVAL;
            VCPU が 1 つ以上すでに定義されている場合は -EBUSY;
            成功した場合は 0。

.. _KVM_S390_VM_CPU_MACHINE_SUBFUNC:

2.5. 属性: KVM_S390_VM_CPU_MACHINE_SUBFUNC (r/o)
------------------------------------------------

ユーザ空間が、設定された IBC によるフィルタリングなしで、利用可能な CPU
サブファンクションを取得できる。これらのサブファンクションは、query または
"test bit" サブファンクションを介してゲスト VCPU に通知され、たとえば cpacf の
各機能、plo、ptff で使われる。

サブファンクションブロックが有効なのは、KVM_S390_VM_CPU_MACHINE が対象命令を
導入する STFL(E) ビットを含む場合だけである。対象命令が "query subfunction" で
サブファンクションを示す場合、応答ブロックは返される構造体に含まれる。対象命令が
"test bit" の仕組みでサブファンクションを示す場合、サブファンクションコードは
MSB 0 ビット番号付けで返される構造体に含まれる。

::

  struct kvm_s390_vm_cpu_subfunc {
       u8 plo[32];           # always valid (ESA/390 feature)
       u8 ptff[16];          # valid with TOD-clock steering
       u8 kmac[16];          # valid with Message-Security-Assist
       u8 kmc[16];           # valid with Message-Security-Assist
       u8 km[16];            # valid with Message-Security-Assist
       u8 kimd[16];          # valid with Message-Security-Assist
       u8 klmd[16];          # valid with Message-Security-Assist
       u8 pckmo[16];         # valid with Message-Security-Assist-Extension 3
       u8 kmctr[16];         # valid with Message-Security-Assist-Extension 4
       u8 kmf[16];           # valid with Message-Security-Assist-Extension 4
       u8 kmo[16];           # valid with Message-Security-Assist-Extension 4
       u8 pcc[16];           # valid with Message-Security-Assist-Extension 4
       u8 ppno[16];          # valid with Message-Security-Assist-Extension 5
       u8 kma[16];           # valid with Message-Security-Assist-Extension 8
       u8 kdsa[16];          # valid with Message-Security-Assist-Extension 9
       u8 reserved[1792];    # reserved for future instructions
  };

:Parameters: サブファンクションブロックを読み込むバッファのアドレス。
:Returns:  指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
           成功した場合は 0。

2.6. 属性: KVM_S390_VM_CPU_PROCESSOR_SUBFUNC (r/w)
--------------------------------------------------

ユーザ空間が、ある VM のすべての VCPU に対して通知される CPU サブファンクションを
取得または変更できる。この属性は、カーネルとハードウェアのサポートがそろって
いる場合にのみ利用できる。

カーネルは、設定されたサブファンクションブロックをゲストへの通知に使う。
サブファンクションブロックが使われるのは、対応する STFL(E) ビットがユーザ空間に
よって無効化されていない場合だけである（つまり、問い合わせる命令が実際に
ゲストで利用可能である）。

データがまだ書き込まれていない間は、読み取りが失敗する。この場合、利用可能な
サブファンクションの判定には IBC が使われる。これにより後方互換性が保証される。

パラメータの構造体の説明は :ref:`KVM_S390_VM_CPU_MACHINE_SUBFUNC` を参照。

:Parameters: サブファンクションブロックを格納または読み込むバッファのアドレス。
:Returns:   指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
            読み取り時で、まだ書き込みがない場合は -EINVAL;
            VCPU が 1 つ以上すでに定義されている場合は -EBUSY;
            成功した場合は 0。

3. グループ: KVM_S390_VM_TOD
============================

:Architectures: s390

3.1. 属性: KVM_S390_VM_TOD_HIGH
-------------------------------

ユーザ空間が TOD クロック拡張（u8）を設定/取得できる
（KVM_S390_VM_TOD_EXT に置き換えられた）。

:Parameters: データ（u8）を格納するユーザ空間のバッファのアドレス
:Returns:   指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
            TOD クロック拡張を 0 以外に設定することがサポートされていない場合は -EINVAL;
            PV ゲスト（TOD は ultravisor が管理する）の場合は -EOPNOTSUPP

3.2. 属性: KVM_S390_VM_TOD_LOW
------------------------------

ユーザ空間が、POP で定義された TOD クロックレジスタのビット 0〜63（u64）を
設定/取得できる。

:Parameters: データ（u64）を格納するユーザ空間のバッファのアドレス
:Returns:    指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
             PV ゲスト（TOD は ultravisor が管理する）の場合は -EOPNOTSUPP

3.3. 属性: KVM_S390_VM_TOD_EXT
------------------------------

ユーザ空間が、POP で定義された TOD クロックレジスタのビット 0〜63（u64）を
設定/取得できる。ゲスト CPU モデルが TOD クロック拡張（u8）をサポートしていれば、
ユーザ空間はそれも取得/設定できる。サポートしていない場合、TOD クロック拡張は
0 として格納され、0 以外の値に設定することはできない。

:Parameters: データ（kvm_s390_vm_tod_clock）を格納するユーザ空間のバッファの
             アドレス
:Returns:   指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
            TOD クロック拡張を 0 以外に設定することがサポートされていない場合は -EINVAL;
            PV ゲスト（TOD は ultravisor が管理する）の場合は -EOPNOTSUPP

4. グループ: KVM_S390_VM_CRYPTO
===============================

:Architectures: s390

4.1. 属性: KVM_S390_VM_CRYPTO_ENABLE_AES_KW (w/o)
-------------------------------------------------

ユーザ空間が、新しいラッピングキーの生成を含め、aes キーラッピングを
有効にできる。

:Parameters: なし
:Returns:    0

4.2. 属性: KVM_S390_VM_CRYPTO_ENABLE_DEA_KW (w/o)
-------------------------------------------------

ユーザ空間が、新しいラッピングキーの生成を含め、dea キーラッピングを
有効にできる。

:Parameters: なし
:Returns:    0

4.3. 属性: KVM_S390_VM_CRYPTO_DISABLE_AES_KW (w/o)
--------------------------------------------------

ユーザ空間が、ラッピングキーをクリアして、aes キーラッピングを無効にできる。

:Parameters: なし
:Returns:    0

4.4. 属性: KVM_S390_VM_CRYPTO_DISABLE_DEA_KW (w/o)
--------------------------------------------------

ユーザ空間が、ラッピングキーをクリアして、dea キーラッピングを無効にできる。

:Parameters: なし
:Returns:    0

4.5. 属性: KVM_S390_VM_CRYPTO_ENABLE_APIE (w/o)
-----------------------------------------------

ユーザ空間が AP 解釈実行を有効にできる。

:Parameters: なし
:Returns:    成功した場合は 0;
             ゲストで AP 命令が利用できない場合は -EOPNOTSUPP

4.6. 属性: KVM_S390_VM_CRYPTO_DISABLE_APIE (w/o)
------------------------------------------------

ユーザ空間が AP 解釈実行を無効にできる。

:Parameters: なし
:Returns:    成功した場合は 0;
             ゲストで AP 命令が利用できない場合は -EOPNOTSUPP

5. グループ: KVM_S390_VM_MIGRATION
==================================

:Architectures: s390

5.1. 属性: KVM_S390_VM_MIGRATION_STOP (w/o)
-------------------------------------------

ユーザ空間が、PGSTE マイグレーションに必要なマイグレーションモードを
停止できる。マイグレーションモードが有効でないときにこの属性を設定しても、
何の効果もない。

:Parameters: なし
:Returns:    0

5.2. 属性: KVM_S390_VM_MIGRATION_START (w/o)
--------------------------------------------

ユーザ空間が、PGSTE マイグレーションに必要なマイグレーションモードを
開始できる。マイグレーションモードがすでに有効なときにこの属性を設定しても、
何の効果もない。

すべてのメモリスロットでダーティトラッキングを有効にしなければならない。
そうでない場合は -EINVAL が返る。いずれかのメモリスロットでダーティトラッキングが
無効になると、マイグレーションモードは自動的に停止する。

:Parameters: なし
:Returns:   マイグレーションモードを開始するのに十分な空きメモリがない場合は -ENOMEM;
            VM の状態が不正な場合（メモリが定義されていないなど）は -EINVAL;
            成功した場合は 0。

5.3. 属性: KVM_S390_VM_MIGRATION_STATUS (r/o)
---------------------------------------------

ユーザ空間がマイグレーションモードの状態を問い合わせできる。

:Parameters: データ（u64）を格納するユーザ空間のバッファのアドレス;
             データ自体は、マイグレーションモードが無効なら 0、有効なら 1 である
:Returns:   指定したアドレスにカーネル空間からアクセスできない場合は -EFAULT;
            成功した場合は 0。

6. グループ: KVM_ARM_VM_SMCCC_CTRL
==================================

:Architectures: arm64

6.1. 属性: KVM_ARM_VM_SMCCC_FILTER (w/o)
----------------------------------------

:Parameters: ``struct kvm_smccc_filter`` へのポインタ

:Returns:

        ======  =============================================
        EEXIST  既に登録された範囲または予約済みの範囲と交差する
        EBUSY   VM 内の vCPU がすでに実行されている
        EINVAL  フィルタの設定が不正
        ENOMEM  カーネル内の SMCCC フィルタの表現用のメモリの割り当てに失敗した
        ======  =============================================

次のように定義される SMCCC 呼び出しフィルタのインストールを要求する::

    enum kvm_smccc_filter_action {
            KVM_SMCCC_FILTER_HANDLE = 0,
            KVM_SMCCC_FILTER_DENY,
            KVM_SMCCC_FILTER_FWD_TO_USER,
    };

    struct kvm_smccc_filter {
            __u32 base;
            __u32 nr_functions;
            __u8 action;
            __u8 pad[15];
    };

フィルタは、重複しない範囲の集合として定義される。各範囲は、その範囲内の
SMCCC 呼び出しに適用するアクションを定義する。ユーザ空間は、この属性を続けて
呼び出すことで、複数の範囲をフィルタに挿入できる。

KVM のデフォルト設定では、実装済みのすべての SMCCC 呼び出しが許可される。
したがって、ユーザ空間はデフォルトの動作を変更する範囲だけを記述して、
SMCCC フィルタを疎に定義できる。

``struct kvm_smccc_filter`` が表す範囲は
[``base``, ``base + nr_functions``) である。範囲のラップは許されない。つまり、
ユーザ空間は ``base + nr_functions`` がオーバーフローすることに依存できない。

SMCCC フィルタは、ゲストが開始する SMC 呼び出しと HVC 呼び出しの両方に
適用される。SMCCC フィルタは、SMCCC 呼び出しのカーネル内エミュレーションを
制御し、そのため SMCCC 呼び出しを扱う他のインタフェース（ハイパーコール
ビットマップレジスタなど）より先に作用する。

Actions:
 - ``KVM_SMCCC_FILTER_HANDLE``: ゲストの SMCCC 呼び出しをカーネル内で
   処理できるようにする。ユーザ空間は、許可する SMCCC 呼び出しの範囲を
   明示的に記述し\ *ない*\ ことが強く推奨される。

 - ``KVM_SMCCC_FILTER_DENY``: ゲストの SMCCC 呼び出しをカーネル内で
   拒否し、ゲストに戻る。

 - ``KVM_SMCCC_FILTER_FWD_TO_USER``: ゲストの SMCCC 呼び出しは、
   ``KVM_EXIT_HYPERCALL`` というエグジット理由でユーザ空間に転送される。

``pad`` フィールドは将来の使用のために予約済みで、0 でなければならない。
このフィールドが 0 でない場合、KVM は ``-EINVAL`` を返すことがある。

KVM は関数 ID の 'Arm Architecture Calls' の範囲を予約しており、これらの
範囲のいずれかの部分に対してフィルタを定義しようとすると拒否する:

        ===========  ===============
        開始         終了（両端を含む）
        ===========  ===============
        0x8000_0000  0x8000_FFFF
        0xC000_0000  0xC000_FFFF
        ===========  ===============
