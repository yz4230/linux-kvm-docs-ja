.. SPDX-License-Identifier: GPL-2.0

===================================================================
SEV ゲスト API 完全ドキュメント
===================================================================

1. 概要
=======

SEV API は、ゲストまたはハイパーバイザが SEV 仮想マシンの特定の側面を取得
または設定するために使う ioctl の集合である。ioctl は次のクラスに分かれる。

 - ハイパーバイザ ioctl: SEV ファームウェア全体に影響するグローバル属性を
   問い合わせて設定する。これらの ioctl はプラットフォームのプロビジョニング
   ツールが使う。

 - ゲスト ioctl: SEV 仮想マシンの属性を問い合わせて設定する。

2. API の説明
=============

この節では、SEV ファームウェアから SEV ゲストレポートを問い合わせるために
使う ioctl を説明する。各 ioctl について、説明とあわせて次の情報を示す。

  Technology:
      この ioctl を提供する SEV 技術。SEV、SEV-ES、SEV-SNP のいずれか、
      またはすべて。

  Type:
      ハイパーバイザまたはゲスト。この ioctl はゲスト内でもハイパーバイザ内
      でも使える。

  Parameters:
      ioctl が受け付けるパラメータ。

  Returns:
      返される値。一般的なエラー番号（-ENOMEM、-EINVAL）は詳述しないが、
      固有の意味を持つエラーは記す。

ゲスト ioctl は /dev/sev-guest デバイスのファイルディスクリプタに対して
発行する。ioctl は struct snp_guest_request_ioctl を受け取る。入力構造体と
出力構造体は、それぞれ req_data フィールドと resp_data フィールドで指定する。
ファームウェアエラーで ioctl の実行に失敗した場合は fw_error コードが設定
され、それ以外の場合は fw_error に -1 が設定される。

ファームウェアは、メッセージシーケンスカウンタがゲストのメッセージ
シーケンスカウンタより 1 大きいことを確認する。ゲストドライバがメッセージ
カウンタをインクリメントできない場合（例: カウンタのオーバーフロー）、
-EIO が返される。

::

        struct snp_guest_request_ioctl {
                /* Message version number */
                __u32 msg_version;

                /* Request and response structure address */
                __u64 req_data;
                __u64 resp_data;

                /* bits[63:32]: VMM error code, bits[31:0] firmware error code (see psp-sev.h) */
                union {
                        __u64 exitinfo2;
                        struct {
                                __u32 fw_error;
                                __u32 vmm_error;
                        };
                };
        };

ホスト ioctl は /dev/sev デバイスのファイルディスクリプタに対して発行する。
ioctl は以下に示すコマンド ID と入力構造体を受け取る。

::

        struct sev_issue_cmd {
                /* Command ID */
                __u32 cmd;

                /* Command request structure */
                __u64 data;

                /* Firmware error code on failure (see psp-sev.h) */
                __u32 error;
        };


2.1 SNP_GET_REPORT
------------------

:Technology: sev-snp
:Type: ゲスト ioctl
:Parameters (in): struct snp_report_req
:Returns (out): 成功時は struct snp_report_resp、エラー時は負の値

SNP_GET_REPORT ioctl は、SEV-SNP ファームウェアからアテステーションレポート
を問い合わせるために使える。この ioctl は、SEV-SNP ファームウェアが提供する
SNP_GUEST_REQUEST（MSG_REPORT_REQ）コマンドを使ってアテステーションレポート
を問い合わせる。

成功すると、snp_report_resp.data にレポートが入る。レポートの形式は SEV-SNP
仕様に記述されている。詳細は SEV-SNP 仕様を参照。

2.2 SNP_GET_DERIVED_KEY
-----------------------
:Technology: sev-snp
:Type: ゲスト ioctl
:Parameters (in): struct snp_derived_key_req
:Returns (out): 成功時は struct snp_derived_key_resp、エラー時は負の値

SNP_GET_DERIVED_KEY ioctl は、ルート鍵から派生した鍵を取得するために使える。
派生鍵は、鍵のシーリングや外部との通信など、ゲストが任意の目的で使える。

この ioctl は、SEV-SNP ファームウェアが提供する SNP_GUEST_REQUEST
（MSG_KEY_REQ）コマンドを使って鍵を派生する。鍵派生要求で渡す各種フィールド
の詳細は SEV-SNP 仕様を参照。

成功すると、snp_derived_key_resp.data に派生鍵の値が入る。詳細は SEV-SNP
仕様を参照。


2.3 SNP_GET_EXT_REPORT
----------------------
:Technology: sev-snp
:Type: ゲスト ioctl
:Parameters (in/out): struct snp_ext_report_req
:Returns (out): 成功時は struct snp_report_resp、エラー時は負の値

SNP_GET_EXT_REPORT ioctl は SNP_GET_REPORT に似ている。違いは、レポートと
一緒に返される追加の証明書データにある。返される証明書データは、ハイパー
バイザが SNP_SET_EXT_CONFIG を通じて提供する。

この ioctl は、SEV-SNP ファームウェアが提供する SNP_GUEST_REQUEST
（MSG_REPORT_REQ）コマンドを使ってアテステーションレポートを取得する。

成功すると、snp_ext_report_resp.data にアテステーションレポートが入り、
snp_ext_report_req.certs_address に証明書ブロブが入る。ブロブの長さが想定
より小さい場合は、snp_ext_report_req.certs_len が想定値で更新される。

証明書ブロブの解析方法の詳細は GHCB 仕様を参照。

2.4 SNP_PLATFORM_STATUS
-----------------------
:Technology: sev-snp
:Type: ハイパーバイザ ioctl コマンド
:Parameters (out): struct sev_user_data_snp_status
:Returns (out): 成功時は 0、エラー時は負の値

SNP_PLATFORM_STATUS コマンドは、SNP プラットフォームのステータスを問い合わせ
るために使う。ステータスには API のメジャーバージョン、マイナーバージョン
などが含まれる。詳細は SEV-SNP 仕様を参照。

2.5 SNP_COMMIT
--------------
:Technology: sev-snp
:Type: ハイパーバイザ ioctl コマンド
:Returns (out): 成功時は 0、エラー時は負の値

SNP_COMMIT は、SEV-SNP ファームウェアの SNP_COMMIT コマンドを使って、現在
インストールされているファームウェアをコミットするために使う。これにより、
以前にコミットしたファームウェアバージョンへのロールバックを防ぐ。また、
報告される TCB を現在インストールされているファームウェアのものに合わせて
更新する。

2.6 SNP_SET_CONFIG
------------------
:Technology: sev-snp
:Type: ハイパーバイザ ioctl コマンド
:Parameters (in): struct sev_user_data_snp_config
:Returns (out): 成功時は 0、エラー時は負の値

SNP_SET_CONFIG は、アテステーションレポートで報告される TCB バージョンなど、
システム全体の設定を行うために使う。このコマンドは SEV-SNP 仕様で定義されて
いる SNP_CONFIG コマンドに似ている。このコマンドの影響を受けるファームウェア
パラメータの現在値は、SNP_PLATFORM_STATUS で問い合わせられる。

2.7 SNP_VLEK_LOAD
-----------------
:Technology: sev-snp
:Type: ハイパーバイザ ioctl コマンド
:Parameters (in): struct sev_user_data_snp_vlek_load
:Returns (out): 成功時は 0、エラー時は負の値

アテステーションレポートを要求するとき、ゲストは SNP ファームウェアにどちら
の鍵でレポートに署名させるかを指定できる。チップ固有の秘密から派生する
Versioned Chip Endorsement Key（VCEK）か、AMD Key Derivation Service（KDS）
から取得し、登録済みクラウドサービスプロバイダに割り当てられたシードから
派生する Versioned Loaded Endorsement Key（VLEK）である。

VLEK 鍵の場合は、KDS から取得した後にシステムへロードするために
SNP_VLEK_LOAD SNP コマンドを使う。これは SEV-SNP 仕様で規定されている
SNP_VLEK_LOAD ファームウェアコマンドにほぼ対応する。

3. SEV-SNP の CPUID 強制
========================

SEV-SNP ゲストは、SNP_LAUNCH_UPDATE ファームウェアコマンドの一部として PSP が
検証した CPUID 値の表を含む特別なページにアクセスできる。このページは、
CPUID 値の正当性について次のことを保証する。

 - そのアドレスはブートローダ/ファームウェア（CC blob 経由）から取得され、
   それらのバイナリは SEV-SNP アテステーションレポートの一部として測定
   される。
 - その初期状態は暗号化済みかつ pvalidate 済みになる。そのため実行中に変更
   しようとすると、不正なデータが書き込まれるか、ハイパーバイザがバッキング
   ページをスワップしようとすると検証状態の変化により #VC 例外が発生する。
 - ハイパーバイザが通常のページや CPUID 用でない暗号化ページを使って PSP の
   検査を回避しようとすると、SEV-SNP アテステーションレポートが提供する測定値
   が変わる。
 - CPUID ページの内容は測定され*ない*が、ゲストの初期化の一環として CPUID
   ページの想定内容を変更しようとすると、SNP_LAUNCH_UPDATE 中にそのページに
   対して行われる PSP の CPUID 強制ポリシー検査で阻まれ、ゲスト所有者が
   CPUID 値の独自チェックを実装していれば後から気付ける。

最後の保証は、カーネルがブートのすべての段階で SEV-SNP CPUID を使うよう配慮
している場合にのみ役立つことに注意することが重要である。そうでなければ、
ゲスト所有者のアテステーションは、ブート中のどこかの時点でカーネルに誤った
値が渡されなかったことを保証しない。

4. SEV ゲストドライバの通信用鍵
===============================

SEV ゲストと AMD Secure Processor（ASP、別名 PSP）内の SEV ファームウェアとの
通信は、VM Platform Communication Key（VMPCK）で保護される。既定では、
sev-guest ドライバはゲストが動作している VM Privilege Level（VMPL）に対応
する VMPCK を使う。この鍵が sev-guest ドライバによって消去された場合
（VMPCK が消去される理由はドライバを参照）、sev-guest ドライバを再ロードし、
vmpck_id モジュールパラメータで目的の鍵を指定すれば、別の鍵を使える。


参考文献
---------

SEV-SNP および GHCB 仕様: developer.amd.com/sev

このドライバは SEV-SNP ファームウェア仕様 0.9 と GHCB 仕様バージョン 2.0 に
基づく。
