import json
import os
from pathlib import Path
from typing import Optional


class DeepSeekConfig:
    """DeepSeek配置管理类"""

    DEFAULT_CONFIG = {
        "api_key": "",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "custom_prompt": "",
        "enabled": False,
    }

    CONFIG_FILE = "deepseek_config.json"

    def __init__(self):
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            print(f"加载配置文件失败: {e}")

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key: str, value):
        """设置配置项"""
        self.config[key] = value

    def is_enabled(self) -> bool:
        """检查DeepSeek是否启用"""
        return self.config.get("enabled", False) and bool(self.config.get("api_key"))

    def get_api_key(self) -> str:
        """获取API密钥"""
        return self.config.get("api_key", "")

    def get_api_url(self) -> str:
        """获取API URL"""
        return self.config.get("api_url", self.DEFAULT_CONFIG["api_url"])

    def get_model(self) -> str:
        """获取模型名称"""
        return self.config.get("model", self.DEFAULT_CONFIG["model"])

    def get_custom_prompt(self) -> str:
        """获取自定义提示词"""
        return self.config.get("custom_prompt", "")
