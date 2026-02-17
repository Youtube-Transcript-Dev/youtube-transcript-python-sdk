"""Tests for the YouTubeTranscript SDK."""

import pytest
from youtubetranscript.models import Segment, Transcript, TranscriptJob, AccountStats
from youtubetranscript.exceptions import (
    raise_for_status,
    AuthenticationError,
    NoCaptionsError,
    RateLimitError,
    InsufficientCreditsError,
    InvalidRequestError,
    ServerError,
)


# ─── Model Tests ─────────────────────────────────────────────────────

class TestSegment:
    def test_from_dict_basic(self):
        s = Segment.from_dict({"text": "Hello", "start": 1.5, "end": 3.0})
        assert s.text == "Hello"
        assert s.start == 1.5
        assert s.end == 3.0
        assert s.duration == 1.5

    def test_from_dict_with_duration(self):
        s = Segment.from_dict({"text": "Hi", "start": 0, "duration": 2.5})
        assert s.end == 2.5

    def test_start_formatted(self):
        s = Segment(text="", start=125.0)
        assert s.start_formatted == "02:05"

    def test_start_hms(self):
        s = Segment(text="", start=3725.0)
        assert s.start_hms == "01:02:05"


class TestTranscript:
    def test_from_response_nested(self):
        data = {
            "status": "completed",
            "request_id": "abc",
            "data": {
                "video_id": "dQw4w9WgXcQ",
                "language": "en",
                "transcript": {
                    "text": "Hello world",
                    "segments": [
                        {"text": "Hello", "start": 0, "end": 1000},
                        {"text": "world", "start": 1000, "end": 2000},
                    ]
                }
            }
        }
        t = Transcript.from_response(data)
        assert t.video_id == "dQw4w9WgXcQ"
        assert len(t.segments) == 2
        assert t.segments[0].text == "Hello"
        assert t.language == "en"

    def test_from_response_flat_segments(self):
        data = {
            "data": {
                "video_id": "test123",
                "segments": [{"text": "one", "start": 0, "end": 1}]
            }
        }
        t = Transcript.from_response(data)
        assert len(t.segments) == 1

    def test_to_plain_text(self):
        t = Transcript(
            video_id="x",
            segments=[Segment(text="Hello", start=0), Segment(text="world", start=1)],
        )
        assert t.to_plain_text() == "Hello world"

    def test_to_srt(self):
        t = Transcript(
            video_id="x",
            segments=[Segment(text="Hello", start=0, end=1.5)],
        )
        srt = t.to_srt()
        assert "1\n" in srt
        assert "00:00:00,000 --> 00:00:01,500" in srt
        assert "Hello" in srt

    def test_to_vtt(self):
        t = Transcript(
            video_id="x",
            segments=[Segment(text="Hi", start=0, end=2.0)],
        )
        vtt = t.to_vtt()
        assert vtt.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.000" in vtt

    def test_search(self):
        t = Transcript(
            video_id="x",
            segments=[
                Segment(text="Hello world", start=0),
                Segment(text="Goodbye moon", start=1),
                Segment(text="Hello again", start=2),
            ],
        )
        results = t.search("hello")
        assert len(results) == 2

    def test_word_count(self):
        t = Transcript(video_id="x", text="one two three four")
        assert t.word_count == 4

    def test_duration(self):
        t = Transcript(
            video_id="x",
            segments=[
                Segment(text="a", start=0, end=1),
                Segment(text="b", start=5, end=10),
            ],
        )
        assert t.duration == 10.0


class TestTranscriptJob:
    def test_processing_job(self):
        j = TranscriptJob.from_response({
            "job_id": "j123",
            "status": "processing",
            "video_id": "vid1",
        })
        assert j.is_processing
        assert not j.is_complete
        assert j.transcript is None

    def test_completed_job(self):
        j = TranscriptJob.from_response({
            "job_id": "j123",
            "status": "completed",
            "data": {
                "video_id": "vid1",
                "transcript": {
                    "segments": [{"text": "hi", "start": 0, "end": 1}]
                }
            }
        })
        assert j.is_complete
        assert j.transcript is not None
        assert len(j.transcript.segments) == 1


class TestAccountStats:
    def test_from_response(self):
        s = AccountStats.from_response({
            "credits_remaining": 42,
            "credits_used": 10,
            "plan": "pro",
        })
        assert s.credits_remaining == 42
        assert s.plan == "pro"


# ─── Exception Tests ─────────────────────────────────────────────────

class TestExceptions:
    def test_401_raises_auth_error(self):
        with pytest.raises(AuthenticationError) as exc_info:
            raise_for_status(401, {"error_code": "invalid_api_key", "message": "Bad key"})
        assert exc_info.value.status_code == 401

    def test_402_raises_credits_error(self):
        with pytest.raises(InsufficientCreditsError):
            raise_for_status(402, {"message": "Insufficient credits"})

    def test_404_raises_no_captions(self):
        with pytest.raises(NoCaptionsError):
            raise_for_status(404, {"error_code": "no_captions", "message": "No captions"})

    def test_429_raises_rate_limit(self):
        with pytest.raises(RateLimitError) as exc_info:
            raise_for_status(429, {"message": "Too many requests", "retry_after": 30})
        assert exc_info.value.retry_after == 30

    def test_400_raises_invalid_request(self):
        with pytest.raises(InvalidRequestError):
            raise_for_status(400, {"message": "Invalid video ID"})

    def test_500_raises_server_error(self):
        with pytest.raises(ServerError):
            raise_for_status(500, {"message": "Internal error"})

    def test_200_does_not_raise(self):
        raise_for_status(200, {})  # should not raise
