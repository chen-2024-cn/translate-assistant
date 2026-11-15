"""
语言方向判断 — 基于 Unicode 字符脚本实现 (确定性, 无网络, 无统计模型)

为什么不用 langdetect:
    langdetect 是基于 n-gram 画像的统计模型, 汉字同时存在于中/日/韩画像中,
    纯汉字短文本极易误判。实测 "明天预期什么时候" 被判为韩语 ko (置信度 0.9999),
    导致 MyMemory 以 ko|zh-CN 语言对翻译中文, 返回翻译记忆垃圾片段 "时间段为"。

为什么不能按"哪种字符数量最多"判断:
    中文技术文档常嵌入英文术语, 如事故句
    "配好后，PyCharm 的 Terminal 会自动帮你激活，右下角也会显示 Python 3.14 (.venv)。"
    汉字 18 个, 拉丁字母却有 25 个 (一个英文单词贡献一串字母), 按数量比会把
    中文句翻成"英文" → 走"译成中文"方向 → 百度中→中原样返回, 用户看到的还是原文。
    因此改用"脚本特征优先级"判断 (见 detect_script)。
"""
import re

_HAN = re.compile(r"[㐀-䶿一-鿿]")                   # 汉字 (含扩展A)
_HANGUL = re.compile(r"[ᄀ-ᇿ㄰-ㆎ가-힯]")  # 谚文
_KANA = re.compile(r"[぀-ヿ]")                        # 日文假名
_LATIN = re.compile(r"[A-Za-z]")                       # 拉丁字母

# 脚本 → MyMemory/Google 使用的语言代码
_SCRIPT_CODES = {"zh": "zh-CN", "en": "en", "ko": "ko", "ja": "ja"}


def detect_script(text: str) -> str:
    """按脚本特征优先级判断语言: 'zh' / 'ko' / 'ja' / 'en' / 'unknown'

    规则(按序短路):
      1. 谚文 ≥2            → ko
      2. 假名 ≥2            → ja
      3. 汉字 ≥2            → zh   (中英混排句仍是中文, 不受嵌入英文术语数量影响)
      4. 汉字 =1 且无拉丁字母 → zh   (单字选区, 如 "译")
      5. 有拉丁字母          → en
      6. 其余(纯数字/符号)   → unknown
    """
    han = len(_HAN.findall(text))
    hangul = len(_HANGUL.findall(text))
    kana = len(_KANA.findall(text))
    latin = len(_LATIN.findall(text))

    if hangul >= 2:
        return "ko"
    if kana >= 2:
        return "ja"
    if han >= 2:
        return "zh"
    if han == 1 and latin == 0:
        return "zh"
    if latin > 0:
        return "en"
    return "unknown"


def lang_pair(text: str) -> tuple:
    """自动翻译方向: 中文→英文; 英/韩/日/未知→中文
    返回 (源语言代码, 目标语言代码); 源永远是具体语言代码 (MyMemory 不接受 auto)"""
    script = detect_script(text)
    if script == "zh":
        return "zh-CN", "en"
    # 未知脚本默认按英文源处理 (取词场景绝大多数是英文), 与旧版异常兜底行为一致
    return _SCRIPT_CODES.get(script, "en"), "zh-CN"


def result_matches_target(translated: str, target: str) -> bool:
    """译文质量门: 目标语言为英文但译文仍以汉字为主 → 判为垃圾结果
    (拦截 MyMemory 在错误语言对下返回的 "时间段为" 式翻译记忆碎片)"""
    if not translated or not translated.strip():
        return False
    if target.lower().startswith("en"):
        han = len(_HAN.findall(translated))
        return han / len(translated) < 0.3
    return True


def is_noop_translation(original: str, translated: str, target: str) -> bool:
    """空翻译检测: 原文含 ≥2 个汉字, 而"译成中文"的结果与原文逐字相同
    → 引擎根本没翻译 (典型场景: 方向误判把中文送去"译成中文", 百度会原样返回)。
    专有名词原样输出 (如 "Python"→"Python") 不含汉字, 不会被误伤。"""
    if not target.lower().startswith("zh"):
        return False
    if (original or "").strip() != (translated or "").strip():
        return False
    return len(_HAN.findall(original or "")) >= 2
