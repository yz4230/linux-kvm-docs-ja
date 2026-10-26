.. SPDX-License-Identifier: GPL-2.0

====================================================
ARM 仮想汎用割り込みコントローラ v5 (VGICv5)
====================================================


対応するデバイスタイプ:
  - KVM_DEV_TYPE_ARM_VGIC_V5     ARM 汎用割り込みコントローラ v5.0

この API を通じて生成できる VGIC インスタンスは 1 つだけである。生成された
VGIC は VM の割り込みコントローラとして動作する。そのため、エミュレートされた
ユーザ空間のデバイスは、割り込みを CPU に直接注入するのではなく、VGIC に注入
する必要がある。

ゲストの GICv5 デバイスを作成するには、GICv5 のホストが必要である。VGICv5
デバイスは PPI、SPI、LPI の各割り込みに対応する。PPI と SPI の割り込みは、
エミュレートされたカーネル内のデバイス（Arch Timer や PMU など）から注入
することも、KVM_IRQ_LINE ioctl 経由で注入することもできる。LPI は外部から
注入されることはなく、LPI IST を通じてハードウェアで処理される。その
ペンディング状態はゲストが直接制御する。

Groups:
  KVM_DEV_ARM_VGIC_GRP_ADDR
   Attributes:

    KVM_VGIC_V5_ADDR_TYPE_IRS (rw, 64-bit)
      ゲスト物理アドレス空間における GICv5 IRS (Interrupt Routing Service)
      レジスタマッピングのベースアドレス。KVM_DEV_TYPE_ARM_VGIC_V5 でのみ
      有効である。このアドレスは 64K にアラインされている必要があり、領域は
      128 KByte を占める。IRS には CONFIG_FRAME と SETLPI_FRAME があり、
      それぞれ 64 KByte のサイズである。

      IRS は SPI と LPI の処理を担うため、VGIC のリソースをマップする前に、
      GPA 空間における IRS のアドレスを設定することが必須である。最初の
      vCPU の実行前に IRS アドレスを設定しないと、エラーになる。

  KVM_DEV_ARM_VGIC_GRP_NR_IRQS
   Attributes:

    この GIC インスタンスの SPI 数を表す値。これは GICv5 固有である。
    GICv2/v3 と違って、値に SGI や PPI は含まれない。値の範囲は 32 から
    KVM の VGICv5 の最大値である 1024 SPI までで、32 刻みである。ユーザ空間が
    この属性を設定しない場合、KVM はデフォルトで 32 SPI を使う。

    kvm_device_attr.addr は __u32 の値へのポインタである。

  KVM_DEV_ARM_VGIC_GRP_CTRL
   Attributes:

    KVM_DEV_ARM_VGIC_CTRL_INIT
      VGIC の初期化を要求する。kvm_device_attr.addr に追加のパラメータはない。
      すべての vCPU を作成した後に呼び出さなければならない。

   KVM_DEV_ARM_VGIC_USERSPACE_PPIS
      ユーザ空間から操作できる PPI のマスクを要求する。GICv5 では PPI の一部
      だけをユーザ空間から直接操作でき、返されるマスクは、KVM_IRQ_LINE 経由で
      どの PPI を操作できるかをユーザ空間に伝える。

      ユーザ空間は kvm_device_attr.addr に __u64[2] のデータを確保し、その
      ポインタを渡さなければならない。この呼び出しが返ると、渡されたメモリに
      ユーザ空間用の PPI マスクが格納される。下位の __u64 には下位 64 個の
      PPI のマスクが入り、残りの 64 個は 2 番目の __u64 に入る。

      これは読み取り専用の属性であり、設定はできない。設定しようとすると
      拒否される。

  Errors:

    =======  ========================================================
    -ENXIO   呼び出し前に VGIC が必要な状態に設定されていない
    -ENODEV  オンラインの vCPU がない
    -ENOMEM  vgic 内部データの割り当て時にメモリが不足した
    -EFAULT  ゲスト RAM へのアクセスが無効である
    -EBUSY   1 つ以上の vCPU が実行中である
    =======  ========================================================

  KVM_DEV_ARM_VGIC_GRP_CPU_SYSREGS
   Attributes:

    kvm_device_attr の attr フィールドは 2 つの値をエンコードする::

      bits:     | 63      ....       32 | 31  ....  16 | 15  ....  0 |
      values:   |         mpidr         |      RES     |    instr    |

    mpidr フィールドは、アーキテクチャで定義された MPIDR の affinity 情報に
    基づいて CPU ID をエンコードする。フィールドは次のようにエンコードされる::

      | 63 .... 56 | 55 .... 48 | 47 .... 40 | 39 .... 32 |
      |    Aff3    |    Aff2    |    Aff1    |    Aff0    |

    instr フィールドは、システムレジスタアクセス用の A64 命令セット
    エンコーディングで定義されたフィールドに基づいて、アクセスするシステム
    レジスタをエンコードする (RES は、そのビットが将来の使用のために予約されて
    おり、0 であるべきことを意味する)::

      | 15 ... 14 | 13 ... 11 | 10 ... 7 | 6 ... 3 | 2 ... 0 |
      |   Op 0    |    Op1    |    CRn   |   CRm   |   Op2   |

    この API を通じてアクセスするシステムレジスタはすべて (rw, 64-bit) であり、
    kvm_device_attr.addr は __u64 の値へのポインタである。

    KVM_DEV_ARM_VGIC_GRP_CPU_SYSREGS は、mpidr フィールドで指定した CPU の
    CPU インタフェースレジスタにアクセスする。

    利用できるレジスタは次のとおりである:

    =======================  ===================================================
    ICC_ICSR_EL1
    ICC_PPI_ENABLER0_EL1
    ICC_PPI_ENABLER1_EL1
    ICC_PPI_SACTIVER0_EL1    ICC_PPI_CACTIVER0_EL1 はサポートされていない。
                             ICC_PPI_SACTIVER0_EL1 への書き込みは、基になる
                             状態への RAW 書き込みとして扱われる。
    ICC_PPI_SACTIVER1_EL1    ICC_PPI_CACTIVER1_EL1 はサポートされていない。
                             ICC_PPI_SACTIVER1_EL1 への書き込みは、基になる
                             状態への RAW 書き込みとして扱われる。
    ICC_PPI_SPENDR0_EL1      ICC_PPI_CPENDR0_EL1 はサポートされていない。
                             ICC_PPI_SPENDR0_EL1 への書き込みは、基になる状態
                             への RAW 書き込みとして扱われる。
    ICC_PPI_SPENDR1_EL1      ICC_PPI_CPENDR1_EL1 はサポートされていない。
                             ICC_PPI_SPENDR1_EL1 への書き込みは、基になる状態
                             への RAW 書き込みとして扱われる。
    ICC_PPI_PRIORITYR0_EL1
    ICC_PPI_PRIORITYR1_EL1
    ICC_PPI_PRIORITYR2_EL1
    ICC_PPI_PRIORITYR3_EL1
    ICC_PPI_PRIORITYR4_EL1
    ICC_PPI_PRIORITYR5_EL1
    ICC_PPI_PRIORITYR6_EL1
    ICC_PPI_PRIORITYR7_EL1
    ICC_PPI_PRIORITYR8_EL1
    ICC_PPI_PRIORITYR9_EL1
    ICC_PPI_PRIORITYR10_EL1
    ICC_PPI_PRIORITYR11_EL1
    ICC_PPI_PRIORITYR12_EL1
    ICC_PPI_PRIORITYR13_EL1
    ICC_PPI_PRIORITYR14_EL1
    ICC_PPI_PRIORITYR15_EL1
    ICC_APR_EL1
    ICC_CR0_EL1
    ICC_PCR_EL1
    =======================  ===================================================

  Errors:

    =======  =============================================================
    -ENXIO   このレジスタの取得または設定はサポートされていない
    -EBUSY   vCPU が実行中である、または vCPU の実行後に書き込みが行われた
    -EINVAL  指定された mpidr またはレジスタの値が無効である
    =======  =============================================================


  KVM_DEV_ARM_VGIC_GRP_IRS_REGS
   Attributes:
      kvm_device_attr の attr フィールドには、IRS CONFIG_FRAME のベース
      アドレスからの相対オフセットで IRS レジスタを指定する。このベース
      アドレスは、最初に VGICv5 を作成したときに KVM_VGIC_V5_ADDR_TYPE_IRS
      で指定したアドレスである。

      kvm_device_attr.addr は、対象のレジスタの幅 (32/64 ビット) にかかわらず
      __u64 の値へのポインタである。64 ビットレジスタは完全な長さでしか
      アクセスできない。

      読み取り専用レジスタへの書き込みはカーネルによって無視される。ただし
      IRS_IDR0 〜 IRS_IDR2 と IRS_IDR5 〜 IRS_IDR7 は例外で、妥当な設定と
      一致するかを確認する検査が行われる。

      IRS_IDR3 と IRS_IDR4 は RAZ/WI である。ネスト仮想化に対応していない
      ためである。

      専用のユーザ空間アクセサを持たないレジスタの取得と設定には、ゲストの
      読み書きと同じエミュレートされた MMIO ハンドラを使う。専用のユーザ空間
      アクセサを使うと、ゲストに見える副作用を起こさずにマイグレーション状態
      を保存または復元できる。たとえば IRS_IST_BASER の復元は、エミュレート
      されたレジスタの状態だけを復元する。復元した IRS_IST_CFGR と
      IRS_IST_BASER の状態に基づくホストの LPI IST の割り当ては、
      KVM_DEV_ARM_VGIC_GRP_IST を復元するときに行われる。

      一度 LPI IST を割り当てると、IRS_IST_CFGR は変更できない。ユーザ空間は
      現在の値を書き戻してよいが、異なる値を設定すると -EINVAL で拒否される。

      一度 LPI IST を割り当てると、IRS_IST_BASER は変更できない。ユーザ空間は
      現在の値を書き戻してよいが、異なる値を設定すると -EINVAL で拒否される。

  Errors:

    =======  =================================================================
    -ENXIO   オフセットがサポートされるどのレジスタにも対応していない
    -EFAULT  attr->addr のユーザポインタが無効である
    -EINVAL  32 ビット MMIO レジスタに対してオフセットが 32 ビットに
             アラインされていない、64 ビットレジスタに対して 64 ビットに
             アラインされていない、または指定したレジスタの値が設定済みの
             VGICv5 IRS の状態と互換性がない
    -EBUSY   VGIC が初期化されていない、1 つ以上の vCPU が実行中である、
             または vCPU の実行後に書き込みが行われた
    =======  =================================================================

  KVM_DEV_ARM_VGIC_GRP_IST
   Attributes:
      このインタフェースは、IRS の割り込み状態テーブル (IST) の状態を保存
      するため、または復元するために使う。get 操作は IST の状態を保存し、
      set 操作は IST の状態を復元する。kvm_device_attr.attr は予約済みであり、
      0 でなければならない。

      このインタフェースを使う前に VGIC を初期化しなければならない。復元は、
      VM を実行する前に行わなければならない。復元の際は、ユーザ空間が、ゲスト
      の LPI IST を記述するために必要な IRS の状態をあらかじめ復元しておく
      必要がある。

      保存では、まず IRS に保存と VM の静止を要求し、割り込みの状態が IST に
      書き戻されるようにする。KVM は、SPI と LPI の IST の状態をコピーして
      いる間、VM が静止したままであることを確認する。

      kvm_device_attr.addr は struct kvm_vgic_v5_ist へのポインタである::

        struct kvm_vgic_v5_ist {
                __u64   spi_ist_addr;
                __u64   spi_ist_size;
                __u64   lpi_ist_addr;
                __u64   lpi_ist_size;
        };

      SPI と LPI の IST バッファには、割り込みごとにリトルエンディアンの
      32 ビット IST エントリが 1 つずつ、割り込み番号の順に格納される。
      アーキテクチャで定められた 32 ビットの ISTE の状態だけがユーザ空間に
      公開され、ホストの IST のレイアウトとメタデータは KVM に閉じている。

      SPI IST バッファは必須であり、そのサイズは次のとおりでなければならない:

        nr_spis * sizeof(__u32)

      ここで nr_spis は、VGICv5 デバイスに対する KVM_DEV_ARM_VGIC_GRP_NR_IRQS
      が返す値である。VGICv5 ではこの値は SPI の数であり、割り込みの総数では
      ない。

      LPI IST バッファは、ゲストの IRS_IST_CFGR と IRS_IST_BASER の状態が
      有効な LPI IST を記述している場合に必須であり、そのサイズは次のとおり
      でなければならない:

        BIT(lpi_id_bits) * sizeof(__u32)

      ここで lpi_id_bits は、IRS_IST_CFGR で設定された LPI ID の幅である。
      LPI IST が設定されていない場合、lpi_ist_addr と lpi_ist_size はどちらも
      0 でなければならない。

    Errors:

      ===========  ============================================================
      -EBUSY       1 つ以上の vCPU が実行中である、VGIC が初期化されていない、
                   復元が VM の実行後に要求された、LPI IST がすでに存在する、
                   または保存処理が完了した後に VM が静止状態を保てなかった
      -EINVAL      attr->addr が NULL である、ユーザ空間の IST 記述子に必要な
                   バッファがない、LPI IST が設定されていないのに 0 以外の
                   LPI バッファが指定された、バッファサイズが設定済みの
                   VGICv5 IST の状態と一致しない、または VM の内部テーブル
                   操作が VM の状態を拒否した
      -EFAULT      attr->addr、spi_ist_addr、lpi_ist_addr のいずれかのユーザ
                   ポインタが無効である
      -ENXIO       必要な VM ごとの VGICv5/IST バッキング状態が存在しないか
                   矛盾している
      -ENOMEM      ホストの LPI IST やペンディング割り込みの追跡を割り当てる
                   際に IST の復元が失敗した
      -ETIMEDOUT   IRS の保存または VM の操作がタイムアウトした
      ===========  ============================================================

IRS 保存の手順:
------------------

仮想 GICv5 の IRS を保存するときは、次の操作が必要である:

a) KVM_DEV_ARM_VGIC_GRP_IST に対して KVM_GET_DEVICE_ATTR を発行し、IST を
   保存する。
b) KVM_DEV_ARM_VGIC_GRP_IRS_REGS に対して KVM_GET_DEVICE_ATTR を発行し、
   IRS の MMIO レジスタの状態を保存する。

これら 2 つの手順はどちらの順序で行ってもよい。IST を保存すると、すべての
IST の状態がユーザ空間が用意したバッファに書き出され、ゲストメモリは更新
されない。

IRS 復元の手順:
---------------------

仮想 GICv5 と IRS を復元するときは、次の順序に従わなければならない:

a) vCPU を作成する。
b) KVM_DEV_ARM_VGIC_GRP_ADDR に対して KVM_SET_DEVICE_ATTR を発行し、IRS の
   ベースアドレスを指定する。
c) KVM_DEV_ARM_VGIC_GRP_NR_IRQS に対して KVM_SET_DEVICE_ATTR を発行し、SPI
   数を復元する。
d) KVM_DEV_ARM_VGIC_GRP_CTRL に対して KVM_DEV_ARM_VGIC_CTRL_INIT を指定して
   KVM_SET_DEVICE_ATTR を発行し、GIC を初期化する。これによりデフォルト状態が
   設定され、SPI IST が作成される。
e) KVM_DEV_ARM_VGIC_GRP_IRS_REGS に対して KVM_SET_DEVICE_ATTR を発行し、IRS
   の MMIO レジスタの状態を復元する。IRS レジスタは任意の順序で復元してよい。
   ただし IRS_IDR* の状態と、LPI IST を記述する IRS_IST_CFGR/IRS_IST_BASER の
   状態は、IST を復元する前に復元しなければならない。KVM は復元された
   IRS_IST_CFGR と IRS_IST_BASER の状態を使って、次の手順で LPI IST を
   割り当てる。
f) KVM_DEV_ARM_VGIC_GRP_IST に対して KVM_SET_DEVICE_ATTR を発行し、IST を
   復元する。

SPI 数は VGIC の初期化前に復元しなければならない。初期化で SPI の状態が
割り当てられ、IRS の ID レジスタが公開する SPI の範囲が確定するためである。

IRS の MMIO レジスタは、IST を復元する前に復元しなければならない。ゲストが
設定した LPI の数を KVM に伝えるために使われるためである。

現在の KVM の実装では、各種の ``*_STATUSR`` レジスタは観測用の状態である。
ユーザ空間は検証やデバッグのためにこれらを保存してよいが、復元の入力としては
必要なく、復元中に再現する必要もない。

その後、vCPU を起動できる。
