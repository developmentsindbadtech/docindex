"""SharePoint API routes."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Body, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.services.sharepoint_service import SharePointService
from app.services.index_service import IndexService
from app.services.background_tasks import BackgroundTaskManager
from app.models.index_models import IndexStatus, IndexStats
from app.utils.pagination import paginate, PaginatedResponse
from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

router = APIRouter(prefix="/api", tags=["sharepoint"])


def require_auth(request: Request):
    """Dependency to require authentication for routes.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return request.session.get("user")

# Initialize services (singleton pattern)
_sharepoint_service: Optional[SharePointService] = None
_index_service: Optional[IndexService] = None
_task_manager: Optional[BackgroundTaskManager] = None


def get_services() -> tuple[SharePointService, IndexService, BackgroundTaskManager]:
    """Get or create service instances.

    Returns:
        Tuple of (SharePointService, IndexService, BackgroundTaskManager)
    """
    global _sharepoint_service, _index_service, _task_manager

    if _sharepoint_service is None:
        _sharepoint_service = SharePointService()
        _index_service = IndexService()
        _task_manager = BackgroundTaskManager(_sharepoint_service, _index_service)

    return _sharepoint_service, _index_service, _task_manager


@router.get("/sites/discover")
async def discover_sites(user: Dict = Depends(require_auth)) -> Dict[str, Any]:
    """Discover all SharePoint sites without indexing them.

    Returns:
        List of available SharePoint sites
    """
    sharepoint_service, _, _ = get_services()

    try:
        sites = await sharepoint_service.get_all_sites()
        
        # Format sites for frontend
        formatted_sites = [
            {
                "id": site.get("id"),
                "name": site.get("name") or site.get("displayName", "Unknown"),
                "url": site.get("webUrl", ""),
                "description": site.get("description", ""),
            }
            for site in sites
        ]

        return {
            "sites": formatted_sites,
            "total": len(formatted_sites),
        }
    except Exception as e:
        logger.error(f"Failed to discover sites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to discover sites: {str(e)}")


class SiteConfig(BaseModel):
    """Configuration for a single site."""
    site_id: str
    index_sharepoint: bool = True
    index_email: bool = True


class RefreshRequest(BaseModel):
    """Request model for refresh endpoint."""
    site_ids: Optional[List[str]] = None  # Legacy support
    sites: Optional[List[SiteConfig]] = None  # New format with options


@router.post("/refresh")
async def refresh_index(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(require_auth),
    request: Optional[RefreshRequest] = Body(default=None),
) -> Dict[str, Any]:
    """Trigger a SharePoint index refresh for selected sites.

    Args:
        site_ids: Optional list of site IDs to index. If None or empty, indexes all sites.

    Returns:
        Job ID and status
    """
    _, _, task_manager = get_services()

    try:
        # Support both old format (site_ids) and new format (sites with options)
        if request and request.sites:
            # New format: sites with individual options
            sites_config = {site.site_id: {'index_sharepoint': site.index_sharepoint, 'index_email': site.index_email} for site in request.sites}
            site_ids = [site.site_id for site in request.sites]
            job_id = await task_manager.start_indexing(site_ids, sites_config=sites_config)
        else:
            # Legacy format: just site_ids (default to both options enabled)
            site_ids = request.site_ids if request else None
            job_id = await task_manager.start_indexing(site_ids)
        # Add the actual indexing task to background
        background_tasks.add_task(task_manager.run_indexing, job_id)

        return {
            "job_id": job_id,
            "status": "started",
            "message": "Indexing started in background",
        }
    except Exception as e:
        logger.error(f"Failed to start indexing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {str(e)}")


@router.get("/status", response_model=IndexStatus)
async def get_indexing_status(
    job_id: Optional[str] = Query(None),
    user: Dict = Depends(require_auth),
) -> IndexStatus:
    """Get the status of an indexing job.

    Args:
        job_id: Optional job ID (if not provided, returns current job)

    Returns:
        IndexStatus with current progress
    """
    _, _, task_manager = get_services()

    status = task_manager.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found or no active job")

    return status


@router.get("/index", response_model=PaginatedResponse)
async def get_index(
    page: int = Query(1, ge=1),
    limit: int = Query(None, ge=1, le=settings.max_page_size),
    user: Dict = Depends(require_auth),
) -> PaginatedResponse:
    """Get the current index structure (paginated).

    Args:
        page: Page number (1-indexed)
        limit: Items per page

    Returns:
        Paginated list of site indexes
    """
    _, index_service, _ = get_services()

    limit = limit or settings.default_page_size
    all_sites = index_service.get_all_sites()

    # Convert to dict for pagination
    sites_data = [site.model_dump() for site in all_sites]

    return paginate(sites_data, page=page, page_size=limit, max_page_size=settings.max_page_size)


@router.get("/index/stats", response_model=IndexStats)
async def get_index_stats(user: Dict = Depends(require_auth)) -> IndexStats:
    """Get statistics about the current index.

    Returns:
        IndexStats with aggregated statistics
    """
    _, index_service, _ = get_services()
    return index_service.get_stats()


@router.get("/files", response_model=PaginatedResponse)
async def get_all_files(
    page: int = Query(1, ge=1),
    limit: int = Query(None, ge=1, le=settings.max_page_size),
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    user: Dict = Depends(require_auth),
) -> PaginatedResponse:
    """Get all files (name and link only) for fast listing.

    Args:
        page: Page number (1-indexed)
        limit: Items per page
        site_id: Optional site ID to filter files

    Returns:
        Paginated file list with minimal data
    """
    _, index_service, _ = get_services()

    limit = limit or settings.default_page_size
    all_files = []

    # Collect all files from all sites (or specific site)
    for site_index in index_service.get_all_sites():
        if site_id and site_index.site_id != site_id:
            continue
        
        for file_meta in site_index.root_folder.files:
            file_path = file_meta.path if hasattr(file_meta, 'path') and file_meta.path else ""
            file_type = getattr(file_meta, 'file_type', '')
            if not file_type and file_meta.name and '.' in file_meta.name:
                file_type = file_meta.name.split('.')[-1].upper()
            
            source = getattr(file_meta, 'source', 'sharepoint')
            all_files.append({
                "name": file_meta.name,
                "url": str(file_meta.web_url) if file_meta.web_url else "",
                "type": file_type,
                "created_date": file_meta.created_date_time.isoformat() if file_meta.created_date_time else "",
                "modified_date": file_meta.last_modified_date_time.isoformat() if file_meta.last_modified_date_time else "",
                "owner": file_meta.created_by or file_meta.last_modified_by or "",
                "path": file_path,
                "site_name": site_index.site_name,
                "source": source,  # "sharepoint" or "email"
            })

    # Sort by name for consistent ordering
    all_files.sort(key=lambda x: x["name"].lower())

    return paginate(all_files, page=page, page_size=limit, max_page_size=settings.max_page_size)


@router.get("/search", response_model=PaginatedResponse)
async def search_files(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(None, ge=1, le=settings.max_page_size),
    user: Dict = Depends(require_auth),
) -> PaginatedResponse:
    """Search for files across all indexed sites (name and link only).

    Args:
        q: Search query
        page: Page number (1-indexed)
        limit: Items per page

    Returns:
        Paginated search results with minimal data
    """
    _, index_service, _ = get_services()

    limit = limit or settings.default_page_size
    results = index_service.search_files(q, limit=limit * page)  # Get enough for pagination

    # Format results with table data
    formatted_results = []
    for site_index, file_meta, file_path in results:
        file_type = getattr(file_meta, 'file_type', '')
        if not file_type and file_meta.name and '.' in file_meta.name:
            file_type = file_meta.name.split('.')[-1].upper()
        
        source = getattr(file_meta, 'source', 'sharepoint')
        formatted_results.append({
            "name": file_meta.name,
            "url": str(file_meta.web_url) if file_meta.web_url else "",
            "type": file_type,
            "created_date": file_meta.created_date_time.isoformat() if file_meta.created_date_time else "",
            "modified_date": file_meta.last_modified_date_time.isoformat() if file_meta.last_modified_date_time else "",
            "owner": file_meta.created_by or file_meta.last_modified_by or "",
            "path": file_path,
            "site_name": site_index.site_name,
            "source": source,  # "sharepoint" or "email"
        })

    return paginate(formatted_results, page=page, page_size=limit, max_page_size=settings.max_page_size)


@router.post("/cancel")
async def cancel_indexing(
    job_id: Optional[str] = Query(None),
    user: Dict = Depends(require_auth),
) -> Dict[str, Any]:
    """Cancel an indexing job.

    Args:
        job_id: Optional job ID (if None, cancels current job)

    Returns:
        Cancellation status
    """
    _, _, task_manager = get_services()

    try:
        cancelled = await task_manager.cancel_indexing(job_id)
        if cancelled:
            return {
                "status": "cancelled",
                "message": "Indexing job cancelled successfully",
            }
        else:
            raise HTTPException(status_code=404, detail="Job not found or not running")
    except Exception as e:
        logger.error(f"Failed to cancel indexing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel indexing: {str(e)}")


@router.post("/clear-all")
async def clear_all(user: Dict = Depends(require_auth)) -> Dict[str, Any]:
    """Clear all indexed data and stop all processes.

    This will:
    - Cancel any ongoing indexing jobs
    - Clear all indexed data
    - Reset the index

    Returns:
        Status of the operation
    """
    _, index_service, task_manager = get_services()

    try:
        # Cancel any ongoing indexing
        await task_manager.cancel_indexing()
        
        # Reset task manager state completely
        task_manager.reset()
        
        # Clear all indexed data
        index_service.clear_index()
        
        logger.info("All data cleared and processes stopped")
        return {
            "status": "success",
            "message": "All indexed data cleared and processes stopped"
        }
    except Exception as e:
        logger.error(f"Failed to clear all: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear all: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "Sindbad.Tech SharePoint Doc Indexer",
    }

