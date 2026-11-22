' Starts Eye + Head Mouse with no terminal window (used by the desktop shortcut).
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = here
sh.Run """" & here & "\.venv\Scripts\python.exe"" app.py --log", 0, False
