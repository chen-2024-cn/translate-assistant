"""
有道翻译引擎
需要申请 app_key 和 app_secret
申请地址: https://ai.youdao.com/
"""
import hashlib
import uuid
import requests
from translator.base import BaseTranslator


class YoudaoTranslator(BaseTranslator):
    """有道翻译实现"""

    def name(self) -> str:
        return "有道翻译"

    def translate(self, text: str, dest: str = "auto") -> dict:
        app_key = self.config.get("app_key", "")
        app_secret = self.config.get("app_secret", "")
        api_url = self.config.get("api_url", "")

        salt = str(uuid.uuid4())
        curtime = str(int(__import__("time").time()))
        sign_str = app_key + _truncate(text) + salt + curtime + app_secret
        sign = hashlib.sha256(sign_str.encode()).hexdigest()

        dest_map = {"zh": "zh-CHS", "en": "en", "auto": "auto"}
        target = dest_map.get(dest, "auto")

        from_lang = "auto"
        if dest == "zh":
            from_lang = "en"
        elif dest == "en":
            from_lang = "zh-CHS"

        params = {
            "q": text,
            "from": from_lang,
            "to": target,
            "appKey": app_key,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime,
        }

        resp = requests.get(api_url, params=params, timeout=10)
        data = resp.json()

        if data.get("errorCode") and data["errorCode"] != "0":
            raise RuntimeError(f"有道翻译错误 [{data['errorCode']}]: {data.get('errorMsg', '')}")

        return {
            "original": text,
            "translated": " ".join(data.get("translation", [text])),
            "source_lang": data.get("l", "unknown").split("2")[0] if "2" in data.get("l", "") else data.get("l", "unknown"),
            "target_lang": target,
        }


def _truncate(q: str) -> str:
    """有道签名要求：q 长度 >20 时取前10 + 长度 + 后10"""
    if q is None:
        q = ""
    size = len(q)
    if size <= 20:
        return q
    return q[:10] + str(size) + q[-10:]
