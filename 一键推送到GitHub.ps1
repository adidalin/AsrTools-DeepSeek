# AsrTools 自动推送到GitHub脚本
# 作者: adidalin

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AsrTools 自动推送到GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置仓库信息
$GITHUB_USERNAME = "adidalin"
$REPO_NAME = "AsrTools-DeepSeek"
$REPO_URL = "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

Write-Host "GitHub用户名: $GITHUB_USERNAME" -ForegroundColor Yellow
Write-Host "仓库名: $REPO_NAME" -ForegroundColor Yellow
Write-Host "仓库地址: $REPO_URL" -ForegroundColor Yellow
Write-Host ""

# 检查Git
Write-Host "[1/5] 检查Git安装..." -ForegroundColor Green
try {
    $gitVersion = git --version
    Write-Host "Git已安装: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "错误：未找到Git" -ForegroundColor Red
    Write-Host "请从 https://git-scm.com/downloads 下载安装Git" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# 初始化仓库
Write-Host "[2/5] 初始化Git仓库..." -ForegroundColor Green
if (Test-Path ".git") {
    Write-Host "已存在Git仓库，跳过初始化" -ForegroundColor Yellow
} else {
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "初始化失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}
Write-Host ""

# 添加文件
Write-Host "[3/5] 添加所有文件..." -ForegroundColor Green
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "添加文件失败" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# 提交
Write-Host "[4/5] 提交修改..." -ForegroundColor Green
$commitMessage = @"
feat: 添加DeepSeek AI字幕修正功能

- 新增DeepSeek API集成，支持字幕智能修正
- 新增字幕预览和编辑功能  
- 新增AI修正对比弹窗
- 新增配置管理功能
- 支持直接选择字幕文件进行修正
- 保留原始时间戳，只修正文本内容
"@
git commit -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Host "提交失败" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# 推送
Write-Host "[5/5] 推送到GitHub..." -ForegroundColor Green
Write-Host ""
Write-Host "请确保你已经在GitHub上创建了仓库：" -ForegroundColor Yellow
Write-Host "https://github.com/new" -ForegroundColor Cyan
Write-Host ""
Write-Host "仓库名: $REPO_NAME" -ForegroundColor Yellow
Write-Host "不要勾选 README、.gitignore、License" -ForegroundColor Yellow
Write-Host ""
Read-Host "按回车键继续"

git remote add origin $REPO_URL 2>$null
git branch -M main
git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "推送失败！可能的原因：" -ForegroundColor Red
    Write-Host "1. 仓库不存在 - 请先在GitHub上创建仓库" -ForegroundColor Yellow
    Write-Host "2. 认证失败 - 需要配置Personal Access Token" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "解决方法：" -ForegroundColor Cyan
    Write-Host "1. 访问 https://github.com/settings/tokens" -ForegroundColor White
    Write-Host "2. 点击 'Generate new token (classic)'" -ForegroundColor White
    Write-Host "3. 勾选所有repo权限" -ForegroundColor White
    Write-Host "4. 复制生成的token" -ForegroundColor White
    Write-Host "5. 推送时用token代替密码" -ForegroundColor White
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "推送成功！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "仓库地址: https://github.com/$GITHUB_USERNAME/$REPO_NAME" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车键退出"