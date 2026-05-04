# AsrTools - DeepSeek AI 字幕修正版

基于 [WEIFENG2333/AsrTools](https://github.com/WEIFENG2333/AsrTools) 的修改版本，添加了 DeepSeek AI 字幕修正功能。

## 🌟 新增功能

### 1. DeepSeek AI 字幕修正
- 智能修正错别字和语法错误
- 人名、地名、专有名词确认（不确定的标注[?]）
- 保留原始时间戳，只修正文本内容
- 生成内容摘要

### 2. 字幕预览和编辑
- 右侧面板显示字幕内容预览
- 支持直接编辑字幕内容
- 支持选择已有的 SRT/TXT/ASS 文件进行修正

### 3. AI 修正对比弹窗
- 显示原始字幕和修正后字幕的对比
- 修改的行用黄色背景高亮显示
- 显示修改原因
- 支持在对话框中继续手动编辑

### 4. 配置管理
- API 密钥配置（支持密码模式显示）
- API URL 配置（支持自定义端点）
- 模型选择（deepseek-chat/deepseek-coder）
- 测试 API 连接功能
- 配置自动保存到本地文件

## 📦 安装

### 方式一：直接使用（推荐）
下载 `AsrTools.exe`，双击即可运行。

### 方式二：从源码运行
```bash
git clone https://github.com/adidalin/AsrTools-DeepSeek.git
cd AsrTools-DeepSeek
pip install -r requirements.txt
python app/asr_gui.py
```

## 🚀 使用方法

### 配置 DeepSeek API

1. 在右侧"DeepSeek 配置"区域输入 API 密钥
2. 选择模型（默认 deepseek-chat）
3. 点击"测试 API"验证连接
4. 勾选"启用 DeepSeek 字幕修正"

### AI 修正流程

**方式一：从 ASR 生成开始**
1. 选择音频/视频文件
2. 点击"开始处理"生成字幕
3. 在左侧表格点击已处理的文件
4. 点击"DeepSeek 修正"按钮

**方式二：直接选择字幕文件**
1. 点击"选择字幕文件"按钮
2. 选择已有的 SRT/TXT/ASS 文件
3. 点击"DeepSeek 修正"按钮

### 对比和编辑

1. 弹出对话框后，先显示原始字幕
2. 等待 AI 处理完成
3. 处理完成后，修正列更新为 AI 修正的结果
4. 可以直接双击修正列进行手动编辑
5. 查看"修改原因"列了解 AI 修改的内容
6. 点击"应用修正"保存，或"取消"放弃

## 📁 文件结构

```
app/
├── __init__.py
├── asr_gui.py              # 主 GUI 界面
├── check_update.py         # 更新检查
├── deepseek_config.py      # DeepSeek 配置管理
└── bk_asr/
    ├── __init__.py
    ├── ASRData.py           # 字幕数据结构
    ├── BaseASR.py           # ASR 基类
    ├── BcutASR.py           # B 站 ASR 接口
    ├── DeepSeekProcessor.py # DeepSeek 处理器
    ├── JianYingASR.py       # 剪映 ASR 接口
    ├── KuaiShouASR.py       # 快手 ASR 接口
    └── WhisperASR.py        # Whisper 接口
```

## ⚙️ 依赖

- Python 3.8+
- PyQt5
- qfluentwidgets
- requests

## 📝 注意事项

1. DeepSeek API 需要自行申请密钥
2. API 调用会产生费用，请注意用量
3. 修正结果仅供参考，建议人工确认
4. 配置文件会自动保存在程序目录下

## 🔗 相关链接

- 原项目：[WEIFENG2333/AsrTools](https://github.com/WEIFENG2333/AsrTools)
- DeepSeek API：[platform.deepseek.com](https://platform.deepseek.com)

## 📄 许可证

本项目基于原项目的 GPL-3.0 许可证。

## 👥 贡献者

- **小花荣** ([@adidalin](https://github.com/adidalin))
  - 添加 DeepSeek AI 字幕修正功能
  - 添加字幕预览和编辑功能
  - 添加 AI 修正对比弹窗
  - 添加配置管理功能
  - 📧 联系邮箱：adidalin@qq.com

## 🙏 致谢

- [WEIFENG2333](https://github.com/WEIFENG2333) - 原项目作者
- [DeepSeek](https://deepseek.com) - AI 模型支持