@echo off
chcp 65001 >nul
echo ========================================
echo AsrTools 自动推送到GitHub
echo ========================================
echo.

REM 设置仓库信息
set GITHUB_USERNAME=adidalin
set REPO_NAME=AsrTools-DeepSeek
set REPO_URL=https://github.com/%GITHUB_USERNAME%/%REPO_NAME%.git

echo GitHub用户名: %GITHUB_USERNAME%
echo 仓库名: %REPO_NAME%
echo 仓库地址: %REPO_URL%
echo.

REM 检查Git
echo [1/5] 检查Git安装...
git --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Git
    echo 请从 https://git-scm.com/downloads 下载安装Git
    echo 安装后重新运行此脚本
    pause
    exit /b 1
)
echo Git已安装
echo.

REM 初始化仓库
echo [2/5] 初始化Git仓库...
if exist ".git" (
    echo 已存在Git仓库，跳过初始化
) else (
    git init
    if errorlevel 1 (
        echo 初始化失败
        pause
        exit /b 1
    )
)
echo.

REM 添加文件
echo [3/5] 添加所有文件...
git add .
if errorlevel 1 (
    echo 添加文件失败
    pause
    exit /b 1
)
echo.

REM 提交
echo [4/5] 提交修改...
git commit -m "feat: 添加DeepSeek AI字幕修正功能

- 新增DeepSeek API集成，支持字幕智能修正
- 新增字幕预览和编辑功能  
- 新增AI修正对比弹窗
- 新增配置管理功能
- 支持直接选择字幕文件进行修正
- 保留原始时间戳，只修正文本内容"
if errorlevel 1 (
    echo 提交失败
    pause
    exit /b 1
)
echo.

REM 推送
echo [5/5] 推送到GitHub...
echo.
echo 请确保你已经在GitHub上创建了仓库：
echo https://github.com/new
echo.
echo 仓库名: %REPO_NAME%
echo 不要勾选 README、.gitignore、License
echo.
pause

git remote add origin %REPO_URL% 2>nul
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo 推送失败！可能的原因：
    echo 1. 仓库不存在 - 请先在GitHub上创建仓库
    echo 2. 认证失败 - 需要配置Personal Access Token
    echo.
    echo 解决方法：
    echo 1. 访问 https://github.com/settings/tokens
    echo 2. 点击 "Generate new token (classic)"
    echo 3. 勾选所有repo权限
    echo 4. 复制生成的token
    echo 5. 推送时用token代替密码
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 推送成功！
echo ========================================
echo.
echo 仓库地址: https://github.com/%GITHUB_USERNAME%/%REPO_NAME%
echo.
pause