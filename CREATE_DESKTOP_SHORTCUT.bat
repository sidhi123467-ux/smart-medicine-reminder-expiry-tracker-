@echo off
setlocal
cd /d "%~dp0"
set "TARGET=%~dp0RUN_Smart_Medicine_Reminder.bat"
set "DESKTOP=%USERPROFILE%\Desktop"
set "LNK=%DESKTOP%\Smart Medicine Reminder.lnk"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut($env:LNK); $s.TargetPath=$env:TARGET; $s.WorkingDirectory=(Split-Path $env:TARGET); $s.IconLocation='%SystemRoot%\System32\SHELL32.dll,1'; $s.Description='Smart Medicine Reminder & Expiry Tracker'; $s.Save()"
if exist "%LNK%" (
 echo SUCCESS - Desktop shortcut created.
 echo Double-click "Smart Medicine Reminder" on the Desktop.
) else (
 echo Could not create shortcut.
)
pause
