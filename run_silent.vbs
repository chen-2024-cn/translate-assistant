' Silent launcher for TranslateAssistant.
' Runs main.py with a hidden window so no console is created, then returns at once.
' Keep this file ASCII-only: Windows Script Host reads .vbs in the system ANSI
' codepage, so UTF-8 Chinese text here fails with 800A0408 "invalid character".
Option Explicit

Dim fso, sh, root, pyw, py, target, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = root & "\.venv\Scripts\pythonw.exe"
py = root & "\.venv\Scripts\python.exe"

If fso.FileExists(pyw) Then
    target = pyw
ElseIf fso.FileExists(py) Then
    target = py
Else
    MsgBox "No Python interpreter found in .venv" & vbCrLf & _
           "Create it first: py -3.14 -m venv .venv", 16, "TranslateAssistant"
    WScript.Quit 1
End If

If Not fso.FileExists(root & "\main.py") Then
    MsgBox "main.py not found next to this script.", 16, "TranslateAssistant"
    WScript.Quit 1
End If

sh.CurrentDirectory = root
' style 0 = hidden window, False = do not wait for the process
cmd = """" & target & """ """ & root & "\main.py"""
sh.Run cmd, 0, False
WScript.Quit 0
