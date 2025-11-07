"""SharePoint service for Microsoft Graph API integration."""

import asyncio
import time
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import httpx
from msal import ConfidentialClientApplication
from app.config import settings
from app.utils.logger import setup_logger
from app.models.index_models import FileMetadata, FolderMetadata, FolderNode, SiteIndex

logger = setup_logger(__name__)


class SharePointService:
    """Service for interacting with SharePoint via Microsoft Graph API."""

    def __init__(self):
        """Initialize the SharePoint service."""
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self.token: Optional[str] = None
        self.token_expires_at: float = 0
        self._client_app = ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=settings.azure_client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        )

    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Access token string

        Raises:
            Exception: If token acquisition fails
        """
        # Check if token is still valid (with 5 minute buffer)
        if self.token and time.time() < self.token_expires_at - 300:
            return self.token

        logger.info("Acquiring new access token")
        result = self._client_app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise Exception(f"Failed to acquire token: {error}")

        self.token = result["access_token"]
        expires_in = result.get("expires_in", 3600)
        self.token_expires_at = time.time() + expires_in

        logger.info("Access token acquired successfully")
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
                    # Add timeout wrapper for individual requests
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

        while url:
            response = await self._make_request("GET", url, params=params)
            items = response.get("value", [])
            all_items.extend(items)

            # Check for next page
            url = response.get("@odata.nextLink")
            if url:
                params = {}  # Next link already has params

        return all_items

    async def get_all_sites(self) -> List[Dict[str, Any]]:
        """Get all SharePoint sites accessible to the app.

        Returns:
            List of site metadata
        """
        logger.info("Fetching all SharePoint sites")

        # If specific site IDs are provided, use them
        if settings.sharepoint_site_ids:
            site_ids = [s.strip() for s in settings.sharepoint_site_ids.split(",") if s.strip()]
            sites = []
            for site_id in site_ids:
                try:
                    url = f"{self.graph_endpoint}/sites/{site_id}"
                    site = await self._make_request("GET", url)
                    sites.append(site)
                except Exception as e:
                    logger.warning(f"Failed to fetch site {site_id}: {e}")
            return sites

        # Otherwise, discover all sites
        url = f"{self.graph_endpoint}/sites"
        sites = await self._paginate_request(url)
        logger.info(f"Found {len(sites)} SharePoint sites")
        return sites
    
    async def get_site_owner(self, site_id: str, site_data: Optional[Dict[str, Any]] = None, site_name: Optional[str] = None) -> Optional[str]:
        """Get the owner email address for a SharePoint site.

        Args:
            site_id: SharePoint site ID
            site_data: Optional site metadata (to avoid extra API call)
            site_name: Optional site name (used to match with users)

        Returns:
            Owner email address or None if not found
        """
        # First, try to get owner from site metadata if provided
        if site_data:
            # Check for createdBy or lastModifiedBy
            created_by = site_data.get("createdBy", {})
            if isinstance(created_by, dict):
                user_info = created_by.get("user", {})
                email = user_info.get("email") or user_info.get("displayName")
                if email and "@" in email:
                    return email
            
            # Check for owner in site properties
            owner = site_data.get("owner", {})
            if isinstance(owner, dict):
                email = owner.get("email") or owner.get("userPrincipalName")
                if email and "@" in email:
                    return email
        
        # If we have a site name, we'll try to match it with users in the directory
        # This will be done in the background_tasks where we have access to email_service
        # For now, just return None - the matching will happen in background_tasks
        logger.debug(f"Could not extract owner from site metadata for site {site_id}")
        return None

    async def get_document_libraries(self, site_id: str) -> List[Dict[str, Any]]:
        """Get all document libraries for a site.

        Args:
            site_id: SharePoint site ID

        Returns:
            List of document library metadata
        """
        logger.debug(f"Fetching document libraries for site {site_id}")
        url = f"{self.graph_endpoint}/sites/{site_id}/drives"
        libraries = await self._paginate_request(url)
        return libraries

    async def get_all_files_flat(
        self, drive_id: str, progress_callback: Optional[Callable[[], None]] = None, cancelled_flag: Optional[Any] = None,
        last_index_time: Optional[datetime] = None, existing_files_map: Optional[Dict[str, FileMetadata]] = None
    ) -> List[FileMetadata]:
        """Get all files from a drive as a flat list (simpler and faster).

        Args:
            drive_id: SharePoint drive (library) ID
            progress_callback: Optional callback for progress updates
            cancelled_flag: Optional flag object to check for cancellation
            last_index_time: Optional datetime to only fetch items modified after this time
            existing_files_map: Optional dict of existing files by ID for incremental updates

        Returns:
            List of FileMetadata objects
        """
        all_files = []
        folders_to_process = [("root", "")]
        existing_files_map = existing_files_map or {}
        skipped_count = 0
        
        logger.info(f"Starting flat file collection for drive {drive_id}")
        
        while folders_to_process:
            # Check cancellation if flag provided
            if cancelled_flag and hasattr(cancelled_flag, '_cancelled') and cancelled_flag._cancelled:
                logger.info("File collection cancelled")
                break
                
            folder_id, folder_path = folders_to_process.pop(0)
            
            try:
                if progress_callback:
                    try:
                        progress_callback(folder_path)
                    except TypeError:
                        progress_callback()
                
                url = f"{self.graph_endpoint}/drives/{drive_id}/items/{folder_id}/children"
                
                # Add timeout for folder content fetching
                try:
                    items = await asyncio.wait_for(
                        self._paginate_request(url),
                        timeout=120.0  # 2 minutes max per folder
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout fetching folder {folder_path} - skipping")
                    continue
                except Exception as e:
                    logger.warning(f"Error fetching folder {folder_path}: {e} - continuing")
                    continue
                
                # Process files - fetch name, webUrl, type, dates, and owner
                for item in items:
                    if "file" in item:
                        try:
                            # Add timeout for individual file processing
                            file_id = item.get("id")
                            file_name = item.get("name", "Unknown")
                            file_size = item.get("size", 0)
                            
                            # Log large files but continue processing
                            if file_size and file_size > 100 * 1024 * 1024:  # > 100MB
                                logger.info(f"Processing large file: {file_name} ({file_size / (1024*1024):.1f} MB)")
                            
                            file_modified = self._parse_datetime(item.get("lastModifiedDateTime"))
                            
                            # Skip if incremental update and file hasn't changed
                            if last_index_time and file_id in existing_files_map:
                                existing_file = existing_files_map[file_id]
                                if existing_file.last_modified_date_time and file_modified:
                                    if file_modified <= existing_file.last_modified_date_time:
                                        # File hasn't changed, keep existing
                                        all_files.append(existing_file)
                                        skipped_count += 1
                                        continue
                            
                            # Get file extension for type
                            file_type = ""
                            if "." in file_name:
                                file_type = file_name.split(".")[-1].upper()
                            
                            # Process file metadata with timeout protection
                            try:
                                file_meta = FileMetadata(
                                    id=file_id,
                                    name=file_name,
                                    web_url=item.get("webUrl"),
                                    size=None,  # Not needed for table
                                    created_date_time=self._parse_datetime(item.get("createdDateTime")),
                                    last_modified_date_time=file_modified,
                                    created_by=item.get("createdBy", {}).get("user", {}).get("displayName"),
                                    last_modified_by=item.get("lastModifiedBy", {}).get("user", {}).get("displayName"),
                                    mime_type=item.get("file", {}).get("mimeType"),
                                    download_url=None,
                                )
                                # Store path and type with file
                                file_meta.path = folder_path
                                file_meta.file_type = file_type
                                all_files.append(file_meta)
                                
                                if progress_callback:
                                    try:
                                        progress_callback(folder_path)
                                    except TypeError:
                                        progress_callback()
                            except Exception as file_error:
                                logger.warning(f"Error creating metadata for file {file_name}: {file_error} - skipping file")
                                continue
                                
                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout processing file {item.get('name', 'Unknown')} - skipping")
                            continue
                        except Exception as e:
                            logger.warning(f"Error processing file {item.get('name', 'Unknown')}: {e} - continuing")
                            continue
                    
                    # Add folders to processing queue
                    elif "folder" in item:
                        folder_name = item.get("name", "Unknown")
                        new_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
                        folders_to_process.append((item.get("id"), new_path))
                
                # Log progress every 100 files
                if len(all_files) % 100 == 0 and len(all_files) > 0:
                    logger.info(f"Collected {len(all_files)} files so far, {len(folders_to_process)} folders remaining")
                
                # Add small delay to prevent overwhelming the API
                await asyncio.sleep(0.1)
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout processing folder {folder_path} - skipping")
                continue
            except Exception as e:
                logger.warning(f"Error processing folder {folder_path}: {e} - continuing with next folder")
                continue
        
        if skipped_count > 0:
            logger.info(f"Completed flat file collection: {len(all_files)} files found ({skipped_count} skipped - already indexed)")
        else:
            logger.info(f"Completed flat file collection: {len(all_files)} files found")
        return all_files

    async def get_folder_contents(
        self, drive_id: str, folder_id: str = "root"
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get files and subfolders in a folder.

        Args:
            drive_id: SharePoint drive (library) ID
            folder_id: Folder ID (default: "root")

        Returns:
            Tuple of (files, folders) lists
        """
        url = f"{self.graph_endpoint}/drives/{drive_id}/items/{folder_id}/children"
        items = await self._paginate_request(url)

        files = [item for item in items if "file" in item]
        folders = [item for item in items if "folder" in item]

        return files, folders

    async def build_folder_tree(
        self,
        drive_id: str,
        folder_id: str = "root",
        path: str = "",
        progress_callback: Optional[Callable[[], None]] = None,
        last_index_time: Optional[datetime] = None,
        existing_node: Optional[FolderNode] = None,
        max_depth: int = 50,
        current_depth: int = 0,
    ) -> FolderNode:
        """Recursively build folder tree structure.

        Args:
            drive_id: SharePoint drive ID
            folder_id: Current folder ID
            path: Current folder path
            progress_callback: Optional callback for progress updates
            last_index_time: Optional datetime to only fetch items modified after this time
            existing_node: Optional existing FolderNode to merge updates into
            max_depth: Maximum recursion depth to prevent infinite loops
            current_depth: Current recursion depth

        Returns:
            FolderNode with complete tree structure
        """
        # Prevent infinite recursion
        if current_depth >= max_depth:
            logger.warning(f"Max depth {max_depth} reached at path: {path}")
            folder_meta = FolderMetadata(
                id=folder_id,
                name=path.split("/")[-1] if path else "root",
            )
            return FolderNode(folder=folder_meta, path=path)

        try:
            logger.debug(f"Fetching folder contents: {path} (depth: {current_depth})")
            files, folders = await self.get_folder_contents(drive_id, folder_id)
            logger.debug(f"Found {len(files)} files and {len(folders)} folders in {path}")
        except Exception as e:
            logger.error(f"Error fetching folder {folder_id}: {e}")
            # Return empty folder node on error
            folder_meta = FolderMetadata(
                id=folder_id,
                name=path.split("/")[-1] if path else "root",
            )
            return FolderNode(folder=folder_meta, path=path)

        # Get folder metadata
        try:
            url = f"{self.graph_endpoint}/drives/{drive_id}/items/{folder_id}"
            folder_data = await self._make_request("GET", url)
        except Exception as e:
            logger.warning(f"Could not fetch folder metadata for {folder_id}: {e}")
            folder_data = {"name": path.split("/")[-1] if path else "root"}

        folder_meta = FolderMetadata(
            id=folder_id,
            name=folder_data.get("name", "Unknown"),
            web_url=folder_data.get("webUrl"),
            created_date_time=self._parse_datetime(folder_data.get("createdDateTime")),
            last_modified_date_time=self._parse_datetime(
                folder_data.get("lastModifiedDateTime")
            ),
            child_count=len(files) + len(folders),
        )

        # Process files - incremental update if last_index_time provided
        file_metadata_list = []
        existing_files_map = {}
        if existing_node:
            existing_files_map = {f.id: f for f in existing_node.files}

        for file_data in files:
            try:
                file_id = file_data.get("id")
                file_modified = self._parse_datetime(file_data.get("lastModifiedDateTime"))
                
                # Skip if incremental update and file hasn't changed
                if last_index_time and file_id in existing_files_map:
                    existing_file = existing_files_map[file_id]
                    if existing_file.last_modified_date_time and file_modified:
                        if file_modified <= existing_file.last_modified_date_time:
                            # File hasn't changed, keep existing
                            file_metadata_list.append(existing_file)
                            continue

                file_meta = FileMetadata(
                    id=file_id,
                    name=file_data.get("name", "Unknown"),
                    web_url=file_data.get("webUrl"),
                    size=file_data.get("size"),
                    created_date_time=self._parse_datetime(file_data.get("createdDateTime")),
                    last_modified_date_time=file_modified,
                    created_by=file_data.get("createdBy", {}).get("user", {}).get("displayName"),
                    last_modified_by=file_data.get(
                        "lastModifiedBy", {}
                    ).get("user", {}).get("displayName"),
                    mime_type=file_data.get("file", {}).get("mimeType"),
                    download_url=file_data.get("@microsoft.graph.downloadUrl"),
                )
                file_metadata_list.append(file_meta)
            except Exception as e:
                logger.warning(f"Error processing file {file_data.get('name')}: {e}")

        # Process subfolders recursively - incremental update if last_index_time provided
        subfolders = {}
        existing_subfolders = existing_node.subfolders if existing_node else {}
        
        # Limit number of folders processed to prevent hanging on sites with thousands of folders
        max_folders_per_level = 1000
        folders_to_process = folders[:max_folders_per_level]
        if len(folders) > max_folders_per_level:
            logger.warning(f"Limiting folder processing to {max_folders_per_level} folders at {path} (found {len(folders)})")
        
        for idx, folder_data in enumerate(folders_to_process):
            folder_name = folder_data.get("name", "Unknown")
            new_path = f"{path}/{folder_name}" if path else folder_name
            folder_modified = self._parse_datetime(folder_data.get("lastModifiedDateTime"))

            # Update progress more frequently
            if progress_callback:
                try:
                    # Try to call with folder path if callback supports it
                    progress_callback(new_path)
                except TypeError:
                    # Fallback for callbacks that don't accept arguments
                    progress_callback()
            
            # Log progress every 50 folders
            if idx % 50 == 0 and idx > 0:
                logger.info(f"Processing folder {idx}/{len(folders_to_process)} in {path}")

            try:
                # Check if we need to process this folder (incremental update)
                existing_subfolder = existing_subfolders.get(folder_name)
                if last_index_time and existing_subfolder:
                    # Check if folder or its contents have changed
                    folder_id_val = folder_data.get("id")
                    if folder_modified and existing_subfolder.folder.last_modified_date_time:
                        if folder_modified <= existing_subfolder.folder.last_modified_date_time:
                            # Folder hasn't changed, keep existing but check children
                            # Still need to check for new files/folders
                            pass

                subfolder_node = await self.build_folder_tree(
                    drive_id,
                    folder_data.get("id"),
                    new_path,
                    progress_callback,
                    last_index_time,
                    existing_subfolder,
                    max_depth,
                    current_depth + 1,
                )
                subfolders[folder_name] = subfolder_node
            except asyncio.TimeoutError:
                logger.error(f"Timeout processing subfolder {folder_name} at {new_path}")
                # Continue with next folder
            except Exception as e:
                logger.warning(f"Error processing subfolder {folder_name} at {new_path}: {e}", exc_info=True)
                # Continue with next folder instead of failing completely
        
        # Keep existing subfolders that weren't found (they might have been deleted, but we keep them for now)
        if existing_node and not last_index_time:
            # Full refresh - don't keep old folders
            pass
        elif existing_node:
            # Incremental - keep folders that still exist but weren't in this batch
            for folder_name, existing_subfolder in existing_subfolders.items():
                if folder_name not in subfolders:
                    subfolders[folder_name] = existing_subfolder

        return FolderNode(
            folder=folder_meta,
            files=file_metadata_list,
            subfolders=subfolders,
            path=path,
        )

    async def index_site(
        self,
        site_id: str,
        site_name: str,
        site_url: str,
        progress_callback: Optional[Callable[[], None]] = None,
        last_index_time: Optional[datetime] = None,
        existing_index: Optional[SiteIndex] = None,
    ) -> SiteIndex:
        """Index all content in a SharePoint site.

        Args:
            site_id: SharePoint site ID
            site_name: Site name
            site_url: Site URL
            progress_callback: Optional callback for progress updates
            last_index_time: Optional datetime to only fetch items modified after this time
            existing_index: Optional existing SiteIndex to merge updates into

        Returns:
            SiteIndex with complete site structure
        """
        logger.info(f"Indexing site: {site_name} ({site_id})")

        libraries = await self.get_document_libraries(site_id)
        if not libraries:
            logger.warning(f"No document libraries found for site {site_id}")
            # Return empty site index
            root_folder = FolderNode(
                folder=FolderMetadata(id="root", name="root"),
                path="",
            )
            return SiteIndex(
                site_id=site_id,
                site_name=site_name,
                site_url=site_url,
                root_folder=root_folder,
                last_indexed=datetime.now(),
            )

        # For now, index the first library (can be extended to handle multiple)
        # In a full implementation, you might want to merge multiple libraries
        drive_id = libraries[0].get("id")
        
        # Use simplified flat file collection (faster and simpler)
        logger.info(f"Starting flat file collection for site {site_name}, drive {drive_id}")
        
        # Build existing files map for incremental updates
        existing_files_map = {}
        if existing_index and existing_index.root_folder:
            for file_meta in existing_index.root_folder.files:
                existing_files_map[file_meta.id] = file_meta
        
        all_files = await self.get_all_files_flat(
            drive_id, progress_callback, self, last_index_time, existing_files_map
        )
        logger.info(f"Completed file collection for site {site_name}: {len(all_files)} files")
        
        # Create a simple folder structure with all files in root (for compatibility)
        # This is much simpler than building a full tree
        root_folder = FolderNode(
            folder=FolderMetadata(id="root", name="root", child_count=len(all_files)),
            files=all_files,
            subfolders={},
            path="",
        )

        # Calculate statistics
        def count_files_and_folders(node: FolderNode) -> tuple[int, int, int]:
            """Recursively count files, folders, and total size."""
            files_count = len(node.files)
            folders_count = 1  # Count this folder
            total_size = sum(f.size or 0 for f in node.files)

            for subfolder in node.subfolders.values():
                sub_files, sub_folders, sub_size = count_files_and_folders(subfolder)
                files_count += sub_files
                folders_count += sub_folders
                total_size += sub_size

            return files_count, folders_count, total_size

        total_files, total_folders, total_size = count_files_and_folders(root_folder)

        return SiteIndex(
            site_id=site_id,
            site_name=site_name,
            site_url=site_url,
            root_folder=root_folder,
            total_files=total_files,
            total_folders=total_folders,
            total_size=total_size,
            last_indexed=datetime.now(),
        )

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

