.. SPDX-License-Identifier: GPL-2.0

======================================
Secure Encrypted Virtualization (SEV)
======================================

概要
========

Secure Encrypted Virtualization (SEV) は AMD
プロセッサに搭載された機能である。

SEV は AMD-V
アーキテクチャの拡張であり、ハイパーバイザの制御下で仮想マシン（VM）を実行できるようにする。SEV
を有効にすると、VM のメモリ内容は、その VM に固有の鍵で透過的に暗号化される。

ハイパーバイザは CPUID 命令で SEV のサポート状況を判定できる。CPUID ファンクション
0x8000001f は SEV に関する情報を報告する::

	0x8000001f[eax]:
			Bit[1] 	indicates support for SEV
	    ...
		  [ecx]:
			Bits[31:0]  Number of encrypted guests supported simultaneously

SEV のサポートがある場合、MSR 0xc001_0010（MSR_AMD64_SYSCFG）と
MSR 0xc001_0015（MSR_K7_HWCR）を使うと、SEV
を有効にできるかどうかを判定できる::

	0xc001_0010:
		Bit[23]	   1 = memory encryption can be enabled
			   0 = memory encryption can not be enabled

	0xc001_0015:
		Bit[0]	   1 = memory encryption can be enabled
			   0 = memory encryption can not be enabled

SEV のサポートが利用できる場合、VMRUN を実行する前に SEV ビットを設定すると、特定の
VM で SEV を有効にできる。::

	VMCB[0x90]:
		Bit[1]	    1 = SEV is enabled
			    0 = SEV is disabled

SEV ハードウェアは ASID を使って、メモリ暗号化鍵を VM に対応付ける。そのため、SEV
を有効にしたゲストの ASID は、1 から CPUID 0x8000001f[ecx]
フィールドで定義される最大値までの範囲でなければならない。

KVM_MEMORY_ENCRYPT_OP ioctl
===============================

SEV にアクセスするための主要な ioctl は KVM_MEMORY_ENCRYPT_OP
で、これは VM
のファイルディスクリプタに対して操作する。KVM_MEMORY_ENCRYPT_OP の引数が
NULL の場合、ioctl は SEV が有効なら 0 を返し、無効なら ``ENOTTY``
を返す（古いバージョンの Linux では、引数が NULL でも ioctl
は通常どおり実行しようとするため、SEV が有効なら 0 ではなく ``EFAULT``
を返す可能性が高い）。引数が非 NULL の場合、KVM_MEMORY_ENCRYPT_OP
の引数は struct kvm_sev_cmd でなければならない::

       struct kvm_sev_cmd {
               __u32 id;
               __u64 data;
               __u32 error;
               __u32 sev_fd;
       };


``id`` フィールドにはサブコマンドが入り、``data``
フィールドはコマンドに固有の引数を持つ別の構造体を指す。``sev_fd`` は、必要なら
``/dev/sev``
デバイスでオープンしたファイルディスクリプタを指すべきである（個々のコマンドを参照）。

出力では、``error`` は成功なら 0、そうでなければエラーコードになる。エラーコードは
``<linux/psp-dev.h>`` で定義されている。

KVM は、SEV
ゲストの起動、実行、スナップショット、マイグレーション、廃止といった一般的なライフサイクルイベントを支えるために、次のコマンドを実装している。

1. KVM_SEV_INIT2
----------------

KVM_SEV_INIT2 コマンドは、ハイパーバイザが SEV
プラットフォームコンテキストを初期化するために使う。一般的なワークフローでは、このコマンドを最初に発行すべきである。

このコマンドが受け付けられるには、KVM_X86_SEV_VM または
KVM_X86_SEV_ES_VM のいずれかを KVM_CREATE_VM ioctl
に渡しておく必要がある。逆に、これらのマシンタイプで作成した仮想マシンは、KVM_SEV_INIT2
を呼び出すまで実行できない。

パラメータ: struct kvm_sev_init (in)

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_init {
                __u64 vmsa_features;  /* initial value of features field in VMSA */
                __u32 flags;          /* must be 0 */
                __u16 ghcb_version;   /* maximum guest GHCB version allowed */
                __u16 pad1;
                __u32 pad2[8];
        };

``flags`` または ``vmsa_features``
に設定されたビットのうち、ハイパーバイザがサポートしないものがあるとエラーになる。SEV
仮想マシンは VMSA を持たないため、``vmsa_features`` は 0
でなければならない。

SEV 仮想マシンは GHCB 要求を発行しないため、``ghcb_version`` は 0
でなければならない。他のゲストタイプで ``ghcb_version`` が 0
の場合、許容されるゲスト GHCB プロトコルの最大値はデフォルトでバージョン 2 になる。

このコマンドは、非推奨の KVM_SEV_INIT と KVM_SEV_ES_INIT
コマンドを置き換える。これらのコマンドにはパラメータがなく（```data```
フィールドは未使用だった）、KVM_X86_DEFAULT_VM マシンタイプ（0）でのみ動作する。

これらは次のように振る舞う:

* KVM_SEV_INIT では VM タイプが
  KVM_X86_SEV_VM、KVM_SEV_ES_INIT では
  KVM_X86_SEV_ES_VM である

* ``struct kvm_sev_init`` の ``flags`` フィールドと
  ``vmsa_features`` フィールドが 0 に設定され、``ghcb_version``
  は KVM_SEV_INIT では 0、KVM_SEV_ES_INIT では 1 に設定される。

``KVM_X86_SEV_VMSA_FEATURES`` 属性が存在しない場合、ハイパーバイザは
KVM_SEV_INIT と KVM_SEV_ES_INIT
しかサポートしない。その場合、``kvm-amd.ko`` の ``debug_swap``
パラメータの値によっては、KVM_SEV_ES_INIT がデバッグスワップ VMSA 機能（ビット
5）を設定する可能性がある点に注意すること。

2. KVM_SEV_LAUNCH_START
-----------------------

KVM_SEV_LAUNCH_START
コマンドは、メモリ暗号化コンテキストを作成するために使う。暗号化コンテキストを作成するには、ユーザはゲストポリシー、オーナーの公開
Diffie-Hellman（PDH）鍵、セッション情報を提供しなければならない。

パラメータ: struct kvm_sev_launch_start (in/out)

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_launch_start {
                __u32 handle;           /* if zero then firmware creates a new handle */
                __u32 policy;           /* guest's policy */

                __u64 dh_uaddr;         /* userspace address pointing to the guest owner's PDH key */
                __u32 dh_len;

                __u64 session_addr;     /* userspace address which points to the guest session information */
                __u32 session_len;
        };

成功すると 'handle' フィールドに新しいハンドルが入り、エラー時には負の値が入る。

KVM_SEV_LAUNCH_START では ``sev_fd``
フィールドが有効である必要がある。

詳細は SEV 仕様の 6.2 節を参照。

3. KVM_SEV_LAUNCH_UPDATE_DATA
-----------------------------

KVM_SEV_LAUNCH_UPDATE_DATA
は、メモリ領域を暗号化するために使う。あわせてメモリ内容の測定値も計算する。測定値はメモリ内容の署名であり、ファームウェアがメモリを正しく暗号化したことを示すアテステーションとして、ゲストオーナーに送ることができる。

パラメータ (in): struct kvm_sev_launch_update_data

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_launch_update_data {
                __u64 uaddr;    /* userspace address to be encrypted (must be 16-byte aligned) */
                __u32 len;      /* length of the data to be encrypted (must be 16-byte aligned) */
        };

詳細は SEV 仕様の 6.3 節を参照。

4. KVM_SEV_LAUNCH_MEASURE
-------------------------

KVM_SEV_LAUNCH_MEASURE
コマンドは、KVM_SEV_LAUNCH_UPDATE_DATA
コマンドで暗号化したデータの測定値を取得するために使う。ゲストオーナーは、測定値を検証できるまで、ゲストに機密情報を渡すのを待ってもよい。ゲストオーナーは起動時のゲストの初期内容を知っているため、測定値は期待する値と比較して検証できる。

呼び出し時に len が 0 なら、測定値ブロブの長さが len に書き込まれ、uaddr
は使われない。

パラメータ (in): struct kvm_sev_launch_measure

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_launch_measure {
                __u64 uaddr;    /* where to copy the measurement */
                __u32 len;      /* length of measurement blob */
        };

測定値の検証フローの詳細は、SEV 仕様の 6.4 節を参照。

5. KVM_SEV_LAUNCH_FINISH
------------------------

起動フローが完了した後、KVM_SEV_LAUNCH_FINISH
コマンドを発行すると、ゲストを実行できる状態にできる。

戻り値: 成功なら 0、エラーなら負の値

6. KVM_SEV_GUEST_STATUS
-----------------------

KVM_SEV_GUEST_STATUS コマンドは、SEV
を有効にしたゲストの状態情報を取得するために使う。

パラメータ (out): struct kvm_sev_guest_status

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_guest_status {
                __u32 handle;   /* guest handle */
                __u32 policy;   /* guest policy */
                __u8 state;     /* guest state (see enum below) */
        };

SEV ゲストの状態:

::

        enum {
        SEV_STATE_INVALID = 0;
        SEV_STATE_LAUNCHING,    /* guest is currently being launched */
        SEV_STATE_SECRET,       /* guest is being launched and ready to accept the ciphertext data */
        SEV_STATE_RUNNING,      /* guest is fully launched and running */
        SEV_STATE_RECEIVING,    /* guest is being migrated in from another SEV machine */
        SEV_STATE_SENDING       /* guest is getting migrated out to another SEV machine */
        };

7. KVM_SEV_DBG_DECRYPT
----------------------

KVM_SEV_DEBUG_DECRYPT
コマンドを使うと、ハイパーバイザはファームウェアに対して、指定したメモリ領域のデータを復号するよう要求できる。

パラメータ (in): struct kvm_sev_dbg

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_dbg {
                __u64 src_uaddr;        /* userspace address of data to decrypt */
                __u64 dst_uaddr;        /* userspace address of destination */
                __u32 len;              /* length of memory region to decrypt */
        };

ゲストポリシーがデバッグを許可していない場合、このコマンドはエラーを返す。

8. KVM_SEV_DBG_ENCRYPT
----------------------

KVM_SEV_DEBUG_ENCRYPT
コマンドを使うと、ハイパーバイザはファームウェアに対して、指定したメモリ領域のデータを暗号化するよう要求できる。

パラメータ (in): struct kvm_sev_dbg

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_dbg {
                __u64 src_uaddr;        /* userspace address of data to encrypt */
                __u64 dst_uaddr;        /* userspace address of destination */
                __u32 len;              /* length of memory region to encrypt */
        };

ゲストポリシーがデバッグを許可していない場合、このコマンドはエラーを返す。

9. KVM_SEV_LAUNCH_SECRET
------------------------

KVM_SEV_LAUNCH_SECRET
コマンドを使うと、ハイパーバイザは、ゲストオーナーが測定値を検証した後に秘密データを注入できる。

パラメータ (in): struct kvm_sev_launch_secret

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_launch_secret {
                __u64 hdr_uaddr;        /* userspace address containing the packet header */
                __u32 hdr_len;

                __u64 guest_uaddr;      /* the guest memory region where the secret should be injected */
                __u32 guest_len;

                __u64 trans_uaddr;      /* the hypervisor memory region which contains the secret */
                __u32 trans_len;
        };

10. KVM_SEV_GET_ATTESTATION_REPORT
----------------------------------

KVM_SEV_GET_ATTESTATION_REPORT
コマンドを使うと、ハイパーバイザはアテステーションレポートを照会できる。このレポートには、KVM_SEV_LAUNCH
系コマンドで渡されたゲストメモリと VMSA の SHA-256 ダイジェストが含まれ、PEK
で署名されている。このコマンドが返すダイジェストは、ゲストオーナーが
KVM_SEV_LAUNCH_MEASURE で使うダイジェストと一致すべきである。

呼び出し時に len が 0 なら、測定値ブロブの長さが len に書き込まれ、uaddr
は使われない。

パラメータ (in): struct kvm_sev_attestation_report

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_attestation_report {
                __u8 mnonce[16];        /* A random mnonce that will be placed in the report */

                __u64 uaddr;            /* userspace address where the report should be copied */
                __u32 len;
        };

11. KVM_SEV_SEND_START
----------------------

KVM_SEV_SEND_START
コマンドを使うと、ハイパーバイザは送信側のゲスト暗号化コンテキストを作成できる。

呼び出し時に session_len が 0 なら、ゲストセッション情報の長さが
session_len に書き込まれ、他のフィールドはすべて使われない。

パラメータ (in): struct kvm_sev_send_start

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_send_start {
                __u32 policy;                 /* guest policy */

                __u64 pdh_cert_uaddr;         /* platform Diffie-Hellman certificate */
                __u32 pdh_cert_len;

                __u64 plat_certs_uaddr;        /* platform certificate chain */
                __u32 plat_certs_len;

                __u64 amd_certs_uaddr;        /* AMD certificate */
                __u32 amd_certs_len;

                __u64 session_uaddr;          /* Guest session information */
                __u32 session_len;
        };

12. KVM_SEV_SEND_UPDATE_DATA
----------------------------

KVM_SEV_SEND_UPDATE_DATA
コマンドを使うと、ハイパーバイザは、KVM_SEV_SEND_START
で作成した暗号化コンテキストで送信側のゲストメモリ領域を暗号化できる。

呼び出し時に hdr_len または trans_len が 0
なら、パケットヘッダとトランスポート領域の長さがそれぞれ hdr_len と trans_len
に書き込まれ、他のフィールドはすべて使われない。

パラメータ (in): struct kvm_sev_send_update_data

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_send_update_data {
                __u64 hdr_uaddr;        /* userspace address containing the packet header */
                __u32 hdr_len;

                __u64 guest_uaddr;      /* the source memory region to be encrypted */
                __u32 guest_len;

                __u64 trans_uaddr;      /* the destination memory region  */
                __u32 trans_len;
        };

13. KVM_SEV_SEND_FINISH
------------------------

マイグレーションフローが完了した後、ハイパーバイザは KVM_SEV_SEND_FINISH
コマンドを発行して暗号化コンテキストを削除できる。

戻り値: 成功なら 0、エラーなら負の値

14. KVM_SEV_SEND_CANCEL
------------------------

SEND_START の完了後、SEND_FINISH の前なら、移行元の VMM は
SEND_CANCEL
コマンドを発行してマイグレーションを停止できる。これは、キャンセルしたマイグレーションが後で新しい移行先で再開できるようにするために必要である。

戻り値: 成功なら 0、エラーなら負の値

15. KVM_SEV_RECEIVE_START
-------------------------

KVM_SEV_RECEIVE_START コマンドは、受け入れ側の SEV
ゲストのメモリ暗号化コンテキストを作成するために使う。暗号化コンテキストを作成するには、ユーザはゲストポリシー、プラットフォームの公開
Diffie-Hellman（PDH）鍵、セッション情報を提供しなければならない。

パラメータ: struct kvm_sev_receive_start (in/out)

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_receive_start {
                __u32 handle;           /* if zero then firmware creates a new handle */
                __u32 policy;           /* guest's policy */

                __u64 pdh_uaddr;        /* userspace address pointing to the PDH key */
                __u32 pdh_len;

                __u64 session_uaddr;    /* userspace address which points to the guest session information */
                __u32 session_len;
        };

成功すると 'handle' フィールドに新しいハンドルが入り、エラー時には負の値が入る。

詳細は SEV 仕様の 6.12 節を参照。

16. KVM_SEV_RECEIVE_UPDATE_DATA
-------------------------------

KVM_SEV_RECEIVE_UPDATE_DATA
コマンドを使うと、ハイパーバイザは、KVM_SEV_RECEIVE_START
で作成した暗号化コンテキストで、受け入れ側のバッファをゲストメモリ領域にコピーできる。

パラメータ (in): struct kvm_sev_receive_update_data

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_receive_update_data {
                __u64 hdr_uaddr;        /* userspace address containing the packet header */
                __u32 hdr_len;

                __u64 guest_uaddr;      /* the destination guest memory region */
                __u32 guest_len;

                __u64 trans_uaddr;      /* the incoming buffer memory region  */
                __u32 trans_len;
        };

17. KVM_SEV_RECEIVE_FINISH
--------------------------

マイグレーションフローが完了した後、ハイパーバイザは KVM_SEV_RECEIVE_FINISH
コマンドを発行して、ゲストを実行できる状態にできる。

戻り値: 成功なら 0、エラーなら負の値

18. KVM_SEV_SNP_LAUNCH_START
----------------------------

KVM_SNP_LAUNCH_START コマンドは、SEV-SNP
ゲストのメモリ暗号化コンテキストを作成するために使う。KVM_SEV_SNP_LAUNCH_UPDATE
または KVM_SEV_SNP_LAUNCH_FINISH を発行する前に呼び出さなければならない。

パラメータ (in): struct kvm_sev_snp_launch_start

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_snp_launch_start {
                __u64 policy;           /* Guest policy to use. */
                __u8 gosvw[16];         /* Guest OS visible workarounds. */
                __u16 flags;            /* Must be zero. */
                __u8 pad0[6];
                __u64 pad1[4];
        };

``struct kvm_sev_snp_launch_start``
の入力パラメータの詳細は、SEV-SNP 仕様 [snp-fw-abi]_ の
SNP_LAUNCH_START を参照。

19. KVM_SEV_SNP_LAUNCH_UPDATE
-----------------------------

KVM_SEV_SNP_LAUNCH_UPDATE
コマンドは、ユーザ空間から提供されたデータをゲストの GPA 範囲に読み込み、その内容を
KVM_SEV_SNP_LAUNCH_START で作成した SNP
ゲストコンテキストに測定し、その後その GPA
範囲を暗号化・検証するために使う。こうすると、ゲストが起動した時点で、ゲストコンテキストに対応する暗号化鍵でその範囲をすぐに読めるようになる。その後、ゲストは秘密をアンロックする前に、自身のコンテキストに対応する測定値をアテステーションできる。

このコマンドで初期化する GPA 範囲には、あらかじめ
KVM_MEMORY_ATTRIBUTE_PRIVATE
属性を設定しておく必要がある。この点の詳細は
KVM_SET_MEMORY_ATTRIBUTES/KVM_SET_MEMORY_ATTRIBUTES2
のドキュメントを参照。

成功した場合でも、このコマンドが要求された範囲全体を処理したとは限らない。代わりに、``struct
kvm_sev_snp_launch_update`` の
``gfn_start``、``uaddr``、``len``
フィールドが、まだ処理されていない残りの範囲に対応するよう更新される。呼び出し側は、これらのフィールドが範囲全体を処理したことを示すまで、このコマンドを呼び続けるべきである。たとえば
``len`` が 0、``gfn_start`` が範囲内の最後の GFN に 1
を足した値、``uaddr``（指定されている場合）がユーザ空間から提供された元バッファのアドレスの最後のバイトに
1 を足した値になる。

``type`` が KVM_SEV_SNP_PAGE_TYPE_ZERO
の場合、``uaddr``
は完全に無視される。他のすべてのページタイプでは、その場での変換が有効な場合（つまり、ページが共有状態のときにデータが
guest_memfd に直接書き込まれていた場合）は ``uaddr``
は省略可能で、その場での変換が無効な場合は必須である。

パラメータ (in): struct kvm_sev_snp_launch_update

戻り値: 成功なら 0、エラーなら 0 未満、呼び出し側が再試行すべき場合は -EAGAIN

::

        struct kvm_sev_snp_launch_update {
                __u64 gfn_start;        /* Guest page number to load/encrypt data into. */
                __u64 uaddr;            /* 4k-aligned address of data to be loaded/encrypted. */
                __u64 len;              /* 4k-aligned length in bytes to copy into guest memory.*/
                __u8 type;              /* The type of the guest pages being initialized. */
                __u8 pad0;
                __u16 flags;            /* Must be zero. */
                __u32 pad1;
                __u64 pad2[4];

        };

page_type として許容される値は次のように #define されている::

        KVM_SEV_SNP_PAGE_TYPE_NORMAL
        KVM_SEV_SNP_PAGE_TYPE_ZERO
        KVM_SEV_SNP_PAGE_TYPE_UNMEASURED
        KVM_SEV_SNP_PAGE_TYPE_SECRETS
        KVM_SEV_SNP_PAGE_TYPE_CPUID

各ページタイプがどのように使われ・測定されるかの詳細は、SEV-SNP 仕様
[snp-fw-abi]_ を参照。

20. KVM_SEV_SNP_LAUNCH_FINISH
-----------------------------

SNP ゲストの起動フローが完了した後、KVM_SEV_SNP_LAUNCH_FINISH
コマンドを発行すると、ゲストを実行できる状態にできる。

パラメータ (in): struct kvm_sev_snp_launch_finish

戻り値: 成功なら 0、エラーなら負の値

::

        struct kvm_sev_snp_launch_finish {
                __u64 id_block_uaddr;
                __u64 id_auth_uaddr;
                __u8 id_block_en;
                __u8 auth_key_en;
                __u8 vcek_disabled;
                __u8 host_data[32];
                __u8 pad0[3];
                __u16 flags;                    /* Must be zero */
                __u64 pad1[4];
        };


``struct kvm_sev_snp_launch_finish``
の入力パラメータの詳細は、SEV-SNP 仕様 [snp-fw-abi]_ の
SNP_LAUNCH_FINISH を参照。

21. KVM_SEV_SNP_ENABLE_REQ_CERTS
--------------------------------

KVM_SEV_SNP_ENABLE_REQ_CERTS
コマンドは、ゲストのアテステーションレポートを処理する一環として、``KVM_EXIT_SNP_REQ_CERTS``
エグジットタイプでユーザ空間にエグジットするよう KVM
を設定する。これにより、ユーザ空間は、ファームウェアがそのアテステーションレポートの署名に使う保証鍵（endorsement
key）に対応する証明書を提供できるようになる。

戻り値: 成功なら 0、エラーなら負の値

備考: ファームウェアが使う保証鍵は、SEV-SNP
ファームウェアの更新や新しい保証鍵の読み込みといった管理作業の結果として変わりうる。そのため、アテステーション要求を
SNP
ファームウェアに送る時点でファームウェアが実際に使っている保証鍵と、返す証明書データを同期させるよう注意すべきである。これを実現する推奨の方法は、次のようにファイルロック（たとえば
fcntl() の F_OFD_SETLK）を使うことである:

  - ``KVM_EXIT_SNP_REQ_CERTS``
    エグジットタイプの処理の一環として証明書データを取得・提供する前に、VMM
    は証明書ブロブファイルを読み取って KVM
    に返す前に、そのファイルに対して共有/読み取りロックまたは排他/書き込みロックを取得すべきである。そして、アテステーション要求を実際にファームウェアへ送るまで、そのロックを保持し続けるべきである。これをやりやすくするため、VMM
    は証明書データを渡した直後、vCPU を再開する直前に kvm_run の
    ``immediate_exit``
    フラグを設定できる。こうすると、ファームウェアからアテステーション要求を取得し終えた後に vCPU
    が必ず ``-EINTR`` で再びユーザ空間にエグジットするので、その時点で VMM
    は安全にファイルロックを解放できる。

  - SNP ファームウェアの TCB 値や保証鍵を更新するツール／ライブラリ（たとえば
    ``SNP_COMMIT``、``SNP_SET_CONFIG``、``SNP_VLEK_LOAD``
    といった /dev/sev インタフェース経由。詳細は
    Documentation/virt/coco/sev-guest.rst
    を参照）が、証明書ブロブの更新を必要とする形で更新を行う場合も、同様に、保証鍵や証明書ブロブの内容の更新の間は証明書ブロブに排他ロックを取得すべきである。これは、上記の方式を使う
    VMM
    が、アテステーション要求を実際に発行した時点でファームウェアが使っている保証鍵と同期の取れていない証明書ブロブデータを返さないようにするためである。

この方式を推奨するのは、ツールがファイルロックによるファームウェア／証明書の更新の同期に、かなり汎用的で自然な方法を使えるようにするためであり、ツール／VMM／ベンダー間の相互運用性を保ちやすくするはずである。

デバイス属性 API
====================

SEV 実装の属性は、``/dev/kvm`` デバイスノードに対して
``KVM_HAS_DEVICE_ATTR`` と ``KVM_GET_DEVICE_ATTR``
ioctl を使い、グループ ``KVM_X86_GRP_SEV`` を指定して取得できる。

現在実装されている属性は次のとおりである:

* ``KVM_X86_SEV_VMSA_FEATURES``: ``KVM_SEV_INIT2`` の
  ``vmsa_features`` で受け付けられるすべてのビットの集合を返す。

* ``KVM_X86_SEV_SNP_REQ_CERTS``: カーネルが
  ``KVM_EXIT_SNP_REQ_CERTS`` エグジットをサポートしていれば 1
  を返す。このエグジットにより、ゲストが発行する SNP
  アテステーション要求ごとに、ユーザ空間から保証鍵証明書を取得できる。

ファームウェア管理
===================

SEV ゲストの鍵管理は、AMD Secure
Processor（AMD-SP）と呼ばれる別のプロセッサが担う。AMD-SP
内で動作するファームウェアは、ブートストラップコードの暗号化、スナップショット、マイグレーション、ゲストのデバッグといった一般的なハイパーバイザの操作を行うための、安全な鍵管理インタフェースを提供する。詳細は
SEV Key Management 仕様 [api-spec]_ を参照。

AMD-SP ファームウェアは、自身の不揮発性ストレージを使って初期化することも、OS が
``ccp`` モジュールの ``init_ex_path`` パラメータを使ってファームウェア用の
NV ストレージを管理することもできる。``init_ex_path``
で指定したファイルが存在しないか無効な場合、OS は PSP
の不揮発性ストレージでそのファイルを作成または上書きする。

参考文献
==========


詳細は
[white-paper]_、[api-spec]_、[amd-apm]_、[kvm-forum]_、[snp-fw-abi]_
を参照。

.. [white-paper] https://docs.amd.com/v/u/en-US/memory-encryption-white-paper
.. [api-spec] https://docs.amd.com/v/u/en-US/55766_PUB_3.24_SEV_API
.. [amd-apm] https://docs.amd.com/v/u/en-US/24593_3.44_APM_Vol2 (section 15.34)
.. [kvm-forum]  https://www.linux-kvm.org/images/7/74/02x08A-Thomas_Lendacky-AMDs_Virtualizatoin_Memory_Encryption_Technology.pdf
.. [snp-fw-abi] https://www.amd.com/content/dam/amd/en/documents/developer/56860.pdf
