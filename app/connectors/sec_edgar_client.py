"""SEC EDGAR API HTTP Client with compliant rate limiting and caching."""

import hashlib
import logging
import time
from typing import Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class SECClientError(Exception):
    """Base exception for SEC EDGAR client errors."""
    pass


class SECRateLimitError(SECClientError):
    """Raised when rate limit is exceeded."""
    pass


class SECResourceNotFoundError(SECClientError):
    """Raised when an issuer or filing is not found."""
    pass


class SECEdgarClient:
    """Robust, compliant client for official SEC EDGAR public APIs."""

    BASE_DATA_URL = "https://data.sec.gov"
    BASE_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    def __init__(
        self,
        user_agent: str | None = None,
        rate_limit_per_sec: float | None = None,
        timeout_seconds: float | None = None,
        max_retries: int = 3,
    ) -> None:
        self.user_agent = user_agent or settings.SEC_USER_AGENT
        self.rate_limit_interval = 1.0 / (rate_limit_per_sec or settings.SEC_RATE_LIMIT_PER_SEC)
        self.timeout_seconds = timeout_seconds or settings.SEC_TIMEOUT_SECONDS
        self.max_retries = max_retries

        self._last_request_time = 0.0
        self._cache: dict[str, Any] = {}
        self._ticker_map: dict[str, dict[str, Any]] | None = None

    def _wait_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_interval:
            time.sleep(self.rate_limit_interval - elapsed)
        self._last_request_time = time.time()

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov" if "data.sec.gov" in self.BASE_DATA_URL else "www.sec.gov",
        }

    def _request_with_retry(self, url: str, is_json: bool = True) -> Any:
        self._wait_rate_limit()

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

        retries = 0
        backoff = 1.0

        while retries <= self.max_retries:
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.get(url, headers=headers)

                if resp.status_code == 200:
                    return resp.json() if is_json else resp.content

                if resp.status_code == 404:
                    raise SECResourceNotFoundError(f"SEC resource not found at URL: {url}")

                if resp.status_code == 429:
                    logger.warning("SEC 429 Rate Limit encountered. Backing off for %.2fs", backoff)
                    time.sleep(backoff)
                    retries += 1
                    backoff *= 2.0
                    continue

                if resp.status_code >= 500:
                    logger.warning("SEC server error %d at %s. Retrying in %.2fs", resp.status_code, url, backoff)
                    time.sleep(backoff)
                    retries += 1
                    backoff *= 1.5
                    continue

                resp.raise_for_status()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning("SEC network failure for %s: %s. Retrying in %.2fs", url, e, backoff)
                time.sleep(backoff)
                retries += 1
                backoff *= 1.5
                if retries > self.max_retries:
                    raise SECClientError(f"SEC EDGAR request timed out after {self.max_retries} retries: {url}") from e

        raise SECRateLimitError(f"Exceeded max retries ({self.max_retries}) accessing SEC URL: {url}")

    def load_ticker_mapping(self) -> dict[str, dict[str, Any]]:
        """Loads and indexes company_tickers.json from cache or SEC."""
        if self._ticker_map is not None:
            return self._ticker_map

        if "company_tickers" in self._cache:
            self._ticker_map = self._cache["company_tickers"]
            return self._ticker_map

        try:
            raw_data = self._request_with_retry(self.COMPANY_TICKERS_URL, is_json=True)
            ticker_map: dict[str, dict[str, Any]] = {}
            for item in raw_data.values():
                t = str(item.get("ticker", "")).upper()
                cik_str = str(item.get("cik_str", "")).zfill(10)
                title = str(item.get("title", ""))
                ticker_map[t] = {
                    "ticker": t,
                    "cik": cik_str,
                    "title": title,
                }
            self._ticker_map = ticker_map
            self._cache["company_tickers"] = ticker_map
            return self._ticker_map
        except Exception as e:
            logger.error("Failed to load company_tickers.json from SEC: %s", e)
            raise SECClientError(f"Could not load SEC ticker mapping: {e}") from e

    def resolve_issuer(self, identifier: str) -> dict[str, Any]:
        """Resolves a ticker symbol or company name to CIK and official title."""
        clean = identifier.strip().upper()

        # If already a 10-digit or integer CIK
        if clean.isdigit():
            cik_padded = clean.zfill(10)
            return {"cik": cik_padded, "ticker": None, "title": f"CIK {cik_padded}"}

        ticker_map = self.load_ticker_mapping()
        if clean in ticker_map:
            return ticker_map[clean]

        # Case-insensitive search by company title
        clean_lower = identifier.strip().lower()
        for item in ticker_map.values():
            if clean_lower in item["title"].lower():
                return item

        raise SECResourceNotFoundError(f"Unable to resolve issuer '{identifier}' to a valid SEC CIK.")

    def get_submissions(self, cik: str) -> dict[str, Any]:
        """Fetches filing history and entity metadata for a given CIK."""
        cik_padded = cik.strip().zfill(10)
        cache_key = f"submissions_{cik_padded}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{self.BASE_DATA_URL}/submissions/CIK{cik_padded}.json"
        data = self._request_with_retry(url, is_json=True)
        self._cache[cache_key] = data
        return data

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        """Fetches standardized XBRL company facts for a given CIK."""
        cik_padded = cik.strip().zfill(10)
        cache_key = f"company_facts_{cik_padded}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{self.BASE_DATA_URL}/api/xbrl/companyfacts/CIK{cik_padded}.json"
        data = self._request_with_retry(url, is_json=True)
        self._cache[cache_key] = data
        return data

    def fetch_filing_document(self, url: str) -> bytes:
        """Fetches raw filing document bytes."""
        cache_key = f"doc_{hashlib.sha256(url.encode()).hexdigest()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        content = self._request_with_retry(url, is_json=False)
        self._cache[cache_key] = content
        return content

    @staticmethod
    def construct_document_url(cik: str, accession_number: str, primary_document: str) -> str:
        """Constructs canonical SEC archive URL for a filing document."""
        clean_cik = str(int(cik.strip()))
        acc_no_hyphens = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/{acc_no_hyphens}/{primary_document}"
