# AsrTools 修改说明

基于 [WEIFENG2333/AsrTools](https://github.com/WEIFENG2333/AsrTools) 项目的修改版本。

## 修改内容

### 1. 新增 DeepSeek AI 字幕修正功能

#### 新增文件：
- `app/deepseek_config.py` - DeepSeek配置管理模块
- `app/bk_asr/DeepSeekProcessor.py` - DeepSeek API处理器
- `deepseek_config.json` - 配置文件（运行时自动生成）

#### 功能说明：
- 集成 DeepSeek API 进行字幕智能修正
- 支持修正错别字和语法错误
- 支持人名、地名、专有名词确认（不确定的标注[?]）
- 保留原始时间戳，只修正文本内容
- 生成内容摘要

### 2. 字幕预览和编辑功能

#### 修改文件：
- `app/asr_gui.py`

#### 功能说明：
- **右侧预览面板**：显示字幕内容预览
- **直接选择字幕文件**：支持选择已有的SRT/TXT/ASS文件进行修正
- **手动编辑**：预览文本框可直接编辑字幕内容
- **记住文件位置**：自动记住最近打开的文件目录

### 3. AI修正对比弹窗

#### 功能说明：
- 点击"DeepSeek 修正"后立即弹出对话框
- 先显示原始字幕，修正列显示"等待处理..."
- 处理完成后自动更新修正结果
- 支持在对话框中继续手动编辑
- 修改的行用黄色背景高亮显示
- 显示修改原因

### 4. 配置管理

#### 功能说明：
- API密钥配置（支持密码模式显示）
- API URL配置（支持自定义端点）
- 模型选择（deepseek-chat/deepseek-coder）
- 测试API连接功能
- 配置自动保存到本地文件

## 使用方法

### 1. 配置DeepSeek API

1. 在右侧"DeepSeek 配置"区域输入API密钥
2. 选择模型（默认deepseek-chat）
3. 点击"测试API"验证连接
4. 勾选"启用 DeepSeek 字幕修正"

### 2. AI修正流程

**方式一：从ASR生成开始**
1. 选择音频/视频文件
2. 点击"开始处理"生成字幕
3. 在左侧表格点击已处理的文件
4. 点击"DeepSeek 修正"按钮

**方式二：直接选择字幕文件**
1. 点击"选择字幕文件"按钮
2. 选择已有的SRT/TXT/ASS文件
3. 点击"DeepSeek 修正"按钮

### 3. 对比和编辑

1. 弹出对话框后，先显示原始字幕
2. 等待AI处理完成（显示"⏳ 正在使用DeepSeek处理字幕，请稍候..."）
3. 处理完成后，修正列更新为AI修正的结果
4. 可以直接双击修正列进行手动编辑
5. 查看"修改原因"列了解AI修改的内容
6. 点击"应用修正"保存，或"取消"放弃

## 文件结构

```
app/
├── __init__.py
├── asr_gui.py              # 主GUI界面（已修改）
├── check_update.py         # 更新检查
├── deepseek_config.py      # DeepSeek配置管理（新增）
└── bk_asr/
    ├── __init__.py          # 已修改，导出新类
    ├── ASRData.py           # 字幕数据结构
    ├── BaseASR.py           # ASR基类
    ├── BcutASR.py           # B站ASR接口
    ├── DeepSeekProcessor.py # DeepSeek处理器（新增）
    ├── JianYingASR.py       # 剪映ASR接口
    ├── KuaiShouASR.py       # 快手ASR接口
    └── WhisperASR.py        # Whisper接口
```

## 依赖

在原有依赖基础上，新增：
- `requests` - 用于调用DeepSeek API

## 注意事项

1. DeepSeek API需要自行申请密钥
2. API调用会产生费用，请注意用量
3. 修正结果仅供参考，建议人工确认
4. 配置文件会自动保存在程序目录下

## 更新日志

### v1.2.0 (张林修改版)
- 新增DeepSeek AI字幕修正功能
- 新增字幕预览和编辑功能
- 新增AI修正对比弹窗
- 新增配置管理功能
- 支持直接选择字幕文件进行修正

### v1.1.0 (原版)
- 支持视频文件直接处理
- 多样化输出格式支持