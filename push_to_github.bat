@echo off
echo ========================================
echo AsrTools GitHub 推送脚本
echo ========================================
echo.

REM 检查Git是否安装
git --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Git，请先安装Git
    echo 下载地址：https://git-scm.com/downloads
    pause
    exit /b 1
)

echo Git已安装：
git --version
echo.

REM 初始化Git仓库
if not exist ".git" (
    echo 正在初始化Git仓库...
    git init
    echo.
)

REM 添加所有文件
echo 正在添加文件...
git add .
echo.

REM 提交
echo 正在提交...
git commit -m "feat: 添加DeepSeek AI字幕修正功能

- 新增DeepSeek API集成，支持字幕智能修正
- 新增字幕预览和编辑功能
- 新增AI修正对比弹窗
- 新增配置管理功能
- 支持直接选择字幕文件进行修正"
echo.

echo ========================================
echo 接下来需要手动操作：
echo ========================================
echo.
echo 1. 在GitHub上创建新仓库：
echo    - 访问 https://github.com/new
echo    - 仓库名建议：AsrTools-DeepSeek
echo    - 选择 Public 或 Private
echo    - 不要勾选 README、.gitignore、License
echo    - 点击 Create repository
echo.
echo 2. 复制仓库地址（HTTPS或SSH）
echo    例如：https://github.com/你的用户名/AsrTools-DeepSeek.git
echo.
echo 3. 执行以下命令推送：
echo    git remote add origin https://github.com/你的用户名/AsrTools-DeepSeek.git
echo    git branch -M main
echo    git push -u origin main
echo.
echo ========================================
pause