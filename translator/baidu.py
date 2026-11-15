"""
百度翻译引擎 (百度翻译开放平台 - 通用文本翻译)
需要申请 appid 和 secret_key, 申请地址: https://fanyi-api.baidu.com/

注意事项:
- 百度的 to(目标语言) 参数不支持 auto, 必须指明具体语言。
  旧实现在 dest="auto" 时直接发 to=auto, 百度必然报错(58083/54000), 已修复:
  自动方向 = 中文→英文, 其他→中文 (方向判断见 translator/lang_util.py)
- 标准版单次请求 q 最长 2048 字节(约 680 汉字), 长文本按句子切块分段翻译
- 标准版限频 1 QPS, 同一引擎的分块/跨段/连续请求均限制间隔, 避免 54003 错误
"""
import hashlib
import random
import threading
import time

import requests

from translator.base import BaseTranslator
from translator.lang_util import detect_script, result_matches_target, is_noop_translation
# 复用 MyMemory 的句子切块逻辑 (按句末标点切, 不切断句子)
from translator.mymemory import _split

# 百度标准版单次 2048 字节; 汉字 UTF-8 占 3 字节, 取 600 字符留足余量
_CHUNK = 600
# 标准版限频 1 QPS
_QPS_INTERVAL = 1.0


class BaiduTranslator(BaseTranslator):
    """百度翻译实现"""

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._request_lock = threading.Lock()
        self._last_request_at = None

    def _wait_for_slot(self):
        # 跨段落/连续调用也限速, 不再只保护同一次翻译中的分块。
        with self._request_lock:
            now = time.monotonic()
            if self._last_request_at is not None:
                delay = _QPS_INTERVAL - (now - self._last_request_at)
                if delay > 0:
                    time.sleep(delay)
            self._last_request_at = time.monotonic()

    def name(self) -> str:
        return "百度翻译"

    def translate(self, text: str, dest: str = "auto") -> dict:
        appid = self.config.get("appid", "")
        secret_key = self.config.get("secret_key", "")
        api_url = self.config.get("api_url", "")

        # 百度 to 参数不支持 auto: 自动模式 = 中文→英文, 其他→中文
        if dest == "auto":
            target = "en" if detect_script(text) == "zh" else "zh"
        else:
            target = {"zh": "zh", "en": "en"}.get(dest, dest)

        out = []
        chunks = _split(text, limit=_CHUNK)
        for chunk in chunks:
            self._wait_for_slot()
            salt = str(random.randint(32768, 65536))
            # 百度签名: md5(appid + q + salt + 密钥), q 用原文(非URL编码)
            sign = hashlib.md5((appid + chunk + salt + secret_key).encode()).hexdigest()
            params = {
                "q": chunk,
                "from": "auto",
                "to": target,
                "appid": appid,
                "salt": salt,
                "sign": sign,
            }
            # 用 POST: GET 拼 URL 会受 URL 长度限制, 中文长文本必挂
            resp = requests.post(api_url, data=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("error_code"):
                raise RuntimeError(
                    f"百度翻译错误 [{data['error_code']}]: {data.get('error_msg', '未知错误')}"
                )

            result_list = data.get("trans_result") or []
            if not result_list:
                # 空结果视为失败(触发 fallback 降级), 绝不把原文当译文静默返回
                raise RuntimeError("百度翻译返回空结果")
            # trans_result 按行返回, 必须全部拼接
            # (旧实现只取 result_list[0], 多行文本从第二行起全部丢失)
            out.append("\n".join(item.get("dst", "") for item in result_list))

        translated = "\n".join(out)
        # 质量门: 目标为英文但译文仍以汉字为主 → 判失败, 不展示垃圾结果
        if not result_matches_target(translated, target):
            raise RuntimeError(f"译文语言与目标不符, 疑似引擎返回垃圾结果: {translated[:50]}")
        # 空翻译门: 中文原文"译成中文"且结果与原文逐字相同 → 方向误判/引擎未翻译, 判失败触发降级
        # (事故回归: 中英混排句曾被误判为英文, 百度中→中原样返回, 用户看到的还是原文)
        if is_noop_translation(text, translated, target):
            raise RuntimeError("译文与原文相同, 引擎未执行翻译")

        return {
            "original": text,
            "translated": translated,
            "source_lang": "auto",
            "target_lang": target,
        }
