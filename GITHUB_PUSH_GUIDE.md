# 推送到GitHub指南

## 前提条件

1. 已安装Git
2. 已有GitHub账号

## 步骤一：在GitHub上创建新仓库

1. 打开浏览器，访问 https://github.com/new
2. 填写仓库信息：
   - **Repository name**: `AsrTools-DeepSeek` （或其他你喜欢的名字）
   - **Description**: `AsrTools with DeepSeek AI subtitle correction`
   - **Public/Private**: 根据需要选择
   - **不要勾选** README、.gitignore、License（因为本地已有）
3. 点击 **Create repository**

## 步骤二：运行推送脚本

1. 双击运行 `push_to_github.bat`
2. 脚本会自动：
   - 检查Git是否安装
   - 初始化Git仓库
   - 添加所有文件
   - 提交修改

## 步骤三：手动推送到GitHub

脚本运行完成后，打开命令行（CMD或PowerShell），执行以下命令：

```bash
# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/AsrTools-DeepSeek.git

# 设置主分支
git branch -M main

# 推送到GitHub
git push -u origin main
```

## 步骤四：验证

1. 打开你的GitHub仓库页面
2. 确认所有文件已上传
3. 查看 `MODIFICATIONS.md` 了解修改内容

## 后续更新

如果以后有修改，可以执行以下命令推送更新：

```bash
git add .
git commit -m "描述你的修改"
git push
```

## 常见问题

### Q: 推送时要求输入用户名和密码？
A: GitHub现在不支持密码认证，需要使用Personal Access Token：
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token"
3. 选择权限（repo全部勾选）
4. 生成token后，用token代替密码

### Q: 如何获取仓库地址？
A: 在GitHub仓库页面，点击绿色的 "Code" 按钮，复制HTTPS地址

### Q: 想使用SSH而不是HTTPS？
A: 需要先配置SSH密钥：
1. 生成SSH密钥：`ssh-keygen -t rsa -b 4096`
2. 添加到GitHub：Settings -> SSH and GPG keys
3. 使用SSH地址：`git@github.com:用户名/AsrTools-DeepSeek.git`