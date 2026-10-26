.. SPDX-License-Identifier: GPL-2.0

==========
ネスト VMX
==========

概要
----

Intel プロセッサ上で、KVM は Intel の VMX (Virtual-Machine eXtensions) を
使ってゲストオペレーティングシステムを簡単かつ効率的に実行する。通常、
これらのゲストは自身がハイパーバイザとなって自分のゲストを動かすことは
*できない*。VMX ではゲストが VMX 命令を使えないためである。

「ネスト VMX」機能は、この欠けていた能力、すなわち VMX を使うゲスト
ハイパーバイザをそのネストゲストとともに動かす能力を追加する。これは、
ゲストに VMX 命令の使用を許可し、ハードウェアで利用できる単一レベルの
VMX を使ってそれらを正しく効率的にエミュレートすることで実現する。

ネスト VMX 機能の背景にある理論、その実装、性能特性については、OSDI
2010 の論文「The Turtles Project: Design and Implementation of Nested
Virtualization」で詳しく説明している。論文は次で入手できる。

	https://www.usenix.org/events/osdi10/tech/full_papers/Ben-Yehuda.pdf


用語
----

単一レベルの仮想化には、ホスト (KVM) とゲストの 2 つのレベルがある。
ネスト仮想化では 3 つのレベルがある。ホスト (KVM) を L0、ゲスト
ハイパーバイザを L1、そのネストゲストを L2 と呼ぶ。


ネスト VMX の実行
-----------------

ネスト VMX 機能は Linux カーネル v4.20 以降、既定で有効である。それより
古い Linux カーネルでは、kvm-intel モジュールに "nested=1" オプションを
渡すと有効にできる。


ユーザ空間 (qemu) の変更は不要である。ただし、qemu の既定のエミュレート
CPU タイプ (qemu64) は "VMX" CPU 機能を列挙しないため、次のいずれかの
オプションを qemu に渡して明示的に有効にする必要がある。

     - cpu host              (エミュレート CPU が実 CPU のすべての機能を持つ)

     - cpu qemu64,+vmx       (名前付き CPU タイプに vmx 機能だけを追加する)


ABI
---

ネスト VMX は、ゲストハイパーバイザが使うための標準的で (最終的には)
完全に機能する VMX 実装を提供することを目指している。そのため、ここで
提供する ABI の公式仕様は Intel の VMX 仕様、すなわち「Intel 64 and IA-32
Architectures Software Developer's Manual」の volume 3B である。現在、
VMX のすべての機能が完全にサポートされているわけではないが、最終的には
すべてをサポートすることが目標であり、まず一般的なハイパーバイザ (KVM
など) が実際に使う VMX 機能から始める。

VMX 実装として、ネスト VMX は L1 に VMCS 構造を提示する。仕様で定められて
いるとおり、revision_id と abort の 2 つのフィールドを除き、この構造は
利用者にとって*不透明*であり、利用者はその内部構造を知る必要も気にする
必要もない。代わりに、この構造には VMREAD 命令と VMWRITE 命令を通じて
アクセスする。それでも、デバッグ目的で、KVM の開発者はこの構造の内部を
知りたいかもしれない。それが arch/x86/kvm/vmx.c の struct vmcs12 である。

「vmcs12」という名前は、L1 が L2 のために作る VMCS を指す。コードには
「vmcs01」、すなわち L0 が L1 のために作る VMCS もあり、「vmcs02」は
L0 が実際に L2 を動かすために作る VMCS である。これがどのように行われる
かは前述の論文で説明されている。

便宜上、ここに struct vmcs12 の内容を再掲する。この構造の内部が変わると、
KVM のバージョン間でのライブマイグレーションが壊れるおそれがある。
struct vmcs12 またはその内部の struct shadow_vmcs を変更した場合は、
VMCS12_REVISION (vmx.c より) を変更すべきである。

::

	typedef u64 natural_width;
	struct __packed vmcs12 {
		/* According to the Intel spec, a VMCS region must start with
		 * these two user-visible fields */
		u32 revision_id;
		u32 abort;

		u32 launch_state; /* set to 0 by VMCLEAR, to 1 by VMLAUNCH */
		u32 padding[7]; /* room for future expansion */

		u64 io_bitmap_a;
		u64 io_bitmap_b;
		u64 msr_bitmap;
		u64 vm_exit_msr_store_addr;
		u64 vm_exit_msr_load_addr;
		u64 vm_entry_msr_load_addr;
		u64 tsc_offset;
		u64 virtual_apic_page_addr;
		u64 apic_access_addr;
		u64 ept_pointer;
		u64 guest_physical_address;
		u64 vmcs_link_pointer;
		u64 guest_ia32_debugctl;
		u64 guest_ia32_pat;
		u64 guest_ia32_efer;
		u64 guest_pdptr0;
		u64 guest_pdptr1;
		u64 guest_pdptr2;
		u64 guest_pdptr3;
		u64 host_ia32_pat;
		u64 host_ia32_efer;
		u64 padding64[8]; /* room for future expansion */
		natural_width cr0_guest_host_mask;
		natural_width cr4_guest_host_mask;
		natural_width cr0_read_shadow;
		natural_width cr4_read_shadow;
		natural_width dead_space[4]; /* Last remnants of cr3_target_value[0-3]. */
		natural_width exit_qualification;
		natural_width guest_linear_address;
		natural_width guest_cr0;
		natural_width guest_cr3;
		natural_width guest_cr4;
		natural_width guest_es_base;
		natural_width guest_cs_base;
		natural_width guest_ss_base;
		natural_width guest_ds_base;
		natural_width guest_fs_base;
		natural_width guest_gs_base;
		natural_width guest_ldtr_base;
		natural_width guest_tr_base;
		natural_width guest_gdtr_base;
		natural_width guest_idtr_base;
		natural_width guest_dr7;
		natural_width guest_rsp;
		natural_width guest_rip;
		natural_width guest_rflags;
		natural_width guest_pending_dbg_exceptions;
		natural_width guest_sysenter_esp;
		natural_width guest_sysenter_eip;
		natural_width host_cr0;
		natural_width host_cr3;
		natural_width host_cr4;
		natural_width host_fs_base;
		natural_width host_gs_base;
		natural_width host_tr_base;
		natural_width host_gdtr_base;
		natural_width host_idtr_base;
		natural_width host_ia32_sysenter_esp;
		natural_width host_ia32_sysenter_eip;
		natural_width host_rsp;
		natural_width host_rip;
		natural_width paddingl[8]; /* room for future expansion */
		u32 pin_based_vm_exec_control;
		u32 cpu_based_vm_exec_control;
		u32 exception_bitmap;
		u32 page_fault_error_code_mask;
		u32 page_fault_error_code_match;
		u32 cr3_target_count;
		u32 vm_exit_controls;
		u32 vm_exit_msr_store_count;
		u32 vm_exit_msr_load_count;
		u32 vm_entry_controls;
		u32 vm_entry_msr_load_count;
		u32 vm_entry_intr_info_field;
		u32 vm_entry_exception_error_code;
		u32 vm_entry_instruction_len;
		u32 tpr_threshold;
		u32 secondary_vm_exec_control;
		u32 vm_instruction_error;
		u32 vm_exit_reason;
		u32 vm_exit_intr_info;
		u32 vm_exit_intr_error_code;
		u32 idt_vectoring_info_field;
		u32 idt_vectoring_error_code;
		u32 vm_exit_instruction_len;
		u32 vmx_instruction_info;
		u32 guest_es_limit;
		u32 guest_cs_limit;
		u32 guest_ss_limit;
		u32 guest_ds_limit;
		u32 guest_fs_limit;
		u32 guest_gs_limit;
		u32 guest_ldtr_limit;
		u32 guest_tr_limit;
		u32 guest_gdtr_limit;
		u32 guest_idtr_limit;
		u32 guest_es_ar_bytes;
		u32 guest_cs_ar_bytes;
		u32 guest_ss_ar_bytes;
		u32 guest_ds_ar_bytes;
		u32 guest_fs_ar_bytes;
		u32 guest_gs_ar_bytes;
		u32 guest_ldtr_ar_bytes;
		u32 guest_tr_ar_bytes;
		u32 guest_interruptibility_info;
		u32 guest_activity_state;
		u32 guest_sysenter_cs;
		u32 host_ia32_sysenter_cs;
		u32 padding32[8]; /* room for future expansion */
		u16 virtual_processor_id;
		u16 guest_es_selector;
		u16 guest_cs_selector;
		u16 guest_ss_selector;
		u16 guest_ds_selector;
		u16 guest_fs_selector;
		u16 guest_gs_selector;
		u16 guest_ldtr_selector;
		u16 guest_tr_selector;
		u16 host_es_selector;
		u16 host_cs_selector;
		u16 host_ss_selector;
		u16 host_ds_selector;
		u16 host_fs_selector;
		u16 host_gs_selector;
		u16 host_tr_selector;
	};


作者
----

これらのパッチを書いたのは次の人たちである。
    - Abel Gordon, abelg <at> il.ibm.com
    - Nadav Har'El, nyh <at> il.ibm.com
    - Orit Wasserman, oritw <at> il.ibm.com
    - Ben-Ami Yassor, benami <at> il.ibm.com
    - Muli Ben-Yehuda, muli <at> il.ibm.com

貢献したのは次の人たちである。
    - Anthony Liguori, aliguori <at> us.ibm.com
    - Mike Day, mdday <at> us.ibm.com
    - Michael Factor, factor <at> il.ibm.com
    - Zvi Dubitzky, dubi <at> il.ibm.com

貴重なレビューをしてくれたのは次の人たちである。
    - Avi Kivity, avi <at> redhat.com
    - Gleb Natapov, gleb <at> redhat.com
    - Marcelo Tosatti, mtosatti <at> redhat.com
    - Kevin Tian, kevin.tian <at> intel.com
    - その他多数。
