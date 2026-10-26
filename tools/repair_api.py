#!/usr/bin/env python3
"""Restore C code blocks that the api.rst chunk translation truncated.

tools/check.py found 17 code lines present in the English original but absent
from source/api.rst: the ``::`` blocks of 4.47 KVM_PPC_GET_PVINFO and of
4.125 KVM_S390_PV_COMMAND kept only their opening line.  The missing lines are
restored verbatim from the original (tabs included), so the blocks render as
monospace again.  Idempotent: a second run reports "already applied".
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "source" / "kvm" / "api.rst"

REPAIRS: list[tuple[str, str, str]] = [
    (
        "4.47 KVM_PPC_GET_PVINFO: truncated flags bitmap",
        "   /* the host supports the ePAPR idle hcall\n",
        "   /* the host supports the ePAPR idle hcall\n"
        "   #define KVM_PPC_PVINFO_FLAGS_EV_IDLE   (1<<0)\n",
    ),
    (
        "4.125 KVM_S390_PV_COMMAND: pv_cmd_info_id / pv_info_header / pv_info",
        "     enum pv_cmd_info_id {\n",
        "     enum pv_cmd_info_id {\n"
        "\tKVM_PV_INFO_VM,\n"
        "\tKVM_PV_INFO_DUMP,\n"
        "     };\n"
        "\n"
        "     struct kvm_s390_pv_info_header {\n"
        "\t__u32 id;\n"
        "\t__u32 len_max;\n"
        "\t__u32 len_written;\n"
        "\t__u32 reserved;\n"
        "     };\n"
        "\n"
        "     struct kvm_s390_pv_info {\n"
        "\tstruct kvm_s390_pv_info_header header;\n"
        "\tstruct kvm_s390_pv_info_dump dump;\n"
        "\tstruct kvm_s390_pv_info_vm vm;\n"
        "     };\n",
    ),
    (
        "4.125 KVM_S390_PV_COMMAND: pv_info_vm body",
        "      struct kvm_s390_pv_info_vm {\n",
        "      struct kvm_s390_pv_info_vm {\n"
        "\t__u64 inst_calls_list[4];\n"
        "\t__u64 max_cpus;\n"
        "\t__u64 max_guests;\n"
        "\t__u64 max_guest_addr;\n"
        "\t__u64 feature_indication;\n"
        "      };\n",
    ),
    (
        "4.125 KVM_S390_PV_COMMAND: pv_info_dump body",
        "      struct kvm_s390_pv_info_dump {\n",
        "      struct kvm_s390_pv_info_dump {\n"
        "\t__u64 dump_cpu_buffer_len;\n"
        "\t__u64 dump_config_mem_buffer_per_1m;\n"
        "\t__u64 dump_config_finalize_len;\n"
        "      };\n",
    ),
]


def main() -> int:
    text = API.read_text(encoding="utf-8")
    for label, old, new in REPAIRS:
        if new in text:
            print(f"already applied: {label}")
            continue
        if text.count(old) != 1:
            print(f"FAILED (anchor count {text.count(old)}): {label}")
            return 1
        text = text.replace(old, new, 1)
        print(f"repaired: {label}")
    API.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
