' Starts A.I Assistant (HOLO) without a console window. Used by the autostart shortcut.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
WScript.Sleep 12000   ' let Windows finish logging in and the network come up
sh.CurrentDirectory = dir
sh.Run """" & dir & "\Start-Jarvis-HOLO.cmd""", 0, False
