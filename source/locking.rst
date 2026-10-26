.. SPDX-License-Identifier: GPL-2.0

====================
KVM のロックの概要
====================

1. 取得順序
-----------

mutex の取得順序は次のとおりである。

- cpus_read_lock() は kvm_lock の外側で取得する

- kvm_usage_lock は cpus_read_lock() の外側で取得する

- kvm->lock は vcpu->mutex の外側で取得する

- kvm->lock は kvm->slots_lock および kvm->irq_lock の外側で取得する

- vcpu->mutex は kvm->slots_lock および kvm->slots_arch_lock の外側で取得する

- kvm->slots_lock は kvm->irq_lock の外側で取得する。ただし、両者を一緒に
  取得することはごくまれである。

- kvm->mn_active_invalidate_count は、invalidate_range_start() と
  invalidate_range_end() のコールバックの組が同じ memslots 配列を使うことを
  保証する。memslots を変更するときは待機側で kvm->slots_lock と
  kvm->slots_arch_lock を取得する。したがって、MMU ノーティファイアは
  kvm->slots_lock も kvm->slots_arch_lock も取得してはならない。

cpus_read_lock() と kvm_lock:

- cpus_read_lock() を kvm_lock の外側で取得するのは、それが公式の順序であっても
  問題がある。kvm_lock を保持している間に、無意識に cpus_read_lock() を
  引き起こすことが非常に起きやすいためである。vm_list をたどるときは注意する。
  たとえば、可能な限り複雑な操作を避ける。

SRCU について:

- ``synchronize_srcu(&kvm->srcu)`` は kvm->lock、vcpu->mutex、kvm->slots_lock の
  クリティカルセクションの内側で呼び出される。これらのロックは kvm->srcu の
  リード側クリティカルセクションの内側では取得しては _ならない_。つまり、
  次のコードは壊れている::

      srcu_read_lock(&kvm->srcu);
      mutex_lock(&kvm->slots_lock);

- 一方、kvm->slots_arch_lock は ``synchronize_srcu()`` の呼び出しの前に
  解放される。したがって、kvm->srcu のリード側クリティカルセクションの内側で、
  たとえば vmexit を処理している間に取得して _よい_。

x86 の場合:

- vcpu->mutex は kvm->arch.hyperv.hv_lock および kvm->arch.xen.xen_lock の
  外側で取得する

- kvm->arch.mmu_lock は rwlock である。kvm->arch.tdp_mmu_pages_lock と
  kvm->arch.mmu_unsync_pages_lock のクリティカルセクションも
  kvm->arch.mmu_lock を取得しなければならない

その他はすべてリーフである。クリティカルセクションの内側で取得するロックは
他にない。

2. 例外
-------

高速ページフォールト:

高速ページフォールトは、x86 で mmu-lock の外側でゲストのページフォールトを
修正する高速パスである。現在、ページフォールトは次の 2 つのケースのいずれかで
高速に処理できる。

1. アクセストラッキング: SPTE が存在しないが、アクセストラッキングのために
   マークされている。これは、保存された R/X ビットを復元する必要があることを
   意味する。これについては後で詳しく説明する。

2. 書き込み保護: SPTE が存在し、フォールトが書き込み保護によって引き起こされて
   いる。これは、spte の W ビットを変更するだけでよいことを意味する。

競合をすべて避けるために使うのは、spte の Host-writable ビットと
MMU-writable ビットである。

- Host-writable は、その gfn がホストカーネルのページテーブルとその KVM
  メモリスロットの両方で書き込み可能であることを意味する。
- MMU-writable は、その gfn がゲストの mmu で書き込み可能であり、
  シャドウページの書き込み保護によって書き込み保護されていないことを意味する。

高速ページフォールトのパスでは、spte.HOST_WRITEABLE = 1 かつ
spte.WRITE_PROTECT = 1 のときに cmpxchg を使って spte の W ビットをアトミックに
セットする。アクセストラッキングされた spte であれば保存された R/X ビットを
復元し、あるいはその両方を行う。これらのビットを変更するときは常に cmpxchg で
検出できるため、これは安全である。

ただし、次のケースは注意深く確認する必要がある。

1) gfn から pfn へのマッピング

gfn から pfn へのマッピングは、cmpxchg の間ずっと pfn が変わらないことしか
保証できないため、途中で変わりうる。これは ABA 問題である。たとえば、次の
ケースが起こる。

+------------------------------------------------------------------------+
| 最初に::                                                               |
|                                                                        |
|	gpte = gfn1                                                      |
|	gfn1 is mapped to pfn1 on host                                   |
|	spte is the shadow page table entry corresponding with gpte and  |
|	spte = pfn1                                                      |
+------------------------------------------------------------------------+
| 高速ページフォールトのパスで:                                          |
+------------------------------------+-----------------------------------+
| CPU 0:                             | CPU 1:                            |
+------------------------------------+-----------------------------------+
| ::                                 |                                   |
|                                    |                                   |
|   old_spte = *spte;                |                                   |
+------------------------------------+-----------------------------------+
|                                    | pfn1 がスワップアウトされる::     |
|                                    |                                   |
|                                    |    spte = 0;                      |
|                                    |                                   |
|                                    | pfn1 が gfn2 に再割り当てされる。 |
|                                    |                                   |
|                                    | ゲストによって gpte が            |
|                                    | gfn2 を指すように変更される::     |
|                                    |                                   |
|                                    |    spte = pfn1;                   |
+------------------------------------+-----------------------------------+
| ::                                                                     |
|                                                                        |
|   if (cmpxchg(spte, old_spte, old_spte+W)                              |
|	mark_page_dirty(vcpu->kvm, gfn1)                                 |
|            OOPS!!!                                                     |
+------------------------------------------------------------------------+

gfn1 に対してダーティログを取る。つまり gfn2 はダーティビットマップから
失われる。

直接 sp では、直接 sp の spte が gfn に固定されているため、これを容易に
避けられる。間接 sp では、単純化のために高速ページフォールトを無効にした。

間接 sp の解決策は、cmpxchg の前に gfn をピン留めすることである。ピン留めした
後は:

- pfn の参照カウントを保持している。つまり、pfn は解放されて別の gfn に
  再利用されることがない。
- pfn は書き込み可能であり、したがって KSM によって異なる gfn 間で共有される
  ことがない。

そうすれば、gfn に対してダーティビットマップが正しく設定されることを保証できる。

2) ダーティビットのトラッキング

元のコードでは、spte が読み出し専用で Accessed ビットがすでにセットされている
場合、spte を（アトミックでなく）高速に更新できた。Accessed ビットと Dirty
ビットは失われないからである。

しかし、高速ページフォールトの後はこれは成り立たない。spte を読み出してから
更新するまでの間に spte が書き込み可能とマークされうるからである。次のケースの
ようになる。

+-------------------------------------------------------------------------+
| 最初に::                                                                |
|                                                                         |
|  spte.W = 0                                                             |
|  spte.Accessed = 1                                                      |
+-------------------------------------+-----------------------------------+
| CPU 0:                              | CPU 1:                            |
+-------------------------------------+-----------------------------------+
| mmu_spte_update() の中::            |                                   |
|                                     |                                   |
|  old_spte = *spte;                  |                                   |
|                                     |                                   |
|                                     |                                   |
|  /* 'if' condition is satisfied. */ |                                   |
|  if (old_spte.Accessed == 1 &&      |                                   |
|       old_spte.W == 0)              |                                   |
|     spte = new_spte;                |                                   |
+-------------------------------------+-----------------------------------+
|                                     | 高速ページフォールトのパスで::    |
|                                     |                                   |
|                                     |    spte.W = 1                     |
|                                     |                                   |
|                                     | spte へのメモリ書き込み::         |
|                                     |                                   |
|                                     |    spte.Dirty = 1                 |
+-------------------------------------+-----------------------------------+
|  ::                                 |                                   |
|                                     |                                   |
|   else                              |                                   |
|     old_spte = xchg(spte, new_spte);|                                   |
|   if (old_spte.Accessed &&          |                                   |
|       !new_spte.Accessed)           |                                   |
|     flush = true;                   |                                   |
|   if (old_spte.Dirty &&             |                                   |
|       !new_spte.Dirty)              |                                   |
|     flush = true;                   |                                   |
|     OOPS!!!                         |                                   |
+-------------------------------------+-----------------------------------+

このケースでは Dirty ビットが失われる。

この種の問題を避けるため、mmu-lock の外側で更新されうる spte は常に「揮発性」
として扱う（spte_needs_atomic_update() を参照）。つまり、この場合 spte を常に
アトミックに更新する。

3) spte の更新による TLB のフラッシュ

spte が書き込み可能から読み出し専用に更新される場合は、すべての TLB を
フラッシュしなければならない。そうしないと、書き込み可能な spte が CPU の
TLB にキャッシュされていても、rmap_write_protect が読み出し専用の spte を
見つけてしまう。

前述のとおり、高速ページフォールトのパスでは、spte は mmu-lock の外側で
書き込み可能に更新されうる。このパスを簡単に監査できるようにするため、
mmu_spte_update() の中で、フラッシュが必要な TLB がこの理由で生じたかどうかを
調べる。mmu_spte_update() は spte を更新する共通関数である（present ->
present）。

spte は mmu-lock の外側で更新されうるなら「揮発性」であるため、常に spte を
アトミックに更新し、高速ページフォールトによる競合を避けられる。
spte_needs_atomic_update() と mmu_spte_update() のコメントを参照のこと。

ロックレスなアクセストラッキング:

これは、EPT を使うが EPT の A/D ビットをサポートしない Intel CPU で使う。
この場合、PTE は A/D 無効としてタグ付けされ（無視されるビットを使う）。
KVM MMU ノーティファイアがページへのアクセスを追跡するために呼び出されると
（kvm_mmu_notifier_clear_flush_young 経由）、PTE の RWX ビットをクリアし、
元の R ビットと X ビットをさらに未使用/無視されるビットに保存することで、
ハードウェア上で PTE を not-present にする。その後 VM がそのページに
アクセスしようとするとフォールトが発生し、上述の高速ページフォールトの
仕組みを使って PTE をアトミックに Present 状態に戻す。PTE がアクセス
トラッキングのためにマークされるときに W ビットは保存されず、Present 状態に
戻すときに、書き込みアクセスだったかどうかに応じて W ビットがセットされる。
書き込みでなかった場合、W ビットはクリアされたままで、書き込みアクセスが
起きたときに上で説明したダーティトラッキングの仕組みを使ってセットされる。

3. リファレンス
---------------

``kvm_lock``
^^^^^^^^^^^^

:Type:            ミューテックス
:Arch:            すべて
:Protects:        - vm_list

``kvm_usage_lock``
^^^^^^^^^^^^^^^^^^

:Type:            ミューテックス
:Arch:            すべて
:Protects:        - kvm_usage_count
                  - ハードウェア仮想化の有効化/無効化
:Comment:         kvm_usage_count を保護している間に cpus_read_lock() を取得できるようにするために存在する。
                  これにより、仮想化の有効化のロジックが単純になる。

``kvm->mn_invalidate_lock``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

:Type:            spinlock_t
:Arch:            すべて
:Protects:        mn_active_invalidate_count, mn_memslots_update_rcuwait

``kvm_arch::tsc_write_lock``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:Type:            raw_spinlock_t
:Arch:            x86
:Protects:        - kvm_arch::{last_tsc_write,last_tsc_nsec,last_tsc_offset}
                  - vmcb の tsc オフセット
:Comment:         tsc オフセットの更新はプリエンプトされてはならないため「raw」である。

``kvm->mmu_lock``
^^^^^^^^^^^^^^^^^
:Type:            spinlock_t または rwlock_t
:Arch:            すべて
:Protects:        - シャドウページ/シャドウ TLB エントリ
:Comment:         mmu ノーティファイアで使われるためスピンロックである。

``kvm->srcu``
^^^^^^^^^^^^^
:Type:            srcu ロック
:Arch:            すべて
:Protects:        - kvm->memslots
                  - kvm->buses
:Comment:         memslots にアクセスする間（たとえば gfn_to_* 関数を使うとき）、およびカーネル内の
                  MMIO/PIO のアドレスからデバイス構造体へのマッピング（kvm->buses）にアクセスする間は、
                  srcu のリードロックを保持しなければならない。複数の関数で必要なら、srcu の
                  インデックスは vcpu ごとに kvm_vcpu->srcu_idx に保存できる。

``kvm->slots_arch_lock``
^^^^^^^^^^^^^^^^^^^^^^^^
:Type:            ミューテックス
:Arch:            すべて（ただし x86 でのみ必要）
:Protects:        ``kvm->srcu`` のリード側クリティカルセクションで変更する必要がある、
                  memslots のアーキテクチャ固有のフィールド
:Comment:         現在の memslots へのポインタを読む前から、memslots への変更がすべて完了するまでの
                  間、保持しなければならない

``wakeup_vcpus_on_cpu_lock``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:Type:            spinlock_t
:Arch:            x86
:Protects:        wakeup_vcpus_on_cpu
:Comment:         これは CPU ごとのロックで、VT-d のポステッド割り込みに使われる。VT-d の
                  ポステッド割り込みがサポートされていて、VM にデバイスが割り当てられている場合は、
                  ブロックされた vCPU を blocked_vcpu_on_cpu_lock で保護された
                  blocked_vcpu_on_cpu リストに置く。割り当てられたデバイスからの外部割り込みが
                  発生して VT-d ハードウェアがウェイクアップ通知イベントを発行すると、リストから
                  vCPU を見つけてウェイクアップする。

``vendor_module_lock``
^^^^^^^^^^^^^^^^^^^^^^
:Type:            ミューテックス
:Arch:            x86
:Protects:        ベンダモジュール（kvm_amd または kvm_intel）の読み込み
:Comment:         kvm_lock を使うとデッドロックになるため存在する。kvm_lock は、たとえば
                  __kvmclock_cpufreq_notifier() のようなノーティファイアで取得される。この
                  ノーティファイアは、たとえば cpufreq_boost_trigger_state() から
                  cpu_hotplug_lock を保持した状態で呼び出されうる。また、ベンダモジュールを
                  読み込むとき（たとえば static call の更新）には、多くの操作が
                  cpu_hotplug_lock を取得する必要がある。
