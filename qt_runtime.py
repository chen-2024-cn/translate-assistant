"""源码运行时使用当前PyQt5自带的平台插件,不依赖机器特定绝对路径。
冻结exe保留PyInstaller的Qt初始化;只改当前进程,不改系统环境变量。
"""
import os
from pathlib import Path
import sys


def find_windows_plugins(package_root: Path, reported: str = "") -> Path:
    root = package_root.resolve()
    candidates = [root / "Qt5" / "plugins", root / "Qt" / "plugins"]
    if reported:
        path = Path(reported).resolve()
        if path.is_relative_to(root):
            candidates.append(path)
    for path in candidates:
        if (path / "platforms" / "qwindows.dll").is_file():
            return path
    raise RuntimeError(
        "当前Python环境缺少PyQt5 Windows平台插件 qwindows.dll。\n"
        f"Python: {sys.executable}\nPyQt5: {root}\n"
        "请在该环境重新安装完整的Qt组件,不要单独下载DLL:\n"
        f'"{sys.executable}" -m pip install --only-binary=:all: --force-reinstall '
        '"PyQt5>=5.15.11,<5.16" "PyQt5-Qt5>=5.15.2,<5.16" "PyQt5-sip>=12.20.1,<13"'
    )


def configure_qt_runtime():
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return None
    try:
        import PyQt5
        from PyQt5.QtCore import QCoreApplication, QLibraryInfo
    except ImportError as e:
        raise RuntimeError(f"当前Python未完整安装PyQt5: {sys.executable}\n"
                           "请用这个解释器执行 -m pip install --only-binary=:all: -r requirements.txt") from e
    plugins = find_windows_plugins(Path(PyQt5.__file__).parent,
                                   QLibraryInfo.location(QLibraryInfo.PluginsPath))
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins / "platforms")
    os.environ.pop("QT_PLUGIN_PATH", None)
    # 单测可显式选择offscreen;应用正常启动仍由main选择windows。
    QCoreApplication.setLibraryPaths([str(plugins)])
    return plugins
