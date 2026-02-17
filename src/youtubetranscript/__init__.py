"""
YouTubeTranscript.dev Python SDK
=================================

Official Python client for the YouTubeTranscript.dev API.

Quick start::

    from youtubetranscript import YouTubeTranscript

    yt = YouTubeTranscript("your_api_key")
    result = yt.transcribe("dQw4w9WgXcQ")

    for segment in result.segments:
        print(f"[{segment.start:.1f}s] {segment.text}")

Get your free API key at https://youtubetranscript.dev
"""

from youtubetranscript.client import YouTubeTranscript
from youtubetranscript.async_client import AsyncYouTubeTranscript
from youtubetranscript.models import (
    Transcript,
    Segment,
    TranscriptJob,
    BatchResult,
    AccountStats,
)
from youtubetranscript.exceptions import (
    YouTubeTranscriptError,
    AuthenticationError,
    InsufficientCreditsError,
    NoCaptionsError,
    RateLimitError,
    InvalidRequestError,
    ServerError,
)

__version__ = "0.1.1"
__all__ = [
    "YouTubeTranscript",
    "AsyncYouTubeTranscript",
    "Transcript",
    "Segment",
    "TranscriptJob",
    "BatchResult",
    "AccountStats",
    "YouTubeTranscriptError",
    "AuthenticationError",
    "InsufficientCreditsError",
    "NoCaptionsError",
    "RateLimitError",
    "InvalidRequestError",
    "ServerError",
]
