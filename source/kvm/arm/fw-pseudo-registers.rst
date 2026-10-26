.. SPDX-License-Identifier: GPL-2.0

=======================================
ARM ファームウェア疑似レジスタインターフェース
=======================================

KVM は、ゲストの要求に応じてハイパーコールサービスを処理する。新しいハイパーコール
サービスは、仮想化の観点から意味がある場合、ARM 仕様または KVM によって
(ベンダーサービスとして) 定期的に利用可能になる。

つまり、2 つの異なるバージョンの KVM 上で起動したゲストは、2 つの異なる
"ファームウェア" リビジョンを観測できる。これは、特定のゲストが特定のバージョンの
ハイパーコールサービスに結び付いている場合、またはマイグレーションによって、
予期しないゲストに異なるバージョンが突然公開される場合に、問題を引き起こす可能性がある。

この状況を改善するため、KVM は "ファームウェア疑似レジスタ" のセットを公開する。
これらは GET/SET_ONE_REG インターフェースを使って操作できる。これらのレジスタは
ユーザ空間によって保存/復元でき、必要に応じて都合のよい値に設定できる。

次のレジスタが定義されている:

* KVM_REG_ARM_PSCI_VERSION:

  KVM は、CPU のオン/オフ、リセット、パワーオフなどのサービスをゲストに提供するため、
  PSCI (Power State Coordination Interface) 仕様を実装している。

  - vCPU が KVM_ARM_VCPU_PSCI_0_2 機能セットを持つ場合
    (したがってすでに初期化されている場合) にのみ有効
  - GET_ONE_REG で現在の PSCI バージョンを返す (デフォルトでは、
    KVM が実装し v0.2 と互換性のある最高の PSCI バージョン)
  - KVM が実装し v0.2 と互換性のある任意の PSCI バージョンを
    SET_ONE_REG で設定できる
  - 保護ゲストでは、v1.1 より前のバージョンに対して -EINVAL を返す
    (Documentation/virt/kvm/arm/pkvm.rst を参照)
  - VM 全体に影響する (レジスタの見方が vCPU ごとであっても)

* KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_1:
    CVE-2017-5715 を緩和するためのファームウェアサポートの状態を保持する。
    これは KVM が HVC 呼び出しを介してゲストに提供する。ワークアラウンドは
    [1] の SMCCC_ARCH_WORKAROUND_1 に記述されている。

  受け入れられる値は次のとおりである:

    KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_1_NOT_AVAIL:
      KVM はワークアラウンドのファームウェアサポートを提供しない。
      ゲストの緩和状態は不明である。
    KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_1_AVAIL:
      ワークアラウンドの HVC 呼び出しはゲストに利用可能であり、
      緩和に必要である。
    KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_1_NOT_REQUIRED:
      ワークアラウンドの HVC 呼び出しはゲストに利用可能であるが、
      この vCPU では必要ない。

* KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_2:
    CVE-2018-3639 を緩和するためのファームウェアサポートの状態を保持する。
    これは KVM が HVC 呼び出しを介してゲストに提供する。ワークアラウンドは
    [1]_ の SMCCC_ARCH_WORKAROUND_2 に記述されている。

  受け入れられる値は次のとおりである:

    KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_2_NOT_AVAIL:
      ワークアラウンドは利用できない。KVM はワークアラウンドのファームウェア
      サポートを提供しない。
    KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_2_UNKNOWN:
      ワークアラウンドの状態は不明である。KVM はワークアラウンドのファームウェア
      サポートを提供しない。
    KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_2_AVAIL:
      ワークアラウンドは利用可能であり、vCPU によって無効にできる。
      KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_2_ENABLED が設定されている場合、
      この vCPU で有効である。
    KVM_REG_ARM_SMCCC_ARCH_WORKAROUND_2_NOT_REQUIRED:
      ワークアラウンドはこの vCPU で常に有効であるか、必要ない。


ビットマップ機能ファームウェアレジスタ
---------------------------------

上記のレジスタとは異なり、次のレジスタはハイパーコールサービスを機能ビットマップの
形でユーザ空間に公開する。このビットマップは、ゲストが利用できるサービスに変換される。
サービス呼び出しの所有者ごとに 1 つのレジスタが定義され、GET/SET_ONE_REG
インターフェースを介してアクセスできる。

デフォルトでは、これらのレジスタはサポートされる機能の上限で設定される。これにより、
ユーザ空間は GET_ONE_REG を介して利用可能なすべてのハイパーコールサービスを
発見できる。ユーザ空間は、SET_ONE_REG を介して希望のビットマップを書き戻せる。
手を加えられていないレジスタ (おそらくユーザ空間がそれらを認識していないため) の
機能は、そのままゲストに公開される。

KVM は、いずれかの vCPU が少なくとも 1 回実行された後は、ユーザ空間がレジスタを
設定することを許可しないことに注意。代わりに -EBUSY を返す。

疑似ファームウェアビットマップレジスタは次のとおりである:

* KVM_REG_ARM_STD_BMAP:
    ARM 標準セキュアサービス呼び出しのビットマップを制御する。

  次のビットが受け入れられる:

    Bit-0: KVM_REG_ARM_STD_BIT_TRNG_V1_0:
      このビットは、ARM True Random Number Generator (TRNG) 仕様 ARM DEN0098 の
      v1.0 で提供されるサービスを表す。

* KVM_REG_ARM_STD_HYP_BMAP:
    ARM 標準ハイパーバイザサービス呼び出しのビットマップを制御する。

  次のビットが受け入れられる:

    Bit-0: KVM_REG_ARM_STD_HYP_BIT_PV_TIME:
      このビットは、ARM DEN0057A で表される準仮想化時間サービスを表す。

* KVM_REG_ARM_VENDOR_HYP_BMAP:
    ベンダー固有のハイパーバイザサービス呼び出し[0-63] のビットマップを制御する。

  次のビットが受け入れられる:

    Bit-0: KVM_REG_ARM_VENDOR_HYP_BIT_FUNC_FEAT
      このビットは、ARM_SMCCC_VENDOR_HYP_KVM_FEATURES_FUNC_ID と
      ARM_SMCCC_VENDOR_HYP_CALL_UID_FUNC_ID の function-id を表す。

    Bit-1: KVM_REG_ARM_VENDOR_HYP_BIT_PTP:
      このビットは、Precision Time Protocol の KVM サービスを表す。

* KVM_REG_ARM_VENDOR_HYP_BMAP_2:
    ベンダー固有のハイパーバイザサービス呼び出し[64-127] のビットマップを制御する。

  次のビットが受け入れられる:

    Bit-0: KVM_REG_ARM_VENDOR_HYP_BIT_DISCOVER_IMPL_VER
      これは ARM_SMCCC_VENDOR_HYP_KVM_DISCOVER_IMPL_VER_FUNC_ID の
      function-id を表す。これは 0 にリセットされる。

    Bit-1: KVM_REG_ARM_VENDOR_HYP_BIT_DISCOVER_IMPL_CPUS
      これは ARM_SMCCC_VENDOR_HYP_KVM_DISCOVER_IMPL_CPUS_FUNC_ID の
      function-id を表す。これは 0 にリセットされる。

Errors:

    =======  =============================================================
    -ENOENT   不明なレジスタがアクセスされた。
    -EBUSY    VM の起動後にレジスタへ 'write' を試みた。
    -EINVAL   レジスタに無効なビットマップが書き込まれた。
    =======  =============================================================

.. [1] https://developer.arm.com/-/media/developer/pdf/ARM_DEN_0070A_Firmware_interfaces_for_mitigating_CVE-2017-5715.pdf
