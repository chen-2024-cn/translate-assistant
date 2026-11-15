"""Qt启动诊断: 仅输出解释器/Qt路径,不输出API凭证。
--check仅检查插件存在;默认在子进程中真的显示短暂窗口,捕获加载失败。
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qt_runtime import configure_qt_runtime


def probe():
    configure_qt_runtime()
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
    from PyQt5.QtCore import QTimer
    app = QApplication([])
    window = QWidget()
    window.setWindowTitle("TranslateAssistant - Qt startup diagnostic")
    window.resize(440, 160)
    layout = QVBoxLayout(window)
    layout.addWidget(QLabel("Windows Qt platform plugin loaded successfully"))
    window.show()
    app.processEvents()
    evidence = ROOT / "artifacts" / "verification" / "qt-startup"
    evidence.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(evidence / "qt-window.png"))
    QTimer.singleShot(500, app.quit)
    app.exec_()
    print("PASS: Qt Windows window displayed and closed normally")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--probe" in sys.argv:
        probe()
        return 0
    if "--check" not in sys.argv:
        print("Python:", sys.executable)
        print("Virtual environment:", sys.prefix != sys.base_prefix)
        print("Inherited Qt environment:", {k: v for k, v in os.environ.items() if k.startswith("QT_")})
    try:
        plugins = configure_qt_runtime()
    except RuntimeError as e:
        print(e)
        return 1
    if "--check" in sys.argv:
        return 0
    from PyQt5.QtCore import QLibraryInfo, QT_VERSION_STR, PYQT_VERSION_STR
    print("Qt / PyQt versions:", QT_VERSION_STR, PYQT_VERSION_STR)
    print("Qt reported plugins:", QLibraryInfo.location(QLibraryInfo.PluginsPath))
    print("Selected plugin folder:", plugins)
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "windows"
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--probe"],
                                env=env, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=15)
    except subprocess.TimeoutExpired:
        print("FAIL: Qt window startup timed out")
        return 1
    print(result.stdout)
    if result.stderr:
        print(result.stderr[:6000])
    if result.returncode:
        print("FAIL: Qt platform plugin could not initialize; child exit:", result.returncode)
        print("如qwindows.dll存在仍加载失败,请检查插件依赖/架构/安全软件日志。")
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("Qt diagnostic failed:", type(e).__name__, str(e))
        raise SystemExit(1)
