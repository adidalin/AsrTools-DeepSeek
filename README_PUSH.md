# 一键推送指南

## 快速开始

### 方法1：运行批处理脚本（推荐）
双击运行 `一键推送到GitHub.bat`

### 方法2：运行PowerShell脚本
右键点击 `一键推送到GitHub.ps1`，选择"使用PowerShell运行"

## 脚本会自动完成以下操作

1. ✅ 检查Git是否安装
2. ✅ 初始化Git仓库
3. ✅ 添加所有文件
4. ✅ 提交修改
5. ✅ 推送到GitHub

## 你需要手动完成的步骤

### 第1步：在GitHub上创建仓库

1. 打开浏览器，访问：https://github.com/new

2. 填写信息：
   ```
   Repository name: AsrTools-DeepSeek
   Description: AsrTools with DeepSeek AI subtitle correction
   ```

3. **重要**：不要勾选以下选项：
   - ❌ Add a README file
   - ❌ Add .gitignore
   - ❌ Choose a license

4. 点击 **Create repository**

### 第2步：运行脚本

双击运行 `一键推送到GitHub.bat`

### 第3步：处理认证

如果推送时要求输入密码，需要使用Personal Access Token：

1. 访问：https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 填写：
   - Note: `AsrTools Push`
   - Expiration: `90 days` 或 `No expiration`
   - 勾选所有 `repo` 权限
4. 点击 **Generate token**
5. **复制生成的token**（只显示一次）
6. 推送时，在密码框粘贴这个token

## 推送成功后

你的代码将在：https://github.com/adidalin/AsrTools-DeepSeek

## 后续更新

如果以后有修改，只需再次运行 `一键推送到GitHub.bat`，脚本会自动提交并推送更新。

## 常见问题

### Q: 提示 "repository not found"
A: 请先在GitHub上创建仓库

### Q: 提示 "Authentication failed"
A: 需要配置Personal Access Token（见上方步骤）

### Q: 如何修改仓库名？
A: 编辑 `一键推送到GitHub.bat`，修改 `set REPO_NAME=AsrTools-DeepSeek` 这一行

### Q: 如何使用SSH而不是HTTPS？
A: 需要先配置SSH密钥，然后修改脚本中的URL为 `git@github.com:adidalin/AsrTools-DeepSeek.git`