import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import List, Optional, Union

import requests

from .ASRData import ASRDataSeg
from .BaseASR import BaseASR


class TencentASR(BaseASR):
    """腾讯云语音识别接口"""

    API_HOST = "asr.tencentcloudapi.com"
    API_URL = f"https://{API_HOST}"
    SERVICE = "asr"
    VERSION = "2019-06-14"

    ENGINE_OPTIONS = {
        "中文普通话": "16k_zh",
        "中文大模型(推荐)": "16k_zh_large",
        "中英粤大模型": "16k_zh_en",
        "英语": "16k_en",
        "粤语": "16k_yue",
        "日语": "16k_ja",
        "韩语": "16k_ko",
    }

    def __init__(
        self,
        audio_path: Union[str, bytes],
        secret_id: str,
        secret_key: str,
        engine_model: str = "16k_zh_large",
        use_cache: bool = False,
    ):
        super().__init__(audio_path, use_cache)
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.engine_model = engine_model

    def _run(self, callback=None) -> dict:
        if callback:
            callback(20, "提交识别任务...")

        task_id = self._create_task()

        if callback:
            callback(40, f"等待识别结果(TaskId:{task_id})...")

        result = self._poll_result(task_id, callback)

        if callback:
            callback(100, "识别完成")

        return result

    def _create_task(self) -> int:
        if len(self.file_binary) <= 5 * 1024 * 1024:
            data_b64 = base64.b64encode(self.file_binary).decode("utf-8")
            payload = {
                "EngineModelType": self.engine_model,
                "ChannelNum": 1,
                "ResTextFormat": 3,
                "SourceType": 1,
                "Data": data_b64,
                "DataLen": len(self.file_binary),
                "ConvertNumMode": 1,
            }
        else:
            raise ValueError(
                f"音频文件过大({len(self.file_binary) // 1024 // 1024}MB)，腾讯云本地上传限制5MB。"
                f"请使用较短的音频文件。"
            )

        resp = self._api_request("CreateRecTask", payload)
        task_id = resp.get("Data", {}).get("TaskId")
        if not task_id:
            raise ValueError(f"创建任务失败: {resp}")
        return task_id

    def _poll_result(self, task_id: int, callback=None) -> dict:
        for i in range(300):
            time.sleep(2)
            resp = self._api_request("DescribeTaskStatus", {"TaskId": task_id})
            data = resp.get("Data", {})
            status = data.get("Status")

            if callback and i % 5 == 0:
                progress = min(40 + int(i * 0.2), 90)
                callback(progress, f"识别中...状态:{status}")

            if status == 3:
                return data
            elif status == -1:
                raise ValueError(f"识别失败: {data.get('StatusStr', '未知错误')}")

        raise ValueError("识别超时(10分钟)")

    def _make_segments(self, resp_data: dict) -> List[ASRDataSeg]:
        segments = []
        detail = resp_data.get("ResultDetail", [])
        if detail:
            for item in detail:
                text = item.get("FinalSentence", "") or item.get("Sentence", "")
                start_time = int(item.get("StartTime", 0))
                end_time = int(item.get("EndTime", 0))
                if text.strip():
                    segments.append(ASRDataSeg(text.strip(), start_time, end_time))
        else:
            result_text = resp_data.get("Result", "")
            if result_text:
                segments.append(ASRDataSeg(result_text.strip(), 0, 0))
        return segments

    def _api_request(self, action: str, payload: dict) -> dict:
        timestamp = int(time.time())
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

        payload_json = json.dumps(payload)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.API_HOST,
            "X-TC-Action": action,
            "X-TC-Version": self.VERSION,
            "X-TC-Timestamp": str(timestamp),
        }

        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = (
            f"content-type:{headers['Content-Type']}\n"
            f"host:{headers['Host']}\n"
        )
        signed_headers = "content-type;host"
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        canonical_request = (
            f"POST\n{canonical_uri}\n{canonical_querystring}\n"
            f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )

        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.SERVICE}/tc3_request"
        string_to_sign = (
            f"{algorithm}\n{timestamp}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = _hmac_sha256(
            f"TC3{self.secret_key}".encode("utf-8"), date
        )
        secret_service = _hmac_sha256(secret_date, self.SERVICE)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(
            secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        headers["Authorization"] = authorization

        response = requests.post(
            self.API_URL, headers=headers, data=payload_json, timeout=120
        )
        response.raise_for_status()
        resp = response.json()

        if "Error" in resp.get("Response", {}):
            error = resp["Response"]["Error"]
            raise ValueError(
                f"腾讯云API错误: {error.get('Code')} - {error.get('Message')}"
            )

        return resp.get("Response", resp)
