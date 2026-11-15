"""
用户设置持久化
托盘菜单里改的开关/触发方式保存在 APPDATA 下的 TranslateAssistant/settings.json
(打包成 exe 后 config.py 无法修改，所以运行期设置单独存放)
"""
import json
import os

import config

APP_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), "TranslateAssistant"
)
_FILE = os.path.join(APP_DIR, "settings.json")

MODE_CTRL = "ctrl"  # 按住 Ctrl 再选中才翻译
MODE_AUTO = "auto"  # 选中即译

_VALID_MODES = (MODE_CTRL, MODE_AUTO)


def load() -> dict:
    mode = config.TRIGGER_MODE if config.TRIGGER_MODE in _VALID_MODES else MODE_CTRL
    data = {"enabled": True, "trigger_mode": mode}
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved.get("enabled"), bool):
            data["enabled"] = saved["enabled"]
        if saved.get("trigger_mode") in _VALID_MODES:
            data["trigger_mode"] = saved["trigger_mode"]
    except Exception:
        pass
    return data


def save(data: dict) -> None:
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
