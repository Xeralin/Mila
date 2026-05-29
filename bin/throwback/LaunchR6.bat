@echo off
setlocal
cd /d "%~dp0"

taskkill /IM RainbowSix.exe /F /T >nul 2>&1
taskkill /IM RainbowSix_DX11.exe /F /T >nul 2>&1
taskkill /IM RainbowSix_DX12.exe /F /T >nul 2>&1
taskkill /IM RainbowSix_Vulkan.exe /F /T >nul 2>&1
taskkill /IM RainbowSixGame.exe /F /T >nul 2>&1
taskkill /IM cheatengine-x86_64.exe /F /T >nul 2>&1

__CE_START__
if exist "RainbowSixGame.exe"    ( echo RainbowSixGame.exe launching...    & start "" "RainbowSixGame.exe"    /belaunch /nologo & goto :wait_and_kill )
if exist "RainbowSix_DX11.exe"   ( echo RainbowSix_DX11.exe launching...   & start "" "RainbowSix_DX11.exe"   /belaunch /nologo & goto :wait_and_kill )
if exist "RainbowSix.exe"        ( echo RainbowSix.exe launching...        & start "" "RainbowSix.exe"        /belaunch /nologo & goto :wait_and_kill )
if exist "RainbowSix_Vulkan.exe" ( echo RainbowSix_Vulkan.exe launching... & start "" "RainbowSix_Vulkan.exe" /belaunch /nologo & goto :wait_and_kill )

echo.
echo ERROR: Could not find any R6 executable in this folder.
echo Press any key to exit...
pause > nul
goto :eof

:wait_and_kill
echo Press any key to close the game...
pause >nul
echo Closing R6...

taskkill /IM RainbowSix.exe /F /T >nul 2>&1
taskkill /IM RainbowSix_DX11.exe /F /T >nul 2>&1
taskkill /IM RainbowSix_DX12.exe /F /T >nul 2>&1
taskkill /IM RainbowSix_Vulkan.exe /F /T >nul 2>&1
taskkill /IM RainbowSixGame.exe /F /T >nul 2>&1
taskkill /IM cheatengine-x86_64.exe /F /T >nul 2>&1

echo Exiting...