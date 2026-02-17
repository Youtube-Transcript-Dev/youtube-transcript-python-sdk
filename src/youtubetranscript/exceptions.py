"""Custom exceptions for the YouTubeTranscript SDK."""

from __future__ import annotations

from typing import Optional


class YouTubeTranscriptError(Exception):
    """Base exception for all API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(YouTubeTranscriptError):
    """Invalid or missing API key (401)."""
    pass


class InsufficientCreditsError(YouTubeTranscriptError):
    """Not enough credits for the requested operation (402)."""
    pass


class InvalidRequestError(YouTubeTranscriptError):
    """Bad request — invalid parameters or missing fields (400)."""
    pass


class NoCaptionsError(YouTubeTranscriptError):
    """Video has no captions and ASR was not requested (404)."""
    pass


class RateLimitError(YouTubeTranscriptError):
    """Too many requests (429). Check retry_after attribute."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        **kwargs,
    ):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class ServerError(YouTubeTranscriptError):
    """Server-side error (5xx). Safe to retry with backoff."""
    pass


# Map HTTP status + error codes to exception classes
_ERROR_MAP = {
    401: AuthenticationError,
    402: InsufficientCreditsError,
    404: NoCaptionsError,
    429: RateLimitError,
}


def raise_for_status(status_code: int, body: dict) -> None:
    """Raise the appropriate exception based on API error response."""
    if 200 <= status_code < 300:
        return

    message = body.get("message") or body.get("error") or f"API error {status_code}"
    error_code = body.get("error_code")

    exc_class = _ERROR_MAP.get(status_code)

    if exc_class is None:
        if status_code >= 500:
            exc_class = ServerError
        elif status_code >= 400:
            exc_class = InvalidRequestError
        else:
            exc_class = YouTubeTranscriptError

    kwargs = {"status_code": status_code, "error_code": error_code}

    if exc_class is RateLimitError:
        kwargs["retry_after"] = body.get("retry_after")

    raise exc_class(message, **kwargs)
