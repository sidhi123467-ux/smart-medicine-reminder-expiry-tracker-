@echo off
cd /d "%~dp0"
where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "Smart Medicine Reminder" pyw.exe "%~dp0Smart_Medicine_Reminder.pyw"
    exit /b
)
where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "Smart Medicine Reminder" pythonw.exe "%~dp0Smart_Medicine_Reminder.pyw"
    exit /b
)
where python.exe >nul 2>&1
if not errorlevel 1 (
    start "Smart Medicine Reminder" python.exe "%~dp0Smart_Medicine_Reminder.pyw"
    exit /b
)
echo Python was not found on this computer.
pause
