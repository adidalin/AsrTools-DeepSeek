from .BcutASR import BcutASR
from .JianYingASR import JianYingASR
from .KuaiShouASR import KuaiShouASR
from .DeepSeekProcessor import DeepSeekProcessor, SubtitleProcessResult
# from .WhisperASR import WhisperASR

__all__ = [
    "BcutASR",
    "JianYingASR",
    "KuaiShouASR",
    "DeepSeekProcessor",
    "SubtitleProcessResult",
]


def transcribe(audio_file, platform):
    assert platform in __all__
    asr = globals()[platform](audio_file)
    return asr.run()
