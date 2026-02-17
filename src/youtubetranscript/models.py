"""Data models for API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Segment:
    """A single transcript segment with timing."""

    text: str
    start: float
    end: float = 0.0
    duration: float = 0.0
    words: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        if self.end == 0.0 and self.duration > 0:
            self.end = self.start + self.duration
        if self.duration == 0.0 and self.end > self.start:
            self.duration = self.end - self.start

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(
            text=d.get("text", ""),
            start=float(d.get("start", 0)),
            end=float(d.get("end", 0)),
            duration=float(d.get("duration", 0)),
            words=d.get("words"),
        )

    @property
    def start_formatted(self) -> str:
        """Format start time as MM:SS."""
        m, s = divmod(int(self.start), 60)
        return f"{m:02d}:{s:02d}"

    @property
    def start_hms(self) -> str:
        """Format start time as HH:MM:SS."""
        h, rem = divmod(int(self.start), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class Transcript:
    """A complete video transcript."""

    video_id: str
    segments: List[Segment] = field(default_factory=list)
    text: str = ""
    language: str = ""
    status: str = "completed"
    request_id: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_response(cls, data: dict) -> "Transcript":
        """Parse from API response."""
        # Handle nested structures: data.data.transcript.segments, data.data.segments, etc.
        inner = data.get("data", data)
        transcript_obj = inner.get("transcript", inner)

        # Segments can be in transcript.segments or directly transcript (as list)
        raw_segments = []
        if isinstance(transcript_obj, dict):
            raw_segments = transcript_obj.get("segments", [])
            full_text = transcript_obj.get("text", "")
        elif isinstance(transcript_obj, list):
            raw_segments = transcript_obj
            full_text = ""
        else:
            full_text = ""

        # Fallback: segments at data level
        if not raw_segments:
            raw_segments = inner.get("segments", [])

        segments = [Segment.from_dict(s) for s in raw_segments]

        # Build full text if not provided
        if not full_text and segments:
            full_text = " ".join(s.text for s in segments)

        return cls(
            video_id=inner.get("video_id", data.get("video_id", "")),
            segments=segments,
            text=full_text,
            language=inner.get("language", data.get("language", "")),
            status=data.get("status", "completed"),
            request_id=data.get("request_id", ""),
            raw=data,
        )

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0

    @property
    def duration(self) -> float:
        """Total duration in seconds based on last segment."""
        if not self.segments:
            return 0.0
        last = self.segments[-1]
        return last.end if last.end > 0 else last.start + last.duration

    def to_plain_text(self) -> str:
        """Export as plain text without timestamps."""
        return " ".join(s.text for s in self.segments)

    def to_timestamped_text(self) -> str:
        """Export as text with timestamps."""
        lines = []
        for s in self.segments:
            lines.append(f"[{s.start_formatted}] {s.text}")
        return "\n".join(lines)

    def to_srt(self) -> str:
        """Export as SRT subtitle format."""
        lines = []
        for i, s in enumerate(self.segments, 1):
            start = _srt_time(s.start)
            end = _srt_time(s.end if s.end > 0 else s.start + max(s.duration, 2.0))
            lines.append(f"{i}\n{start} --> {end}\n{s.text}\n")
        return "\n".join(lines)

    def to_vtt(self) -> str:
        """Export as WebVTT subtitle format."""
        lines = ["WEBVTT", ""]
        for s in self.segments:
            start = _vtt_time(s.start)
            end = _vtt_time(s.end if s.end > 0 else s.start + max(s.duration, 2.0))
            lines.append(f"{start} --> {end}\n{s.text}\n")
        return "\n".join(lines)

    def search(self, query: str) -> List[Segment]:
        """Find segments containing the query text (case-insensitive)."""
        q = query.lower()
        return [s for s in self.segments if q in s.text.lower()]


@dataclass
class TranscriptJob:
    """An async ASR transcription job."""

    job_id: str
    status: str
    video_id: str = ""
    transcript: Optional[Transcript] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_response(cls, data: dict) -> "TranscriptJob":
        transcript = None
        if data.get("status") == "completed":
            transcript = Transcript.from_response(data)

        return cls(
            job_id=data.get("job_id", data.get("request_id", "")),
            status=data.get("status", "unknown"),
            video_id=data.get("video_id", data.get("data", {}).get("video_id", "")),
            transcript=transcript,
            raw=data,
        )

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"

    @property
    def is_processing(self) -> bool:
        return self.status in ("processing", "queued")

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


@dataclass
class BatchResult:
    """Result of a batch transcription request."""

    batch_id: str
    status: str
    completed: List[Transcript] = field(default_factory=list)
    failed: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_response(cls, data: dict) -> "BatchResult":
        completed = []
        for item in data.get("completed", data.get("data", [])):
            if isinstance(item, dict):
                completed.append(Transcript.from_response(item))

        return cls(
            batch_id=data.get("batch_id", ""),
            status=data.get("status", "completed"),
            completed=completed,
            failed=data.get("failed", []),
            raw=data,
        )


@dataclass
class AccountStats:
    """Account usage statistics."""

    credits_remaining: int = 0
    credits_used: int = 0
    transcripts_created: int = 0
    plan: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_response(cls, data: dict) -> "AccountStats":
        return cls(
            credits_remaining=data.get("credits_remaining", data.get("credits_left", 0)),
            credits_used=data.get("credits_used", 0),
            transcripts_created=data.get("transcripts_created", 0),
            plan=data.get("plan", ""),
            raw=data,
        )


def _srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_time(seconds: float) -> str:
    """Format seconds as VTT timestamp: HH:MM:SS.mmm"""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
