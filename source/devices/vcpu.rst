.. SPDX-License-Identifier: GPL-2.0

========================
汎用 vCPU インタフェース
========================

仮想 CPU の「デバイス」は、ioctl の KVM_SET_DEVICE_ATTR、
KVM_GET_DEVICE_ATTR、KVM_HAS_DEVICE_ATTR も受け付ける。このインタフェースは
他のデバイスと同じ struct kvm_device_attr を使うが、対象は vCPU 全体の設定と
制御である。

仮想 CPU ごとのグループと属性は、存在する場合、アーキテクチャ固有である。

1. グループ: KVM_ARM_VCPU_PMU_V3_CTRL
=====================================

:Architectures: ARM64

1.1. 属性: KVM_ARM_VCPU_PMU_V3_IRQ
---------------------------------------

:Parameters: kvm_device_attr.addr には、PMU オーバーフロー割り込みのアドレス
             として int へのポインタを指定する

Returns:

	 =======  ========================================================
	 -EBUSY   PMU オーバーフロー割り込みがすでに設定されている
	 -EFAULT  割り込み番号の読み取りでエラーが発生した
	 -ENXIO   PMUv3 がサポートされていない、または取得しようとしたときに
		  オーバーフロー割り込みが設定されていない
	 -ENODEV  vCPU に KVM_ARM_VCPU_PMU_V3 の機能がない
	 -EINVAL  指定された PMU オーバーフロー割り込み番号が無効である、
		  またはカーネル内 irqchip を使わずに IRQ 番号を設定しようと
		  した
	 =======  ========================================================

この vCPU の PMUv3 (Performance Monitor Unit v3) オーバーフロー割り込み番号を
表す値。この割り込みは PPI でも SPI でもよいが、割り込みの種類は vCPU ごとに
同じでなければならない。PPI の場合、割り込み番号はすべての vCPU で同じである。
SPI の場合は vCPU ごとに別の番号でなければならない。

GICv5 ベースのゲストでは、アーキテクチャで定められた PPI (23) を使わなければ
ならず、GICv5 形式の完全な Interrupt ID、すなわち 0x20000017 として指定しなけ
ればならない。GICv5 ベースのゲストでは、この ioctl を完全に省略できる。

1.2 属性: KVM_ARM_VCPU_PMU_V3_INIT
---------------------------------------

:Parameters: kvm_device_attr.addr に追加のパラメータはない

Returns:

	 =======  ======================================================
	 -EEXIST  割り込み番号がすでに使われている
	 -ENODEV  PMUv3 がサポートされていない、または GIC が初期化されて
		  いない
	 -ENXIO   PMUv3 がサポートされていない、vCPU の機能がない、
		  ハードウェア PMU がない、または割り込み番号が設定されて
		  いない（GICv5 以外のゲストのみ）
	 -EBUSY   PMUv3 がすでに初期化されている
	 =======  ======================================================

PMUv3 の初期化を要求する。PMUv3 をカーネル内の仮想 GIC 実装と組み合わせて
使う場合は、カーネル内の irqchip を初期化した後にこれを行わなければならない。

vCPU の機能 KVM_ARM_VCPU_PMU_V3_STRICT が有効な場合は、ハードウェア PMU を
選択した後にこれを行わなければならない。

1.3 属性: KVM_ARM_VCPU_PMU_V3_FILTER
-----------------------------------------

:Parameters: kvm_device_attr.addr には、PMU イベントフィルタのアドレスとして
             struct kvm_pmu_event_filter へのポインタを指定する

:Returns:

	 =======  ======================================================
	 -ENODEV  PMUv3 がサポートされていない、または GIC が初期化されて
		  いない
	 -ENXIO   PMUv3 が正しく設定されていない、または呼び出し前にカーネル
	 	  内 irqchip が必要な状態に設定されていない
	 -EBUSY   PMUv3 がすでに初期化されている、または vCPU がすでに
		  実行された
	 -EINVAL  フィルタ範囲が無効である
	 =======  ======================================================

次のように記述される PMU イベントフィルタの設定を要求する::

    struct kvm_pmu_event_filter {
	    __u16	base_event;
	    __u16	nevents;

    #define KVM_PMU_EVENT_ALLOW	0
    #define KVM_PMU_EVENT_DENY	1

	    __u8	action;
	    __u8	pad[3];
    };

フィルタ範囲は、範囲 [@base_event, @base_event + @nevents) と、@action
(KVM_PMU_EVENT_ALLOW または KVM_PMU_EVENT_DENY) の組で定義される。最初に
登録した範囲が全体の方針を決める（最初の @action が DENY なら全体が ALLOW、
最初の @action が ALLOW なら全体が DENY）。複数の範囲を設定でき、それぞれは
PMU アーキテクチャが定めるイベント空間（ARMv8.0 では 10 ビット、ARMv8.1 以降
では 16 ビット）に収まらなければならない。

備考: 同じ範囲に逆のアクションを登録してフィルタを「取り消す」ことをしても、
デフォルトのアクションは変わらない。たとえば、イベント範囲 [0:10) に ALLOW
フィルタを最初のフィルタとして設定し、その後で同じ範囲に DENY アクションを
適用すると、範囲全体が無効のままになる。

制限: イベント 0 (SW_INCR) はフィルタの対象にならない。ハードウェアイベントを
数えないためである。イベント 0x1E (CHAIN) をフィルタしても効果はない。厳密には
イベントではないためである。サイクルカウンタは、イベント 0x11 (CPU_CYCLES) を
使ってフィルタできる。

vCPU の機能 KVM_ARM_VCPU_PMU_V3_STRICT が有効な場合は、ハードウェア PMU を
選択した後にこれを行わなければならない。

1.4 属性: KVM_ARM_VCPU_PMU_V3_SET_PMU
------------------------------------------

:Parameters: kvm_device_attr.addr には、PMU 識別子を表す int のアドレスを
             指定する。

:Returns:

	 =======  ====================================================
	 -EBUSY   PMUv3 がすでに初期化されている、vCPU がすでに実行された、
		  またはイベントフィルタがすでに設定されている
	 -EFAULT  PMU 識別子へのアクセスでエラーが発生した
	 -ENXIO   PMU が見つからない
	 -ENODEV  PMUv3 がサポートされていない、または GIC が初期化されて
		  いない
	 -ENOMEM  メモリを割り当てられなかった
	 =======  ====================================================

PMU のエミュレーションのためにゲストのイベントを作成する際に、指定した
ハードウェア PMU を vCPU が使うように要求する。PMU の識別子は、
/sys/devices（または同等の /sys/bus/event_source）配下にある目的の PMU
インスタンスの "type" ファイルから読み取れる。この属性は、システム上に
少なくとも 2 つの CPU PMU があるヘテロジニアスシステムで特に役立つ。ある
vCPU に設定した PMU は、他のすべての vCPU でも使われる。PMU イベント
フィルタがすでに存在する場合、PMU は設定できない。

KVM は、この属性で指定した PMU に対応する物理 CPU で vCPU を実行しようとは
しない。これは完全にユーザ空間に任される。ただし、PMU が対応していない物理
CPU で vCPU を実行しようとすると失敗し、KVM_RUN は exit_reason =
KVM_EXIT_FAIL_ENTRY で戻る。このとき fail_entry 構造体が設定され、
hardare_entry_failure_reason フィールドに
KVM_EXIT_FAIL_ENTRY_CPU_UNSUPPORTED が、cpu フィールドにプロセッサ ID が
入る。

1.5 属性: KVM_ARM_VCPU_PMU_V3_SET_NR_COUNTERS
--------------------------------------------------

:Parameters: kvm_device_attr.addr には、PMCR_EL0.N が取り得る最大値を表す
	     unsigned int のアドレスを指定する

:Returns:

	 =======  ====================================================
	 -EBUSY   PMUv3 がすでに初期化されている、vCPU がすでに実行された、
		  またはイベントフィルタがすでに設定されている
	 -EFAULT  addr が指す値へのアクセスでエラーが発生した
	 -ENODEV  PMUv3 がサポートされていない、または GIC が初期化されて
		  いない
	 -EINVAL  PMUv3 が明示的に選択されていない、または N の値が範囲外で
	 	  ある
	 =======  ====================================================

仮想 PMU に実装されているイベントカウンタの数を設定する。そのためには
KVM_ARM_VCPU_PMU_V3_SET_PMU で PMU を明示的に選択しておく必要があり、PMU を
明示的に選択していない場合や、カウンタ数が選択した PMU の範囲外である場合は
失敗する。新しい PMU を選択すると、この属性の設定は無効になる。

2. グループ: KVM_ARM_VCPU_TIMER_CTRL
====================================

:Architectures: ARM64

2.1. 属性: KVM_ARM_VCPU_TIMER_IRQ_{VTIMER,PTIMER,HVTIMER,HPTIMER}
-----------------------------------------------------------------------

:Parameters: kvm_device_attr.addr には、タイマー割り込みのアドレスとして
	     int へのポインタを指定する

Returns:

	 =======  =================================
	 -EINVAL  タイマー割り込み番号が無効である
	 -EBUSY   1 つ以上の vCPU がすでに実行されている
	 =======  =================================

カーネル内の仮想 GIC に接続する場合の、アーキテクチャで定められたタイマー
割り込み番号を表す値。これは PPI でなければならない (16 <= intid < 32)。この
属性を設定すると、デフォルト値（下記参照）が上書きされる。

==============================  ==========================================
KVM_ARM_VCPU_TIMER_IRQ_VTIMER   EL1 仮想タイマーの intid（デフォルト: 27）
KVM_ARM_VCPU_TIMER_IRQ_PTIMER   EL1 物理タイマーの intid（デフォルト: 30）
KVM_ARM_VCPU_TIMER_IRQ_HVTIMER  EL2 仮想タイマーの intid（デフォルト: 28）
KVM_ARM_VCPU_TIMER_IRQ_HPTIMER  EL2 物理タイマーの intid（デフォルト: 26）
==============================  ==========================================

異なるタイマーに同じ PPI を設定すると、vCPU は実行できなくなる。ある vCPU で
割り込み番号を設定すると、その時点で作成済みのすべての vCPU が、指定した
タイマーに対してその番号を使うように設定され、他の vCPU で以前に設定した値は
上書きされる。ユーザ空間は、すべての vCPU を作成した後、いずれかの vCPU を
実行する前に、少なくとも 1 つの vCPU で割り込み番号を設定すべきである。

.. _kvm_arm_vcpu_pvtime_ctrl:

3. グループ: KVM_ARM_VCPU_PVTIME_CTRL
=====================================

:Architectures: ARM64

3.1 属性: KVM_ARM_VCPU_PVTIME_IPA
--------------------------------------

:Parameters: 64 ビットのベースアドレス

Returns:

	 =======  ======================================
	 -ENXIO   stolen time が実装されていない
	 -EEXIST  この vCPU に対してベースアドレスがすでに設定されている
	 -EINVAL  ベースアドレスが 64 バイトにアラインされていない
	 =======  ======================================

この vCPU の stolen time 構造体のベースアドレスを指定する。ベースアドレスは
64 バイトにアラインされている必要があり、有効なゲストメモリ領域内に存在
しなければならない。stolen time 構造体のレイアウトなどの詳細は
Documentation/virt/kvm/arm/pvtime.rst を参照。stolen time は保護 VM では
サポートされない (Documentation/virt/kvm/arm/pkvm.rst を参照)。

4. グループ: KVM_VCPU_TSC_CTRL
==============================

:Architectures: x86

4.1 属性: KVM_VCPU_TSC_OFFSET

:Parameters: 64 ビット符号なし TSC オフセット

Returns:

	 ======= ======================================
	 -EFAULT 指定されたパラメータのアドレスの
		 読み取りまたは書き込みでエラーが発生した
	 -ENXIO  この属性はサポートされていない
	 ======= ======================================

ホストの TSC を基準としたゲストの TSC オフセットを指定する。ゲストの TSC は
次の式で求められる:

  guest_tsc = host_tsc + KVM_VCPU_TSC_OFFSET

この属性は、ライブマイグレーション時にゲストの TSC を調整するのに役立ち、
VM が停止していた時間を TSC が数えるようにできる。以下に、この目的で使える
アルゴリズムの一例を示す。

移行元の VMM プロセスでの手順:

1. KVM_GET_CLOCK ioctl を呼び出し、ホストの TSC (tsc_src)、kvmclock の
   ナノ秒 (guest_src)、ホストの CLOCK_REALTIME のナノ秒 (host_src) を
   記録する。

2. すべての vCPU について KVM_VCPU_TSC_OFFSET 属性を読み取り、ゲストの
   TSC オフセット (ofs_src[i]) を記録する。

3. KVM_GET_TSC_KHZ ioctl を呼び出し、ゲストの TSC の周波数 (freq) を
   記録する。

移行先の VMM プロセスでの手順:

4. KVM_SET_CLOCK ioctl を呼び出し、移行元のナノ秒である kvmclock
   (guest_src) と CLOCK_REALTIME (host_src) をそれぞれのフィールドに渡す。
   渡す構造体で KVM_CLOCK_REALTIME フラグが立っていることを確認する。

   KVM は、クロック値を記録してから経過した時間を反映するように VM の
   kvmclock を進める。移行元と移行先で CLOCK_REALTIME が同期していないか、
   移行元が VM を停止してから移行先が手順 4〜7 を実行するまでにほどよく
   短い時間が経過していないと、ゲストで問題（タイムアウトなど）が起きる。

5. KVM_GET_CLOCK ioctl を呼び出し、ホストの TSC (tsc_dest) と kvmclock の
   ナノ秒 (guest_dest) を記録する。

6. すべての vCPU についてゲストの TSC オフセットを調整し、(1) 状態を記録
   してからの経過時間と、(2) 移行元と移行先のマシン間の TSC の差を反映
   させる:

   ofs_dst[i] = ofs_src[i] -
     (guest_src - guest_dest) * freq +
     (tsc_src - tsc_dest)

   ("ofs[i] + tsc - guest * freq" は、kvmclock の時刻 0 に対応するゲストの
   TSC 値である。上の式は、これが移行先でも移行元と同じになることを保証
   する)。

7. すべての vCPU について、前の手順で求めたそれぞれの値を
   KVM_VCPU_TSC_OFFSET 属性に書き込む。
