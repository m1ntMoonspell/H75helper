@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title H75 Helper - 一键环境配置脚本
color 0A

echo ============================================================
echo        H75 Helper  一键环境配置脚本
echo ============================================================
echo.

:: ══════════════════════════════════════════════════════════════
::  1. 检查 Python
:: ══════════════════════════════════════════════════════════════
echo [1/6] 检查 Python ...
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo   [错误] 未找到 Python。
    echo          请从 https://www.python.org/downloads/ 安装 Python 3.10+
    echo          安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo   Python !PYVER! ... OK
echo.

:: ══════════════════════════════════════════════════════════════
::  2. 安装 Python 依赖
:: ══════════════════════════════════════════════════════════════
echo [2/6] 安装 Python 依赖 (PySide6, pywin32) ...
pip install PySide6 pywin32 --quiet 2>nul
if !errorlevel! neq 0 (
    echo   pip install 遇到问题，尝试 --user ...
    pip install PySide6 pywin32 --user --quiet 2>nul
)
echo   PySide6, pywin32 ... OK
echo.

:: ══════════════════════════════════════════════════════════════
::  3. 检查 / 下载 ADB
:: ══════════════════════════════════════════════════════════════
echo [3/6] 检查 ADB ...
adb version >nul 2>&1
if !errorlevel! equ 0 goto :adb_ok

echo   未找到 adb，正在下载 Android SDK Platform Tools ...

set "ADB_TARGET=%~dp0platform-tools"
if exist "!ADB_TARGET!\adb.exe" goto :adb_set_path

echo   下载中 (约 15MB) ...
powershell -NoProfile -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile '%TEMP%\platform-tools.zip'"
if !errorlevel! neq 0 (
    echo   [错误] 下载失败。请手动下载:
    echo          https://developer.android.com/studio/releases/platform-tools
    goto :adb_fail
)

echo   解压中 ...
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\platform-tools.zip' -DestinationPath '%~dp0' -Force"
del "%TEMP%\platform-tools.zip" >nul 2>&1

if not exist "!ADB_TARGET!\adb.exe" (
    echo   [错误] 解压后未找到 adb.exe
    goto :adb_fail
)

:adb_set_path
:: 添加到当前进程 PATH
set "PATH=!ADB_TARGET!;!PATH!"

:: 持久写入用户 PATH（避免重复添加）
call :add_to_user_path "!ADB_TARGET!"
echo   已将 platform-tools 添加到用户 PATH

:adb_ok
for /f "tokens=*" %%L in ('adb version 2^>^&1') do (
    echo   %%L
    goto :adb_done
)
:adb_fail
:adb_done
echo.

:: ══════════════════════════════════════════════════════════════
::  4. 检查 / 下载 scrcpy
:: ══════════════════════════════════════════════════════════════
echo [4/6] 检查 scrcpy ...
scrcpy --version >nul 2>&1
if !errorlevel! equ 0 goto :scrcpy_ok

echo   未找到 scrcpy，正在下载 ...

set "SCRCPY_VER=3.1"
set "SCRCPY_ZIP=scrcpy-win64-v!SCRCPY_VER!"
set "SCRCPY_TARGET=%~dp0scrcpy"

if exist "!SCRCPY_TARGET!\scrcpy.exe" goto :scrcpy_set_path

echo   下载 scrcpy v!SCRCPY_VER! (约 40MB) ...
powershell -NoProfile -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/Genymobile/scrcpy/releases/download/v!SCRCPY_VER!/!SCRCPY_ZIP!.zip' -OutFile '%TEMP%\scrcpy.zip'"
if !errorlevel! neq 0 (
    echo   [错误] 下载失败。请手动下载:
    echo          https://github.com/Genymobile/scrcpy/releases
    goto :scrcpy_fail
)

echo   解压中 ...
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\scrcpy.zip' -DestinationPath '%~dp0' -Force"
del "%TEMP%\scrcpy.zip" >nul 2>&1

:: 解压后目录名为 scrcpy-win64-vX.Y，重命名为 scrcpy
if exist "%~dp0!SCRCPY_ZIP!" (
    if exist "!SCRCPY_TARGET!" rmdir /s /q "!SCRCPY_TARGET!" >nul 2>&1
    ren "%~dp0!SCRCPY_ZIP!" scrcpy
)

if not exist "!SCRCPY_TARGET!\scrcpy.exe" (
    echo   [错误] 解压后未找到 scrcpy.exe
    echo          请检查 %~dp0 下是否有 scrcpy 相关文件夹，手动重命名为 scrcpy
    goto :scrcpy_fail
)

:scrcpy_set_path
set "PATH=!SCRCPY_TARGET!;!PATH!"
call :add_to_user_path "!SCRCPY_TARGET!"
echo   已将 scrcpy 添加到用户 PATH

:scrcpy_ok
scrcpy --version 2>&1
echo   scrcpy ... OK
goto :scrcpy_done

:scrcpy_fail
echo   [警告] scrcpy 不可用，Android 投屏功能将无法使用，其他功能正常
:scrcpy_done
echo.

:: ══════════════════════════════════════════════════════════════
::  5. 生成 requirements.txt
:: ══════════════════════════════════════════════════════════════
echo [5/6] 生成 requirements.txt ...
(
    echo PySide6
    echo pywin32
) > "%~dp0requirements.txt"
echo   requirements.txt 已创建
echo.

:: ══════════════════════════════════════════════════════════════
::  6. 验证环境
:: ══════════════════════════════════════════════════════════════
echo [6/6] 验证环境 ...
echo.

python -c "import PySide6; print('  [OK] PySide6', PySide6.__version__)" 2>nul
if !errorlevel! neq 0 echo   [FAIL] PySide6

python -c "import win32gui; print('  [OK] pywin32')" 2>nul
if !errorlevel! neq 0 echo   [FAIL] pywin32

adb version >nul 2>&1
if !errorlevel! equ 0 ( echo   [OK] adb ) else ( echo   [FAIL] adb )

scrcpy --version >nul 2>&1
if !errorlevel! equ 0 ( echo   [OK] scrcpy ) else ( echo   [WARN] scrcpy 未就绪 )

echo.
echo ============================================================
echo  环境配置完成!
echo.
echo  启动方式:     python main.py
echo.
echo  Android 投屏:
echo      1. 手机 设置 ^> 开发者选项 ^> 开启 USB 调试
echo      2. 数据线连接电脑
echo      3. 手机弹窗中点击「允许 USB 调试」
echo      4. 在 H75 Helper 中: Android ^> 刷新设备 ^> 连接
echo ============================================================
echo.
pause
exit /b 0


:: ══════════════════════════════════════════════════════════════
::  子程序: 将目录添加到用户 PATH (不重复添加)
:: ══════════════════════════════════════════════════════════════
:add_to_user_path
set "NEW_DIR=%~1"

:: 读取当前用户 PATH
set "CURRENT_PATH="
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%B"

:: 检查是否已存在
echo !CURRENT_PATH! | findstr /I /C:"!NEW_DIR!" >nul 2>&1
if !errorlevel! equ 0 (
    exit /b 0
)

:: 追加并写入
if "!CURRENT_PATH!"=="" (
    setx PATH "!NEW_DIR!" >nul 2>&1
) else (
    setx PATH "!CURRENT_PATH!;!NEW_DIR!" >nul 2>&1
)
exit /b 0
