.. SPDX-License-Identifier: GPL-2.0

===================
VFIO 仮想デバイス
===================

サポートするデバイスタイプ:

  - KVM_DEV_TYPE_VFIO

VM ごとに VFIO インスタンスは 1 つしか生成できない。生成されたデバイスは、
その VM が使用中の VFIO ファイル（group または device）と、VM の正しさと
高速化にとって重要なそれら group/device の機能を追跡する。VM が group/device
を使用可能／使用不可にしたら、その存在を KVM に伝える必要がある。KVM に
登録されると、その VFIO ファイルへの参照は KVM が保持する。

Groups:
  KVM_DEV_VFIO_FILE
	別名: KVM_DEV_VFIO_GROUP

KVM_DEV_VFIO_FILE の属性:
  KVM_DEV_VFIO_FILE_ADD: VFIO ファイル（group/device）を VFIO-KVM デバイスの
	追跡対象に追加する

	kvm_device_attr.addr は、VFIO ファイルのファイルディスクリプタ（int32_t）を
	指す。

  KVM_DEV_VFIO_FILE_DEL: VFIO ファイル（group/device）を VFIO-KVM デバイスの
	追跡対象から削除する

	kvm_device_attr.addr は、VFIO ファイルのファイルディスクリプタ（int32_t）を
	指す。

KVM_DEV_VFIO_GROUP（VFIO group fd の扱いに限定された従来の kvm デバイスグループ）:
  KVM_DEV_VFIO_GROUP_ADD: group fd のみを対象とする点を除き、
	KVM_DEV_VFIO_FILE_ADD と同じ

  KVM_DEV_VFIO_GROUP_DEL: group fd のみを対象とする点を除き、
	KVM_DEV_VFIO_FILE_DEL と同じ

  KVM_DEV_VFIO_GROUP_SET_SPAPR_TCE: sPAPR KVM が確保した、ゲストから見える
	TCE テーブルを関連付ける。
	kvm_device_attr.addr は次の構造体を指す::

		struct kvm_vfio_spapr_tce {
			__s32	groupfd;
			__s32	tablefd;
		};

	where:
	- @groupfd は VFIO グループのファイルディスクリプタである。
	- @tablefd は KVM_CREATE_SPAPR_TCE で確保した TCE テーブルの
	  ファイルディスクリプタである。

上記の FILE/GROUP_ADD 操作は、VFIO_GROUP_GET_DEVICE_FD でデバイスのファイル
ディスクリプタにアクセスする前に呼び出す必要がある。これは、.open_device()
コールバックで kvm ポインタが設定されていることを要求するドライバに対応する
ためである。VFIO_DEVICE_BIND_IOMMUFD 経由でデバイスにアクセスするキャラクタ
デバイスのオープンでも同じである。そのようなファイルディスクリプタでは、
先の文で述べたドライバに対応するため、VFIO_DEVICE_BIND_IOMMUFD の前に
FILE_ADD を呼び出す必要がある。
