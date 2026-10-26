==================
ゲストの停止ポーリング
==================

haltpoll governor を備えた cpuidle_haltpoll ドライバを使うと、
ゲストの vCPU は、停止する前に指定した時間だけポーリングできる。

これはホスト側のポーリングに次の利点をもたらす。

	1) ポーリングの実行中は POLL フラグが設定される。これにより、
	   リモートの vCPU は、ウェイクアップを行うときに IPI の送信
	   （および IPI 処理に伴うコスト）を避けられる。

	2) VM エグジットのコストを避けられる。

ゲスト側のポーリングの欠点は、ホスト上に実行可能なタスクがほかにある
場合でもポーリングが行われることである。

基本的な動作は次のとおりである。グローバル値 guest_halt_poll_ns をユーザが
設定し、ポーリングが許される最大時間を示す。この値は固定である。

各 vCPU は調整可能な guest_halt_poll_ns（「per-cpu guest_halt_poll_ns」）
を持ち、アルゴリズムがイベントに応じてこれを調整する（後述）。

モジュールパラメータ
=================

haltpoll governor には、調整可能なモジュールパラメータが 5 つある。

1) guest_halt_poll_ns:

停止する前にポーリングを行う最大時間（ナノ秒）。

デフォルト: 200000

2) guest_halt_poll_shrink:

グローバルの guest_halt_poll_ns を超えてからウェイクアップイベントが
発生したときに、per-cpu guest_halt_poll_ns を縮めるための除数。

デフォルト: 2

3) guest_halt_poll_grow:

per-cpu guest_halt_poll_ns を超えたあと、グローバルの
guest_halt_poll_ns に達する前にイベントが発生したときに、
per-cpu guest_halt_poll_ns を伸ばすための乗数。

デフォルト: 2

4) guest_halt_poll_grow_start:

アイドル状態のシステムでは、per-cpu guest_halt_poll_ns は最終的に
ゼロになる。この値は、伸ばすときの per-cpu guest_halt_poll_ns の
初期値を設定する。初期の伸長段階での取りこぼしを避けるため、
10000 から増やせる。

10k, 20k, 40k, ...（例は guest_halt_poll_grow=2 を想定）。

デフォルト: 50000

5) guest_halt_poll_allow_shrink:

縮小を許可するブール値のパラメータ。N に設定すると縮小しない
（per-cpu guest_halt_poll_ns は、グローバルの guest_halt_poll_ns の
値に達すると高いままになる）。

デフォルト: Y

モジュールパラメータは次の sysfs ファイルから設定できる::

	/sys/module/haltpoll/parameters/

補足
=============

- guest_halt_poll_ns パラメータを設定するときは注意が必要である。大きな
  値にすると、ほかに何もなければほぼ完全にアイドルになるマシンで、CPU
  使用率が 100% になるおそれがある。
