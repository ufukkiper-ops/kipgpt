' KipGPT — konsolsuz başlatıcı (masaüstü kısayolu için)
Option Explicit

Dim fso, sh, root, pythonw, mainpy, startBat
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
pythonw = root & "\.venv\Scripts\pythonw.exe"
mainpy = root & "\desktop\main.py"
startBat = root & "\desktop\start.bat"

sh.CurrentDirectory = root

If fso.FileExists(pythonw) And fso.FileExists(mainpy) Then
  ' 0 = gizli pencere (cmd yok)
  sh.Run """" & pythonw & """ """ & mainpy & """", 0, False
Else
  ' İlk kurulum / venv yok: start.bat
  sh.Run """" & startBat & """", 1, False
End If
