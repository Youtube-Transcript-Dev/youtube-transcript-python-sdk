"""Async client for the YouTubeTranscript.dev API."""

from __future__ import annotations

import asyncio
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


class AsyncYouTubeTranscript:
    """
    Async client for YouTubeTranscript.dev API.

    Usage::

        async with AsyncYouTubeTranscript("your_api_key") as yt:
            result = await yt.transcribe("dQw4w9WgXcQ")
            print(result.text)

            # Concurrent extraction
            import asyncio
            results = await asyncio.gather(
                yt.transcribe("video1"),
                yt.transcribe("video2"),
                yt.transcribe("video3"),
            )

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
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "youtubetranscript-python/0.1.0 (async)",
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        await self._client.aclose()

    # ─── Core Methods ────────────────────────────────────────────────

    async def transcribe(
        self,
        video: str,
        *,
        language: Optional[str] = None,
        source: Optional[str] = None,
        format: Optional[Union[str, Dict[str, bool]]] = None,
    ) -> Transcript:
        """Extract transcript from a YouTube video."""
        body: Dict[str, Any] = {"video": video}
        if language:
            body["language"] = language
        if source:
            body["source"] = source
        if format:
            body["format"] = format

        data = await self._post("/v2/transcribe", body)
        return Transcript.from_response(data)

    async def transcribe_asr(
        self,
        video: str,
        *,
        language: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> TranscriptJob:
        """Transcribe from audio using ASR (async operation)."""
        body: Dict[str, Any] = {
            "video": video,
            "source": "asr",
            "format": {"timestamp": True, "paragraphs": True, "words": True},
        }
        if language:
            body["language"] = language
        if webhook_url:
            body["webhook_url"] = webhook_url

        data = await self._post("/v2/transcribe", body)
        return TranscriptJob.from_response(data)

    async def get_job(self, job_id: str) -> TranscriptJob:
        """Check status of an ASR transcription job."""
        data = await self._get(f"/v2/jobs/{job_id}", params={
            "include_segments": "true",
            "include_paragraphs": "true",
            "include_words": "true",
        })
        return TranscriptJob.from_response(data)

    async def wait_for_job(
        self,
        job_id: str,
        *,
        poll_interval: float = 10.0,
        timeout: float = 1200.0,
    ) -> Transcript:
        """Poll an ASR job until completion."""
        start = time.monotonic()
        while True:
            job = await self.get_job(job_id)
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
            await asyncio.sleep(poll_interval)

    async def batch(
        self,
        video_ids: List[str],
        *,
        language: Optional[str] = None,
    ) -> BatchResult:
        """Extract transcripts from up to 100 videos."""
        if len(video_ids) > 100:
            raise ValueError("Maximum 100 videos per batch request")

        body: Dict[str, Any] = {"video_ids": video_ids}
        if language:
            body["language"] = language

        data = await self._post("/v2/batch", body)
        return BatchResult.from_response(data)

    async def get_batch(self, batch_id: str) -> BatchResult:
        """Check status of a batch request."""
        data = await self._get(f"/v2/batch/{batch_id}")
        return BatchResult.from_response(data)

    async def list_transcripts(self, **kwargs) -> Dict[str, Any]:
        """List your transcript history."""
        params: Dict[str, Any] = {
            "limit": kwargs.get("limit", 10),
            "page": kwargs.get("page", 1),
        }
        for k in ("search", "language", "status"):
            if kwargs.get(k):
                params[k] = kwargs[k]
        return await self._get("/v1/history", params=params)

    async def get_transcript(self, video_id: str, **kwargs) -> Transcript:
        """Get a previously extracted transcript."""
        params: Dict[str, Any] = {
            "include_timestamps": str(kwargs.get("include_timestamps", True)).lower()
        }
        for k in ("language", "source"):
            if kwargs.get(k):
                params[k] = kwargs[k]
        data = await self._get(f"/v1/transcripts/{video_id}", params=params)
        return Transcript.from_response(data)

    async def stats(self) -> AccountStats:
        """Get account stats."""
        data = await self._get("/v1/stats")
        return AccountStats.from_response(data)

    async def delete_transcript(self, **kwargs) -> Dict[str, Any]:
        """Delete transcripts by video ID or record IDs."""
        body: Dict[str, Any] = {}
        if kwargs.get("video_id"):
            body["video_id"] = kwargs["video_id"]
        if kwargs.get("ids"):
            body["ids"] = kwargs["ids"]
        return await self._post("/v1/transcripts/bulk-delete", body)

    # ─── HTTP Layer ──────────────────────────────────────────────────

    async def _post(self, path: str, body: dict) -> dict:
        return await self._request("POST", path, json=body)

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        return await self._request("GET", path, params=params)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base_url}{path}"
        last_exc = None

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as e:
                last_exc = YouTubeTranscriptError(f"Request timed out: {e}")
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise last_exc from e
            except httpx.HTTPError as e:
                raise YouTubeTranscriptError(f"HTTP error: {e}") from e

            try:
                data = resp.json()
            except Exception:
                if not resp.is_success:
                    raise YouTubeTranscriptError(
                        f"Server returned {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code,
                    )
                raise YouTubeTranscriptError("Invalid JSON in response")

            if not resp.is_success and resp.status_code not in (202,):
                if resp.status_code >= 500 and attempt < self._max_retries:
                    last_exc = None
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise_for_status(resp.status_code, data)

            return data

        if last_exc:
            raise last_exc
        raise YouTubeTranscriptError("Request failed after retries")
