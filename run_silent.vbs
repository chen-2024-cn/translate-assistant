' 无控制台启动器: 用 WScript 以隐藏窗口(样式 0)启动解释器, 启动后立即返回。
' 用途: 当 .venv 里没有 pythonw.exe 时, run.bat 用它兜底, 保证不留可见终端,
'       且关闭任何终端/父进程都不会带走翻译助手。
Option Explicit

Dim fso, shell, root, pyw, py, target
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = root & "\.venv\Scripts\pythonw.exe"
py = root & "\.venv\Scripts\python.exe"

target = pyw
If Not fso.FileExists(target) Then target = py
If Not fso.FileExists(target) Then
    MsgBox "未找到 .venv 解释器。" & vbCrLf & "请先按 README 创建虚拟环境:" & vbCrLf & _
           "py -3.14 -m venv .venv", 16, "翻译助手"
    WScript.Quit 1
End If

shell.CurrentDirectory = root
' 0 = 隐藏窗口, False = 不等待进程结束
shell.Run """" & target & """ """ & root & "\main.py""", 0, False
