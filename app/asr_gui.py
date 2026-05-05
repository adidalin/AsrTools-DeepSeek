import json
import logging
import os
from pathlib import Path
import platform
import subprocess
import sys
import webbrowser
import requests

# FIX: 修复中文路径报错 https://github.com/WEIFENG2333/AsrTools/issues/18  设置QT_QPA_PLATFORM_PLUGIN_PATH
plugin_path = os.path.join(
    sys.prefix, "Lib", "site-packages", "PyQt5", "Qt5", "plugins"
)
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
print(os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"])

from PyQt5.QtCore import (
    Qt,
    QRunnable,
    QThreadPool,
    QObject,
    pyqtSignal as Signal,
    pyqtSlot as Slot,
    QSize,
    QThread,
    pyqtSignal,
    QMetaObject,
    Q_ARG,
)
from PyQt5.QtGui import QCursor, QColor, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QTableWidgetItem,
    QHeaderView,
    QSizePolicy,
    QTextEdit,
    QSplitter,
    QGroupBox,
    QCheckBox,
    QDialog,
    QLabel,
    QTabWidget,
    QTableWidget,
    QAbstractItemView,
    QScrollArea,
)
from qfluentwidgets import (
    ComboBox,
    PushButton,
    LineEdit,
    TableWidget,
    FluentIcon as FIF,
    Action,
    RoundMenu,
    InfoBar,
    InfoBarPosition,
    FluentWindow,
    BodyLabel,
    MessageBox,
    PlainTextEdit,
)

from .bk_asr.BcutASR import BcutASR
from .bk_asr.JianYingASR import JianYingASR
from .bk_asr.KuaiShouASR import KuaiShouASR
from .bk_asr.DeepSeekProcessor import DeepSeekProcessor, SubtitleProcessResult
from .bk_asr.ASRData import ASRData
from .deepseek_config import DeepSeekConfig

# 设置日志配置
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class SubtitleEditDialog(QDialog):
    """字幕编辑弹窗 - 支持处理进度显示和手动编辑"""

    def __init__(self, original_data=None, parent=None, mode="correct"):
        """
        Args:
            original_data: 原始字幕数据
            parent: 父窗口
            mode: "correct"=字幕修正模式, "bilingual"=双语翻译模式
        """
        super().__init__(parent)
        self.result = None
        self.original_data = original_data
        self.mode = mode
        self.setWindowTitle("字幕修正" if mode == "correct" else "字幕翻译(双语)")
        self.setMinimumSize(1200 if mode == "bilingual" else 1000, 700)
        self.init_ui()

        # 如果有原始数据，先显示原始字幕
        if original_data:
            self._populate_original_table(original_data)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 内容摘要区域
        self.summary_group = QGroupBox("内容摘要")
        self.summary_group.setVisible(False)
        summary_layout = QVBoxLayout(self.summary_group)
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 14px; padding: 10px;")
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(self.summary_group)

        # 处理进度提示（显示在表格上方）
        progress_text = "⏳ 正在使用DeepSeek处理字幕，请稍候..."
        if self.mode == "bilingual":
            progress_text = "⏳ 正在校正并翻译字幕，请稍候..."
        self.progress_label = QLabel(progress_text)
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet(
            "font-size: 14px; color: #0078d4; padding: 10px; background-color: #e6f3ff;"
        )
        layout.addWidget(self.progress_label)

        # 修改统计
        self.stats_layout = QHBoxLayout()
        self.stats_label = QLabel("")
        self.stats_layout.addWidget(self.stats_label)
        self.stats_layout.addStretch()
        self.stats_widget = QWidget()
        self.stats_widget.setLayout(self.stats_layout)
        self.stats_widget.setVisible(False)
        layout.addWidget(self.stats_widget)

        # 提示标签
        if self.mode == "bilingual":
            self.tip_label = QLabel("💡 提示：校正后字幕和英文翻译列可直接编辑 | 仅中文变动时高亮")
        else:
            self.tip_label = QLabel("💡 提示：修正后字幕列可直接编辑")
        self.tip_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.tip_label)

        # 对比表格
        self.compare_table = QTableWidget()

        if self.mode == "bilingual":
            self.compare_table.setColumnCount(6)
            self.compare_table.setHorizontalHeaderLabels(
                ["行号", "时间戳", "原始字幕", "校正后字幕", "英文翻译", "修改原因"]
            )
            self.compare_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.compare_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
            self.compare_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.compare_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
            self.compare_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
            self.compare_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
            self.compare_table.setColumnWidth(0, 50)
            self.compare_table.setColumnWidth(1, 180)
            self.compare_table.setColumnWidth(5, 150)
        else:
            self.compare_table.setColumnCount(5)
            self.compare_table.setHorizontalHeaderLabels(
                ["行号", "时间戳", "原始字幕", "修正后字幕", "修改原因"]
            )
            self.compare_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.compare_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
            self.compare_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.compare_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
            self.compare_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
            self.compare_table.setColumnWidth(0, 50)
            self.compare_table.setColumnWidth(1, 180)

        self.compare_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 允许编辑修正后字幕列和翻译列
        self.compare_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )

        layout.addWidget(self.compare_table)

        # 按钮区域
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        btn_text = "应用修正" if self.mode == "correct" else "应用翻译"
        self.accept_button = PushButton(btn_text)
        self.accept_button.clicked.connect(self.accept)
        self.accept_button.setEnabled(False)
        self.button_layout.addWidget(self.accept_button)

        self.reject_button = PushButton("取消")
        self.reject_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.reject_button)

        layout.addLayout(self.button_layout)

    def _populate_original_table(self, original_data):
        """先显示原始字幕，修正列显示等待处理"""
        segments = original_data.segments
        self.compare_table.setRowCount(len(segments))

        for i, seg in enumerate(segments):
            # 行号
            self.compare_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

            # 时间戳
            start_time = self._ms_to_time_str(seg.start_time)
            end_time = self._ms_to_time_str(seg.end_time)
            self.compare_table.setItem(
                i, 1, QTableWidgetItem(f"{start_time} --> {end_time}")
            )

            # 原始字幕（只读）
            original_item = QTableWidgetItem(seg.text)
            original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
            self.compare_table.setItem(i, 2, original_item)

            # 修正后字幕（显示等待处理）
            waiting_item = QTableWidgetItem("等待处理...")
            waiting_item.setForeground(QColor("gray"))
            self.compare_table.setItem(i, 3, waiting_item)

            if self.mode == "bilingual":
                # 英文翻译列（显示等待处理）
                trans_item = QTableWidgetItem("等待处理...")
                trans_item.setForeground(QColor("gray"))
                self.compare_table.setItem(i, 4, trans_item)

                # 修改原因
                reason_item = QTableWidgetItem("")
                reason_item.setFlags(reason_item.flags() & ~Qt.ItemIsEditable)
                self.compare_table.setItem(i, 5, reason_item)
            else:
                # 修改原因
                reason_item = QTableWidgetItem("")
                reason_item.setFlags(reason_item.flags() & ~Qt.ItemIsEditable)
                self.compare_table.setItem(i, 4, reason_item)

    def set_result(self, result: SubtitleProcessResult):
        """设置处理结果"""
        self.result = result

        # 隐藏进度提示
        self.progress_label.setVisible(False)
        self.summary_group.setVisible(True)
        self.stats_widget.setVisible(True)
        self.accept_button.setEnabled(True)

        # 设置摘要
        if result.summary:
            self.summary_label.setText(result.summary)
        else:
            self.summary_group.setVisible(False)

        # 设置统计
        self.stats_label.setText(
            f"原始字幕行数: {len(result.original_data)}  |  修改处数: {len(result.changes)}"
        )

        # 填充对比表格
        self._populate_compare_table(result)

    def set_error(self, error_message: str):
        """设置错误状态"""
        self.progress_label.setText(f"❌ 处理失败: {error_message}")
        self.progress_label.setStyleSheet(
            "font-size: 14px; color: red; padding: 10px; background-color: #ffe6e6;"
        )
        self.accept_button.setEnabled(False)
        self.reject_button.setText("关闭")

    def _populate_compare_table(self, result):
        """填充对比表格"""
        original_segs = result.original_data.segments
        processed_segs = result.processed_data.segments

        # 创建修改原因字典
        reasons = {}
        for change in result.changes:
            reasons[change["line"]] = change.get("reason", "")

        self.compare_table.setRowCount(len(original_segs))

        for i in range(len(original_segs)):
            # 行号
            self.compare_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

            # 时间戳
            start_time = self._ms_to_time_str(original_segs[i].start_time)
            end_time = self._ms_to_time_str(original_segs[i].end_time)
            self.compare_table.setItem(
                i, 1, QTableWidgetItem(f"{start_time} --> {end_time}")
            )

            # 原始字幕（只读）
            original_item = QTableWidgetItem(original_segs[i].text)
            original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
            self.compare_table.setItem(i, 2, original_item)

            if self.mode == "bilingual":
                # 校正后字幕（可编辑）- 取纯中文部分
                processed_text = ""
                translated_text = ""
                if i < len(processed_segs):
                    seg_text = processed_segs[i].text
                    if "\n" in seg_text:
                        parts = seg_text.split("\n", 1)
                        processed_text = parts[0]
                        translated_text = parts[1] if len(parts) > 1 else ""
                    else:
                        processed_text = seg_text

                self.compare_table.setItem(i, 3, QTableWidgetItem(processed_text))
                self.compare_table.setItem(i, 4, QTableWidgetItem(translated_text))

                # 修改原因（只读）
                reason = reasons.get(i + 1, "")
                reason_item = QTableWidgetItem(reason)
                reason_item.setFlags(reason_item.flags() & ~Qt.ItemIsEditable)
                self.compare_table.setItem(i, 5, reason_item)

                # 仅在中文变动时高亮（原始字幕 != 校正后字幕）
                # 都只取中文部分（第一行）进行比较
                original_cn = original_segs[i].text.split("\n", 1)[0].strip()
                corrected_cn = processed_text.strip()
                if original_cn != corrected_cn:
                    for j in range(6):
                        item = self.compare_table.item(i, j)
                        if item:
                            item.setBackground(QColor(255, 255, 200))
            else:
                # 修正后字幕（可编辑）
                processed_text = processed_segs[i].text if i < len(processed_segs) else ""
                self.compare_table.setItem(i, 3, QTableWidgetItem(processed_text))

                # 修改原因（只读）
                reason = reasons.get(i + 1, "")
                reason_item = QTableWidgetItem(reason)
                reason_item.setFlags(reason_item.flags() & ~Qt.ItemIsEditable)
                self.compare_table.setItem(i, 4, reason_item)

                # 如果有修改，高亮显示
                if reason:
                    for j in range(5):
                        item = self.compare_table.item(i, j)
                        if item:
                            item.setBackground(QColor(255, 255, 200))

    def get_processed_data(self):
        """获取编辑后的字幕数据"""
        if not self.result:
            return None

        from .bk_asr.ASRData import ASRDataSeg, ASRData

        # 从表格中读取编辑后的字幕
        segments = []
        for i in range(self.compare_table.rowCount()):
            time_text = self.compare_table.item(i, 1).text()

            if self.mode == "bilingual":
                # 双语模式：合并校正后字幕和英文翻译
                corrected_text = self.compare_table.item(i, 3).text()
                translated_text = self.compare_table.item(i, 4).text()
                if translated_text and translated_text != "等待处理...":
                    processed_text = f"{corrected_text}\n{translated_text}"
                else:
                    processed_text = corrected_text
            else:
                processed_text = self.compare_table.item(i, 3).text()

            # 解析时间戳
            start_time, end_time = self._parse_time_str(time_text)
            segments.append(ASRDataSeg(processed_text, start_time, end_time))

        return ASRData(segments)

    def _parse_time_str(self, time_str: str) -> tuple:
        """解析时间戳字符串"""
        try:
            parts = time_str.split("-->")
            start_str = parts[0].strip()
            end_str = parts[1].strip()

            start_ms = self._time_str_to_ms(start_str)
            end_ms = self._time_str_to_ms(end_str)

            return start_ms, end_ms
        except Exception:
            return 0, 0

    def _time_str_to_ms(self, time_str: str) -> int:
        """将时间字符串转换为毫秒"""
        try:
            if "," in time_str:
                time_part, ms_part = time_str.split(",")
            elif "." in time_str:
                time_part, ms_part = time_str.split(".")
            else:
                return 0

            h, m, s = time_part.split(":")
            total_ms = int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms_part)
            return total_ms
        except Exception:
            return 0

    def _ms_to_time_str(self, ms: int) -> str:
        """将毫秒转换为时间字符串"""
        total_seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(milliseconds):03}"


class WorkerSignals(QObject):
    finished = Signal(str, str)  # file_path, result_text
    errno = Signal(str, str)


class ASRWorker(QRunnable):
    """ASR处理工作线程"""

    def __init__(self, file_path, asr_engine, export_format):
        super().__init__()
        self.file_path = file_path
        self.asr_engine = asr_engine
        self.export_format = export_format
        self.signals = WorkerSignals()

        self.audio_path = None

    @Slot()
    def run(self):
        try:
            use_cache = True

            # 检查文件类型,如果不是音频则转换
            logging.info("[+]正在进ffmpeg转换")
            audio_exts = [".mp3", ".wav"]
            if not any(self.file_path.lower().endswith(ext) for ext in audio_exts):
                temp_audio = self.file_path.rsplit(".", 1)[0] + ".mp3"
                if not video2audio(self.file_path, temp_audio):
                    raise Exception("音频转换失败，确保安装ffmpeg")
                self.audio_path = temp_audio
            else:
                self.audio_path = self.file_path

            # 根据选择的 ASR 引擎实例化相应的类
            if self.asr_engine == "B 接口":
                asr = BcutASR(self.audio_path, use_cache=use_cache)
            elif self.asr_engine == "J 接口":
                asr = JianYingASR(self.audio_path, use_cache=use_cache)
            elif self.asr_engine == "K 接口":
                asr = KuaiShouASR(self.audio_path, use_cache=use_cache)
            elif self.asr_engine == "Whisper":
                # from bk_asr.WhisperASR import WhisperASR
                # asr = WhisperASR(self.file_path, use_cache=use_cache)
                raise NotImplementedError("WhisperASR 暂未实现")
            else:
                raise ValueError(f"未知的 ASR 引擎: {self.asr_engine}")

            logging.info(f"开始处理文件: {self.file_path} 使用引擎: {self.asr_engine}")
            result = asr.run()

            # 根据导出格式选择转换方法
            save_ext = self.export_format.lower()
            if save_ext == "srt":
                result_text = result.to_srt()
            elif save_ext == "ass":
                result_text = result.to_ass()
            elif save_ext == "txt":
                result_text = result.to_txt()

            logging.info(f"完成处理文件: {self.file_path} 使用引擎: {self.asr_engine}")
            save_path = self.file_path.rsplit(".", 1)[0] + "." + save_ext
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(result_text)
            self.signals.finished.emit(self.file_path, result_text)
        except Exception as e:
            logging.error(f"处理文件 {self.file_path} 时出错: {str(e)}")
            self.signals.errno.emit(self.file_path, f"处理时出错: {str(e)}")


class UpdateCheckerThread(QThread):
    msg = pyqtSignal(str, str, str)  # 用于发送消息的信号

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            from check_update import check_update, check_internet_connection

            # 检查互联网连接
            if not check_internet_connection():
                self.msg.emit("错误", "无法连接到互联网，请检查网络连接。", "")
                return
            # 检查更新
            config = check_update(self)
            if config:
                if config["fource"]:
                    self.msg.emit(
                        "更新",
                        "检测到新版本，请下载最新版本。",
                        config["update_download_url"],
                    )
                else:
                    self.msg.emit(
                        "可更新",
                        "检测到新版本，请下载最新版本。",
                        config["update_download_url"],
                    )
        except Exception as e:
            pass


class ASRWidget(QWidget):
    """ASR处理界面"""

    # 定义信号用于后台线程更新UI
    deepseek_finished_signal = Signal(str, object)  # file_path, processed_data
    deepseek_error_signal = Signal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.deepseek_config = DeepSeekConfig()
        self.init_ui()
        self.max_threads = 3  # 设置最大线程数
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(self.max_threads)
        self.processing_queue = []
        self.workers = {}  # 维护文件路径到worker的映射
        self.current_subtitle_path = None  # 当前直接选择的字幕文件路径

        # 连接信号
        self.deepseek_finished_signal.connect(self.update_preview_after_processing)
        self.deepseek_error_signal.connect(self.show_deepseek_error)

    def init_ui(self):
        # 创建主布局，使用QSplitter分割左右两侧
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：ASR处理界面
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # ASR引擎选择区域
        engine_layout = QHBoxLayout()
        engine_label = BodyLabel("选择接口:", self)
        engine_label.setFixedWidth(70)
        self.combo_box = ComboBox(self)
        self.combo_box.addItems(["B 接口", "J 接口", "K 接口", "Whisper"])
        engine_layout.addWidget(engine_label)
        engine_layout.addWidget(self.combo_box)
        left_layout.addLayout(engine_layout)

        # 导出格式选择区域
        format_layout = QHBoxLayout()
        format_label = BodyLabel("导出格式:", self)
        format_label.setFixedWidth(70)
        self.format_combo = ComboBox(self)
        self.format_combo.addItems(["SRT", "TXT", "ASS"])
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        left_layout.addLayout(format_layout)

        # 文件选择区域
        file_layout = QHBoxLayout()
        self.file_input = LineEdit(self)
        self.file_input.setPlaceholderText("拖拽文件或文件夹到这里")
        self.file_input.setReadOnly(True)
        self.file_button = PushButton("选择文件", self)
        self.file_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.file_button)
        left_layout.addLayout(file_layout)

        # 文件列表表格
        self.table = TableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["文件名", "状态"])
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.table)

        # 设置表格列的拉伸模式
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 100)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 处理按钮
        self.process_button = PushButton("开始处理", self)
        self.process_button.clicked.connect(self.process_files)
        self.process_button.setEnabled(False)  # 初始禁用
        left_layout.addWidget(self.process_button)

        # 右侧：DeepSeek配置和字幕预览
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # DeepSeek配置区域
        deepseek_group = QGroupBox("DeepSeek 配置")
        deepseek_layout = QVBoxLayout(deepseek_group)

        # 启用DeepSeek复选框
        self.deepseek_enabled = QCheckBox("启用 DeepSeek 字幕修正", self)
        self.deepseek_enabled.setChecked(self.deepseek_config.is_enabled())
        self.deepseek_enabled.stateChanged.connect(self.on_deepseek_enabled_changed)
        deepseek_layout.addWidget(self.deepseek_enabled)

        # API密钥输入
        api_key_layout = QHBoxLayout()
        api_key_label = BodyLabel("API Key:", self)
        api_key_label.setFixedWidth(70)
        self.api_key_input = LineEdit(self)
        self.api_key_input.setPlaceholderText("请输入DeepSeek API密钥")
        self.api_key_input.setEchoMode(LineEdit.Password)
        self.api_key_input.setText(self.deepseek_config.get_api_key())
        self.api_key_input.textChanged.connect(self.on_api_key_changed)
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_input)
        deepseek_layout.addLayout(api_key_layout)

        # API URL输入
        api_url_layout = QHBoxLayout()
        api_url_label = BodyLabel("API URL:", self)
        api_url_label.setFixedWidth(70)
        self.api_url_input = LineEdit(self)
        self.api_url_input.setPlaceholderText("DeepSeek API端点")
        self.api_url_input.setText(self.deepseek_config.get_api_url())
        self.api_url_input.textChanged.connect(self.on_api_url_changed)
        api_url_layout.addWidget(api_url_label)
        api_url_layout.addWidget(self.api_url_input)
        deepseek_layout.addLayout(api_url_layout)

        # 模型选择
        model_layout = QHBoxLayout()
        model_label = BodyLabel("模型:", self)
        model_label.setFixedWidth(70)
        self.model_combo = ComboBox(self)
        self.model_combo.addItems(["deepseek-chat", "deepseek-coder"])
        self.model_combo.setCurrentText(self.deepseek_config.get_model())
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        deepseek_layout.addLayout(model_layout)

        # 处理模式选择
        mode_layout = QHBoxLayout()
        mode_label = BodyLabel("处理模式:", self)
        mode_label.setFixedWidth(70)
        self.process_mode_combo = ComboBox(self)
        self.process_mode_combo.addItems(["字幕修正", "翻译成英文(双语)"])
        saved_mode = self.deepseek_config.get("process_mode", "字幕修正")
        if saved_mode in ["字幕修正", "翻译成英文(双语)"]:
            self.process_mode_combo.setCurrentText(saved_mode)
        self.process_mode_combo.currentTextChanged.connect(self.on_process_mode_changed)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.process_mode_combo)
        deepseek_layout.addLayout(mode_layout)

        # Prompt输入
        prompt_label = BodyLabel("自定义Prompt:", self)
        deepseek_layout.addWidget(prompt_label)
        self.prompt_input = PlainTextEdit(self)
        self.prompt_input.setPlaceholderText(
            "留空使用默认Prompt。自定义指令会覆盖默认修正/翻译逻辑。"
        )
        self.prompt_input.setPlainText(self.deepseek_config.get_custom_prompt())
        self.prompt_input.setMaximumHeight(100)
        self.prompt_input.textChanged.connect(self.on_prompt_changed)
        deepseek_layout.addWidget(self.prompt_input)

        # 保存配置和测试API按钮
        config_button_layout = QHBoxLayout()
        save_config_button = PushButton("保存配置", self)
        save_config_button.clicked.connect(self.save_deepseek_config)
        config_button_layout.addWidget(save_config_button)

        test_api_button = PushButton("测试API", self)
        test_api_button.clicked.connect(self.test_deepseek_api)
        config_button_layout.addWidget(test_api_button)
        deepseek_layout.addLayout(config_button_layout)

        right_layout.addWidget(deepseek_group)

        # 字幕预览区域
        preview_group = QGroupBox("字幕预览")
        preview_layout = QVBoxLayout(preview_group)

        # 选择字幕文件按钮
        select_subtitle_layout = QHBoxLayout()
        self.select_subtitle_button = PushButton("选择字幕文件", self)
        self.select_subtitle_button.clicked.connect(self.select_subtitle_file)
        self.select_subtitle_button.setToolTip(
            "直接选择已有的SRT/TXT/ASS字幕文件进行修正"
        )
        select_subtitle_layout.addWidget(self.select_subtitle_button)
        select_subtitle_layout.addStretch()
        preview_layout.addLayout(select_subtitle_layout)

        # 预览文本框（可编辑）
        self.preview_text = PlainTextEdit(self)
        self.preview_text.setPlaceholderText(
            "字幕内容将在这里显示...\n可以手动编辑后点击保存"
        )
        self.preview_text.setReadOnly(False)
        preview_layout.addWidget(self.preview_text)

        # 提示标签
        tip_label = BodyLabel("提示：可以直接编辑字幕内容，然后点击保存", self)
        tip_label.setStyleSheet("color: gray; font-size: 11px;")
        preview_layout.addWidget(tip_label)

        # DeepSeek处理按钮
        button_layout = QHBoxLayout()
        self.deepseek_process_button = PushButton("DeepSeek 修正", self)
        self.deepseek_process_button.clicked.connect(self.process_with_deepseek)
        self.deepseek_process_button.setEnabled(False)
        button_layout.addWidget(self.deepseek_process_button)

        # 保存修改按钮
        self.save_button = PushButton("保存修改", self)
        self.save_button.clicked.connect(self.save_modified_subtitles)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        preview_layout.addLayout(button_layout)

        right_layout.addWidget(preview_group)

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])  # 设置初始大小

        main_layout.addWidget(splitter)

        self.setAcceptDrops(True)

        # 连接表格选择变化信号
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)

    def select_file(self):
        """选择文件对话框"""
        # 获取最近打开的目录
        last_dir = self.deepseek_config.get("last_open_dir", "")

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频或视频文件",
            last_dir,
            "Media Files (*.mp3 *.wav *.ogg *.mp4 *.avi *.mov *.ts)",
        )
        if files:
            # 保存最近打开的目录
            self.deepseek_config.set("last_open_dir", os.path.dirname(files[0]))
            self.deepseek_config.save_config()

            for file in files:
                self.add_file_to_table(file)
            self.update_start_button_state()

    def select_subtitle_file(self):
        """选择字幕文件对话框"""
        # 获取最近打开的目录
        last_dir = self.deepseek_config.get("last_subtitle_dir", "")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择字幕文件",
            last_dir,
            "Subtitle Files (*.srt *.txt *.ass *.vtt)",
        )
        if file_path:
            # 保存最近打开的目录
            self.deepseek_config.set("last_subtitle_dir", os.path.dirname(file_path))
            self.deepseek_config.save_config()

            # 读取字幕文件内容
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.preview_text.setPlainText(content)

                # 存储当前选择的字幕文件路径
                self.current_subtitle_path = file_path

                # 启用DeepSeek修正按钮
                self.deepseek_process_button.setEnabled(
                    self.deepseek_config.is_enabled()
                )
                self.save_button.setEnabled(True)

                InfoBar.success(
                    title="已加载字幕文件",
                    content=f"已加载: {os.path.basename(file_path)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
            except Exception as e:
                logging.error(f"读取字幕文件失败: {e}")
                InfoBar.error(
                    title="读取失败",
                    content=f"读取字幕文件失败: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )

    def add_file_to_table(self, file_path):
        """将文件添加到表格中"""
        if self.find_row_by_file_path(file_path) != -1:
            InfoBar.warning(
                title="文件已存在",
                content=f"文件 {os.path.basename(file_path)} 已经添加到列表中。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        item_filename = self.create_non_editable_item(os.path.basename(file_path))
        item_status = self.create_non_editable_item("未处理")
        item_status.setForeground(QColor("gray"))
        self.table.setItem(row_count, 0, item_filename)
        self.table.setItem(row_count, 1, item_status)
        item_filename.setData(Qt.UserRole, file_path)

    def create_non_editable_item(self, text):
        """创建不可编辑的表格项"""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def show_context_menu(self, pos):
        """显示右键菜单"""
        current_row = self.table.rowAt(pos.y())
        if current_row < 0:
            return

        self.table.selectRow(current_row)

        menu = RoundMenu(self)
        reprocess_action = Action(FIF.SYNC, "重新处理")
        delete_action = Action(FIF.DELETE, "删除任务")
        open_dir_action = Action(FIF.FOLDER, "打开文件目录")
        menu.addActions([reprocess_action, delete_action, open_dir_action])

        delete_action.triggered.connect(self.delete_selected_row)
        open_dir_action.triggered.connect(self.open_file_directory)
        reprocess_action.triggered.connect(self.reprocess_selected_file)

        menu.exec(QCursor.pos())

    def delete_selected_row(self):
        """删除选中的行"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            file_path = self.table.item(current_row, 0).data(Qt.UserRole)
            if file_path in self.workers:
                worker = self.workers[file_path]
                worker.signals.finished.disconnect(self.update_table)
                worker.signals.errno.disconnect(self.handle_error)
                # QThreadPool 不支持直接终止线程，通常需要设计任务可中断
                # 这里仅移除引用
                self.workers.pop(file_path, None)
            self.table.removeRow(current_row)
            self.update_start_button_state()

    def open_file_directory(self):
        """打开文件所在目录"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            current_item = self.table.item(current_row, 0)
            if current_item:
                file_path = current_item.data(Qt.UserRole)
                directory = os.path.dirname(file_path)
                try:
                    if platform.system() == "Windows":
                        os.startfile(directory)
                    elif platform.system() == "Darwin":
                        subprocess.Popen(["open", directory])
                    else:
                        subprocess.Popen(["xdg-open", directory])
                except Exception as e:
                    InfoBar.error(
                        title="无法打开目录",
                        content=str(e),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self,
                    )

    def reprocess_selected_file(self):
        """重新处理选中的文件"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            file_path = self.table.item(current_row, 0).data(Qt.UserRole)
            status = self.table.item(current_row, 1).text()
            if status == "处理中":
                InfoBar.warning(
                    title="当前文件正在处理中",
                    content="请等待当前文件处理完成后再重新处理。",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )
                return
            self.add_to_queue(file_path)

    def add_to_queue(self, file_path):
        """将文件添加到处理队列并更新状态"""
        self.processing_queue.append(file_path)
        self.process_next_in_queue()

    def process_files(self):
        """处理所有未处理的文件"""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == "未处理":
                file_path = self.table.item(row, 0).data(Qt.UserRole)
                self.processing_queue.append(file_path)
        self.process_next_in_queue()

    def process_next_in_queue(self):
        """处理队列中的下一个文件"""
        while (
            self.thread_pool.activeThreadCount() < self.max_threads
            and self.processing_queue
        ):
            file_path = self.processing_queue.pop(0)
            if file_path not in self.workers:
                self.process_file(file_path)

    def process_file(self, file_path):
        """处理单个文件"""
        selected_engine = self.combo_box.currentText()
        selected_format = self.format_combo.currentText()
        worker = ASRWorker(file_path, selected_engine, selected_format)
        worker.signals.finished.connect(self.update_table)
        worker.signals.errno.connect(self.handle_error)
        self.thread_pool.start(worker)
        self.workers[file_path] = worker

        row = self.find_row_by_file_path(file_path)
        if row != -1:
            status_item = self.create_non_editable_item("处理中")
            status_item.setForeground(QColor("orange"))
            self.table.setItem(row, 1, status_item)
            self.update_start_button_state()

    def update_table(self, file_path, result):
        """更新表格中文件的处理状态"""
        row = self.find_row_by_file_path(file_path)
        if row != -1:
            item_status = self.create_non_editable_item("已处理")
            item_status.setForeground(QColor("green"))
            self.table.setItem(row, 1, item_status)

            InfoBar.success(
                title="处理完成",
                content=f"文件 {self.table.item(row, 0).text()} 已处理完成",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self,
            )

        self.workers.pop(file_path, None)
        self.process_next_in_queue()
        self.update_start_button_state()

    def handle_error(self, file_path, error_message):
        """处理错误信息"""
        row = self.find_row_by_file_path(file_path)
        if row != -1:
            item_status = self.create_non_editable_item("错误")
            item_status.setForeground(QColor("red"))
            self.table.setItem(row, 1, item_status)

            InfoBar.error(
                title="处理出错",
                content=error_message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

        self.workers.pop(file_path, None)
        self.process_next_in_queue()
        self.update_start_button_state()

    def find_row_by_file_path(self, file_path):
        """根据文件路径查找表格中的行号"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item.data(Qt.UserRole) == file_path:
                return row
        return -1

    def update_start_button_state(self):
        """根据文件列表更新开始处理按钮的状态"""
        has_unprocessed = any(
            self.table.item(row, 1).text() == "未处理"
            for row in range(self.table.rowCount())
        )
        self.process_button.setEnabled(has_unprocessed)

    def on_deepseek_enabled_changed(self, state):
        """DeepSeek启用状态变化"""
        self.deepseek_config.set("enabled", state == Qt.Checked)
        self.update_deepseek_button_state()

    def on_api_key_changed(self, text):
        """API密钥变化"""
        self.deepseek_config.set("api_key", text)
        self.update_deepseek_button_state()

    def on_api_url_changed(self, text):
        """API URL变化"""
        self.deepseek_config.set("api_url", text)

    def on_model_changed(self, text):
        """模型变化"""
        self.deepseek_config.set("model", text)

    def on_prompt_changed(self):
        """Prompt变化"""
        self.deepseek_config.set("custom_prompt", self.prompt_input.toPlainText())

    def on_process_mode_changed(self, text):
        """处理模式变化"""
        self.deepseek_config.set("process_mode", text)

    def save_deepseek_config(self):
        """保存DeepSeek配置"""
        self.deepseek_config.save_config()
        InfoBar.success(
            title="配置已保存",
            content="DeepSeek配置已保存成功",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def test_deepseek_api(self):
        """测试DeepSeek API连接"""
        if not self.deepseek_config.is_enabled():
            InfoBar.warning(
                title="API未配置",
                content="请先启用DeepSeek并配置API密钥",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 创建DeepSeek处理器
        processor = DeepSeekProcessor(
            api_key=self.deepseek_config.get_api_key(),
            api_url=self.deepseek_config.get_api_url(),
            model=self.deepseek_config.get_model(),
        )

        # 测试API连接
        try:
            import requests

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_config.get_api_key()}",
            }
            # 发送一个简单的测试请求
            test_payload = {
                "model": self.deepseek_config.get_model(),
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10,
            }

            response = requests.post(
                self.deepseek_config.get_api_url(),
                headers=headers,
                json=test_payload,
                timeout=10,
            )

            if response.status_code == 200:
                InfoBar.success(
                    title="API测试成功",
                    content="DeepSeek API连接正常",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
            else:
                InfoBar.error(
                    title="API测试失败",
                    content=f"HTTP状态码: {response.status_code}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )
        except requests.exceptions.Timeout:
            InfoBar.error(
                title="API测试失败",
                content="连接超时，请检查网络或API地址",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="API测试失败",
                content=f"错误: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def on_table_selection_changed(self):
        """表格选择变化时更新预览"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            file_path = self.table.item(current_row, 0).data(Qt.UserRole)
            # 自动查找已存在的字幕文件
            subtitle_content = self._find_subtitle_file(file_path)
            if subtitle_content:
                self.preview_text.setPlainText(subtitle_content)
                self.deepseek_process_button.setEnabled(
                    self.deepseek_config.is_enabled()
                )
                self.save_button.setEnabled(True)
            else:
                self.preview_text.setPlainText("")
                self.deepseek_process_button.setEnabled(False)
                self.save_button.setEnabled(False)
        else:
            self.preview_text.setPlainText("")
            self.deepseek_process_button.setEnabled(False)
            self.save_button.setEnabled(False)

    def _find_subtitle_file(self, file_path):
        """自动查找已存在的字幕文件"""
        # 按优先级查找字幕文件
        for ext in ["srt", "txt", "ass"]:
            subtitle_path = file_path.rsplit(".", 1)[0] + "." + ext
            if os.path.exists(subtitle_path):
                try:
                    with open(subtitle_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    logging.error(f"读取字幕文件失败: {e}")
                    continue
        return None

    def generate_html_preview(self, asr_data):
        """生成HTML预览内容"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
                    margin: 10px;
                    background-color: #f5f5f5;
                }
                .subtitle-container {
                    max-width: 100%;
                    margin: 0 auto;
                }
                .subtitle-item {
                    background-color: white;
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    border-left: 4px solid #0078d4;
                }
                .subtitle-time {
                    color: #666;
                    font-size: 12px;
                    margin-bottom: 5px;
                    font-family: 'Consolas', 'Courier New', monospace;
                }
                .subtitle-text {
                    color: #333;
                    font-size: 14px;
                    line-height: 1.5;
                }
                .subtitle-index {
                    color: #0078d4;
                    font-weight: bold;
                    margin-right: 10px;
                }
            </style>
        </head>
        <body>
            <div class="subtitle-container">
        """

        for i, seg in enumerate(asr_data.segments, 1):
            # 转换时间格式
            start_time = self._ms_to_time_str(seg.start_time)
            end_time = self._ms_to_time_str(seg.end_time)

            html += f"""
                <div class="subtitle-item">
                    <div class="subtitle-time">
                        <span class="subtitle-index">#{i}</span>
                        {start_time} --> {end_time}
                    </div>
                    <div class="subtitle-text">{seg.text}</div>
                </div>
            """

        html += """
            </div>
        </body>
        </html>
        """
        return html

    def _ms_to_time_str(self, ms):
        """将毫秒转换为时间字符串"""
        total_seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{int(milliseconds):03}"

    def update_deepseek_button_state(self):
        """更新DeepSeek处理按钮状态"""
        current_row = self.table.currentRow()
        has_selection = current_row >= 0
        has_subtitle_file = False
        if has_selection:
            file_path = self.table.item(current_row, 0).data(Qt.UserRole)
            has_subtitle_file = self._find_subtitle_file(file_path) is not None
        self.deepseek_process_button.setEnabled(
            self.deepseek_config.is_enabled() and has_subtitle_file
        )

    def process_with_deepseek(self):
        """使用DeepSeek处理字幕"""
        if not self.deepseek_config.is_enabled():
            InfoBar.warning(
                title="DeepSeek未启用",
                content="请先启用DeepSeek并配置API密钥",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        # 获取字幕文件路径（优先使用直接选择的字幕文件）
        subtitle_path = None
        file_path = None

        # 检查是否有直接选择的字幕文件
        if hasattr(self, "current_subtitle_path") and self.current_subtitle_path:
            subtitle_path = self.current_subtitle_path
            file_path = subtitle_path
        else:
            # 从表格中选择的文件
            current_row = self.table.currentRow()
            if current_row < 0:
                InfoBar.warning(
                    title="未选择文件",
                    content="请先选择一个文件或字幕文件",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return

            file_path = self.table.item(current_row, 0).data(Qt.UserRole)

            # 自动查找字幕文件
            for ext in ["srt", "txt", "ass"]:
                temp_path = file_path.rsplit(".", 1)[0] + "." + ext
                if os.path.exists(temp_path):
                    subtitle_path = temp_path
                    break

            if not subtitle_path:
                InfoBar.warning(
                    title="字幕文件不存在",
                    content="请先生成字幕文件或选择字幕文件",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return

        # 读取字幕数据
        try:
            from .bk_asr.ASRData import from_subtitle_file

            asr_data = from_subtitle_file(subtitle_path)
        except Exception as e:
            logging.error(f"读取字幕文件失败: {e}")
            InfoBar.error(
                title="读取失败",
                content=f"读取字幕文件失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
            return

        # 创建DeepSeek处理器
        processor = DeepSeekProcessor(
            api_key=self.deepseek_config.get_api_key(),
            api_url=self.deepseek_config.get_api_url(),
            model=self.deepseek_config.get_model(),
        )

        # 获取当前处理模式
        is_bilingual = self.process_mode_combo.currentText() == "翻译成英文(双语)"

        # 先弹出对话框，显示原始字幕和处理进度
        dialog_mode = "bilingual" if is_bilingual else "correct"
        dialog = SubtitleEditDialog(original_data=asr_data, parent=self, mode=dialog_mode)
        dialog.show()

        # 禁用按钮
        self.deepseek_process_button.setEnabled(False)
        self.deepseek_process_button.setText("处理中...")
        self.select_subtitle_button.setEnabled(False)

        # 在后台线程中处理
        import threading

        def process_in_background():
            try:
                if is_bilingual:
                    result = processor.process_bilingual(
                        asr_data, self.deepseek_config.get_custom_prompt()
                    )
                else:
                    result = processor.process_subtitles(
                        asr_data, self.deepseek_config.get_custom_prompt()
                    )
                # 使用信号更新UI
                self.deepseek_finished_signal.emit(subtitle_path, result)
            except Exception as e:
                logging.error(f"DeepSeek处理失败: {e}")
                self.deepseek_error_signal.emit(str(e))

        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()

        # 保存对话框引用，以便后续更新
        self.current_dialog = dialog
        self.current_subtitle_path_for_save = subtitle_path

    def update_preview_after_processing(self, file_path, result):
        """处理完成后更新预览，显示对比弹窗"""
        # 恢复按钮状态
        self.deepseek_process_button.setText("DeepSeek 修正")
        self.deepseek_process_button.setEnabled(True)
        self.select_subtitle_button.setEnabled(True)

        # 更新对话框显示结果
        if hasattr(self, "current_dialog") and self.current_dialog:
            self.current_dialog.set_result(result)

            # 等待用户操作
            if self.current_dialog.exec_() == QDialog.Accepted:
                # 用户选择应用修正（可能包含手动编辑）
                processed_data = self.current_dialog.get_processed_data()
                if processed_data:
                    save_ext = self.format_combo.currentText().lower()
                    save_path = file_path.rsplit(".", 1)[0] + "." + save_ext
                    try:
                        processed_data.save(save_path)
                        # 更新预览
                        self.preview_text.setPlainText(processed_data.to_srt())
                        InfoBar.success(
                            title="修正已应用",
                            content="字幕修正已保存",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self,
                        )
                    except Exception as e:
                        logging.error(f"保存处理后的字幕失败: {e}")
                        InfoBar.error(
                            title="保存失败",
                            content=f"保存处理后的字幕失败: {str(e)}",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP,
                            duration=3000,
                            parent=self,
                        )
            else:
                # 用户取消
                InfoBar.info(
                    title="修正已取消",
                    content="字幕修正未应用",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )

            self.current_dialog = None

    def show_deepseek_error(self, error_message):
        """显示DeepSeek处理错误"""
        # 恢复按钮状态
        self.deepseek_process_button.setText("DeepSeek 修正")
        self.deepseek_process_button.setEnabled(True)
        self.select_subtitle_button.setEnabled(True)

        # 更新对话框显示错误
        if hasattr(self, "current_dialog") and self.current_dialog:
            self.current_dialog.set_error(error_message)
            self.current_dialog.exec_()
            self.current_dialog = None
        else:
            InfoBar.error(
                title="处理失败",
                content=f"DeepSeek处理失败: {error_message}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def save_modified_subtitles(self):
        """保存修改后的字幕"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        file_path = self.table.item(current_row, 0).data(Qt.UserRole)

        # 获取当前预览文本
        current_text = self.preview_text.toPlainText()
        if not current_text:
            return

        # 保存到文件
        try:
            save_ext = self.format_combo.currentText().lower()
            save_path = file_path.rsplit(".", 1)[0] + "." + save_ext
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(current_text)

            InfoBar.success(
                title="保存成功",
                content=f"字幕已保存到: {os.path.basename(save_path)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            logging.error(f"保存字幕失败: {e}")
            InfoBar.error(
                title="保存失败",
                content=f"保存字幕失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """拖拽释放事件"""
        supported_formats = (
            ".mp3",
            ".wav",
            ".ogg",
            ".flac",
            ".aac",
            ".m4a",
            ".wma",  # 音频格式
            ".mp4",
            ".avi",
            ".mov",
            ".ts",
            ".mkv",
            ".wmv",
            ".flv",
            ".webm",
            ".rmvb",
        )  # 视频格式
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file in files:
            if os.path.isdir(file):
                for root, dirs, files_in_dir in os.walk(file):
                    for f in files_in_dir:
                        if f.lower().endswith(supported_formats):
                            self.add_file_to_table(os.path.join(root, f))
            elif file.lower().endswith(supported_formats):
                self.add_file_to_table(file)
        self.update_start_button_state()


class InfoWidget(QWidget):
    """个人信息界面"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # GitHub URL
        ORIGINAL_GITHUB_URL = "https://github.com/WEIFENG2333/AsrTools"
        MY_GITHUB_URL = "https://github.com/adidalin"

        APP_DESCRIPTION = """
🎤 AsrTools - DeepSeek AI 字幕修正版

基于 WEIFENG2333/AsrTools 的修改版本，添加了 DeepSeek AI 字幕修正功能。
        """

        FEATURES = """
✨ 新增功能：

🤖 DeepSeek AI 字幕修正
   • 智能修正错别字和语法错误
   • 人名、地名、专有名词确认
   • 保留原始时间戳，只修正文本内容

📝 字幕预览和编辑
   • 右侧面板显示字幕内容预览
   • 支持直接编辑字幕内容
   • 支持选择已有的字幕文件进行修正

🔍 AI 修正对比弹窗
   • 显示原始字幕和修正后字幕的对比
   • 修改的行用黄色背景高亮显示
   • 支持在对话框中继续手动编辑
        """

        USAGE = """
📋 快速上手：

【基本操作 - 生成字幕】

1️⃣ 选择 ASR 接口
   • B 接口：必剪接口，速度快
   • J 接口：剪映接口，效果好
   • K 接口：快手接口

2️⃣ 选择导出格式
   • SRT：通用字幕格式（推荐）
   • TXT：纯文本格式
   • ASS：高级字幕格式

3️⃣ 添加文件
   • 点击"选择文件"按钮
   • 或直接拖拽文件/文件夹到窗口

4️⃣ 开始处理
   • 点击"开始处理"按钮
   • 等待处理完成，字幕文件保存在原文件同目录

【AI 修正 - DeepSeek 增强】

1️⃣ 配置 DeepSeek API
   • 输入 API 密钥
   • 点击"测试 API"验证连接
   • 勾选"启用 DeepSeek 字幕修正"

2️⃣ 选择字幕
   • 点击已处理的文件，或
   • 点击"选择字幕文件"加载已有字幕

3️⃣ AI 修正
   • 点击"DeepSeek 修正"按钮
   • 在弹窗中查看对比结果
   • 可手动编辑修正内容
   • 点击"应用修正"保存
        """

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignTop)

        # 标题
        title_label = BodyLabel("  ASRTools - DeepSeek", content_widget)
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)

        # 应用描述
        app_desc_label = BodyLabel(APP_DESCRIPTION, content_widget)
        app_desc_label.setFont(QFont("Segoe UI", 11))
        content_layout.addWidget(app_desc_label)

        # 功能介绍
        features_label = BodyLabel(FEATURES, content_widget)
        features_label.setFont(QFont("Segoe UI", 10))
        content_layout.addWidget(features_label)

        # 使用说明
        usage_label = BodyLabel(USAGE, content_widget)
        usage_label.setFont(QFont("Segoe UI", 10))
        content_layout.addWidget(usage_label)

        # 贡献者信息
        contributor_label = BodyLabel("👤 贡献者", content_widget)
        contributor_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        content_layout.addWidget(contributor_label)

        contributor_info = BodyLabel("小花荣 (adidalin)\nadidalin@qq.com", content_widget)
        contributor_info.setFont(QFont("Segoe UI", 11))
        content_layout.addWidget(contributor_info)

        # 按钮区域
        button_layout = QHBoxLayout()

        original_button = PushButton("原项目", content_widget)
        original_button.setIcon(FIF.GITHUB)
        original_button.setIconSize(QSize(20, 20))
        original_button.setMinimumHeight(36)
        original_button.clicked.connect(lambda _: webbrowser.open(ORIGINAL_GITHUB_URL))
        button_layout.addWidget(original_button)

        my_button = PushButton("我的 GitHub", content_widget)
        my_button.setIcon(FIF.GITHUB)
        my_button.setIconSize(QSize(20, 20))
        my_button.setMinimumHeight(36)
        my_button.clicked.connect(lambda _: webbrowser.open(MY_GITHUB_URL))
        button_layout.addWidget(my_button)

        content_layout.addLayout(button_layout)

        # 设置滚动区域的内容
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)


class MainWindow(FluentWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASR Processing Tool")

        # ASR 处理界面
        self.asr_widget = ASRWidget()
        self.asr_widget.setObjectName("main")
        self.addSubInterface(self.asr_widget, FIF.ALBUM, "ASR Processing")

        # 个人信息界面
        self.info_widget = InfoWidget()
        self.info_widget.setObjectName("info")  # 设置对象名称
        self.addSubInterface(self.info_widget, FIF.GITHUB, "About")

        self.navigationInterface.setExpandWidth(200)
        self.resize(800, 600)

        self.update_checker = UpdateCheckerThread(self)
        self.update_checker.msg.connect(self.show_msg)
        self.update_checker.start()

    def show_msg(self, title, content, update_download_url):
        w = MessageBox(title, content, self)
        if w.exec() and update_download_url:
            webbrowser.open(update_download_url)
        if title == "更新":
            sys.exit(0)


def video2audio(input_file: str, output: str = "") -> bool:
    """使用ffmpeg将视频转换为音频"""
    # 创建output目录
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output = str(output)

    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-ac",
        "1",
        "-f",
        "mp3",
        "-af",
        "aresample=async=1",
        "-y",
        output,
    ]
    result = subprocess.run(
        cmd, capture_output=True, check=True, encoding="utf-8", errors="replace"
    )

    if result.returncode == 0 and Path(output).is_file():
        return True
    else:
        return False


def start():
    # enable dpi scale
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    # setTheme(Theme.DARK)  # 如果需要深色主题，取消注释此行
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    start()
