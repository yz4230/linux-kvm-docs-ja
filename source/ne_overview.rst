.. SPDX-License-Identifier: GPL-2.0

==============
Nitro Enclaves
==============

概要
========

Nitro Enclaves (NE) は Amazon Elastic Compute Cloud (EC2) の新しい
ケイパビリティで、顧客が EC2 インスタンス内に分離されたコンピュート環境を
切り出せるようにする [1]。

たとえば、機密データを処理するアプリケーションが VM で動いている場合、
同じ VM で動くほかのアプリケーションから分離できる。このアプリケーションは、
プライマリ VM とは別の VM、すなわち enclave で動く。enclave は、それを作った
VM と並んで動く。この構成は、低レイテンシを必要とするアプリケーションの
要求に合う。

アップストリームの Linux カーネルにある NE カーネルドライバが現在
サポートするアーキテクチャは、x86 と ARM64 である。

enclave に割り当てられるメモリや CPU などのリソースは、プライマリ VM から
切り出される。各 enclave はプライマリ VM で動く 1 つのプロセスに対応付けられ、
そのプロセスが ioctl インタフェースを通じて NE カーネルドライバと通信する。

この意味で、2 つの構成要素がある。

1. enclave 抽象化プロセス - プライマリ VM のゲストで動くユーザ空間プロセスで、
NE ドライバが提供する ioctl インタフェースを使って enclave VM（下記の 2）を
生成する。

プライマリ VM には、NE のエミュレートされた PCI デバイスが公開される。この
新しい PCI デバイスのドライバは、NE ドライバに含まれる。

ioctl の処理は PCI デバイスのコマンドに対応付けられる。たとえば
NE_START_ENCLAVE ioctl は enclave 起動の PCI コマンドに対応する。PCI デバイスの
コマンドは、ハイパーバイザ側で行われる動作に変換される。そのハイパーバイザは、
プライマリ VM が動くホストで動く Nitro ハイパーバイザである。Nitro ハイパーバイザ
は、KVM の中核技術に基づいている。

2. enclave 自体 - それを作ったプライマリ VM と同じホストで動く VM である。
メモリと CPU はプライマリ VM から切り出され、enclave VM 専用になる。enclave には
永続ストレージが接続されない。

プライマリ VM から切り出して enclave に渡すメモリ領域は、2 MiB / 1 GiB で
アラインされた物理的に連続したメモリ領域（またはその倍数。たとえば 8 MiB）
である必要がある。メモリは、たとえばユーザ空間から hugetlbfs を使って
割り当てられる [2][3][7]。enclave のメモリサイズは、少なくとも 64 MiB で
ある必要がある。enclave のメモリと CPU は、同じ NUMA ノードのものである
必要がある。

enclave は専用のコアで動く。CPU 0 とその兄弟 CPU は、プライマリ VM が使える
ように残しておく必要がある。NE 用の CPU プールは、管理者ケイパビリティを
持つユーザが設定する必要がある。CPU プールの書式については、カーネル
ドキュメントの cpu list の節 [4] を参照。

enclave は、virtio-vsock [5] を使ったローカルの通信チャネルでプライマリ VM と
通信する。プライマリ VM は virtio-pci の vsock エミュレートデバイスを持ち、
enclave VM は virtio-mmio の vsock エミュレートデバイスを持つ。vsock デバイスは
シグナリングに eventfd を使う。enclave VM は、virtio-vsock デバイスからの
割り込みを受け取るために、通常のインタフェース（local APIC と IOAPIC）を使う。
virtio-mmio デバイスは、通常の 4 GiB 未満のメモリに置かれる。

enclave で動くアプリケーションは、enclave VM で動く OS
（カーネル、ramdisk、init など）と一緒に enclave イメージにまとめる必要が
ある。enclave VM は独自のカーネルを持ち、標準の Linux ブートプロトコルに
従う [6][8]。

カーネルの bzImage、カーネルコマンドライン、ramdisk は、Enclave Image
Format (EIF) の一部である。さらに、マジックナンバー、eif バージョン、
イメージサイズ、CRC などのメタデータを含む EIF ヘッダがある。

enclave イメージ全体（EIF）、カーネル、ramdisk についてハッシュ値が計算される。
これは、たとえば enclave VM に読み込まれた enclave イメージが、実行しようと
したものであることを確認するために使われる。

これらの暗号学的な測定値は、Nitro ハイパーバイザが生成する署名付き
アテステーションドキュメントに含まれ、enclave の同一性を証明するために
使われる。NE が連携し、そのアテステーションドキュメントを確認するサービスの
例が KMS である。

enclave イメージ（EIF）は、enclave のメモリのオフセット 8 MiB に読み込まれる。
enclave の init プロセスは、プライマリ VM の vsock CID とあらかじめ決められた
ポート 9000 に接続し、ハートビート値 0xb7 を送る。この仕組みは、enclave が
起動したことをプライマリ VM で確認するために使われる。プライマリ VM の
CID は 3 である。

enclave VM がクラッシュしたか正常に終了すると、NE ドライバが割り込みイベントを
受け取る。このイベントはさらに、poll 通知の仕組みによって、プライマリ VM で
動くユーザ空間の enclave プロセスに送られる。すると、ユーザ空間の enclave
プロセスは終了できる。

[1] https://aws.amazon.com/ec2/nitro/nitro-enclaves/
[2] https://www.kernel.org/doc/html/latest/admin-guide/mm/hugetlbpage.html
[3] https://lwn.net/Articles/807108/
[4] https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html
[5] https://man7.org/linux/man-pages/man7/vsock.7.html
[6] https://www.kernel.org/doc/html/latest/x86/boot.html
[7] https://www.kernel.org/doc/html/latest/arm64/hugetlbpage.html
[8] https://www.kernel.org/doc/html/latest/arm64/booting.html
