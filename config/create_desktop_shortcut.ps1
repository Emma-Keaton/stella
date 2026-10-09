$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('C:\Users\ravit\OneDrive\Desktop\Stella Evo.lnk')
$Shortcut.TargetPath = 'D:\TiTech Prabha Solution\Stella AI\Stella AI\Stella-AI---Lite-main\Stella-AI---Lite-main\.venv\Scripts\pythonw.exe'
$Shortcut.Arguments = '"D:\TiTech Prabha Solution\Stella AI\Stella AI\Stella-AI---Lite-main\Stella-AI---Lite-main\main.py"'
$Shortcut.WorkingDirectory = 'D:\TiTech Prabha Solution\Stella AI\Stella AI\Stella-AI---Lite-main\Stella-AI---Lite-main'
$Shortcut.WindowStyle = 7
$Shortcut.Description = 'Launch Stella Evo'
if ('D:\TiTech Prabha Solution\Stella AI\Stella AI\Stella-AI---Lite-main\Stella-AI---Lite-main\assets\Stella_Lite_Logo.ico') { $Shortcut.IconLocation = 'D:\TiTech Prabha Solution\Stella AI\Stella AI\Stella-AI---Lite-main\Stella-AI---Lite-main\assets\Stella_Lite_Logo.ico,0' }
$Shortcut.Save()