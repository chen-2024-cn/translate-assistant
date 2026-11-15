"""
带备用的翻译器: 主引擎失败(被限流/断网)时自动改用下一个引擎
失败的引擎冷却一段时间不再重试, 避免每次翻译都先白等一轮
"""
import threading
import time

from translator.base import BaseTranslator

_COOLDOWN = 300  # 秒
_TIMEOUT = 12    # 单个引擎的最长等待(秒), deep-translator 自身没有超时
_failed_at = {}  # 引擎名 -> 上次失败时间 (模块级, 多个实例共享)


def _call_with_timeout(fn, timeout: float = _TIMEOUT):
    """在守护线程里执行, 超时就放弃(线程留在后台, 不会拖住进程退出)"""
    box = {}

    def run():
        try:
            box["result"] = fn()
        except BaseException as e:
            box["error"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"超过 {timeout:g} 秒没有响应")
    if "error" in box:
        raise box["error"]
    return box["result"]


class FallbackTranslator(BaseTranslator):
    def __init__(self, engines: list):
        super().__init__()
        self._engines = engines
        self._last = engines[0]

    def name(self) -> str:
        return self._last.name()

    def translate(self, text: str, dest: str = "auto") -> dict:
        now = time.time()
        candidates = [e for e in self._engines
                      if now - _failed_at.get(e.name(), 0) > _COOLDOWN]
        if not candidates:
            candidates = self._engines

        errors = []
        for engine in candidates:
            try:
                result = _call_with_timeout(lambda e=engine: e.translate(text, dest))
                self._last = engine
                _failed_at.pop(engine.name(), None)
                return result
            except Exception as e:
                _failed_at[engine.name()] = time.time()
                first_line = (str(e).splitlines() or [""])[0][:80]
                errors.append(f"{engine.name()}: {first_line}")
        raise RuntimeError("; ".join(errors))
