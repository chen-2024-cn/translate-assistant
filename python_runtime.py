"""Validate the source interpreter before importing native GUI dependencies."""
import platform
import struct
import sys
import sysconfig


def check_python_runtime():
    if getattr(sys, "frozen", False):
        return
    if (sys.implementation.name != "cpython" or not (3, 11) <= sys.version_info[:2] <= (3, 15)
            or sys.platform != "win32" or struct.calcsize("P") != 8
            or platform.machine().lower() not in ("amd64", "x86_64")
            or sysconfig.get_config_var("Py_GIL_DISABLED")):
        raise RuntimeError(
            "源码运行需要标准 CPython 3.11-3.15 / Windows x64 (非ARM或自由线程版)。\n"
            f"当前解释器: {sys.executable}\n当前版本: {sys.version.split()[0]}\n"
            "可使用 py -3.14 -m venv .venv 明确创建环境,或运行匹配架构的便携exe。"
        )


if __name__ == "__main__":
    try:
        check_python_runtime()
    except RuntimeError as error:
        print(error)
        raise SystemExit(1)
