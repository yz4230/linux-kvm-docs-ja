.. SPDX-License-Identifier: GPL-2.0

====================================
FLIC (フローティング割り込みコントローラ)
====================================

FLIC は、フローティング (CPU ごとではない) 割り込み、つまり I/O、サービス、および一部の
マシンチェック割り込みを扱う。すべての割り込みは、VM ごとの保留中割り込みリストに
格納される。FLIC はこのリストに対して操作を行う。

FLIC インスタンスは 1 つだけ生成できる。

FLIC は次をサポートする。
- 割り込みの追加 (KVM_DEV_FLIC_ENQUEUE)
- 現在保留中の割り込みの検査 (KVM_FLIC_GET_ALL_IRQS)
- 保留中のフローティング割り込みのすべてをパージ (KVM_DEV_FLIC_CLEAR_IRQS)
- 保留中のフローティング I/O 割り込みを 1 つパージ (KVM_DEV_FLIC_CLEAR_IO_IRQ)
- ゲストの透過的な非同期ページフォールトの有効化/無効化
- アダプタ割り込みソースの登録と変更 (KVM_DEV_FLIC_ADAPTER_*)
- AIS (アダプタ割り込み抑制) モード状態の変更 (KVM_DEV_FLIC_AISM)
- 指定されたアダプタでアダプタ割り込みを注入 (KVM_DEV_FLIC_AIRQ_INJECT)
- すべての AIS モード状態の取得/設定 (KVM_DEV_FLIC_AISM_ALL)

Groups:
  KVM_DEV_FLIC_ENQUEUE
    バッファと長さをカーネルに渡し、それらは保留中割り込みのリストに注入される。
    attr->addr にはバッファへのポインタが入り、attr->attr にはバッファの長さが入る。
    ユーザ空間からコピーされるデータ構造 kvm_s390_irq の形式は、
    usr/include/linux/kvm.h で定義されている。

  KVM_DEV_FLIC_GET_ALL_IRQS
    すべてのフローティング割り込みを、ユーザ空間が提供するバッファにコピーする。
    バッファが小さすぎる場合は -ENOMEM を返す。これは、ユーザ空間がより大きなバッファで
    再試行すべきことを示す。

    カーネル空間バッファの割り当てに失敗した場合は -ENOBUFS を返す。

    ユーザ空間へのデータのコピーに失敗した場合は -EFAULT を返す。
    すべての割り込みは保留中のままであり、つまり現在保留中の割り込みのリストから
    削除されない。
    attr->addr には、すべての割り込みデータがコピーされるバッファのユーザ空間アドレスが入る。
    attr->attr には、バッファのサイズ (バイト単位) が入る。

  KVM_DEV_FLIC_CLEAR_IRQS
    現在保留中のフローティング割り込みのリストから、すべての要素を単純に削除する。
    ゲストには割り込みは注入されない。

  KVM_DEV_FLIC_CLEAR_IO_IRQ
    attr->addr (アドレス) と attr->attr (長さ) で指定されるバッファを介して渡される
    サブシステム識別ワードで識別されるサブチャネルの I/O 割り込みを 1 つ (存在する場合) 削除する。

  KVM_DEV_FLIC_APF_ENABLE
    ゲストの非同期ページフォールトを有効にする。したがって、メジャーページフォールトの場合は、
    ホストがこれを非同期に処理し、ゲストを続行できる。

    ucontrol VM の FLIC で呼び出された場合は -EINVAL を返す。

  KVM_DEV_FLIC_APF_DISABLE_WAIT
    ゲストの非同期ページフォールトを無効にし、すでに保留中の非同期ページフォールトが完了するまで待つ。
    これは、割り込みリストをマイグレーションする前に、すべての init 割り込みに対して
    完了割り込みを発生させるために必要である。

    ucontrol VM の FLIC で呼び出された場合は -EINVAL を返す。

  KVM_DEV_FLIC_ADAPTER_REGISTER
    I/O アダプタ割り込みソースを登録する。登録するアダプタを記述する
    kvm_s390_io_adapter を受け取る::

	struct kvm_s390_io_adapter {
		__u32 id;
		__u8 isc;
		__u8 maskable;
		__u8 swap;
		__u8 flags;
	};

   id にはアダプタの一意な ID が入り、isc には使用する I/O 割り込みサブクラスが入る。
   maskable はこのアダプタをマスクできるか (割り込みをオフにできるか) を示し、
   swap はインジケータをバイトスワップする必要があるかを示し、flags には
   アダプタのさらなる特性が入る。

   'flags' に現在定義されている値は次のとおりである。

   - KVM_S390_ADAPTER_SUPPRESSIBLE: アダプタは AIS
     (アダプタ割り込み抑制) 機能の対象である。このフラグは、AIS ケイパビリティが
     有効な場合にのみ効果がある。

   未知のフラグ値は無視される。


  KVM_DEV_FLIC_ADAPTER_MODIFY
    既存の I/O アダプタ割り込みソースの属性を変更する。アダプタと操作を指定する
    kvm_s390_io_adapter_req を受け取る::

	struct kvm_s390_io_adapter_req {
		__u32 id;
		__u8 type;
		__u8 mask;
		__u16 pad0;
		__u64 addr;
	};

    id はアダプタを指定し、type は操作を指定する。サポートされる操作は次のとおりである。

    KVM_S390_IO_ADAPTER_MASK
      mask で指定されたとおりにアダプタをマスクまたはマスク解除する

    KVM_S390_IO_ADAPTER_MAP
      アダプタのインジケータまたはサマリページを長期ピンのためにマップし、
      アトミックコンテキストで割り込み注入を実行できるようにする。長期ピンが
      不可能な場合 (例: ファイルバックのメモリ)、ページは短期ピンで検証され、
      ioctl は成功を返す。割り込み注入は、割り込みごとに短期ピンを使う
      非アトミックな irqfd パスを使う。Secure Execution モードではこれは
      何もしない操作であり、ioctl は成功を返す。

    KVM_S390_IO_ADAPTER_UNMAP
      以前にマップしたアダプタのインジケータまたはサマリページをアンマップし、
      長期ピンを解放する。ページが長期ピンされていなかった場合 (例: ファイルバックの
      メモリ)、マップエントリは削除され、成功が返る。以前のマップエントリが
      存在しない場合は -ENOENT を返す。Secure Execution モードではこれは
      何もしない操作であり、ioctl は成功を返す。

  KVM_DEV_FLIC_AISM
    AIS ケイパビリティが有効な場合、指定された isc のアダプタ割り込み抑制モードを変更する。
    次を記述する kvm_s390_ais_req を受け取る::

	struct kvm_s390_ais_req {
		__u8 isc;
		__u16 mode;
	};

    isc には対象の I/O 割り込みサブクラスが入り、mode には対象の
    アダプタ割り込み抑制モードが入る。現在サポートされるモードは次のとおりである。

    - KVM_S390_AIS_MODE_ALL: ALL-Interruptions モード。つまり airq 注入は
      常に許可される。
    - KVM_S390_AIS_MODE_SINGLE: SINGLE-Interruption モード。つまり airq 注入は
      1 回だけ許可され、以降のアダプタ割り込みは、モードが再び ALL-Interruptions
      または SINGLE-Interruption モードに設定されるまで抑制される。

  KVM_DEV_FLIC_AIRQ_INJECT
    指定されたアダプタでアダプタ割り込みを注入する。
    attr->attr にはアダプタの一意な ID が入り、これによりアダプタ固有の
    チェックとアクションが可能になる。
    AIS の対象となるアダプタについては、AIS ケイパビリティが有効であることを条件に、
    アダプタ割り込み抑制モードに従って isc の airq 注入抑制を処理する。

  KVM_DEV_FLIC_AISM_ALL
    すべての ISC のアダプタ割り込み抑制モードを取得または設定する。
    次を記述する kvm_s390_ais_all を受け取る::

	struct kvm_s390_ais_all {
	       __u8 simm; /* Single-Interruption-Mode mask */
	       __u8 nimm; /* No-Interruption-Mode mask *
	};

    simm にはすべての ISC の Single-Interruption-Mode マスクが入り、nimm には
    すべての ISC の No-Interruption-Mode マスクが入る。simm と nimm の各ビットは
    1 つの ISC に対応する (MSB0 ビット 0 は ISC 0 に対応、以下同様)。simm ビットと
    nimm ビットの組み合わせが、ISC の AIS モードを表す。

    KVM_DEV_FLIC_AISM_ALL は KVM_CAP_S390_AIS_MIGRATION で示される。

備考: 未知のグループまたは属性で FLIC に対して実行される
KVM_SET_DEVICE_ATTR/KVM_GET_DEVICE_ATTR デバイス ioctl は、エラーコード EINVAL を返す
(API ドキュメントで規定されている ENXIO の代わりに)。使用の試行から生じる
エラーコードに基づいて、FLIC 操作が利用できないと結論付けることはできない。

.. note:: KVM_DEV_FLIC_CLEAR_IO_IRQ ioctl は、schid がゼロの場合に EINVAL を返す。
