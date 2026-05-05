import json
import logging
import requests
from typing import List, Optional, Tuple
from .ASRData import ASRDataSeg, ASRData


class SubtitleProcessResult:
    """字幕处理结果"""

    def __init__(
        self,
        original_data: ASRData,
        processed_data: ASRData,
        summary: str = "",
        changes: List[dict] = None,
        corrected_data: ASRData = None,
    ):
        self.original_data = original_data  # 原始字幕数据
        self.processed_data = processed_data  # 修正后的字幕数据（双语模式下包含原文+译文）
        self.summary = summary  # 内容摘要
        self.changes = changes or []  # 修改记录列表
        self.corrected_data = corrected_data  # 校正后的纯中文数据（仅双语模式使用）

    def has_changes(self) -> bool:
        """是否有修改"""
        return len(self.changes) > 0

    def get_changes_text(self) -> str:
        """获取修改说明文本"""
        if not self.changes:
            return "无修改"
        lines = []
        for i, change in enumerate(self.changes, 1):
            lines.append(f"{i}. 第{change['line']}行:")
            lines.append(f"   原文: {change['original']}")
            lines.append(f"   修正: {change['processed']}")
            if change.get("reason"):
                lines.append(f"   原因: {change['reason']}")
        return "\n".join(lines)


class DeepSeekProcessor:
    """DeepSeek API处理器，用于字幕修正和断句优化"""

    DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEFAULT_MODEL = "deepseek-chat"

    def __init__(self, api_key: str, api_url: str = None, model: str = None):
        """
        初始化DeepSeek处理器

        Args:
            api_key: DeepSeek API密钥
            api_url: API端点URL（可选）
            model: 模型名称（可选）
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.model = model or self.DEFAULT_MODEL

    def process_subtitles(
        self, asr_data: ASRData, custom_prompt: str = None
    ) -> SubtitleProcessResult:
        """
        处理字幕数据，进行修正和断句优化

        Args:
            asr_data: 原始ASR数据
            custom_prompt: 自定义提示词（可选）

        Returns:
            SubtitleProcessResult: 包含原始数据、修正数据、摘要和修改记录
        """
        if not asr_data.has_data():
            return SubtitleProcessResult(asr_data, asr_data, "空字幕", [])

        # 将字幕转换为文本格式
        subtitle_text = self._format_subtitles_for_processing(asr_data)

        # 调用DeepSeek API进行处理
        result = self._call_deepseek_api(subtitle_text, custom_prompt)

        if result is None:
            logging.error("DeepSeek API调用失败，返回原始数据")
            return SubtitleProcessResult(asr_data, asr_data, "处理失败", [])

        # 解析处理结果
        return self._parse_process_result(result, asr_data)

    def process_bilingual(
        self, asr_data: ASRData, custom_prompt: str = None
    ) -> SubtitleProcessResult:
        """
        处理字幕数据：先校正，再翻译成英文，生成双语字幕

        Args:
            asr_data: 原始ASR数据
            custom_prompt: 自定义提示词（可选）

        Returns:
            SubtitleProcessResult: 包含原始数据、校正数据、双语数据
        """
        if not asr_data.has_data():
            return SubtitleProcessResult(asr_data, asr_data, "空字幕", [])

        subtitle_text = self._format_subtitles_for_processing(asr_data)
        result = self._call_bilingual_api(subtitle_text, custom_prompt)

        if result is None:
            logging.error("DeepSeek双语翻译API调用失败，返回原始数据")
            return SubtitleProcessResult(asr_data, asr_data, "处理失败", [])

        return self._parse_bilingual_result(result, asr_data)

    def _call_bilingual_api(
        self, subtitle_text: str, custom_prompt: str = None
    ) -> Optional[dict]:
        """
        调用DeepSeek API进行校正+翻译（一次调用完成两步）

        Args:
            subtitle_text: 字幕文本
            custom_prompt: 自定义提示词

        Returns:
            处理结果字典，失败返回None
        """
        if not custom_prompt:
            custom_prompt = self._get_default_bilingual_prompt()

        full_prompt = f"{custom_prompt}\n\n以下是需要处理的字幕：\n{subtitle_text}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的字幕处理助手。请先校正字幕中的错别字和语法错误，然后将校正后的字幕翻译成英文。返回JSON格式。",
                },
                {"role": "user", "content": full_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 8192,
        }

        try:
            response = requests.post(
                self.api_url, headers=headers, json=payload, timeout=120
            )
            response.raise_for_status()

            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        json_str = content.split("```")[1].split("```")[0].strip()
                    else:
                        json_str = content
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return {"subtitles": content, "summary": "", "changes": []}
            else:
                logging.error(f"DeepSeek API返回格式异常: {result}")
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"DeepSeek API请求失败: {e}")
            return None
        except Exception as e:
            logging.error(f"处理DeepSeek响应时出错: {e}")
            return None

    def _get_default_bilingual_prompt(self) -> str:
        """获取默认的双语提示词（校正+翻译）"""
        return """请对以下字幕进行校正和翻译，要求：

【处理规则】
1. 先修正字幕中的错别字和语法错误，得到校正后的中文
2. 将校正后的中文翻译成自然流畅的英文
3. 保持所有时间戳（|HH:MM:SS,mmm --> HH:MM:SS,mmm|）完全不变
4. 保持字幕行数不变，不要合并或拆分

【输出格式】
请以JSON格式返回：
{
  "summary": "字幕内容摘要（50字以内）",
  "subtitles": [
    {
      "line": 行号,
      "time": "时间戳（保留原始格式）",
      "original": "原始文本",
      "corrected": "校正后的中文",
      "translated": "英文翻译"
    }
  ]
}

注意：
- 字幕行数必须与输入完全一致
- 只处理文字内容，不改变时间戳和行数
- 请直接输出JSON，不要添加其他说明"""

    def _parse_bilingual_result(
        self, result: dict, original_data: ASRData
    ) -> SubtitleProcessResult:
        """
        解析双语处理结果

        Args:
            result: DeepSeek返回的结果
            original_data: 原始ASR数据

        Returns:
            SubtitleProcessResult对象，包含:
            - original_data: 原始字幕
            - corrected_data: 校正后的纯中文
            - processed_data: 校正中文\n英文翻译
        """
        summary = result.get("summary", "")
        subtitles = result.get("subtitles", [])

        if isinstance(subtitles, str):
            return self._parse_bilingual_text_result(subtitles, original_data, summary)

        changes = []
        corrected_segments = []
        bilingual_segments = []

        for sub in subtitles:
            line_num = sub.get("line", 0)
            original_text = sub.get("original", "")
            corrected_text = sub.get("corrected", original_text)
            translated_text = sub.get("translated", "")
            time_str = sub.get("time", "")

            start_time, end_time = self._parse_time_str(time_str)

            if (
                start_time == 0
                and end_time == 0
                and line_num > 0
                and line_num <= len(original_data.segments)
            ):
                original_seg = original_data.segments[line_num - 1]
                start_time = original_seg.start_time
                end_time = original_seg.end_time

            # 校正后的纯中文段
            corrected_segments.append(ASRDataSeg(corrected_text, start_time, end_time))

            # 双语段：校正中文\n英文翻译
            if translated_text:
                bilingual_text = f"{corrected_text}\n{translated_text}"
            else:
                bilingual_text = corrected_text
            bilingual_segments.append(ASRDataSeg(bilingual_text, start_time, end_time))

            # 记录中文变动（原始 != 校正）
            if original_text.strip() != corrected_text.strip():
                changes.append(
                    {
                        "line": line_num,
                        "original": original_text,
                        "processed": corrected_text,
                        "reason": f"校正为: {corrected_text}",
                    }
                )

        if len(corrected_segments) == 0:
            logging.warning("解析结果为空，使用原始数据")
            return SubtitleProcessResult(original_data, original_data, summary, [])

        corrected_data = ASRData(corrected_segments)
        processed_data = ASRData(bilingual_segments)
        return SubtitleProcessResult(
            original_data, processed_data, summary, changes, corrected_data
        )

    def _parse_bilingual_text_result(
        self, text: str, original_data: ASRData, summary: str
    ) -> SubtitleProcessResult:
        """解析文本格式的双语结果（兼容旧格式）"""
        processed_lines = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if "|" in line and "-->" in line:
                processed_lines.append(line)

        if len(processed_lines) != len(original_data.segments):
            logging.warning(
                f"处理后的字幕行数({len(processed_lines)})与原始行数({len(original_data.segments)})不匹配"
            )
            return SubtitleProcessResult(original_data, original_data, summary, [])

        changes = []
        corrected_segments = []
        bilingual_segments = []
        for i, (original_seg, processed_line) in enumerate(
            zip(original_data.segments, processed_lines)
        ):
            try:
                parts = processed_line.split("|", 2)
                if len(parts) >= 3:
                    translated_text = parts[2].strip()
                    corrected_segments.append(
                        ASRDataSeg(original_seg.text, original_seg.start_time, original_seg.end_time)
                    )
                    bilingual_text = f"{original_seg.text}\n{translated_text}"
                    bilingual_segments.append(
                        ASRDataSeg(bilingual_text, original_seg.start_time, original_seg.end_time)
                    )
                else:
                    corrected_segments.append(original_seg)
                    bilingual_segments.append(original_seg)
            except Exception as e:
                logging.error(f"解析第{i + 1}行字幕时出错: {e}")
                corrected_segments.append(original_seg)
                bilingual_segments.append(original_seg)

        corrected_data = ASRData(corrected_segments)
        processed_data = ASRData(bilingual_segments)
        return SubtitleProcessResult(
            original_data, processed_data, summary, changes, corrected_data
        )

    def _format_subtitles_for_processing(self, asr_data: ASRData) -> str:
        """将字幕格式化为易于处理的文本格式"""
        lines = []
        for i, seg in enumerate(asr_data.segments, 1):
            # 格式：序号 | 开始时间 --> 结束时间 | 文本
            start_time = self._ms_to_srt_time(seg.start_time)
            end_time = self._ms_to_srt_time(seg.end_time)
            lines.append(f"{i}|{start_time} --> {end_time}|{seg.text}")
        return "\n".join(lines)

    def _ms_to_srt_time(self, ms: int) -> str:
        """将毫秒转换为SRT时间字符串 (HH:MM:SS,mmm)"""
        total_seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(milliseconds):03}"

    def _call_deepseek_api(
        self, subtitle_text: str, custom_prompt: str = None
    ) -> Optional[dict]:
        """
        调用DeepSeek API处理字幕

        Args:
            subtitle_text: 字幕文本
            custom_prompt: 自定义提示词

        Returns:
            处理结果字典，失败返回None
        """
        if not custom_prompt:
            custom_prompt = self._get_default_prompt()

        # 构建完整的提示词
        full_prompt = f"{custom_prompt}\n\n以下是需要处理的字幕：\n{subtitle_text}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": """你是一个专业的字幕处理助手。你的任务是：
1. 修正字幕中的错别字和语法错误
2. 优化断句，确保一句话完整显示在一条字幕中
3. 识别并标记可能的人名、地名等专有名词
4. 保留所有时间戳不变
5. 返回JSON格式的结果""",
                },
                {"role": "user", "content": full_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 8192,
        }

        try:
            response = requests.post(
                self.api_url, headers=headers, json=payload, timeout=120
            )
            response.raise_for_status()

            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # 尝试解析JSON
                try:
                    # 提取JSON部分（可能被```json```包围）
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        json_str = content.split("```")[1].split("```")[0].strip()
                    else:
                        json_str = content
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # 如果不是JSON格式，返回原始文本
                    return {"subtitles": content, "summary": "", "changes": []}
            else:
                logging.error(f"DeepSeek API返回格式异常: {result}")
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"DeepSeek API请求失败: {e}")
            return None
        except Exception as e:
            logging.error(f"处理DeepSeek响应时出错: {e}")
            return None

    def _get_default_prompt(self) -> str:
        """获取默认的处理提示词"""
        return """请对以下字幕进行修正，要求：

【修正规则】
1. 修正错别字和语法错误
2. 人名、地名、专有名词需要确认，如果不确定请标注[?]
3. 保持所有时间戳（|HH:MM:SS,mmm --> HH:MM:SS,mmm|）完全不变
4. 保持字幕行数不变，不要合并或拆分字幕

【输出格式】
请以JSON格式返回：
{
  "summary": "字幕内容摘要（50字以内）",
  "subtitles": [
    {
      "line": 行号,
      "time": "时间戳（保留原始格式）",
      "original": "原始文本",
      "processed": "修正后文本",
      "reason": "修改原因（如有修改请说明）"
    }
  ]
}

注意：
- 字幕行数必须与输入完全一致
- 只修正文字内容，不改变时间戳和行数
- 请直接输出JSON，不要添加其他说明"""

    def _parse_process_result(
        self, result: dict, original_data: ASRData
    ) -> SubtitleProcessResult:
        """
        解析处理结果

        Args:
            result: DeepSeek返回的结果
            original_data: 原始ASR数据

        Returns:
            SubtitleProcessResult对象
        """
        # 提取摘要
        summary = result.get("summary", "")

        # 提取字幕列表
        subtitles = result.get("subtitles", [])

        # 如果subtitles是字符串而不是列表，说明是原始文本格式
        if isinstance(subtitles, str):
            return self._parse_text_result(subtitles, original_data, summary)

        # 解析JSON格式的字幕
        changes = []
        new_segments = []

        for sub in subtitles:
            line_num = sub.get("line", 0)
            original_text = sub.get("original", "")
            processed_text = sub.get("processed", "")
            time_str = sub.get("time", "")
            reason = sub.get("reason", "")

            # 解析时间戳
            start_time, end_time = self._parse_time_str(time_str)

            # 如果时间戳解析失败，尝试从原始数据获取
            if (
                start_time == 0
                and end_time == 0
                and line_num > 0
                and line_num <= len(original_data.segments)
            ):
                original_seg = original_data.segments[line_num - 1]
                start_time = original_seg.start_time
                end_time = original_seg.end_time

            # 创建新的segment
            new_segments.append(ASRDataSeg(processed_text, start_time, end_time))

            # 记录修改
            if original_text != processed_text:
                changes.append(
                    {
                        "line": line_num,
                        "original": original_text,
                        "processed": processed_text,
                        "reason": reason,
                    }
                )

        # 如果解析结果为空，回退到原始数据
        if len(new_segments) == 0:
            logging.warning("解析结果为空，使用原始数据")
            return SubtitleProcessResult(original_data, original_data, summary, [])

        processed_data = ASRData(new_segments)
        return SubtitleProcessResult(original_data, processed_data, summary, changes)

    def _parse_time_str(self, time_str: str) -> tuple:
        """
        解析时间戳字符串

        Args:
            time_str: 时间戳字符串，格式如 "00:00:01,000 --> 00:00:02,000"

        Returns:
            (start_time_ms, end_time_ms) 元组
        """
        try:
            if "-->" not in time_str:
                return 0, 0

            parts = time_str.split("-->")
            start_str = parts[0].strip()
            end_str = parts[1].strip()

            start_ms = self._time_str_to_ms(start_str)
            end_ms = self._time_str_to_ms(end_str)

            return start_ms, end_ms
        except Exception:
            return 0, 0

    def _time_str_to_ms(self, time_str: str) -> int:
        """
        将时间字符串转换为毫秒

        Args:
            time_str: 时间字符串，格式如 "00:00:01,000"

        Returns:
            毫秒数
        """
        try:
            # 处理逗号或点号分隔的毫秒
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

    def _parse_text_result(
        self, text: str, original_data: ASRData, summary: str
    ) -> SubtitleProcessResult:
        """解析文本格式的结果（兼容旧格式）"""
        processed_lines = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if "|" in line and "-->" in line:
                processed_lines.append(line)

        if len(processed_lines) != len(original_data.segments):
            logging.warning(
                f"处理后的字幕行数({len(processed_lines)})与原始行数({len(original_data.segments)})不匹配"
            )
            return SubtitleProcessResult(original_data, original_data, summary, [])

        changes = []
        new_segments = []
        for i, (original_seg, processed_line) in enumerate(
            zip(original_data.segments, processed_lines)
        ):
            try:
                parts = processed_line.split("|", 2)
                if len(parts) >= 3:
                    new_text = parts[2].strip()
                    new_segments.append(
                        ASRDataSeg(
                            new_text, original_seg.start_time, original_seg.end_time
                        )
                    )
                    if original_seg.text != new_text:
                        changes.append(
                            {
                                "line": i + 1,
                                "original": original_seg.text,
                                "processed": new_text,
                                "reason": "",
                            }
                        )
                else:
                    new_segments.append(original_seg)
            except Exception as e:
                logging.error(f"解析第{i + 1}行字幕时出错: {e}")
                new_segments.append(original_seg)

        processed_data = ASRData(new_segments)
        return SubtitleProcessResult(original_data, processed_data, summary, changes)

    @staticmethod
    def validate_config(api_key: str, api_url: str = None) -> bool:
        """验证配置是否有效"""
        if not api_key:
            return False
        return True
