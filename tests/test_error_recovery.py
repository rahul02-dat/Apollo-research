"""Acceptance Test AT-12: Error Recovery, Rate Limiting, and Bounded Retries."""

from unittest.mock import MagicMock, patch
import httpx
import pytest
from app.connectors.sec_edgar_client import SECEdgarClient, SECRateLimitError


def test_at12_rate_limit_backoff_and_bounded_retry() -> None:
    client = SECEdgarClient(rate_limit_per_sec=100.0, max_retries=2)

    # Mock response returning 429 Too Many Requests
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    with patch("httpx.Client.get", return_value=mock_resp_429) as mock_get:
        with patch("time.sleep") as mock_sleep:
            with pytest.raises(SECRateLimitError):
                client._request_with_retry("https://sec.gov/test")

            # Must have retried max_retries times and then failed closed
            assert mock_get.call_count == 3  # initial + 2 retries
            assert mock_sleep.call_count == 3


def test_at12_network_timeout_bounded_retry() -> None:
    client = SECEdgarClient(rate_limit_per_sec=100.0, max_retries=2)

    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Connection timed out")):
        with patch("time.sleep"):
            with pytest.raises(Exception) as excinfo:
                client._request_with_retry("https://sec.gov/test")
            assert "timed out after 2 retries" in str(excinfo.value)
