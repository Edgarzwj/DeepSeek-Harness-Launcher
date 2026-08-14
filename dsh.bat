@echo off
chcp 65001 >nul 2>&1
title DeepSeek Harness Launcher

echo.
echo   ╔════════════════════════════════════════╗
echo   ║     DeepSeek Harness - Quick Launch    ║
echo   ╚════════════════════════════════════════╝
echo.

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [✗] Node.js 未检测到
    echo.
    echo   请先安装 Node.js:
    echo   https://nodejs.org/ 下载 LTS 版本安装即可
    echo.
    pause
    exit /b 1
)

:: Show Node version
for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
echo   [✓] Node.js %NODE_VER%
echo.
echo   正在启动 DeepSeek Harness ...
echo   (首次运行会自动下载依赖，请耐心等待)
echo.

:: Run dsh
npx @deepseek-ai/dsh web %*

if %errorlevel% neq 0 (
    echo.
    echo   [✗] 启动失败，请检查网络连接或 Node.js 版本
    pause
    exit /b 1
)
