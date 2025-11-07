"""Background task processing for async indexing."""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional
from app.services.sharepoint_service import SharePointService
from app.services.email_service import EmailService
from app.services.index_service import IndexService
from app.models.index_models import IndexStatus, SiteIndex, FileMetadata, FolderNode, FolderMetadata
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class BackgroundTaskManager:
    """Manager for background indexing tasks."""

    def __init__(self, sharepoint_service: SharePointService, index_service: IndexService):
        """Initialize the background task manager.

        Args:
            sharepoint_service: SharePointService instance
            index_service: IndexService instance
        """
        self.sharepoint_service = sharepoint_service
        self.email_service = EmailService()
        self.index_service = index_service
        self._jobs: Dict[str, IndexStatus] = {}
        self._current_job_id: Optional[str] = None
        self._selected_site_ids: Optional[list[str]] = None
        self._sites_config: Optional[Dict[str, Dict[str, bool]]] = None  # site_id -> {index_sharepoint: bool, index_email: bool}
        self._current_status: Optional[IndexStatus] = None
        self._cancelled: bool = False

    def get_status(self, job_id: Optional[str] = None) -> Optional[IndexStatus]:
        """Get status of an indexing job.

        Args:
            job_id: Job ID (if None, returns current job status)

        Returns:
            IndexStatus or None if job not found or no active job
        """
        if job_id is None:
            job_id = self._current_job_id

        if job_id is None:
            return None

        status = self._jobs.get(job_id)
        
        # If job is completed/failed/cancelled and it's not the current job, return None
        # This prevents stale completed jobs from blocking new operations
        if status and status.status in ['completed', 'failed', 'cancelled']:
            if job_id != self._current_job_id:
                return None
        
        return status

    async def start_indexing(self, site_ids: Optional[list[str]] = None, sites_config: Optional[Dict[str, Dict[str, bool]]] = None) -> str:
        """Start a new indexing job.

        Args:
            site_ids: Optional list of site IDs to index. If None, indexes all sites.
            sites_config: Optional dict mapping site_id to {index_sharepoint: bool, index_email: bool}

        Returns:
            Job ID
        """
        # Cancel any existing job
        if self._current_job_id:
            await self.cancel_indexing(self._current_job_id)

        # Store selected site IDs and configuration
        self._selected_site_ids = site_ids
        self._sites_config = sites_config
        self._cancelled = False

        # Create new job
        job_id = str(uuid.uuid4())
        status = IndexStatus(
            job_id=job_id,
            status="running",
            progress=0.0,
            started_at=datetime.now(),
        )
        self._jobs[job_id] = status
        self._current_job_id = job_id

        logger.info(f"Started indexing job {job_id} with {len(site_ids) if site_ids else 'all'} sites")

        # Run indexing in background (this will be called as a background task)
        return job_id

    async def cancel_indexing(self, job_id: Optional[str] = None) -> bool:
        """Cancel an indexing job.

        Args:
            job_id: Optional job ID (if None, cancels current job)

        Returns:
            True if job was cancelled, False otherwise
        """
        if job_id is None:
            job_id = self._current_job_id

        if not job_id:
            return False

        status = self._jobs.get(job_id)
        if status and status.status == "running":
            self._cancelled = True
            status.status = "cancelled"
            status.completed_at = datetime.now()
            status.error_message = "Indexing cancelled by user"
            logger.info(f"Cancelled indexing job {job_id}")
            return True

        return False

    def reset(self) -> None:
        """Reset all task manager state (clear all jobs, reset flags).
        
        This is used when clearing all data to ensure a clean state.
        """
        logger.info("Resetting background task manager state")
        self._cancelled = False
        self._current_job_id = None
        self._selected_site_ids = None
        self._sites_config = None
        self._current_status = None
        self._jobs.clear()
        # Also reset the cancelled flag in sharepoint service
        if hasattr(self.sharepoint_service, '_cancelled'):
            self.sharepoint_service._cancelled = False
        logger.info("Background task manager reset complete")

    async def run_indexing(self, job_id: str) -> None:
        """Run the actual indexing process.

        Args:
            job_id: Job ID
        """
        status = self._jobs.get(job_id)
        if not status:
            logger.error(f"Job {job_id} not found")
            return

        try:
            status.status = "running"
            status.progress = 0.0

            # Get sites to index
            logger.info("Fetching SharePoint sites...")
            all_sites = await self.sharepoint_service.get_all_sites()
            
            # Filter to selected sites if provided
            if self._selected_site_ids:
                sites = [s for s in all_sites if s.get("id") in self._selected_site_ids]
                logger.info(f"Indexing {len(sites)} selected sites out of {len(all_sites)} total")
            else:
                sites = all_sites
                logger.info(f"Indexing all {len(sites)} sites")
            
            status.total_sites = len(sites)

            if not sites:
                logger.warning("No SharePoint sites found")
                status.status = "completed"
                status.progress = 1.0
                status.completed_at = datetime.now()
                return

            # Index each site
            site_indexes = []
            files_processed = 0

            def progress_callback(folder_path: Optional[str] = None):
                """Callback for progress updates."""
                nonlocal files_processed
                files_processed += 1
                status.files_processed = files_processed
                if folder_path:
                    status.current_folder = folder_path
                # Update progress more frequently
                if files_processed % 100 == 0:
                    logger.debug(f"Progress: {files_processed} files processed, current folder: {folder_path or 'N/A'}")
                if status.total_sites > 0:
                    # Rough progress estimate (can be improved)
                    site_progress = status.sites_processed / status.total_sites
                    status.progress = min(0.9, site_progress * 0.9)  # Reserve 10% for finalization

            # Get last index time for incremental updates
            last_index_time = self.index_service._last_indexed

            for idx, site in enumerate(sites):
                # Check if cancelled
                if self._cancelled:
                    logger.info("Indexing cancelled by user - preserving already indexed data")
                    # Save any sites that were already indexed before cancelling
                    if site_indexes:
                        logger.info(f"Saving {len(site_indexes)} sites that were indexed before cancellation")
                        self.index_service.update_index(site_indexes)
                    status.status = "cancelled"
                    status.completed_at = datetime.now()
                    status.error_message = "Indexing cancelled by user (partial data preserved)"
                    
                    # Clear current job ID so get_status returns None for cancelled jobs
                    if self._current_job_id == job_id:
                        self._current_job_id = None
                    
                    return

                site_id = site.get("id")
                site_name = site.get("name", site.get("displayName", "Unknown"))
                site_url = site.get("webUrl", "")

                # Get site configuration (what to index)
                site_config = self._sites_config.get(site_id, {"index_sharepoint": True, "index_email": True}) if self._sites_config else {"index_sharepoint": True, "index_email": True}
                index_sharepoint = site_config.get("index_sharepoint", True)
                index_email = site_config.get("index_email", True)

                status.current_site = site_name
                
                # Check if this is an incremental update
                existing_site_index = self.index_service.get_site_index(site_id)
                if last_index_time and existing_site_index:
                    logger.info(f"Incremental update for site {idx + 1}/{len(sites)}: {site_name}")
                else:
                    logger.info(f"Full index for site {idx + 1}/{len(sites)}: {site_name}")

                # Create or get existing site index
                from app.models.index_models import FolderNode, FolderMetadata
                site_index = existing_site_index
                if not site_index:
                    # Create new site index structure
                    site_index = SiteIndex(
                        site_id=site_id,
                        site_name=site_name,
                        site_url=site_url,
                        root_folder=FolderNode(
                            folder=FolderMetadata(id="root", name="Root", child_count=0),
                            files=[],
                            subfolders={},
                            path="",
                        ),
                        total_files=0,
                        total_folders=0,
                        total_size=0,
                        last_indexed=datetime.now(),
                    )

                try:
                    # Index SharePoint files if enabled
                    if index_sharepoint:
                        logger.info(f"Starting to index SharePoint for site: {site_name} (ID: {site_id})")
                        # Pass cancellation flag to sharepoint service
                        self.sharepoint_service._cancelled = self._cancelled
                        sharepoint_index = await asyncio.wait_for(
                            self.sharepoint_service.index_site(
                                site_id,
                                site_name,
                                site_url,
                                progress_callback,
                                last_index_time,
                                existing_site_index,
                            ),
                            timeout=3600.0,  # 1 hour timeout per site
                        )
                        # Merge SharePoint files into site index
                        site_index.root_folder.files.extend(sharepoint_index.root_folder.files)
                        site_index.total_files += sharepoint_index.total_files
                        site_index.total_folders += sharepoint_index.total_folders
                        site_index.total_size += sharepoint_index.total_size
                        files_processed += sharepoint_index.total_files
                        status.files_processed = files_processed
                        logger.info(f"Successfully indexed SharePoint for site {site_name}: {sharepoint_index.total_files} files, {sharepoint_index.total_folders} folders")
                    else:
                        logger.info(f"Skipping SharePoint indexing for site {site_name} (disabled)")
                    
                    # Index email attachments if enabled
                    if index_email:
                        # Get site owner and index their email attachments
                        try:
                            # Try to get owner from site metadata first
                            owner_email = await self.sharepoint_service.get_site_owner(site_id, site_data=site, site_name=site_name)
                            
                            # If no owner from metadata, try to match site name with user names
                            if not owner_email and site_name:
                                logger.debug(f"Trying to match site name '{site_name}' with users in directory")
                                try:
                                    # Get all users and try to find a match
                                    all_users = await self.email_service.get_all_users()
                                    # Try to find user by matching site name (case-insensitive)
                                    for user in all_users:
                                        user_display_name = user.get("displayName", "")
                                        user_mail = user.get("mail", "")
                                        user_upn = user.get("userPrincipalName", "")
                                        
                                        # Check if site name matches user display name
                                        if user_display_name and site_name.lower() in user_display_name.lower():
                                            owner_email = user_mail or user_upn
                                            logger.info(f"Matched site '{site_name}' with user '{user_display_name}' ({owner_email})")
                                            break
                                        # Also check if site name matches email username
                                        if user_mail and site_name.lower().replace(" ", ".") in user_mail.lower():
                                            owner_email = user_mail
                                            logger.info(f"Matched site '{site_name}' with user email '{user_mail}'")
                                            break
                                except Exception as e:
                                    logger.debug(f"Error matching site name with users: {e}")
                            
                            if owner_email:
                                logger.info(f"Found owner for site {site_name}: {owner_email} - indexing their email attachments")
                                status.current_folder = f"Indexing emails for {owner_email}..."
                                
                                # Get user info by email
                                user_info = await self.email_service.get_user_by_email(owner_email)
                                if user_info:
                                    user_id = user_info.get("id") or user_info.get("userPrincipalName")
                                    if user_id:
                                        # Get email attachments for this site owner
                                        try:
                                            attachments = await self.email_service.get_emails_with_attachments(
                                                user_id,
                                                owner_email,
                                                progress_callback,
                                                self,
                                                last_index_time,
                                            )
                                            
                                            if len(attachments) > 0:
                                                logger.info(f"Found {len(attachments)} email attachments for site owner {owner_email}")
                                                
                                                # Mark all attachments as from email source
                                                for attachment in attachments:
                                                    attachment.source = "email"
                                                
                                                # Add email attachments to the site's root folder
                                                site_index.root_folder.files.extend(attachments)
                                                site_index.total_files += len(attachments)
                                                files_processed += len(attachments)
                                                status.files_processed = files_processed
                                            else:
                                                logger.debug(f"No email attachments found for site owner {owner_email}")
                                        except Exception as e:
                                            error_str = str(e)
                                            # 404 errors are expected for users without mailboxes - don't log as error
                                            if "404" not in error_str and "Not Found" not in error_str:
                                                logger.warning(f"Error indexing emails for site owner {owner_email}: {e}")
                                    else:
                                        logger.debug(f"Could not get user ID for site owner {owner_email}")
                                else:
                                    logger.debug(f"Site owner {owner_email} not found in directory")
                            else:
                                logger.debug(f"No owner found for site {site_name} (tried metadata and name matching)")
                        except Exception as e:
                            # Suppress errors for owner lookup - it's not critical
                            logger.debug(f"Could not get site owner for {site_name}: {e} - continuing")
                    else:
                        logger.info(f"Skipping email indexing for site {site_name} (disabled)")
                    
                    # Add site index to list
                    site_indexes.append(site_index)
                    
                    # Save progress incrementally (after each site) so it's preserved if cancelled
                    if site_indexes:
                        self.index_service.update_index(site_indexes)
                        logger.debug(f"Incremental save: {len(site_indexes)} sites saved to index")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout indexing site {site_name} after 1 hour - skipping")
                    status.error_message = f"Timeout indexing {site_name}"
                    # Continue with other sites
                except Exception as e:
                    logger.error(f"Error indexing site {site_name}: {e}", exc_info=True)
                    # Continue with other sites

                status.sites_processed = idx + 1
                status.progress = min(0.9, (idx + 1) / len(sites) * 0.9)

            # Final update of index (merge with any existing data)
            # This ensures we don't lose data from previous indexing sessions
            # Email attachments are now indexed per site (for each site's owner) in the loop above
            if site_indexes:
                logger.info("Updating index with all indexed data (SharePoint + Email attachments)...")
                self.index_service.update_index(site_indexes)

            # Complete
            status.status = "completed"
            status.progress = 1.0
            status.completed_at = datetime.now()
            status.current_site = None
            status.current_folder = None
            
            # Clear current job ID so get_status returns None for completed jobs
            if self._current_job_id == job_id:
                self._current_job_id = None
            
            logger.info(f"Indexing job {job_id} completed successfully (SharePoint + Email)")

        except Exception as e:
            logger.error(f"Indexing job {job_id} failed: {e}", exc_info=True)
            status.status = "failed"
            status.error_message = str(e)
            status.completed_at = datetime.now()
            
            # Clear current job ID so get_status returns None for failed jobs
            if self._current_job_id == job_id:
                self._current_job_id = None

