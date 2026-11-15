"""本地可重复验证: 真实 Qt 面板点击 + 取词成功信号后的弹窗链路。
不启动鼠标监听器, 不操作系统剪贴板, 不打印密钥。仅使用公开示例句。
"""
import json
import os
from pathlib import Path
import sys
import time
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
import requests
from main import TranslateApp
from panel_ui import TranslatePanel

output = ROOT / "artifacts" / "verification"
output.mkdir(parents=True, exist_ok=True)
app = TranslateApp()
panel = TranslatePanel()
records = []
post = requests.post


def observe_post(url, *args, **kwargs):
    data = kwargs.get("data") or {}
    if "/api/trans/vip/translate" in url:
        records.append({"q": data.get("q"), "to": data.get("to")})
    return post(url, *args, **kwargs)


def wait_for(predicate, seconds=45):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QTest.qWait(50)
        if predicate():
            QTest.qWait(200)
            return
    raise RuntimeError("界面翻译等待超时")


def panel_case(name, text, count):
    panel.present()
    panel.input_edit.setPlainText(text)
    panel.result_edit.clear()
    start = len(records)
    QTest.mouseClick(panel.translate_btn, Qt.LeftButton)
    wait_for(lambda: not panel._busy)
    translated = panel.result_edit.toPlainText()
    if not translated or "失败" in panel.status.text():
        raise RuntimeError("面板未显示成功译文: " + panel.status.text())
    observed = records[start:]
    assert len(observed) == count, (name, observed)
    assert all("\n" not in request["q"] and "\r" not in request["q"] for request in observed)
    assert panel.input_edit.toPlainText() == text
    panel.grab().save(str(output / (name + ".png")))
    print(json.dumps({"case": name, "requests": observed, "translated": translated,
                      "status": panel.status.text()}, ensure_ascii=False))
    QTest.qWait(1100)
    return translated


try:
    with mock.patch("requests.post", side_effect=observe_post):
        wrapped = "配好后，PyCharm 的 Terminal 会自动帮你\n激活，右下角也会显示 Python 3.14 (.venv)。"
        panel_case("panel_chinese_wrapped", wrapped, 1)
        baseline = panel_case("panel_english_single_line", "The meeting will start tomorrow at nine.", 1)
        folded = panel_case("panel_english_wrapped", "The meeting will\nstart tomorrow at nine.", 1)
        assert folded == baseline, (baseline, folded)
        result = panel_case("panel_paragraphs", "会议将于\n明天开始。\n\n请提前\n确认时间。", 2)
        assert "\n\n" in result
        panel.hide()
        start = len(records)
        # 从取词成功的公开信号进入真实控制器/线程池/Qt结果信号/弹窗;
        # 不把这项验证声称为实际鼠标选区和系统复制的验证。
        app.monitor.text_selected.emit(wrapped, 100, 100)
        wait_for(lambda: not app._translating)
        assert app.popup.isVisible()
        assert app.popup._original_text == wrapped
        assert app.popup._translated_text
        observed = records[start:]
        assert len(observed) == 1 and "\n" not in observed[0]["q"]
        app.popup.grab().save(str(output / "popup_chinese_wrapped.png"))
        print(json.dumps({"case": "popup_after_text_extraction", "requests": observed,
                          "translated": app.popup._translated_text,
                          "visible": app.popup.isVisible()}, ensure_ascii=False))
    print("PASS: 面板跨行整句翻译, 单行对照, 空行分段, 取词成功后的弹窗链路")
finally:
    panel.close()
    app.shutdown()
