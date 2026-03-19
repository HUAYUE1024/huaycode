@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

::============================================================
:: HUAYCODE 一键部署脚本 (Windows)
:: 支持: Docker + Nginx 自动部署
:: 用法: deploy.bat
::============================================================

title HUAYCODE 一键部署工具

:: 颜色代码
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "NC=[0m"

:: 显示 Banner
echo %CYAN%
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║         HUAYCODE - Python 代码执行可视化引擎               ║
echo ║                   一键部署工具 v1.0                        ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo %NC%

:: 检查 Docker
echo %BLUE%[INFO]%NC% 检查 Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Docker 未安装或未启动
    echo %YELLOW%请安装 Docker Desktop: https://www.docker.com/products/docker-desktop%NC%
    pause
    exit /b 1
)
echo %GREEN%[SUCCESS]%NC% Docker 已安装

:: 检查 Docker Compose
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    docker compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo %RED%[ERROR]%NC% Docker Compose 未安装
        pause
        exit /b 1
    )
)
echo %GREEN%[SUCCESS]%NC% Docker Compose 已安装

:: 获取用户输入
echo.
echo %CYAN%==>%NC% 配置部署参数
echo.

set /p SERVER_IP="请输入服务器 IP 地址: "
if "!SERVER_IP!"=="" (
    echo %RED%[ERROR]%NC% IP 地址不能为空
    pause
    exit /b 1
)

set /p SSH_PORT="请输入 SSH 端口 [默认: 22]: "
if "!SSH_PORT!"=="" set "SSH_PORT=22"

set /p SSH_USER="请输入 SSH 用户名 [默认: root]: "
if "!SSH_USER!"=="" set "SSH_USER=root"

set /p APP_PORT="请输入应用访问端口 [默认: 80]: "
if "!APP_PORT!"=="" set "APP_PORT=80"

set /p ENABLE_SSL="是否启用 HTTPS/SSL? (y/n) [默认: n]: "
if "!ENABLE_SSL!"=="" set "ENABLE_SSL=n"

:: 显示配置摘要
echo.
echo %BLUE%[INFO]%NC% 部署配置摘要:
echo   服务器 IP: !SERVER_IP!
echo   SSH 端口: !SSH_PORT!
echo   SSH 用户: !SSH_USER!
echo   应用端口: !APP_PORT!
echo   启用 SSL: !ENABLE_SSL!
echo.

set /p CONFIRM="确认以上配置? (y/n) [默认: y]: "
if "!CONFIRM!"=="" set "CONFIRM=y"
if /i "!CONFIRM!" neq "y" (
    echo %YELLOW%[WARNING]%NC% 部署已取消
    pause
    exit /b 0
)

:: 生成 .env 文件
echo %BLUE%[INFO]%NC% 生成配置文件...
(
echo NGINX_PORT=!APP_PORT!
echo FLASK_ENV=production
echo FLASK_DEBUG=false
echo TZ=Asia/Shanghai
) > .env

:: 检查 plink (PuTTY) 或使用 PowerShell SSH
where plink >nul 2>&1
if %errorlevel% equ 0 (
    set "SSH_CMD=plink -P !SSH_PORT! -pw !SSH_PASSWORD! !SSH_USER!@!SERVER_IP!"
) else (
    set "SSH_CMD=powershell -Command ssh -p !SSH_PORT! !SSH_USER!@!SERVER_IP!"
)

:: 测试 SSH 连接
echo %BLUE%[INFO]%NC% 测试 SSH 连接...
!SSH_CMD! "echo 'SSH 连接成功'" >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% 无法连接到服务器
    echo %YELLOW%请检查 IP、端口和网络连接%NC%
    pause
    exit /b 1
)
echo %GREEN%[SUCCESS]%NC% SSH 连接成功

:: 创建远程目录
echo %BLUE%[INFO]%NC% 创建远程项目目录...
!SSH_CMD! "sudo mkdir -p /opt/huaycode && sudo chown !SSH_USER! /opt/huaycode"

:: 使用 SCP 上传文件 (或使用 WinSCP)
echo %BLUE%[INFO]%NC% 上传文件到服务器...
where pscp >nul 2>&1
if %errorlevel% equ 0 (
    pscp -P !SSH_PORT! -pw !SSH_PASSWORD! -r . !SSH_USER!@!SERVER_IP!:/opt/huaycode/
) else (
    powershell -Command "scp -P !SSH_PORT! -r ./* !SSH_USER!@!SERVER_IP!:/opt/huaycode/"
)

if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% 文件上传失败
    pause
    exit /b 1
)
echo %GREEN%[SUCCESS]%NC% 文件上传完成

:: 在服务器上执行部署
echo %BLUE%[INFO]%NC% 在服务器上执行部署...
!SSH_CMD! "cd /opt/huaycode && docker-compose down 2>/dev/null; docker system prune -f && docker-compose build --no-cache && docker-compose up -d"

if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% 部署失败
    pause
    exit /b 1
)

:: 等待服务启动
echo %BLUE%[INFO]%NC% 等待服务启动...
timeout /t 10 /nobreak >nul

:: 检查服务状态
!SSH_CMD! "cd /opt/huaycode && docker-compose ps" | findstr "Up" >nul
if %errorlevel% equ 0 (
    echo %GREEN%[SUCCESS]%NC% 部署成功完成
) else (
    echo %RED%[ERROR]%NC% 服务启动异常
    !SSH_CMD! "cd /opt/huaycode && docker-compose logs"
    pause
    exit /b 1
)

:: 显示结果
echo.
echo %GREEN%
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║                   🎉 部署成功! 🎉                          ║
echo ║                                                            ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                                                            ║
if /i "!ENABLE_SSL!" equ "y" (
    echo ║   访问地址: https://!SERVER_IP!                            ║
) else (
    echo ║   访问地址: http://!SERVER_IP!:!APP_PORT!                  ║
)
echo ║                                                            ║
echo ║   管理命令 (在服务器上执行):                               ║
echo ║     查看状态: cd /opt/huaycode ^&^& docker-compose ps       ║
echo ║     查看日志: cd /opt/huaycode ^&^& docker-compose logs -f  ║
echo ║     重启服务: cd /opt/huaycode ^&^& docker-compose restart  ║
echo ║     停止服务: cd /opt/huaycode ^&^& docker-compose down     ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo %NC%

pause
