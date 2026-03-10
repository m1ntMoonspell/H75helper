@echo off
chcp 65001 >nul 2>&1
title H75 Helper - 一键环境配置脚本
color 0A

echo ============================================================
echo        H75 Helper 一键环境配置脚本
echo ============================================================
echo.

:: ──────────────────────────────────────────────────────────────
::  1. 检查 Python
:: ──────────────────────────────────────────────────────────────
echo [1/6] 检查 Python ...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python。
    echo         请从 https://www.python.org/downloads/ 安装 Python 3.10+
    echo         安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo         Python %PYVER% ... OK
echo.

:: ──────────────────────────────────────────────────────────────
::  2. 安装 Python 依赖
:: ──────────────────────────────────────────────────────────────
echo [2/6] 安装 Python 依赖 (PySide6, pywin32) ...
pip install PySide6 pywin32 --quiet
if %errorlevel% neq 0 (
    echo [警告] pip install 遇到问题，尝试使用 --user 安装 ...
    pip install PySide6 pywin32 --user --quiet
)
echo         PySide6, pywin32 ... OK
echo.

:: ──────────────────────────────────────────────────────────────
::  3. 检查 / 下载 ADB (Android SDK Platform Tools)
:: ──────────────────────────────────────────────────────────────
echo [3/6] 检查 ADB ...
adb version >nul 2>&1
if %errorlevel% neq 0 (
    echo         未找到 adb，正在下载 Android SDK Platform Tools ...
    set "ADB_DIR=%~dp0platform-tools"

    if not exist "%~dp0platform-tools\adb.exe" (
        powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile '%TEMP%\platform-tools.zip' }"
        if %errorlevel% neq 0 (
            echo [错误] 下载 Platform Tools 失败。
            echo         请手动下载: https://developer.android.com/studio/releases/platform-tools
            pause
            exit /b 1
        )
        powershell -Command "Expand-Archive -Path '%TEMP%\platform-tools.zip' -DestinationPath '%~dp0' -Force"
        del "%TEMP%\platform-tools.zip" >nul 2>&1
    )

    :: 添加到当前会话 PATH
    set "PATH=%~dp0platform-tools;%PATH%"

    :: 持久写入用户 PATH
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%B"
    echo %USERPATH% | findstr /I /C:"platform-tools" >nul 2>&1
    if %errorlevel% neq 0 (
        setx PATH "%USERPATH%;%~dp0platform-tools" >nul 2>&1
        echo         已将 platform-tools 添加到用户 PATH
    )

    adb version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] ADB 安装后仍无法运行
        pause
        exit /b 1
    )
)
for /f "tokens=1-5" %%a in ('adb version 2^>^&1') do (
    echo         %%a %%b %%c %%d %%e
    goto :adb_done
)
:adb_done
echo         ADB ... OK
echo.

:: ──────────────────────────────────────────────────────────────
::  4. 检查 / 下载 scrcpy
:: ──────────────────────────────────────────────────────────────
echo [4/6] 检查 scrcpy ...
scrcpy --version >nul 2>&1
if %errorlevel% neq 0 (
    echo         未找到 scrcpy，正在下载 ...
    set "SCRCPY_DIR=%~dp0scrcpy"
    set "SCRCPY_VER=3.1"

    if not exist "%~dp0scrcpy\scrcpy.exe" (
        echo         正在下载 scrcpy v%SCRCPY_VER% (约 40MB) ...
        powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/Genymobile/scrcpy/releases/download/v3.1/scrcpy-win64-v3.1.zip' -OutFile '%TEMP%\scrcpy.zip' }"
        if %errorlevel% neq 0 (
            echo [错误] 下载 scrcpy 失败。
            echo         请手动下载: https://github.com/Genymobile/scrcpy/releases
            pause
            exit /b 1
        )
        powershell -Command "Expand-Archive -Path '%TEMP%\scrcpy.zip' -DestinationPath '%~dp0' -Force"
        del "%TEMP%\scrcpy.zip" >nul 2>&1
        :: 解压后文件夹名通常为 scrcpy-win64-vX.Y，重命名为 scrcpy
        if exist "%~dp0scrcpy-win64-v%SCRCPY_VER%" (
            ren "%~dp0scrcpy-win64-v%SCRCPY_VER%" scrcpy
        )
    )

    set "PATH=%~dp0scrcpy;%PATH%"

    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%B"
    echo %USERPATH% | findstr /I /C:"scrcpy" >nul 2>&1
    if %errorlevel% neq 0 (
        setx PATH "%USERPATH%;%~dp0scrcpy" >nul 2>&1
        echo         已将 scrcpy 添加到用户 PATH
    )

    scrcpy --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [警告] scrcpy 安装后仍无法运行，Android 投屏功能可能不可用
        echo         请手动从 https://github.com/Genymobile/scrcpy/releases 下载
    )
)
scrcpy --version 2>&1 | findstr /R "." && echo         scrcpy ... OK
echo.

:: ──────────────────────────────────────────────────────────────
::  5. 生成 requirements.txt
:: ──────────────────────────────────────────────────────────────
echo [5/6] 生成 requirements.txt ...
(
    echo PySide6
    echo pywin32
) > "%~dp0requirements.txt"
echo         requirements.txt 已创建
echo.

:: ──────────────────────────────────────────────────────────────
::  6. 验证环境
:: ──────────────────────────────────────────────────────────────
echo [6/6] 验证环境 ...
echo.

python -c "import PySide6; print('  [OK] PySide6', PySide6.__version__)" 2>nul || echo   [FAIL] PySide6 未安装
python -c "import win32gui; print('  [OK] pywin32')" 2>nul || echo   [FAIL] pywin32 未安装
adb version >nul 2>&1 && echo   [OK] adb || echo   [FAIL] adb 未找到
scrcpy --version >nul 2>&1 && echo   [OK] scrcpy || echo   [WARN] scrcpy 未找到 (Android 投屏不可用，其他功能正常)

echo.
echo ============================================================
echo  环境配置完成！
echo.
echo  启动 H75 Helper:
echo      python main.py
echo.
echo  如需使用 Android 投屏:
echo      1. 手机开启 USB 调试
echo      2. 用数据线连接到电脑
echo      3. 在弹出的授权对话框中点击「允许」
echo ============================================================
echo.
pause
