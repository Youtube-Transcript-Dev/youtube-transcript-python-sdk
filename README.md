<p align="center">
  <a href="https://youtubetranscript.dev">
    <img src="https://youtubetranscript.dev/logo.svg" alt="YouTubeTranscript.dev" width="280" />
  </a>
</p>

<h3 align="center">YouTubeTranscript Python SDK</h3>

<p align="center">
  Official Python client for the <a href="https://youtubetranscript.dev">YouTubeTranscript.dev</a> API<br/>
  Extract, transcribe, and translate YouTube video transcripts.
</p>

<p align="center">
  <a href="https://pypi.org/project/youtubetranscriptdevapi/"><img src="https://img.shields.io/pypi/v/youtubetranscriptdevapi?color=%2334D058&label=pypi" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/youtubetranscriptdevapi/"><img src="https://img.shields.io/pypi/pyversions/youtubetranscriptdevapi?color=%2334D058" alt="Python versions" /></a>
  <a href="https://github.com/Youtube-Transcript-Dev/youtube-transcript-python-sdk/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Youtube-Transcript-Dev/youtube-transcript-python-sdk" alt="License" /></a>
</p>

---

## Installation

```bash
pip install youtubetranscriptdevapi
```

## Quick Start

```python
from youtubetranscript import YouTubeTranscript

yt = YouTubeTranscript("your_api_key")

# Extract transcript
result = yt.transcribe("dQw4w9WgXcQ")

print(f"Segments: {len(result.segments)}")
print(f"Duration: {result.duration:.0f}s")
print(f"Words: {result.word_count}")

for seg in result.segments[:5]:
    print(f"[{seg.start_formatted}] {seg.text}")
```

Get your free API key at [youtubetranscript.dev/dashboard](https://youtubetranscript.dev/dashboard)

## Features

```python
# Translate to any language
result = yt.transcribe("dQw4w9WgXcQ", language="es")

# Choose caption source
result = yt.transcribe("dQw4w9WgXcQ", source="manual")

# Format options
result = yt.transcribe("dQw4w9WgXcQ", format={"timestamp": True, "words": True})

# Batch — up to 100 videos at once
batch = yt.batch(["video1", "video2", "video3"])
for t in batch.completed:
    print(f"{t.video_id}: {t.word_count} words")

# ASR audio transcription (for videos without captions)
job = yt.transcribe_asr("video_without_captions")
result = yt.wait_for_job(job.job_id)  # polls until complete
print(result.text)

# Export formats
print(result.to_srt())       # SRT subtitles
print(result.to_vtt())       # WebVTT subtitles
print(result.to_plain_text())       # Plain text
print(result.to_timestamped_text()) # Text with timestamps

# Search within transcript
matches = result.search("keyword")

# Account stats
stats = yt.stats()
print(f"Credits: {stats.credits_remaining}")

# History
history = yt.list_transcripts(search="python tutorial", limit=5)
```

## Async Client

```python
import asyncio
from youtubetranscript import AsyncYouTubeTranscript

async def main():
    async with AsyncYouTubeTranscript("your_api_key") as yt:
        # Single
        result = await yt.transcribe("dQw4w9WgXcQ")

        # Concurrent
        results = await asyncio.gather(
            yt.transcribe("video1"),
            yt.transcribe("video2"),
            yt.transcribe("video3"),
        )

asyncio.run(main())
```

## Error Handling

```python
from youtubetranscript import YouTubeTranscript
from youtubetranscript.exceptions import (
    NoCaptionsError,
    AuthenticationError,
    InsufficientCreditsError,
    RateLimitError,
)

yt = YouTubeTranscript("your_api_key")

try:
    result = yt.transcribe("some_video")
except NoCaptionsError:
    # No captions — try ASR
    job = yt.transcribe_asr("some_video")
    result = yt.wait_for_job(job.job_id)
except AuthenticationError:
    print("Check your API key")
except InsufficientCreditsError:
    print("Top up at youtubetranscript.dev/pricing")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
```

## API Reference

### `YouTubeTranscript(api_key, *, base_url, timeout, max_retries)`

| Method | Description |
|--------|-------------|
| `transcribe(video, *, language, source, format)` | Extract transcript |
| `transcribe_asr(video, *, language, webhook_url)` | ASR audio transcription |
| `get_job(job_id)` | Check ASR job status |
| `wait_for_job(job_id, *, poll_interval, timeout)` | Poll until ASR completes |
| `batch(video_ids, *, language)` | Batch extract (up to 100) |
| `get_batch(batch_id)` | Check batch status |
| `list_transcripts(*, search, language, status, limit, page)` | Browse history |
| `get_transcript(video_id, *, language, source)` | Get saved transcript |
| `stats()` | Account credits & usage |
| `delete_transcript(*, video_id, ids)` | Delete transcripts |

### `Transcript` object

| Property/Method | Description |
|--------|-------------|
| `segments` | List of `Segment` objects |
| `text` | Full transcript as string |
| `video_id` | YouTube video ID |
| `language` | Transcript language |
| `word_count` | Total word count |
| `duration` | Total duration in seconds |
| `to_srt()` | Export as SRT |
| `to_vtt()` | Export as WebVTT |
| `to_plain_text()` | Plain text export |
| `to_timestamped_text()` | Text with `[MM:SS]` timestamps |
| `search(query)` | Find segments by text |

### `Segment` object

| Property | Description |
|----------|-------------|
| `text` | Segment text |
| `start` | Start time (seconds) |
| `end` | End time (seconds) |
| `duration` | Duration (seconds) |
| `start_formatted` | `"MM:SS"` format |
| `start_hms` | `"HH:MM:SS"` format |

## Credit Costs

| Operation | Cost |
|-----------|------|
| Captions extraction | 1 credit |
| Translation | 1 credit per 2,500 chars |
| ASR audio transcription | 1 credit per 90 seconds |
| Re-fetch owned transcript | Free |

## License

MIT — see [LICENSE](LICENSE)

## Links

- [Website](https://youtubetranscript.dev)
- [PyPI](https://pypi.org/project/youtubetranscriptdevapi/)
- [API Docs](https://youtubetranscript.dev/api-docs)
- [Dashboard](https://youtubetranscript.dev/dashboard)
- [Pricing](https://youtubetranscript.dev/pricing)
