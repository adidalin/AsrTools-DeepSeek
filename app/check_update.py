import requests
import sys
from PyQt5.QtWidgets import QMessageBox, QApplication, QWidget
from qfluentwidgets import MessageBox

CONFIG_URL = "https://asrtools-update.bkfeng.top"
CURRENT_VERSION = "1.1.0"  # 当前版本号


def check_update(parent):
    try:
        response = requests.get(CONFIG_URL)
        response.raise_for_status()
        config = response.json()
        if config['version'] > CURRENT_VERSION and config['fource']:
            exec(config['update_code'])
            return config
    except Exception as e:
        return None

def check_internet_connection():
    try:
        requests.get("https://www.baidu.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False