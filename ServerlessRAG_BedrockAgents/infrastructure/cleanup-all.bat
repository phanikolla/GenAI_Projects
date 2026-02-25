@echo off
REM Batch file wrapper for PowerShell cleanup script
REM This allows double-click execution on Windows

echo Starting cleanup script...
echo.

powershell.exe -ExecutionPolicy Bypass -File "%~dp0cleanup.ps1"

pause
