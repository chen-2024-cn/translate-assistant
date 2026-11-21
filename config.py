"""
翻译助手 - 配置文件
在此切换翻译 API 以及调整各项参数
"""
import os

# ============================================================
# 翻译 API 配置
# 当前使用: 百度翻译开放平台 (通过用户环境变量提供 APPID/密钥)
# 安全发布: 不在此文件填写真实凭证。
# 凭证来源(优先级从高到低):
#   1. 系统/用户环境变量 (set_credentials.ps1 写入的用户变量)
#   2. 项目根目录的 .env 文件 (本文件启动时读取, 不覆盖已有的环境变量)
# .env 已被 .gitignore 忽略, 不会进 Git; 真实密钥永远不要写在本文件里。
# ============================================================
import os
import sys
from pathlib import Path


def _project_root() -> Path:
    """源码运行取项目根; 打包后取 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ENV_FILE = _project_root() / ".env"


def load_dotenv(path: Path | None = None) -> list:
    """把 .env 里的 KEY=VALUE 读进 os.environ; 已存在的环境变量保持不变。

    只支持最常见的写法: KEY=VALUE / KEY="VALUE" / export KEY=VALUE,
    忽略空行与 # 开头注释行。返回本次真正写入的变量名(不含值, 便于日志)。
    语义与常见 dotenv 一致: 环境变量优先, .env 只补空缺。
    """
    env_path = ENV_FILE if path is None else Path(path)
    if not env_path.is_file():
        return []
    loaded = []
    try:
        raw = env_path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        loaded.append(key)
    return loaded


LOADED_ENV_KEYS = load_dotenv()


# --- 当前 API ---
TRANSLATOR = "baidu"
# 可选值: "google" | "baidu" | "youdao" | "mymemory"

# 主引擎失败(被限流、断网等)时, 自动改用 MyMemory; 失败的引擎 5 分钟内不再重试
FALLBACK_ENABLED = True

# MyMemory 配置 (免费, 匿名每天约 5000 字符; 填一个邮箱可提升到约 50000)
MYMEMORY_CONFIG = {"email": ""}

# --- Google 翻译配置 (deep-translator 免费接口, 无需 key; 国内网络易被限流 429) ---
GOOGLE_CONFIG = {}

# --- 百度翻译配置 (当前默认引擎) ---
# 设置用户环境变量 BAIDU_APPID 和 BAIDU_SECRET_KEY。
# 更换凭证后重新启动应用; 不必重新打包, 不要把密钥写入源码/Git历史。
BAIDU_CONFIG = {
    "appid": os.environ.get("BAIDU_APPID", ""),
    "secret_key": os.environ.get("BAIDU_SECRET_KEY", ""),
    "api_url": "https://fanyi-api.baidu.com/api/trans/vip/translate",
}

# --- 有道翻译配置 (可选, 凭证同样由用户环境变量提供) ---
# TRANSLATOR = "youdao"
YOUDAO_CONFIG = {
    "app_key": os.environ.get("YOUDAO_APP_KEY", ""),
    "app_secret": os.environ.get("YOUDAO_APP_SECRET", ""),
    "api_url": "https://openapi.youdao.com/api",
}

# ============================================================
# 文本选择检测配置
# ============================================================
# 选中文本后多久(秒)自动触发翻译
SELECTION_DELAY = 0.5

# 最短翻译字符数 (小于此值的选中文本会被忽略)
MIN_TEXT_LENGTH = 1

# 最大翻译字符数 (超过此值截断)
MAX_TEXT_LENGTH = 5000

# 触发方式 (托盘菜单里可随时切换, 切换结果会保存到 %APPDATA%\TranslateAssistant\settings.json)
#   "ctrl" : 按住 Ctrl 再用鼠标选中才翻译 (默认, 不会误触)
#   "auto" : 选中即译
TRIGGER_MODE = "ctrl"

# 自动忽略代码/路径/纯数字符号等内容 (只对 "auto" 模式生效; ctrl 模式下是你主动按的, 一律翻译)
SKIP_CODE_LIKE = True

# 终端类程序 (进程名, 小写)。在终端里 Ctrl+C 是"中断正在运行的程序", 所以取词改用 Ctrl+Insert。
# "ctrl" 模式: 按住 Ctrl 选中时照常翻译(用 Ctrl+Insert 复制)
# "auto" 模式: 终端里一律不触发, 避免随手选字就误翻译
TERMINAL_PROCESSES = [
    "windowsterminal.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
    "conhost.exe", "mintty.exe", "wezterm-gui.exe", "alacritty.exe",
]

# 代码编辑器/IDE (进程名, 小写): 仅 "auto" 模式下忽略, 按住 Ctrl 选中时仍然翻译
IGNORE_PROCESSES = [
    "code.exe", "cursor.exe", "devenv.exe", "idea64.exe", "pycharm64.exe",
    "webstorm64.exe", "clion64.exe", "sublime_text.exe", "notepad++.exe",
]

# 诊断日志: 记录每次松开鼠标时的判断结果(只记进程名和判断条件, 不记选中的文字)
# 位置 %APPDATA%\TranslateAssistant\debug.log, 超过 200KB 自动清空
DEBUG_LOG = True

# ============================================================
# UI 配置
# ============================================================
# 弹窗宽度
POPUP_WIDTH = 460
# 译文区最大高度(像素): 高度随内容自适应, 超过该值在弹窗内部滚动; 原文区上限固定 84px
POPUP_MAX_HEIGHT = 480
# 弹窗显示时长(秒)，0 表示不自动关闭
POPUP_DURATION = 0
# 弹窗与鼠标的偏移(像素)
POPUP_OFFSET_X = 15
POPUP_OFFSET_Y = 15

# ============================================================
# 语音配置 (Windows SAPI5)
# ============================================================
# TTS 语速倍速 (0.5-3.0)
TTS_RATE = 1.5
# TTS 音量 (0.0-1.0)
TTS_VOLUME = 1.0
