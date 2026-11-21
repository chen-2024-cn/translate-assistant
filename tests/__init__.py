# 回归测试包
"""导入任何测试模块前, 先把 Qt 平台插件路径指向当前 Python 环境里的 PyQt5。

不这么做时, 用 unittest 跑测试会遇到:
    qt.qpa.plugin: Could not find the Qt platform plugin "windows" in ""
因为 main.py 里那套 configure_qt_runtime() 只在应用入口执行, 测试进程没人调用它;
一旦环境里残留空的 QT_PLUGIN_PATH / QT_QPA_PLATFORM_PLUGIN_PATH, Qt 就搜不到插件。
"""
import os

try:  # 非 Windows 或未装 PyQt5 时交给具体测试自己报错
    from qt_runtime import configure_qt_runtime

    configure_qt_runtime()
except Exception:  # pragma: no cover - 仅在缺少 Qt 的环境触发
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    os.environ.pop("QT_PLUGIN_PATH", None)
