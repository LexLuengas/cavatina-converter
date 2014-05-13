Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run """C:\Users\Administrator\Desktop\rtf2xml.bat"" " & WScript.Arguments.Item(0) & "", 0
Set WshShell = Nothing