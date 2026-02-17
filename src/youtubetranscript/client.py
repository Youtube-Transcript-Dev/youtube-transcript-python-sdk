"""Synchronous client for the YouTubeTranscript.dev API."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union

import httpx

from youtubetranscript.exceptions import raise_for_status, YouTubeTranscriptError
from youtubetranscript.models import (
    AccountStats,
    BatchResult,
    Transcript,
    TranscriptJob,
)

DEFAULT_BASE_URL = "https://youtubetranscript.dev/api"
DEFAULT_TIMEOUT = 30.0


class YouTubeTranscript:
    """
    Synchronous client for YouTubeTranscript.dev API.

    Usage::

        yt = YouTubeTranscript("your_api_key")

        # Extract transcript
        result = yt.transcribe("dQw4w9WgXcQ")
        print(result.text)

        # Translate
        result = yt.transcribe("dQw4w9WgXcQ", language="es")

        # Batch
        results = yt.batch(["video1", "video2", "video3"])

        # ASR (audio transcription)
        job = yt.transcribe_asr("dQw4w9WgXcQ")
        result = yt.wait_for_job(job.job_id)

    Get your API key at https://youtubetranscript.dev
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 2,
    ):
        if not api_key or len(api_key.strip()) < 8:
            raise ValueError(
                "Invalid API key. Get yours at https://youtubetranscript.dev/dashboard"
            )

        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "youtubetranscript-python/0.1.0",
            },
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    # ─── Core Methods ────────────────────────────────────────────────

    def transcribe(
        self,
        video: str,
        *,
        language: Optional[str] = None,
        source: Optional[str] = None,
        format: Optional[Union[str, Dict[str, bool]]] = None,
    ) -> Transcript:
        """
        Extract transcript from a YouTube video.

        Args:
            video: YouTube URL or 11-character video ID.
            language: ISO 639-1 code (e.g. "es", "fr"). Omit for original language.
            source: "auto" (default), "manual", or "asr".
            format: Format options — "timestamp", "paragraphs", "words",
                    or dict like {"timestamp": True, "paragraphs": True}.

        Returns:
            Transcript object with segments, text, and export methods.

        Raises:
            NoCaptionsError: Video has no captions and ASR not requested.
            AuthenticationError: Invalid API key.
            InsufficientCreditsError: Not enough credits.
        """
        body: Dict[str, Any] = {"video": video}
        if language:
            body["language"] = language
        if source:
            body["source"] = source
        if format:
            body["format"] = format

        data = self._post("/v2/transcribe", body)
        return Transcript.from_response(data)

    def transcribe_asr(
        self,
        video: str,
        *,
        language: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> TranscriptJob:
        """
        Transcribe from audio using ASR (async operation).

        Cost: 1 credit per 90 seconds of audio.

        Args:
            video: YouTube URL or video ID.
            language: Optional target language.
            webhook_url: URL to receive results when ready.

        Returns:
            TranscriptJob with job_id for polling.
        """
        body: Dict[str, Any] = {
            "video": video,
            "source": "asr",
            "format": {"timestamp": True, "paragraphs": True, "words": True},
        }
        if language:
            body["language"] = language
        if webhook_url:
            body["webhook_url"] = webhook_url

        data = self._post("/v2/transcribe", body)
        return TranscriptJob.from_response(data)

    def get_job(self, job_id: str) -> TranscriptJob:
        """
        Check status of an ASR transcription job.

        Args:
            job_id: Job ID returned from transcribe_asr().

        Returns:
            TranscriptJob with current status and transcript if complete.
        """
        data = self._get(f"/v2/jobs/{job_id}", params={
            "include_segments": "true",
            "include_paragraphs": "true",
            "include_words": "true",
        })
        return TranscriptJob.from_response(data)

    def wait_for_job(
        self,
        job_id: str,
        *,
        poll_interval: float = 10.0,
        timeout: float = 1200.0,
    ) -> Transcript:
        """
        Poll an ASR job until completion.

        Args:
            job_id: Job ID from transcribe_asr().
            poll_interval: Seconds between polls (default 10).
            timeout: Max seconds to wait (default 1200 = 20 min).

        Returns:
            Completed Transcript.

        Raises:
            YouTubeTranscriptError: If job fails or times out.
        """
        start = time.monotonic()
        while True:
            job = self.get_job(job_id)
            if job.is_complete and job.transcript:
                return job.transcript
            if job.is_failed:
                raise YouTubeTranscriptError(
                    f"ASR job {job_id} failed: {job.raw.get('error', 'unknown')}",
                    error_code="job_failed",
                )
            elapsed = time.monotonic() - start
            if elapsed > timeout:
                raise YouTubeTranscriptError(
                    f"Timed out waiting for job {job_id} after {timeout}s",
                    error_code="timeout",
                )
            time.sleep(poll_interval)

    def batch(
        self,
        video_ids: List[str],
        *,
        language: Optional[str] = None,
    ) -> BatchResult:
        """
        Extract transcripts from up to 100 videos.

        Args:
            video_ids: List of YouTube URLs or video IDs (max 100).
            language: Optional target language for all videos.

        Returns:
            BatchResult with completed transcripts and any failures.
        """
        if len(video_ids) > 100:
            raise ValueError("Maximum 100 videos per batch request")

        body: Dict[str, Any] = {"video_ids": video_ids}
        if language:
            body["language"] = language

        data = self._post("/v2/batch", body)
        return BatchResult.from_response(data)

    def get_batch(self, batch_id: str) -> BatchResult:
        """Check status of a batch request."""
        data = self._get(f"/v2/batch/{batch_id}")
        return BatchResult.from_response(data)

    # ─── V1 Endpoints (History & Stats) ──────────────────────────────

    def list_transcripts(
        self,
        *,
        search: Optional[str] = None,
        language: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        List your transcript history.

        Args:
            search: Search by video ID, title, or transcript text.
            language: Filter by language code.
            status: Filter: "all", "queued", "processing", "succeeded", "failed".
            limit: Results per page (default 10).
            page: Page number.

        Returns:
            Raw API response dict with transcript list.
        """
        params: Dict[str, Any] = {"limit": limit, "page": page}
        if search:
            params["search"] = search
        if language:
            params["language"] = language
        if status:
            params["status"] = status

        return self._get("/v1/history", params=params)

    def get_transcript(
        self,
        video_id: str,
        *,
        language: Optional[str] = None,
        source: Optional[str] = None,
        include_timestamps: bool = True,
    ) -> Transcript:
        """
        Get a previously extracted transcript (V1 endpoint).

        Args:
            video_id: YouTube video ID.
            language: Language filter.
            source: "auto", "manual", or "asr".
            include_timestamps: Include timing data.

        Returns:
            Transcript object.
        """
        params: Dict[str, Any] = {"include_timestamps": str(include_timestamps).lower()}
        if language:
            params["language"] = language
        if source:
            params["source"] = source

        data = self._get(f"/v1/transcripts/{video_id}", params=params)
        return Transcript.from_response(data)

    def stats(self) -> AccountStats:
        """
        Get account stats: credits remaining, plan, usage.

        Returns:
            AccountStats object.
        """
        data = self._get("/v1/stats")
        return AccountStats.from_response(data)

    def delete_transcript(
        self,
        *,
        video_id: Optional[str] = None,
        ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Delete transcripts by video ID or record IDs.

        Args:
            video_id: Delete all transcripts for this video.
            ids: Delete specific transcript record IDs.

        Returns:
            Raw API response.
        """
        body: Dict[str, Any] = {}
        if video_id:
            body["video_id"] = video_id
        if ids:
            body["ids"] = ids
        return self._post("/v1/transcripts/bulk-delete", body)

    # ─── HTTP Layer ──────────────────────────────────────────────────

    def _post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, json=body)

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        return self._request("GET", path, params=params)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base_url}{path}"
        last_exc = None

        for attempt in range(self._max_retries + 1):
            try:
                resp = self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as e:
                last_exc = YouTubeTranscriptError(f"Request timed out: {e}")
                if attempt < self._max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise last_exc from e
            except httpx.HTTPError as e:
                raise YouTubeTranscriptError(f"HTTP error: {e}") from e

            # Parse response
            try:
                data = resp.json()
            except Exception:
                if not resp.is_success:
                    raise YouTubeTranscriptError(
                        f"Server returned {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code,
                    )
                raise YouTubeTranscriptError("Invalid JSON in response")

            # Check for errors
            if not resp.is_success and resp.status_code not in (202,):
                # Retry on 5xx
                if resp.status_code >= 500 and attempt < self._max_retries:
                    last_exc = None
                    time.sleep(2 ** attempt)
                    continue
                raise_for_status(resp.status_code, data)

            return data

        if last_exc:
            raise last_exc
        raise YouTubeTranscriptError("Request failed after retries")
