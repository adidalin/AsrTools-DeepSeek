import json
import os


class TencentConfig:
    """腾讯云配置管理类"""

    DEFAULT_CONFIG = {
        "secret_id": "",
        "secret_key": "",
        "engine_model": "16k_zh_large",
    }

    CONFIG_FILE = "tencent_config.json"

    def __init__(self):
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            print(f"加载腾讯云配置失败: {e}")

    def save_config(self):
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存腾讯云配置失败: {e}")

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value

    def is_configured(self) -> bool:
        return bool(self.config.get("secret_id")) and bool(self.config.get("secret_key"))

    def get_secret_id(self) -> str:
        return self.config.get("secret_id", "")

    def get_secret_key(self) -> str:
        return self.config.get("secret_key", "")

    def get_engine_model(self) -> str:
        return self.config.get("engine_model", "16k_zh_large")
