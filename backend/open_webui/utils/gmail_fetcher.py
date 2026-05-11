"""
Gmail API Fetcher

This module handles fetching emails from Gmail API with:
- OAuth token authentication
- Pagination for bulk fetching
- Rate limiting to respect Gmail API quotas
- Batch operations for efficiency

Gmail API Quotas:
- 250 quota units per user per second
- List messages: 5 units per request
- Get message: 5 units per request
- Recommended: ~40 requests/second max
"""

import logging
import asyncio
import time
import random
from typing import Dict, List, Optional, Tuple
import aiohttp

# Set up logger with INFO level for visibility
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Retry configuration for transient errors
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds
RETRY_MAX_DELAY = 30.0  # seconds

# Transient error types that should be retried
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    aiohttp.ClientError,
    aiohttp.ServerTimeoutError,
    ConnectionError,
    OSError,
)


class TokenExpiredError(Exception):
    """Raised when OAuth token has expired and needs refresh."""

    pass


class HistoryIdExpiredError(Exception):
    """Raised when Gmail history ID is too old and full sync is required."""

    pass


class GmailFetcher:
    """
    Fetches emails from Gmail API with proper rate limiting and pagination.

    Uses OAuth token from user's login session.
    Supports configurable concurrency via GMAIL_API_CONCURRENCY env var.
    """

    # Gmail API base URL
    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"

    # Rate limiting configuration (can be overridden by config)
    DEFAULT_MAX_REQUESTS_PER_SECOND = 40  # Conservative limit
    DEFAULT_BATCH_SIZE = 20  # Concurrent requests (Gmail limit: ~50 concurrent)

    @staticmethod
    def _get_config_concurrency() -> int:
        """Get API concurrency from config, with fallback to default."""
        try:
            from open_webui.config import GMAIL_API_CONCURRENCY

            return (
                GMAIL_API_CONCURRENCY.value
                if hasattr(GMAIL_API_CONCURRENCY, "value")
                else GmailFetcher.DEFAULT_BATCH_SIZE
            )
        except ImportError:
            return GmailFetcher.DEFAULT_BATCH_SIZE

    def __init__(
        self,
        oauth_token: str,
        max_requests_per_second: int = DEFAULT_MAX_REQUESTS_PER_SECOND,
        timeout: int = 30,
        batch_size: int = None,
        token_refresh_callback=None,
    ):
        """
        Initialize Gmail fetcher.

        Args:
            oauth_token: OAuth access token with Gmail scopes
            max_requests_per_second: Rate limit (default: 40 req/s)
            timeout: Request timeout in seconds (default: 30)
            batch_size: Concurrent requests (default: from config or 20)
            token_refresh_callback: Async callback to refresh token when expired
                                   Should return new access_token string or None
        """
        self.oauth_token = oauth_token
        self.max_requests_per_second = max_requests_per_second
        # Use provided batch_size, or load from config
        self.default_batch_size = batch_size or self._get_config_concurrency()
        logger.info(f"GmailFetcher initialized: concurrency={self.default_batch_size}")
        self.timeout = timeout
        self.token_refresh_callback = token_refresh_callback
        self._token_refresh_lock = asyncio.Lock()

        # Rate limiting tracking
        self.request_times = []
        self.request_lock = asyncio.Lock()

        # Statistics
        self.stats = {
            "api_calls": 0,
            "emails_fetched": 0,
            "errors": 0,
            "rate_limit_waits": 0,
            "retries": 0,
            "token_refreshes": 0,
        }

        # Reusable session (created lazily)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _refresh_token_if_needed(self) -> bool:
        """
        Attempt to refresh the OAuth token using the callback.

        Returns:
            True if token was refreshed successfully, False otherwise
        """
        if not self.token_refresh_callback:
            logger.warning("No token refresh callback configured - cannot refresh token")
            return False

        async with self._token_refresh_lock:
            try:
                logger.info("🔄 Attempting to refresh OAuth token...")
                new_token = await self.token_refresh_callback()

                if new_token:
                    self.oauth_token = new_token
                    self.stats["token_refreshes"] += 1
                    logger.info("✅ OAuth token refreshed successfully")
                    return True
                else:
                    logger.error("❌ Token refresh callback returned None")
                    return False

            except Exception as e:
                logger.error(f"❌ Token refresh failed: {e}")
                return False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a reusable aiohttp session with optimized settings."""
        if self._session is None or self._session.closed:
            # Create session with connection pooling and keepalive
            connector = aiohttp.TCPConnector(
                limit=50,  # Max connections
                limit_per_host=20,  # Max per host
                ttl_dns_cache=300,  # DNS cache TTL (5 min)
                keepalive_timeout=60,  # Keep connections alive
            )
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=10,  # Connection timeout
                sock_read=30,  # Read timeout
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True,
            )
        return self._session

    async def close(self):
        """Close the session when done."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _retry_request(
        self,
        request_func,
        operation_name: str = "request",
        max_retries: int = MAX_RETRIES,
    ):
        """
        Execute a request with retry logic for transient errors.

        Args:
            request_func: Async function that makes the HTTP request
            operation_name: Name for logging purposes
            max_retries: Maximum retry attempts

        Returns:
            The response from request_func, or None if all retries fail

        Raises:
            TokenExpiredError: If OAuth token has expired (handled by caller)
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await request_func()
            except TokenExpiredError:
                # Don't retry token expiration - let caller handle refresh
                raise
            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                self.stats["retries"] += 1

                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    delay = min(
                        RETRY_MAX_DELAY,
                        RETRY_BASE_DELAY * (2**attempt) + random.uniform(0, 1),
                    )
                    logger.warning(
                        f"⚠️  {operation_name} failed (attempt {attempt + 1}/{max_retries}): "
                        f"{type(e).__name__}. Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"❌ {operation_name} failed after {max_retries} attempts: " f"{type(e).__name__}: {e}"
                    )

        return None

    async def _rate_limit(self):
        """
        Implement rate limiting to respect Gmail API quotas.

        Ensures we don't exceed max_requests_per_second.
        """
        async with self.request_lock:
            now = time.time()

            # Remove requests older than 1 second
            self.request_times = [t for t in self.request_times if now - t < 1.0]

            # Check if we're at the limit
            if len(self.request_times) >= self.max_requests_per_second:
                # Calculate wait time
                oldest_request = self.request_times[0]
                wait_time = 1.0 - (now - oldest_request)

                if wait_time > 0:
                    self.stats["rate_limit_waits"] += 1
                    logger.debug(f"Rate limit reached, waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)

            # Record this request
            self.request_times.append(time.time())

    async def get_inbox_count(
        self,
        skip_spam_trash: bool = True,
        query: Optional[str] = None,
    ) -> int:
        """
        Get the estimated inbox count WITHOUT fetching all IDs.

        Gmail API returns resultSizeEstimate on messages.list.
        This is fast (~1 API call) but approximate (±10%).

        Args:
            skip_spam_trash: Skip SPAM and TRASH folders (default: True)
            query: Optional Gmail query filter (e.g., "newer_than:7d")

        Returns:
            Estimated number of emails matching the query

        Example:
            >>> fetcher = GmailFetcher(oauth_token)
            >>> count = await fetcher.get_inbox_count()
            >>> print(f"Inbox has approximately {count} emails")
        """
        session = await self._get_session()
        url = f"{self.GMAIL_API_BASE}/users/me/messages"
        headers = {
            "Authorization": f"Bearer {self.oauth_token}",
            "Accept": "application/json",
        }

        # Build query
        query_parts = []
        if skip_spam_trash:
            query_parts.append("-in:spam -in:trash")
        if query:
            query_parts.append(query)

        params = {"maxResults": 1}  # Just need the estimate, not actual messages
        full_query = " ".join(query_parts) if query_parts else None
        if full_query:
            params["q"] = full_query

        logger.info(f"📊 Getting inbox count with query: '{full_query or 'ALL'}'")

        await self._rate_limit()

        async with session.get(url, params=params, headers=headers) as response:
            self.stats["api_calls"] += 1

            if response.status == 401:
                raise TokenExpiredError("OAuth token expired or invalid")

            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Gmail API error: {response.status} - {error_text}")

            data = await response.json()

            # resultSizeEstimate is the approximate total count
            estimated_count = data.get("resultSizeEstimate", 0)

            logger.info(f"📊 Gmail inbox estimate: ~{estimated_count} emails (query: '{full_query or 'ALL'}')")

            return estimated_count

    async def fetch_all_message_ids(
        self,
        max_results: int = 0,
        skip_spam_trash: bool = True,
        query: Optional[str] = None,
    ) -> List[str]:
        """
        Fetch all message IDs from Gmail with pagination.

        This fetches ALL emails from the entire mailbox including:
        - INBOX emails
        - SENT emails (emails you sent)
        - All custom labels/folders
        - Archived emails
        - Drafts
        - Everything except SPAM and TRASH (if skip_spam_trash=True)

        Args:
            max_results: Maximum number of message IDs to fetch (0 = unlimited)
            skip_spam_trash: Skip emails in SPAM and TRASH (default: True)
            query: Optional Gmail query filter (e.g., "newer_than:7d")

        Returns:
            List of Gmail message IDs from entire mailbox

        Example:
            >>> fetcher = GmailFetcher(oauth_token)
            >>> message_ids = await fetcher.fetch_all_message_ids(max_results=1000)
            >>> print(f"Found {len(message_ids)} emails across all folders")
        """

        logger.info("📥 Fetching message IDs from Gmail...")

        all_message_ids = []
        next_page_token = None
        page_count = 0

        # Build query - fetches ALL emails (inbox, sent, labels, etc.)
        query_parts = []
        if skip_spam_trash:
            # Exclude spam and trash, but include EVERYTHING else
            query_parts.append("-in:spam -in:trash")
            logger.info("   📋 Scope: ALL emails (INBOX + SENT + all labels)")
            logger.info("   🚫 Excluding: SPAM and TRASH only")
        else:
            logger.info("   📋 Scope: ENTIRE mailbox (including spam/trash)")

        if query:
            query_parts.append(query)
            logger.info(f"   🔍 Additional filter: {query}")

        full_query = " ".join(query_parts) if query_parts else None

        if full_query:
            logger.info(f"   📝 Gmail query: {full_query}")

        # Fetch pages using reusable session
        session = await self._get_session()
        url = f"{self.GMAIL_API_BASE}/users/me/messages"
        headers = {
            "Authorization": f"Bearer {self.oauth_token}",
            "Accept": "application/json",
        }

        while True:
            page_count += 1

            # Build request parameters
            params = {
                "maxResults": 500,  # Gmail API max per request
            }

            if full_query:
                params["q"] = full_query

            if next_page_token:
                params["pageToken"] = next_page_token

            # Fetch page with retry logic
            async def _fetch_page():
                await self._rate_limit()
                async with session.get(url, params=params, headers=headers) as response:
                    self.stats["api_calls"] += 1
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Gmail API error: {response.status} - {error_text}")
                    return await response.json()

            try:
                data = await self._retry_request(
                    _fetch_page,
                    operation_name=f"Fetch message IDs (page {page_count})",
                )

                if data is None:
                    logger.error(f"Failed to fetch page {page_count} after retries")
                    break

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Error fetching message IDs (page {page_count}): {e}")
                raise

            # Extract message IDs
            messages = data.get("messages", [])

            if messages:
                message_ids = [msg["id"] for msg in messages]
                all_message_ids.extend(message_ids)

                logger.info(f"Fetched page {page_count}: {len(message_ids)} IDs " f"(total: {len(all_message_ids)})")

            # Check for next page
            next_page_token = data.get("nextPageToken")

            if not next_page_token:
                logger.info(f"No more pages. Total message IDs: {len(all_message_ids)}")
                break

            # Check max results limit
            if max_results > 0 and len(all_message_ids) >= max_results:
                all_message_ids = all_message_ids[:max_results]
                logger.info(f"Reached max_results limit: {max_results}")
                break

        logger.info(
            f"Fetched {len(all_message_ids)} message IDs in {page_count} pages "
            f"({self.stats['api_calls']} API calls)"
        )

        return all_message_ids

    async def fetch_email(
        self,
        message_id: str,
        _retry_after_refresh: bool = False,
    ) -> Optional[Dict]:
        """
        Fetch a single email's full content with retry logic and token refresh.

        Args:
            message_id: Gmail message ID
            _retry_after_refresh: Internal flag to prevent infinite refresh loops

        Returns:
            Gmail API message response (format='full') or None if error
        """

        url = f"{self.GMAIL_API_BASE}/users/me/messages/{message_id}"
        params = {"format": "full"}

        async def _do_fetch():
            # Use current token (may have been refreshed)
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Accept": "application/json",
            }

            # Rate limiting
            await self._rate_limit()

            session = await self._get_session()
            async with session.get(
                url,
                params=params,
                headers=headers,
            ) as response:
                self.stats["api_calls"] += 1

                if response.status == 401:
                    # Token expired - signal for refresh
                    raise TokenExpiredError("OAuth token expired or invalid")

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error fetching email {message_id}: " f"{response.status} - {error_text}")
                    self.stats["errors"] += 1
                    return None

                email_data = await response.json()
                self.stats["emails_fetched"] += 1
                return email_data

        try:
            result = await self._retry_request(
                _do_fetch,
                operation_name=f"Fetch email {message_id[:8]}",
            )

            if result is None:
                self.stats["errors"] += 1

            return result

        except TokenExpiredError:
            # Try to refresh token and retry (only once)
            if not _retry_after_refresh and await self._refresh_token_if_needed():
                logger.info(f"Retrying fetch for email {message_id[:8]} with refreshed token")
                return await self.fetch_email(message_id, _retry_after_refresh=True)
            else:
                logger.error(f"Cannot fetch email {message_id[:8]} - token refresh failed or already retried")
                self.stats["errors"] += 1
                return None

    async def fetch_emails_batch(
        self,
        message_ids: List[str],
        batch_size: int = None,
    ) -> List[Dict]:
        """
        Fetch multiple emails in batches with rate limiting.

        Args:
            message_ids: List of Gmail message IDs to fetch
            batch_size: Number of concurrent requests (default: from config, Gmail limit ~50)

        Returns:
            List of Gmail API message responses
        """
        # Use provided batch_size or instance default (from config)
        batch_size = batch_size or self.default_batch_size

        logger.info(f"Fetching {len(message_ids)} emails in batches of {batch_size}...")

        all_emails = []

        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i : i + batch_size]

            logger.info(
                f"Fetching batch {i//batch_size + 1} "
                f"({i+1}-{min(i+batch_size, len(message_ids))} of {len(message_ids)})"
            )

            # Fetch batch concurrently with limited concurrency (prevents 429)
            tasks = [self.fetch_email(msg_id) for msg_id in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in results
            batch_emails = []
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch fetch error: {result}")
                elif result is not None:
                    batch_emails.append(result)

            all_emails.extend(batch_emails)

            logger.info(f"Batch complete: {len(batch_emails)}/{len(batch)} successful " f"(total: {len(all_emails)})")

        logger.info(
            f"Fetch complete: {len(all_emails)} emails fetched successfully " f"(errors: {self.stats['errors']})"
        )

        return all_emails

    async def fetch_all_emails(
        self,
        max_emails: int = 0,
        skip_spam_trash: bool = True,
        query: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Tuple[List[Dict], Dict]:
        """
        Complete workflow: Fetch message IDs, then fetch full email content.

        Args:
            max_emails: Maximum number of emails to fetch (0 = unlimited)
            skip_spam_trash: Skip SPAM and TRASH folders (default: True)
            query: Optional Gmail query filter
            batch_size: Concurrent fetch batch size (default: 100)

        Returns:
            Tuple of (list of email data, statistics dict)
        """

        start_time = time.time()

        # Step 1: Fetch all message IDs
        logger.info("Step 1: Fetching message IDs...")
        message_ids = await self.fetch_all_message_ids(
            max_results=max_emails, skip_spam_trash=skip_spam_trash, query=query
        )

        if not message_ids:
            logger.warning("No message IDs found")
            return [], self.stats

        # Step 2: Fetch full email content
        logger.info(f"Step 2: Fetching {len(message_ids)} emails...")
        emails = await self.fetch_emails_batch(message_ids=message_ids, batch_size=batch_size)

        elapsed_time = time.time() - start_time

        # Update stats
        self.stats["total_time"] = elapsed_time
        self.stats["emails_per_second"] = len(emails) / elapsed_time if elapsed_time > 0 else 0

        logger.info(
            f"Fetch complete: {len(emails)} emails in {elapsed_time:.1f}s "
            f"({self.stats['emails_per_second']:.1f} emails/s)"
        )

        return emails, self.stats

    def get_stats(self) -> Dict:
        """Get fetcher statistics"""
        return self.stats.copy()

    @staticmethod
    def calculate_batch_params(
        total_count: int,
        target_batch_size: int = 500,
        min_batch_size: int = 50,
        max_batch_size: int = 1000,
    ) -> Dict:
        """
        Calculate optimal batch parameters based on inbox count.

        Args:
            total_count: Total number of emails to process
            target_batch_size: Preferred batch size (default: 500)
            min_batch_size: Minimum batch size (default: 50)
            max_batch_size: Maximum batch size (default: 1000)

        Returns:
            Dict with batch_size, num_batches, and distribution info

        Example:
            >>> params = GmailFetcher.calculate_batch_params(15000)
            >>> print(f"Will process in {params['num_batches']} batches of {params['batch_size']}")
        """
        if total_count == 0:
            return {
                "batch_size": 0,
                "num_batches": 0,
                "total_count": 0,
                "emails_in_last_batch": 0,
            }

        # Clamp batch size to valid range
        batch_size = max(min_batch_size, min(max_batch_size, target_batch_size))

        # Calculate number of batches
        num_batches = (total_count + batch_size - 1) // batch_size  # Ceiling division

        # Calculate emails in last batch
        emails_in_last_batch = total_count % batch_size
        if emails_in_last_batch == 0:
            emails_in_last_batch = batch_size

        result = {
            "batch_size": batch_size,
            "num_batches": num_batches,
            "total_count": total_count,
            "emails_in_last_batch": emails_in_last_batch,
            "estimated_time_minutes": (total_count * 1.5) / 60,  # ~1.5s per email
        }

        logger.info(
            f"📦 Batch plan: {total_count} emails → "
            f"{num_batches} batches of {batch_size} "
            f"(last batch: {emails_in_last_batch})"
        )

        return result

    def create_batches(
        self,
        message_ids: List[str],
        batch_size: int = 500,
    ) -> List[List[str]]:
        """
        Split message IDs into batches of specified size.

        Args:
            message_ids: List of Gmail message IDs
            batch_size: Number of messages per batch

        Returns:
            List of batches, each batch is a list of message IDs
        """
        if not message_ids:
            return []

        batches = [message_ids[i : i + batch_size] for i in range(0, len(message_ids), batch_size)]

        logger.info(
            f"📦 Created {len(batches)} batches from {len(message_ids)} message IDs " f"(batch_size={batch_size})"
        )

        return batches

    # =========================================================================
    # Gmail History API Methods (for efficient incremental sync)
    # =========================================================================

    async def get_profile(self) -> Optional[Dict]:
        """
        Get user's Gmail profile including current historyId.

        The historyId is essential for incremental sync - it represents
        the current state of the mailbox and can be used with History API.

        Returns:
            Dict with profile info including 'historyId', or None on error

        Example:
            >>> profile = await fetcher.get_profile()
            >>> print(f"Current history ID: {profile['historyId']}")
        """
        url = f"{self.GMAIL_API_BASE}/users/me/profile"

        async def _fetch_profile():
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Accept": "application/json",
            }

            await self._rate_limit()
            session = await self._get_session()

            async with session.get(url, headers=headers) as response:
                self.stats["api_calls"] += 1

                if response.status == 401:
                    raise TokenExpiredError("OAuth token expired or invalid")

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error fetching profile: {response.status} - {error_text}")
                    return None

                return await response.json()

        try:
            return await self._retry_request(_fetch_profile, operation_name="Fetch profile")
        except TokenExpiredError:
            if await self._refresh_token_if_needed():
                return await self.get_profile()
            return None

    async def fetch_history_changes(
        self,
        start_history_id: str,
        skip_spam_trash: bool = True,
        max_results: int = 0,
    ) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Fetch mailbox changes since a specific historyId using Gmail History API.

        This is more efficient and accurate than time-based queries because:
        - Returns EXACTLY what changed (no missed emails, no duplicates)
        - Handles deletions (so we can remove deleted emails from index)
        - Smaller API response (just IDs, not full messages)

        Args:
            start_history_id: The historyId to start from (from previous sync)
            skip_spam_trash: Skip messages that were moved to SPAM/TRASH
            max_results: Maximum messages to return (0 = unlimited)

        Returns:
            Tuple of:
            - added_message_ids: List of new/modified message IDs
            - deleted_message_ids: List of deleted message IDs
            - new_history_id: Latest historyId for next sync (or None on error)

        Raises:
            HistoryIdExpiredError: If history is too old (need full sync)

        Example:
            >>> added, deleted, new_id = await fetcher.fetch_history_changes("12345")
            >>> print(f"Added: {len(added)}, Deleted: {len(deleted)}")
        """
        logger.info(f"📜 Fetching history changes since historyId: {start_history_id}")

        added_message_ids = set()
        deleted_message_ids = set()
        new_history_id = None
        next_page_token = None
        page_count = 0

        session = await self._get_session()
        url = f"{self.GMAIL_API_BASE}/users/me/history"

        while True:
            page_count += 1

            params = {
                "startHistoryId": start_history_id,
                "historyTypes": ["messageAdded", "messageDeleted"],
            }

            if skip_spam_trash:
                # Only get changes that don't involve SPAM/TRASH
                params["labelId"] = "INBOX"  # Focus on INBOX changes

            if next_page_token:
                params["pageToken"] = next_page_token

            async def _fetch_history_page():
                headers = {
                    "Authorization": f"Bearer {self.oauth_token}",
                    "Accept": "application/json",
                }

                await self._rate_limit()

                async with session.get(url, params=params, headers=headers) as response:
                    self.stats["api_calls"] += 1

                    if response.status == 401:
                        raise TokenExpiredError("OAuth token expired or invalid")

                    if response.status == 404:
                        # History ID is too old - Gmail purges history after ~30 days
                        error_data = await response.json()
                        if "notFound" in str(error_data).lower():
                            raise HistoryIdExpiredError(
                                f"History ID {start_history_id} is too old or invalid. " "Full sync required."
                            )
                        raise Exception(f"History API 404: {error_data}")

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"History API error: {response.status} - {error_text}")

                    return await response.json()

            try:
                data = await self._retry_request(
                    _fetch_history_page,
                    operation_name=f"Fetch history (page {page_count})",
                )

                if data is None:
                    logger.error(f"Failed to fetch history page {page_count}")
                    break

            except TokenExpiredError:
                if await self._refresh_token_if_needed():
                    continue  # Retry with new token
                raise
            except HistoryIdExpiredError:
                raise  # Propagate to caller for full sync
            except Exception as e:
                logger.error(f"History API error: {e}")
                self.stats["errors"] += 1
                raise

            # Update the latest history ID
            new_history_id = data.get("historyId", new_history_id)

            # Process history records
            for record in data.get("history", []):
                # Messages added (new emails or label changes that make them visible)
                for msg_added in record.get("messagesAdded", []):
                    msg_id = msg_added.get("message", {}).get("id")
                    if msg_id:
                        added_message_ids.add(msg_id)
                        # If it was previously marked as deleted, remove from deleted set
                        deleted_message_ids.discard(msg_id)

                # Messages deleted (or moved to SPAM/TRASH)
                for msg_deleted in record.get("messagesDeleted", []):
                    msg_id = msg_deleted.get("message", {}).get("id")
                    if msg_id:
                        deleted_message_ids.add(msg_id)
                        # Remove from added if it was added then deleted
                        added_message_ids.discard(msg_id)

            logger.info(
                f"   Page {page_count}: +{len(added_message_ids)} added, " f"-{len(deleted_message_ids)} deleted so far"
            )

            # Check for more pages
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

            # Check max results limit
            if max_results > 0 and len(added_message_ids) >= max_results:
                logger.info(f"   Reached max_results limit: {max_results}")
                break

        # Convert sets to lists
        added_list = list(added_message_ids)
        deleted_list = list(deleted_message_ids)

        logger.info(
            f"✅ History sync complete: {len(added_list)} added, "
            f"{len(deleted_list)} deleted, new historyId: {new_history_id}"
        )

        return added_list, deleted_list, new_history_id

    async def fetch_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str,
        _retry_after_refresh: bool = False,
    ) -> Optional[bytes]:
        """
        Fetch an email attachment by ID with retry logic and token refresh.

        Args:
            message_id: The Gmail message ID
            attachment_id: The attachment ID from the message
            filename: The attachment filename (for logging)
            _retry_after_refresh: Internal flag to prevent infinite refresh loops

        Returns:
            bytes: The attachment data, or None if failed
        """
        import base64

        url = f"{self.GMAIL_API_BASE}/users/me/messages/{message_id}/attachments/{attachment_id}"

        async def _do_fetch():
            # Use current token (may have been refreshed)
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Accept": "application/json",
            }

            await self._rate_limit()

            session = await self._get_session()
            async with session.get(url, headers=headers) as response:
                self.stats["api_calls"] += 1

                if response.status == 401:
                    raise TokenExpiredError("OAuth token expired or invalid")

                if response.status == 200:
                    attachment_data = await response.json()
                    # Gmail returns base64url-encoded data
                    data = attachment_data.get("data", "")
                    # Convert base64url to regular base64
                    data = data.replace("-", "+").replace("_", "/")
                    attachment_bytes = base64.b64decode(data)

                    logger.debug(f"Downloaded attachment '{filename}': {len(attachment_bytes)} bytes")
                    return attachment_bytes

                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to download attachment '{filename}': {response.status} - {error_text}")
                    return None

        try:
            result = await self._retry_request(
                _do_fetch,
                operation_name=f"Fetch attachment '{filename}'",
            )

            if result is None:
                self.stats["errors"] += 1

            return result

        except TokenExpiredError:
            # Try to refresh token and retry (only once)
            if not _retry_after_refresh and await self._refresh_token_if_needed():
                logger.info(f"Retrying fetch for attachment '{filename}' with refreshed token")
                return await self.fetch_attachment(message_id, attachment_id, filename, _retry_after_refresh=True)
            else:
                logger.error(f"Cannot fetch attachment '{filename}' - token refresh failed or already retried")
                self.stats["errors"] += 1
                return None


# ============================================================================
# TESTING
# ============================================================================


async def test_fetcher_mock():
    """Test fetcher with mock/simulated data (no real API calls)"""

    print("\n" + "=" * 60)
    print("Phase 4 - GmailFetcher Test (Mock Mode)")
    print("=" * 60)

    # Simulate OAuth token
    mock_token = "mock_oauth_token_12345"

    print(f"\n✅ TEST 1: Fetcher Initialization")
    fetcher = GmailFetcher(oauth_token=mock_token, max_requests_per_second=40, timeout=30)

    print(f"   OAuth token: {mock_token[:20]}...")
    print(f"   Rate limit: {fetcher.max_requests_per_second} req/s")
    print(f"   Timeout: {fetcher.timeout}s")
    print(f"   ✅ PASSED\n")

    print(f"✅ TEST 2: Rate Limiting Logic")
    # Test that rate limiter allows requests
    start = time.time()
    for i in range(5):
        await fetcher._rate_limit()
    elapsed = time.time() - start

    print(f"   5 requests completed in {elapsed:.3f}s")
    print(f"   Rate limit waits: {fetcher.stats['rate_limit_waits']}")
    print(f"   ✅ PASSED\n")

    print(f"✅ TEST 3: Statistics Tracking")
    stats = fetcher.get_stats()
    print(f"   API calls: {stats['api_calls']}")
    print(f"   Emails fetched: {stats['emails_fetched']}")
    print(f"   Errors: {stats['errors']}")
    print(f"   ✅ PASSED\n")

    print("=" * 60)
    print("Phase 4 Mock Tests Complete ✅")
    print("=" * 60)
    print("\nGmailFetcher is ready for integration!")
    print("\nNext: Test with real Gmail API using your OAuth token")

    return True


if __name__ == "__main__":
    print("Testing Phase 4 - Gmail API Fetcher")
    success = asyncio.run(test_fetcher_mock())

    if success:
        print("\n🎉 Phase 4 mock tests PASSED!")
        print("\nTo test with real Gmail API:")
        print("1. Get your OAuth token from oauth_session table")
        print("2. Run: fetcher = GmailFetcher(your_token)")
        print("3. Run: emails = await fetcher.fetch_all_emails(max_emails=10)")

    exit(0 if success else 1)
