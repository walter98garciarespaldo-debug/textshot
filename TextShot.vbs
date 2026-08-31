' TextShot Launcher — corre la GUI sin abrir ninguna ventana de consola
' Usar pythonw.exe para que no aparezca la terminal negra

Dim oShell, fso, scriptDir
Set oShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obtener la carpeta donde reside este script
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

oShell.Run "pythonw.exe """ & scriptDir & "\run_gui.py""", 0, False

Set oShell = Nothing
Set fso = Nothing
