# 翻译助手 TranslateAssistant

> Windows 划词翻译 · 本地英语词库 · Alt+1 / Alt+2 窗口开关

**凭证不内置**：百度等付费/认证服务由你在当前电脑配置自己的环境变量。项目不自动加载 `.env`。本仓库只发布源码；本地 `dist/` 不提交到 Git，且当前构建是便携 exe，不是安装程序。

**隐私提醒**：翻译内容会发给所选第三方服务，启用备用引擎时失败请求可能转到 MyMemory；单词查询也可能发送给百度网页词典。词库本地保存，但翻译并非离线。详见 [SECURITY.md](SECURITY.md)。

在 Windows 上**按住 Ctrl 选中英文/中文文本**（也可切换为"选中即译"），自动弹出翻译气泡。支持朗读、复制，常驻系统托盘，不影响正常办公。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🖱 **划词翻译** | 默认按住 Ctrl 再选中才翻译，也可切换为"选中即译"，松开鼠标后弹出翻译 |
| 🔄 **中英互译** | 自动检测语言，英文→中文 / 中文→英文 |
| 📖 **单词词典** | 选中单个单词时显示**词性 + 多种词义**（百度词典接口，免费无需 key），机翻作参考附后；句子仍走正常翻译，不受影响 |
| ⭐ **本地词库** | 单词翻译成功后点击“加入词库”，保存当前词性释义；面板顶部或托盘菜单打开词库，支持搜索、查看和确认删除，重复收藏不覆盖原释义 |
| ⌨ **全局快捷键** | Alt+1 切换翻译面板，Alt+2 切换词库：首次打开，再次隐藏；最小化时恢复显示，不清空输入或词库。面板打开后聚焦原文输入框 |
| 📜 **长文可读** | 弹窗原文/译文区均可滚动：长原文在自己的小区域内滚动，译文区高度随内容自适应（上限 480px），不再被截断覆盖；译文字号 18px |
| ↩ **跨行整句翻译** | 面板和划词共用段落处理：单个换行按排版折行合并，英文词间保留空格，连续中文不加空格；空行才分段，原文显示与复制保留原样。超出接口限制的长段仍需分块，不承诺无限长度整句请求 |
| 🔊 **语音朗读** | 原文、译文均可朗读，自动匹配中/英文语音 |
| 📋 **一键复制** | 点击按钮复制原文或译文 |
| 📌 **系统托盘** | 最小化到托盘常驻后台，不打扰工作 |
| 🎛 **触发方式可切换** | 托盘右键菜单里随时切换「按住 Ctrl 才翻译」/「选中即译」，设置自动保存 |
| ⏻ **划词总开关** | 托盘菜单一键关闭/开启划词翻译，关闭后完全不取词 |
| 🚫 **智能过滤** | 「选中即译」模式下自动忽略代码、路径、URL、纯数字符号，以及常见编辑器/IDE 中的选中 |
| 🛡 **终端保护** | 在 cmd / PowerShell / Windows Terminal 里取词改用 Ctrl+Insert，不会发出 Ctrl+C 中断正在运行的程序；「选中即译」模式下终端一律不触发 |
| 1️⃣ **单实例** | 重复启动会直接退出，不会出现多个托盘图标 |
| 🎨 **独立面板** | 双击托盘图标打开。窗口可自由缩放（默认 940×720），文字较大，原文/译文区可拖动分隔条调整大小，Ctrl+Enter 翻译，可置顶，原文和译文都能朗读，也能一键复制译文 |
| 🎯 **点击外部关闭** | 点击弹窗外任意位置自动关闭 |

---

## 📦 快速开始

### 方式一：直接运行 .exe（推荐）

1. 使用你自行构建的 `dist/TranslateAssistant.exe`（不要使用来源不明的旧包）
2. 先配置该电脑自己的百度环境变量，重开程序；然后**双击运行**
3. 系统托盘出现蓝色 "T" 图标 → 启动成功
4. 在任意窗口**按住 Ctrl 再用鼠标选中**英文/中文 → 翻译弹窗出现（默认模式，可在托盘菜单切换为"选中即译"）

> ⚠️ 首次运行 Windows SmartScreen 可能拦截，点击「更多信息」→「仍要运行」
>
> 📌 修改源码后，`dist/TranslateAssistant.exe` 不会自动更新，需要重新运行 `build.bat` 打包才会生效。

### 方式二：源码运行

安装 Windows Python **3.14 x64**，在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
powershell -ExecutionPolicy Bypass -File scripts\set_credentials.ps1
```

配置后重新打开终端/应用。双击 `run.bat` 通过项目 `.venv` 无控制台启动；调试可运行：

```powershell
.\.venv\Scripts\python.exe main.py
```

脚本优先使用 `.venv`，否则选择 Python Launcher/PATH 的解释器。`requirements.txt` 是直接依赖范围；`requirements.lock.txt` 固定本项目验证环境的运行依赖，`requirements-build.lock.txt` 追加打包依赖。不保证其他 Python 版本或架构能使用同一锁文件。

---

## 🎛 触发方式与托盘菜单

右键系统托盘的蓝色 "T" 图标：

| 菜单项 | 说明 |
|--------|------|
| 📋 打开翻译面板 (Alt+1) | 手动输入文本翻译（全局 Alt+1 或双击托盘图标同样可打开） |
| 📖 打开词库 (Alt+2) | 查看收藏的单词与完整释义，可搜索和确认删除；Alt+2 再按可隐藏 |
| 划词翻译（勾选） | 总开关。取消勾选后不再响应任何选中操作 |
| 按住 Ctrl 再选中才翻译 | **默认模式**。只有按住 Ctrl 的同时选中文字才翻译，平时随便选字、选代码都不会误触 |
| 选中即译（自动忽略代码） | 拖选或双击选词后自动翻译，单击不触发；会过滤代码、路径、URL、纯数字符号，并忽略编辑器/IDE |
| ❌ 退出 | 退出程序 |

两种触发方式的区别：

| | 按住 Ctrl 模式 | 选中即译模式 |
|---|---|---|
| 触发条件 | 按住 Ctrl 的同时拖选或双击选词 | 拖选或双击选词 |
| 代码/路径等内容过滤 | 不过滤（是你主动按的，一律翻译） | 自动过滤 |
| 编辑器/IDE 中 | 照常翻译 | 忽略 |
| 终端（cmd/PowerShell 等） | 照常翻译（用 Ctrl+Insert 取词） | 不触发 |

> 开关和触发方式保存在 `%APPDATA%\TranslateAssistant\settings.json`，下次启动自动沿用。打包成 exe 后同样有效。
>
> 「选中即译」的代码过滤是启发式规则，像 `def foo(x): return x` 这类很短的代码识别不出来。想彻底避免误触，请使用默认的 Ctrl 模式。

---

## 📁 项目结构

```
translate-assistant/
├── main.py                  # 程序入口，应用主控制器
├── config.py                # 配置文件（切换API、调参都在这里）
├── popup_ui.py              # 翻译弹窗 UI（暗色 Catppuccin 风格）
├── selection_monitor.py     # 鼠标选中检测：拖选/双击识别、Ctrl 触发、前台程序过滤
├── settings.py              # 托盘开关/触发方式的持久化（%APPDATA%）
├── text_filter.py           # 选中内容过滤（代码/路径/URL/纯数字符号）
├── tts_engine.py            # 语音朗读（Windows SAPI5 COM）
├── tray_manager.py          # 系统托盘与右键菜单
├── panel_ui.py              # 独立翻译面板（可缩放，翻译在后台线程执行）
├── vocabulary_store.py      # 本地SQLite词库，事务写入与单词去重
├── vocabulary_ui.py         # 词库列表/搜索/详情和复用收藏按钮
├── vocabulary_entry.py      # 英文收藏规范化、旧中文记录只读英文展示
├── global_hotkey.py         # Windows Alt+1/Alt+2独立注册、Qt原生消息与退出注销
├── translator/
│   ├── __init__.py
│   ├── base.py              # 翻译器抽象基类（策略模式）
│   ├── lang_util.py         # 语言方向判断（Unicode 字符脚本，确定性检测）+ 译文质量门
│   ├── word_dict.py         # 单词词典查询（词性+多词义，仅单词触发，句子直通）
│   ├── text_processing.py   # 合并段内换行，保留空行分段和原文，两个翻译入口共用
│   ├── google.py            # Google 翻译（免费，国内网络易被限流）
│   ├── baidu.py             # 百度翻译（默认引擎，需 APPID/密钥）
│   ├── youdao.py            # 有道翻译（需 API Key）
│   ├── mymemory.py          # MyMemory 翻译（免费，备用引擎）
│   ├── fallback.py          # 主引擎失败时自动切换备用引擎
│   └── factory.py           # 工厂方法：自动选择翻译引擎
├── tests/                   # 回归测试（含线上事故用例，改动翻译链路后必跑）
├── requirements.txt         # Python 依赖
├── run.bat                  # 双击启动（开发模式，无终端窗口，只剩托盘图标）
├── run_tests.bat            # 一键跑回归测试（unittest，无网络请求）
├── build.bat                # 检查脱敏配置、测试、调用spec打包
├── TranslateAssistant.spec  # 唯一打包参数，附带许可证材料
├── requirements.lock.txt    # 已验证Windows运行依赖固定版本
├── requirements-build.lock.txt # 打包依赖固定版本
├── LICENSE                  # GPL-3.0-only完整许可证
├── THIRD_PARTY_NOTICES.md    # 第三方许可与来源说明
├── SECURITY.md              # 密钥、隐私与报告渠道
├── scripts/                 # 启动环境、凭证配置、发布检查和界面验收
└── dist/
    └── TranslateAssistant.exe   # 打包好的可执行文件
```

---

## ⚙️ 配置说明

编辑 `config.py` 即可调整所有参数：

### 切换翻译 API

```python
# 当前默认：百度翻译开放平台
# 凭证只从环境变量读取；不要把真实值写入源码。
TRANSLATOR = "baidu"
BAIDU_CONFIG = {
    "appid": os.environ.get("BAIDU_APPID", ""),
    "secret_key": os.environ.get("BAIDU_SECRET_KEY", ""),
    "api_url": "https://fanyi-api.baidu.com/api/trans/vip/translate",
}

# Google 免费接口在国内网络普遍被限流(HTTP 429), 可切回但不推荐
# TRANSLATOR = "google"

# 有道翻译（需填写 app_key 和 app_secret）
# TRANSLATOR = "youdao"
YOUDAO_CONFIG = {
    "app_key": os.environ.get("YOUDAO_APP_KEY", ""),
    "app_secret": os.environ.get("YOUDAO_APP_SECRET", ""),
}
```

### 检测参数

```python
SELECTION_DELAY = 0.5     # 选中后延迟触发(秒)
MIN_TEXT_LENGTH = 1        # 最短翻译字符数
MAX_TEXT_LENGTH = 5000     # 最长翻译字符数
```

### 触发方式与过滤

```python
# 默认触发方式: "ctrl" = 按住 Ctrl 再选中才翻译 | "auto" = 选中即译
# 托盘菜单里改动后会保存到 %APPDATA%\TranslateAssistant\settings.json，并优先于这里的值
TRIGGER_MODE = "ctrl"

# "auto" 模式下是否自动忽略代码/路径/URL 等内容
SKIP_CODE_LIKE = True

# 终端类程序（进程名，小写）：Ctrl 模式下用 Ctrl+Insert 取词，选中即译模式下不触发
TERMINAL_PROCESSES = ["windowsterminal.exe", "cmd.exe", "powershell.exe", ...]

# 代码编辑器/IDE（进程名，小写）：仅 "auto" 模式下忽略，按住 Ctrl 选中时仍会翻译
IGNORE_PROCESSES = ["code.exe", "cursor.exe", "pycharm64.exe", ...]
```

> 打包成 exe 后无法再改 `config.py`，运行期想调整请使用托盘菜单。

### UI 参数

```python
POPUP_WIDTH = 460          # 弹窗宽度(像素)
POPUP_DURATION = 0         # 弹窗自动关闭时间(秒)，0=不自动关闭
POPUP_OFFSET_X = 15        # 弹窗与鼠标水平偏移
POPUP_OFFSET_Y = 15        # 弹窗与鼠标垂直偏移
```

### 语音参数

```python
TTS_RATE = 1.5             # 语速倍速 (0.5-3.0)
TTS_VOLUME = 1.0           # 音量 (0.0-1.0)
```

---

## 🔌 扩展翻译 API

在 `translator/` 下新增文件，继承 `BaseTranslator`，然后在 `factory.py` 注册即可：

```python
# translator/myservice.py
from translator.base import BaseTranslator

class MyTranslator(BaseTranslator):
    def name(self) -> str:
        return "我的翻译"

    def translate(self, text: str, dest: str = "auto") -> dict:
        # ... 实现翻译逻辑
        return {
            "original": text,
            "translated": "翻译结果",
            "source_lang": "en",
            "target_lang": "zh-CN",
        }
```

```python
# translator/factory.py 中注册
elif config.TRANSLATOR == "myservice":
    from translator.myservice import MyTranslator
    return MyTranslator(config.MY_CONFIG)
```

---

## 📦 打包为 .exe

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.lock.txt
.\build.bat
```

`build.bat` 会先运行回归测试，再调用唯一打包配置 `TranslateAssistant.spec`；失败时返回非零退出码。输出 `dist/TranslateAssistant.exe`，不内置 API 凭证，许可证资料一同打包。构建需在 Windows x64 上进行，不在 Linux/macOS 直接生成 Windows 版。

### 在另一台电脑使用

- 目标为兼容的 Windows 10/11 x64；exe 已包含 Python，运行无需安装 Python。
- 复制你信任的无密钥 exe，并通过 Windows 用户环境变量配置自己的 `BAIDU_APPID` / `BAIDU_SECRET_KEY`；配置辅助脚本可单独复制，不要复制真实凭证文件。
- 必须联网；百度IP白名单/额度、代理和防火墙可能影响请求。
- 朗读依赖目标系统安装的中英文语音包。
- 用户词库与设置不随exe复制。迁移词库前先退出两台电脑的应用并备份目标数据库；不要覆盖已有词库或上传到GitHub。
- 未签名exe可能有安全提示，不要关闭系统安全软件；公开分发前需另做签名、许可/对应源码准备和目标电脑验收。

### 测试与验证边界

`run_tests.bat` 运行mock网络/剪贴板的回归测试。`scripts/verify_*.py` 是真实Qt界面验收脚本，部分会请求外部翻译服务，运行前阅读脚本且使用示例文本。其截图、日志、隔离数据库位于被忽略的 `artifacts/`。

当前记录：107个回归测试已通过，Alt+2真实窗口开关已验证；Alt+1完整实际按键验收曾被旧实例占用阻塞，仍需在没有冲突的环境验证。尚未完成另一台干净电脑的整机验收，构建成功不等于所有环境都兼容。

---

## ❓ 常见问题

**如何收藏与打开词库？**
英文单词翻译成功后，在划词弹框或面板译文区点击“加入词库”，按钮和状态行会确认已保存；选区边缘的引号/句号/逗号不会阻止收藏。句子和中文原词不作为新的英语词库词条。通过弹框“打开词库”、托盘菜单或面板顶部“词库”查看：左侧英文词头，选中后右侧中文词性释义。重复英文词不区分大小写、不覆盖旧释义。旧中文记录不删改，有明确英文译词时按英文展示；无法确定时在“旧词条”入口保留。数据在 `%APPDATA%\TranslateAssistant\vocabulary.db`，重启保留、不上传云端。

**面板打开后如何直接输入？**
Alt+1、托盘菜单和双击入口共用焦点处理，恢复最小化后自动定位原文输入框并选中已有内容；直接打字会替换选中的旧输入。激活时不清空原文，打开词库或切走后不会持续抢焦点。

**Alt+1 / Alt+2 如何打开和关闭窗口？**
应用运行时，Alt+1 切换翻译面板，Alt+2 切换词库。窗口未显示时打开，已显示时隐藏；最小化时恢复而非隐藏。隐藏不退出助手、不丢输入、不删除词库。不同入口打开的是同一个词库窗口，快捷键均可关闭。托盘菜单和面板按钮仍只负责打开，不改成开关。出现删除确认框时暂不切换窗口，避免误绕过确认。

使用主键盘数字1/2，而不是小键盘。两组快捷键独立注册，某一组被其他软件占用不会让另一组失效；失败有提示，仍可用托盘菜单打开。退出应用后释放两组快捷键。

**启动时出现了终端窗口？**
用 `run.bat` 启动不会残留终端窗口。如果自己执行 `python main.py`，程序会隐藏专属于它的控制台；想完全无窗口，请用 `pythonw main.py` 或直接运行打包好的 exe。

**选中代码、普通文字时总是弹出翻译？**
把托盘菜单切到「按住 Ctrl 再选中才翻译」（默认），或直接取消勾选「划词翻译」。

**在终端里选中文字没有翻译？**
「选中即译」模式下终端是有意不触发的，避免随手选字就弹翻译；请切到「按住 Ctrl 再选中才翻译」。终端里取词用的是 Ctrl+Insert 而不是 Ctrl+C，不会中断正在运行的程序。如果某个终端仍然取不到词，可以复制后到「翻译面板」里粘贴。

**改了 `config.py` 但 exe 没变化？**
exe 里打包的是旧配置。重新运行 `build.bat`，或者用托盘菜单修改触发方式。

**如何配置百度翻译（当前默认引擎）？**
在百度翻译开放平台申请通用文本翻译服务，获取 APPID 和密钥（单独的其他百度API Key不一定是此服务凭证）。运行 `scripts/set_credentials.ps1`，或在Windows用户环境变量中设置 `BAIDU_APPID` / `BAIDU_SECRET_KEY`，然后重新启动应用。不要填写进 `config.py`，不要粘贴到Issue/日志或提交到Git。`.env.example`只是变量名示例，程序不自动加载它。

**翻译失败，提示百度错误码？**
- `52003 UNAUTHORIZED USER`：APPID/密钥不对，或应用未开通"通用文本翻译"服务
- `54001 sign error`：签名错误，检查密钥是否完整粘贴（首尾不能有空格）
- `58000 客户端IP非法`：在开放平台控制台把当前公网 IP 加入白名单（或将白名单留空表示不限制）
- `54003 请求频率过快`：标准版限 1 QPS，程序已在分块之间自动限速；仍出现说明有其他程序在共用该 APPID
- `58083 参数to错误`：旧版本 bug（发送了百度不支持的 `to=auto`），当前版本已修复，重新打包即可

**翻译失败，提示请求过多（Too many requests）？**
这是 Google 免费接口按 IP 限流（国内网络下普遍出现，因此默认引擎已改为百度）。程序自带降级链：主引擎失败后自动改用 MyMemory，失败的引擎 5 分钟内不再重试。`MYMEMORY_CONFIG` 里填一个邮箱可以把匿名每天约 5000 字符的额度提高到约 50000。

**托盘右键菜单里没有「退出」？**
旧版有这个问题：「退出」菜单项没有被保存引用，会被 Python 回收，导致菜单里凭空消失。现已修复，重启程序即可；打包版需要重新运行 `build.bat`。

**点了「退出」但后台进程还在？**
托盘图标藏在任务栏右下角的「^」折叠区里时容易找不到。退出现在会强制结束进程，并移除托盘图标；翻译请求最多等待 12 秒，不会再拖住退出。如果仍有残留，可在任务管理器里结束 `pythonw.exe`（源码运行）或 `TranslateAssistant.exe`（打包版）。

**按住 Ctrl 选中没有反应？**
查看 `%APPDATA%\TranslateAssistant\debug.log`，每次松开鼠标都会记录前台进程、Ctrl 是否按下、是否被识别为拖选，以及被忽略的具体原因（日志不记录选中的文字）。常见原因：当前窗口是终端；目标程序以管理员身份运行而本程序不是；目标程序不响应 Ctrl+C。不需要日志时把 `config.py` 里的 `DEBUG_LOG` 设为 `False`。

---

## 🛠 技术栈

| 模块 | 技术 |
|------|------|
| GUI 框架 | PyQt5 |
| 鼠标/按键检测 | win32api (GetAsyncKeyState) |
| 前台程序识别 | win32gui + win32process |
| 单实例 / 隐藏控制台 | win32event (命名互斥体) + win32console |
| 剪贴板 | pyperclip |
| 翻译引擎 | 百度翻译开放平台（默认，requests）；备选 Google (deep-translator)、有道、MyMemory，失败自动降级 |
| 语言检测 | 内置 Unicode 字符脚本检测（`translator/lang_util.py`，确定性判断，已替代 langdetect——其对纯汉字短文本会误判为韩语） |
| 语音朗读 | Windows SAPI5 (win32com.client) |
| 系统操作 | pywin32 |
| 打包 | PyInstaller |

---

## 🖥 系统要求

- Windows 10 / 11（64 位）
- 无需安装 Python（使用 .exe 版本）
- 需要网络连接（翻译 API）

---

## 📄 License

本项目采用 **GPL-3.0-only**，完整条款见 [LICENSE](LICENSE)。第三方组件保留各自许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 `third_party/licenses/`。公开分发exe还需满足对应源码与许可声明义务，不能仅附一行“MIT”。