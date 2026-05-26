"""Speech-to-text transcription layer.

Public surface::

    from vod_analyzer.core.transcribe import TranscriptSegment, Word, ASRBackend
    from vod_analyzer.core.transcribe import FasterWhisperBackend
"""

from vod_analyzer.core.transcribe._models import TranscriptSegment, Word
from vod_analyzer.core.transcribe.backend import ASRBackend
from vod_analyzer.core.transcribe.faster_whisper import FasterWhisperBackend

__all__ = [
    "ASRBackend",
    "FasterWhisperBackend",
    "TranscriptSegment",
    "Word",
]
