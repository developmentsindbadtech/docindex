"""Email service for Microsoft Graph API integration to fetch email attachments."""

import asyncio
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import httpx
from msal import ConfidentialClientApplication
from app.config import settings
from app.utils.logger import setup_logger
from app.models.index_models import FileMetadata

logger = setup_logger(__name__)


class EmailService:
    """Service for interacting with Outlook/Exchange via Microsoft Graph API to fetch email attachments."""

    def __init__(self):
        """Initialize the email service."""
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self.token: Optional[str] = None
        self.token_expires_at: float = 0
        self._client_app = ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=settings.azure_client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        )
    
    def clear_token_cache(self):
        """Clear the cached token to force a fresh token acquisition.
        
        Use this if permissions were just added/granted and you need a new token.
        """
        self.token = None
        self.token_expires_at = 0
        logger.info("Token cache cleared - next request will acquire a fresh token")

    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Access token string

        Raises:
            Exception: If token acquisition fails
        """
        import time
        
        # Check if token is still valid (with 5 minute buffer)
        if self.token and time.time() < self.token_expires_at - 300:
            return self.token

        logger.info("Acquiring new access token for email service")
        result = self._client_app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            error_code = result.get("error_codes", [])
            if "AADSTS70011" in str(error_code) or "invalid_scope" in error.lower():
                logger.error("⚠️  Token acquisition failed - permissions may not be properly granted")
                logger.error(f"   Error: {error}")
                logger.error("   Please verify User.Read.All and Mail.Read are granted in Azure Portal")
            raise Exception(f"Failed to acquire token: {error}")

        self.token = result["access_token"]
        expires_in = result.get("expires_in", 3600)
        self.token_expires_at = time.time() + expires_in

        logger.info("Access token acquired successfully for email service")
        return self.token

    async def _make_request(
        self,
        method: str,
        url: str,
        retries: int = 3,
        timeout: float = 30.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            retries: Number of retry attempts
            timeout: Request timeout in seconds (default: 30.0)
            **kwargs: Additional arguments for httpx request

        Returns:
            Response JSON data

        Raises:
            Exception: If request fails after retries
        """
        token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            **kwargs.pop("headers", {}),
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(retries):
                try:
                    try:
                        response = await asyncio.wait_for(
                            client.request(method, url, headers=headers, **kwargs),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        if attempt < retries - 1:
                            wait_time = 2 ** attempt
                            logger.warning(f"Request timeout. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{retries})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Request timeout after {retries} attempts")
                            raise

                    # Handle rate limiting (429)
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue

                    # Handle server errors (503, 502, 500)
                    if response.status_code in [503, 502, 500]:
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"Server error {response.status_code}. Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return response.json()

                except httpx.HTTPStatusError as e:
                    if attempt == retries - 1:
                        logger.error(f"Request failed after {retries} attempts: {e}")
                        raise
                    wait_time = 2 ** attempt
                    logger.warning(f"HTTP error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

                except asyncio.TimeoutError:
                    if attempt == retries - 1:
                        logger.error(f"Request timeout after {retries} attempts")
                        raise
                    wait_time = 2 ** attempt
                    logger.warning(f"Timeout. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"Request failed: {e}")
                        raise
                    wait_time = 2 ** attempt
                    logger.warning(f"Error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

        raise Exception("Request failed after all retries")

    async def _paginate_request(
        self, url: str, params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Paginate through Graph API results.

        Args:
            url: Initial request URL
            params: Query parameters

        Returns:
            List of all items from all pages
        """
        all_items = []
        params = params or {}
        params["$top"] = 999  # Maximum items per page

        last_error = None
        while url:
            try:
                response = await self._make_request("GET", url, params=params)
                items = response.get("value", [])
                all_items.extend(items)

                # Check for next page
                url = response.get("@odata.nextLink")
                if url:
                    params = {}  # Next link already has params
            except Exception as e:
                last_error = e
                logger.warning(f"Error paginating request: {e}")
                break

        # Re-raise the last error if we got one and no items were collected
        if last_error and len(all_items) == 0:
            raise last_error

        return all_items

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users in the organization.

        Returns:
            List of user metadata
            
        Raises:
            Exception: If User.Read.All permission is not granted (403 Forbidden)
        """
        logger.info("Fetching all users for email indexing")
        url = f"{self.graph_endpoint}/users"
        try:
            users = await self._paginate_request(url)
            logger.info(f"Found {len(users)} users")
            return users
        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "Forbidden" in error_str:
                logger.error("⚠️  PERMISSION ERROR: User.Read.All application permission may not be granted!")
                logger.error("   The application cannot list users without User.Read.All permission")
                logger.error("   Please check SETUP_EMAIL_PERMISSIONS.md and ensure User.Read.All (Application) permission is granted")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a specific user by email address.

        Args:
            email: User email address or UPN

        Returns:
            User metadata or None if not found
        """
        try:
            # Try to get user by UPN/email
            url = f"{self.graph_endpoint}/users/{email}"
            user = await self._make_request("GET", url)
            return user
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "Not Found" in error_str:
                logger.debug(f"User {email} not found")
                return None
            # For other errors, log and return None
            logger.warning(f"Error fetching user {email}: {error_str}")
            return None

    async def get_emails_with_attachments(
        self,
        user_id: str,
        user_email: str,
        progress_callback: Optional[Callable[[], None]] = None,
        cancelled_flag: Optional[Any] = None,
        last_index_time: Optional[datetime] = None,
    ) -> List[FileMetadata]:
        """Get all emails with attachments for a user.

        Args:
            user_id: User ID or principal name
            user_email: User email address (for display)
            progress_callback: Optional callback for progress updates
            cancelled_flag: Optional flag object to check for cancellation
            last_index_time: Optional datetime to only fetch items modified after this time

        Returns:
            List of FileMetadata objects for attachments
        """
        all_attachments = []
        
        try:
            # Filter for emails with attachments
            # Only fetch emails that have attachments
            filter_query = "hasAttachments eq true"
            if last_index_time:
                # Add date filter for incremental updates
                date_str = last_index_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                filter_query += f" and lastModifiedDateTime ge {date_str}"
            
            url = f"{self.graph_endpoint}/users/{user_id}/messages"
            params = {
                "$filter": filter_query,
                "$select": "id,subject,hasAttachments,receivedDateTime,lastModifiedDateTime,from",
                "$top": 100,  # Process in batches
            }
            
            logger.info(f"Fetching emails with attachments for user: {user_email}")
            
            try:
                emails = await self._paginate_request(url, params)
                logger.info(f"Found {len(emails)} emails with attachments for {user_email}")
            except Exception as api_error:
                error_str = str(api_error)
                # 404 means user doesn't have a mailbox (guest user, service account, or mailbox disabled)
                if "404" in error_str or "Not Found" in error_str:
                    logger.debug(f"User {user_email} does not have a mailbox (404) - skipping")
                    # Return empty list - this user has no mailbox, which is normal
                    return []
                elif "403" in error_str or "Insufficient privileges" in error_str or "AADSTS" in error_str:
                    logger.error(f"⚠️  PERMISSION ERROR for {user_email}: Mail.Read application permission may not be granted!")
                    logger.error(f"   Error: {error_str}")
                    logger.error("   Please check SETUP_EMAIL_PERMISSIONS.md and ensure Mail.Read (Application) permission is granted")
                    # Re-raise permission errors
                    raise
                else:
                    # Other errors - log and skip this user
                    logger.warning(f"Error fetching emails for {user_email}: {error_str} - skipping user")
                    return []
            
            # Process each email to get attachments
            for idx, email in enumerate(emails):
                # Check cancellation
                if cancelled_flag and hasattr(cancelled_flag, '_cancelled') and cancelled_flag._cancelled:
                    logger.info("Email attachment collection cancelled")
                    break
                
                if progress_callback:
                    try:
                        progress_callback()
                    except TypeError:
                        pass
                
                email_id = email.get("id")
                if not email_id:
                    continue
                
                try:
                    # Get attachments for this email
                    attachments_url = f"{self.graph_endpoint}/users/{user_id}/messages/{email_id}/attachments"
                    
                    # Add timeout for attachment fetching
                    try:
                        attachments = await asyncio.wait_for(
                            self._paginate_request(attachments_url),
                            timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout fetching attachments for email {email.get('subject', 'Unknown')} - skipping")
                        continue
                    except Exception as e:
                        logger.warning(f"Error fetching attachments for email {email.get('subject', 'Unknown')}: {e} - continuing")
                        continue
                    
                    # Process each attachment
                    for attachment in attachments:
                        try:
                            attachment_id = attachment.get("id")
                            attachment_name = attachment.get("name", "Unknown")
                            attachment_size = attachment.get("size", 0)
                            
                            # Get file extension
                            file_type = ""
                            if "." in attachment_name:
                                file_type = attachment_name.split(".")[-1].upper()
                            
                            # Get attachment content URL (for viewing/downloading)
                            # Note: We need to make a separate request to get the content URL
                            # For now, we'll construct a link to view the email in Outlook
                            email_web_url = f"https://outlook.office.com/mail/id/{email_id}"
                            
                            # Parse dates
                            received_date = self._parse_datetime(email.get("receivedDateTime"))
                            last_modified = self._parse_datetime(email.get("lastModifiedDateTime"))
                            
                            # Get sender info
                            from_info = email.get("from", {})
                            sender_name = from_info.get("emailAddress", {}).get("name", "Unknown")
                            
                            # Create FileMetadata for attachment
                            # Use email_id + attachment_id as unique ID
                            unique_id = f"email_{user_id}_{email_id}_{attachment_id}"
                            
                            attachment_meta = FileMetadata(
                                id=unique_id,
                                name=attachment_name,
                                path=f"Email: {email.get('subject', 'No Subject')}",
                                file_type=file_type,
                                web_url=email_web_url,  # Link to email in Outlook
                                size=attachment_size,
                                created_date_time=received_date,
                                last_modified_date_time=last_modified or received_date,
                                created_by=sender_name,
                                last_modified_by=sender_name,
                                mime_type=attachment.get("contentType"),
                                download_url=None,  # We don't download, just index metadata
                            )
                            
                            all_attachments.append(attachment_meta)
                            
                        except Exception as e:
                            logger.warning(f"Error processing attachment {attachment.get('name', 'Unknown')}: {e} - continuing")
                            continue
                    
                    # Log progress every 50 emails
                    if (idx + 1) % 50 == 0:
                        logger.info(f"Processed {idx + 1}/{len(emails)} emails for {user_email}, found {len(all_attachments)} attachments so far")
                    
                    # Small delay to prevent API throttling
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error processing email {email.get('subject', 'Unknown')}: {e} - continuing")
                    continue
            
            logger.info(f"Completed email attachment collection for {user_email}: {len(all_attachments)} attachments found")
            
        except Exception as e:
            error_str = str(e)
            # 404 errors are expected for users without mailboxes - don't log as error
            if "404" in error_str or "Not Found" in error_str:
                logger.debug(f"User {user_email} does not have a mailbox - skipping")
            else:
                logger.error(f"Error fetching emails for user {user_email}: {e}", exc_info=True)
        
        return all_attachments

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string.

        Args:
            dt_str: ISO datetime string

        Returns:
            datetime object or None
        """
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

