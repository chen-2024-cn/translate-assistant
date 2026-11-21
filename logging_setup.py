"""统一的日志基础设施。

目的: 双击 run.bat / 打包 exe 运行时没有控制台, 出问题只能看到窗口一闪而过。
本模块把日志写到项目根目录(打包后为 exe 所在目录)的:
    logs/translate-assistant.log        主日志, 2MB 轮转, 保留 3 份
    logs/crash-faulthandler.log         进程级崩溃(段错误等)堆栈

同时接管:
    - sys.excepthook / threading.excepthook  未捕获异常(含后台线程)
    - Qt 消息处理器                           Qt 自身告警/插件错误
日志里不记录选中的文本内容, 只记录长度和判断结果, 避免把用户内容写进磁盘。
"""
from __future__ import annotations

import faulthandler
import logging
import logging.handlers
import sys
import threading
from pathlib import Path

LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "translate-assistant.log"
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3

_configured = False


def app_root() -> Path:
    """源码运行取项目根; 打包运行取 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log_dir() -> Path:
    return app_root() / LOG_DIR_NAME


def log_file() -> Path:
    return log_dir() / LOG_FILE_NAME


def setup_logging(level: int = logging.INFO) -> Path:
    """配置根日志: 文件始终启用; 有控制台时才额外输出到 stderr。

    pythonw.exe 启动时 sys.stderr 为 None, 不能无条件挂 StreamHandler。
    """
    global _configured
    path = log_file()
    if _configured:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    file_handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        root.addHandler(console)
    _configured = True
    logging.getLogger(__name__).info(
        "日志已初始化 | python=%s | frozen=%s | 文件=%s",
        sys.version.split()[0], getattr(sys, "frozen", False), path,
    )
    return path


def install_exception_hooks() -> None:
    """把未捕获异常写进日志, 而不是让 pythonw 静默退出。"""
    logger = logging.getLogger("crash")
    previous_hook = sys.excepthook

    def _excepthook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            previous_hook(exc_type, exc, tb)
            return
        logger.critical("未捕获异常, 程序可能已退出", exc_info=(exc_type, exc, tb))

    sys.excepthook = _excepthook

    def _thread_excepthook(args):
        logger.critical(
            "线程 %s 抛出未捕获异常",
            getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = _thread_excepthook

    try:
        crash_path = log_dir() / "crash-faulthandler.log"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        with open(crash_path, "a", encoding="utf-8") as stream:
            faulthandler.enable(stream)
    except Exception:  # faulthandler 不可用时不影响主流程
        logging.getLogger(__name__).debug("faulthandler 启用失败", exc_info=True)


def install_qt_message_handler() -> None:
    """把 Qt 自己的告警转进日志, 便于排查 qwindows.dll / 插件问题。"""
    try:
        from PyQt5.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:
        return
    logger = logging.getLogger("Qt")
    levels = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def handler(mode, context, message):
        logger.log(
            levels.get(mode, logging.INFO), "%s (%s:%s)",
            message, getattr(context, "file", None) or "?", getattr(context, "line", 0) or 0,
        )

    qInstallMessageHandler(handler)


def install_all() -> Path:
    path = setup_logging()
    install_exception_hooks()
    install_qt_message_handler()
    return path
