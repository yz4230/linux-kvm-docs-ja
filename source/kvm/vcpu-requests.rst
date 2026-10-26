.. SPDX-License-Identifier: GPL-2.0

===========================
KVM の vCPU リクエスト
===========================

概要
====

KVM は、スレッドがある vCPU スレッドに何らかの処理を依頼できるようにする
内部 API を備えている。たとえば、あるスレッドは vCPU リクエストを使って、
vCPU に自身の TLB のフラッシュを依頼できる。この API は次の関数で構成さ
れる::

  /* Check if any requests are pending for VCPU @vcpu. */
  bool kvm_request_pending(struct kvm_vcpu *vcpu);

  /* Check if VCPU @vcpu has request @req pending. */
  bool kvm_test_request(int req, struct kvm_vcpu *vcpu);

  /* Clear request @req for VCPU @vcpu. */
  void kvm_clear_request(int req, struct kvm_vcpu *vcpu);

  /*
   * Check if VCPU @vcpu has request @req pending. When the request is
   * pending it will be cleared and a memory barrier, which pairs with
   * another in kvm_make_request(), will be issued.
   */
  bool kvm_check_request(int req, struct kvm_vcpu *vcpu);

  /*
   * Make request @req of VCPU @vcpu. Issues a memory barrier, which pairs
   * with another in kvm_check_request(), prior to setting the request.
   */
  void kvm_make_request(int req, struct kvm_vcpu *vcpu);

  /* Make request @req of all VCPUs of the VM with struct kvm @kvm. */
  bool kvm_make_all_cpus_request(struct kvm *kvm, unsigned int req);

通常、依頼側はリクエストを出したあと、できるだけ早く vCPU にその処理を実
行してほしいと考える。そのため、ほとんどのリクエスト（kvm_make_request()
の呼び出し）の後には kvm_vcpu_kick() の呼び出しが続き、kvm_make_all_cpus_request()
はすべての vCPU へのキックを内部に組み込んでいる。

vCPU キック
------------

vCPU キックの目的は、KVM の何らかのメンテナンスを行うために、vCPU スレッ
ドをゲストモードから抜けさせることである。そのために IPI を送り、ゲスト
モードからの離脱を強制する。ただし、キックの時点で vCPU スレッドがゲスト
モードにいるとは限らない。そのため、vCPU スレッドのモードと状態に応じて、
キックはほかに 2 つの動作をとりうる。3 つの動作を次に挙げる:

1) IPI を送る。これによりゲストモードからの離脱が強制される。
2) スリープ中の vCPU を起こす。スリープ中の vCPU とは、ゲストモードの外で待ちキュー（waitqueue）で待っている vCPU スレッドである。これを起こすとスレッドが待ちキューから外れ、再び実行できるようになる。この動作は抑止できる。後述の KVM_REQUEST_NO_WAKEUP を参照。
3) 何もしない。vCPU がゲストモードになく、vCPU スレッドもスリープしていないときは、何もすることがない。

vCPU のモード
--------------

vCPU は ``vcpu->mode``というモード状態を持ち、ゲストがゲストモードで実行
中かどうかや、ゲストモード外のいくつかの特定の状態を追跡するのに使う。ア
ーキテクチャは ``vcpu->mode``を使って、vCPU リクエストが vCPU に確実に届
くようにしたり（「リクエストが確実に届くようにする」を参照）、不要な IPI
の送信を避けたり（「IPI の削減」を参照）、IPI の確認応答を待つようにした
り（「確認応答の待機」を参照）できる。次のモードが定義されている:

OUTSIDE_GUEST_MODE

  vCPU スレッドはゲストモードの外にいる。

IN_GUEST_MODE

  vCPU スレッドはゲストモードにいる。

EXITING_GUEST_MODE

  vCPU スレッドは IN_GUEST_MODE から OUTSIDE_GUEST_MODE へ遷移している。

READING_SHADOW_PAGE_TABLES

  vCPU スレッドはゲストモードの外にいるが、特定の vCPU リクエスト、すなわち KVM_REQ_TLB_FLUSH の送信側に、vCPU スレッドがページテーブルの読み取りを終えるまで待ってほしいと考えている。

vCPU リクエストの内部
======================

vCPU リクエストは、``vcpu->requests``ビットマップのビットインデックスに
すぎない。したがって、[atomic-ops]_ に書かれているような一般的なビット操
作も使える。例::

  clear_bit(KVM_REQ_UNBLOCK & KVM_REQUEST_MASK, &vcpu->requests);

ただし、こうすると抽象化が崩れるため、vCPU リクエストの利用者はそうしな
いようにすべきである。先頭の 8 ビットはアーキテクチャ非依存のリクエスト
用に予約されており、それ以降のビットはすべてアーキテクチャ依存のリクエス
トに使える。

アーキテクチャ非依存のリクエスト
---------------------------------

KVM_REQ_TLB_FLUSH

  KVM 共通の MMU ノティファイアは、ゲストの TLB エントリをすべてフラッシュする必要が生じることがあり、そのために kvm_flush_remote_tlbs() を呼び出す。共通の kvm_flush_remote_tlbs() 実装を使うことを選んだアーキテクチャは、この vCPU リクエストを処理する必要がある。

KVM_REQ_VM_DEAD

  このリクエストは、たとえば致命的なエラーや、VM の状態が意図的に破棄されたことにより、VM が死んでいて使えないことをすべての vCPU に伝える。

KVM_REQ_UNBLOCK

  このリクエストは、kvm_vcpu_block から抜け出すよう vCPU に伝える。たとえば、vCPU の代わりにホスト上で動くタイマハンドラから使われる。また、割り込みの経路を更新し、割り当て済みデバイスが確実に vCPU を起こすようにするためにも使われる。

KVM_REQ_OUTSIDE_GUEST_MODE

  この「リクエスト」は、依頼側が先に進む前に、対象の vCPU がゲストモードから抜けたことを保証する。対象側がとるべき動作はないので、対象に対して実際にリクエストが記録されることはない。このリクエストは「キック」に似ているが、キックと違って vCPU が実際にゲストモードから抜けたことを保証する。キックは vCPU が将来どこかで抜けることしか保証しない。たとえば、以前のキックで離脱が始まっているかもしれないが、キック対象の vCPU が完全にゲストモードから抜けた保証はない。

KVM_REQUEST_MASK
----------------

vCPU リクエストをビット操作で使う前には、KVM_REQUEST_MASK でマスクすべき
である。リクエスト番号の表現に下位 8 ビットしか使わないためである。上位
ビットはフラグとして使う。現在定義されているフラグは 2 つだけである。

vCPU リクエストのフラグ
------------------------

KVM_REQUEST_NO_WAKEUP

  このフラグは、ゲストモードで実行中の vCPU がすぐに対応する必要があるだけのリクエストに付ける。つまり、これらのリクエストのためにスリープ中の vCPU を起こす必要はない。スリープ中の vCPU は、あとで別の理由で起こされたときにこのリクエストを処理する。

KVM_REQUEST_WAIT

  このフラグを付けたリクエストを kvm_make_all_cpus_request() で発行すると、呼び出し側は先に進む前に、各 vCPU が自分の IPI に応答するのを待つ。このフラグは、IPI を受け取る vCPU にだけ当てはまる。たとえば vCPU がスリープしていて IPI が不要なら、依頼側のスレッドは待たない。したがって、このフラグは KVM_REQUEST_NO_WAKEUP と安全に組み合わせられる。KVM_REQUEST_WAIT を付けたリクエストの詳細は「確認応答の待機」を参照。

状態を伴う vCPU リクエスト
===========================

受信側の vCPU に新しい状態を処理させたい依頼側は、その vCPU スレッドの CPU
がリクエストを観測した時点で、新しく書いた状態も観測できるようにしなけれ
ばならない。そのためには、新しい状態を書いたあと、vCPU リクエストのビッ
トを立てる前に、書き込みメモリバリアを挿入する必要がある。また、受信側の
vCPU スレッドでは、リクエストのビットを読んだあと、それに対応する新しい
状態を読む前に、対応する読み取りバリアを挿入する必要がある。[lwn-mb]_ の
シナリオ 3「Message and Flag」と、カーネルドキュメント [memory-barriers]_
を参照。

kvm_check_request() と kvm_make_request() の 2 つの関数がメモリバリアを
提供するので、この要件は API の内部で処理できる。

リクエストが確実に届くようにする
=================================

vCPU にリクエストを出すときは、受信側の vCPU がリクエストを処理せずにゲ
ストモードでいつまでも実行し続ける事態を避けたい。vCPU スレッドがゲスト
モードに入る前に kvm_request_pending() を確認すること、そして必要ならキ
ックが IPI を送ってゲストモードからの離脱を強制することを保証しておけば、
この事態は起こらないと確信できる。ただし、vCPU スレッドが最後に kvm_request_pending()
を確認してからゲストモードに入るまでの期間には特別な注意が必要である。キ
ックの IPI がゲストモードからの離脱を引き起こせるのは、ゲストモードにい
る vCPU スレッドか、少なくともゲストモードに入る準備として割り込みをすで
に無効化した vCPU スレッドだけだからである。したがって、最適化された実装
（「IPI の削減」を参照）は、IPI を送らなくてよいのがいつかを確実に判断し
なければならない。s390 以外のすべてのアーキテクチャがとる解決策の 1 つは、
次のとおりである:

- 割り込みを無効化してから最後に kvm_request_pending() を確認するまでの間に、``vcpu->mode`` を IN_GUEST_MODE に設定する。
- ゲストに入るときに割り込みをアトミックに有効化する。

この解決策では、依頼側のスレッドと受信側の vCPU の両方にメモリバリアを慎
重に置く必要がある。メモリバリアがあれば、vCPU スレッドが最後の確認で !kvm_request_pending()
を観測し、そのあとすぐに自分宛ての次のリクエストが出されたとしても、その
IPI を受け取らないという事態を排除できる。これは Dekker のメモリバリアパ
ターン（[lwn-mb]_ のシナリオ 10）によって実現する。Dekker パターンには 2
つの変数が必要なので、この解決策では ``vcpu->mode``と ``vcpu->requests``
を組にする。これらをパターンに当てはめると次のようになる::

  CPU1                                    CPU2
  =================                       =================
  local_irq_disable();
  WRITE_ONCE(vcpu->mode, IN_GUEST_MODE);  kvm_make_request(REQ, vcpu);
  smp_mb();                               smp_mb();
  if (kvm_request_pending(vcpu)) {        if (READ_ONCE(vcpu->mode) ==
                                              IN_GUEST_MODE) {
      ...abort guest entry...                 ...send IPI...
  }                                       }

前述のとおり、IPI が役に立つのは、ゲストモードにいる vCPU スレッドか、す
でに割り込みを無効化した vCPU スレッドだけである。そのため、この Dekker
パターンの特定のケースでは、``vcpu->mode``を IN_GUEST_MODE に設定する前
に割り込みを無効化するよう拡張している。WRITE_ONCE() と READ_ONCE() は、
メモリバリアパターンを厳密に実装するために使い、コンパイラが ``vcpu->mode``
への慎重に設計されたアクセスに干渉しないことを保証する。

IPI の削減
-----------

vCPU にすべてのリクエストを確認させるのに必要な IPI は 1 つだけなので、IPI
はまとめられる。これは、最初に IPI を送るキックが vCPU のモードを !IN_GUEST_MODE
のいずれかに変えるようにすれば簡単にできる。この目的には、遷移状態である
EXITING_GUEST_MODE を使う。

確認応答の待機
---------------

KVM_REQUEST_WAIT フラグを立てた一部のリクエストは、対象の vCPU スレッド
が IN_GUEST_MODE 以外のモードにいるときでも、IPI を送って確認応答を待つ
必要がある。たとえば、対象の vCPU スレッドが READING_SHADOW_PAGE_TABLES
モードにいる場合がそうである。このモードは割り込みを無効化したあとに設定
される。こうした場合に対応するため、KVM_REQUEST_WAIT フラグは、IPI を送
る条件を「vCPU が IN_GUEST_MODE であること」から「vCPU が OUTSIDE_GUEST_MODE
でないこと」に変える。

リクエストを伴わない vCPU キック
---------------------------------

IPI を送るかどうかの判断は 2 変数の Dekker メモリバリアパターンに依存す
るので、リクエストを伴わない vCPU キックが正しいのはほとんどないことは明
らかである。リクエストを伴うキックでは最後の kvm_request_pending() の確
認がそうするように、IPI を出さないキックでも受信側の vCPU が何らかの動作
をするという保証がなければ、キックはまったく役に立たないかもしれない。た
とえば、モードを IN_GUEST_MODE に設定しようとしている vCPU にリクエスト
なしのキックを出すと、IPI は送られないので、vCPU スレッドはキックが起こ
そうとしていたことを実際には行わないままゲストへの進入を続けるかもしれな
い。

例外の 1 つは x86 の posted interrupt の仕組みである。ただしこの場合も、
リクエストなしの vCPU キックが、前述と同じ local_irq_disable() + smp_mb()
パターンと組み合わされる。posted interrupt ディスクリプタの ON ビット（Outstanding
Notification）が ``vcpu->requests``の役割を担う。posted interrupt を送る
ときは、``vcpu->mode``を読む前に PIR.ON を設定する。逆に vCPU スレッド側
では、vmx_sync_pir_to_irr() が ``vcpu->mode``を IN_GUEST_MODE に設定した
あとに PIR を読む。

その他の考慮事項
=================

スリープ中の vCPU
------------------

vCPU スレッドは、自分をスリープさせる可能性のある関数、たとえば kvm_vcpu_block()
を呼ぶ前や後に、リクエストを考慮する必要があるかもしれない。考慮するかど
うか、また考慮する場合にどのリクエストを考慮する必要があるかは、アーキテ
クチャに依存する。kvm_vcpu_block() は、起こすべきかどうかを確認するため
に kvm_arch_vcpu_runnable() を呼ぶ。そうする理由の 1 つは、必要ならリク
エストを確認できる関数をアーキテクチャに提供することである。

参照
====

.. [atomic-ops] Documentation/atomic_bitops.txt と Documentation/atomic_t.txt
.. [memory-barriers] Documentation/memory-barriers.txt
.. [lwn-mb] https://lwn.net/Articles/573436/
