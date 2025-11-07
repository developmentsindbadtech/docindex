"""Data models for SharePoint index structure."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl


class FileMetadata(BaseModel):
    """Metadata for a SharePoint file or email attachment."""

    id: str
    name: str
    path: str = ""  # File path for flat list structure, or email subject for attachments
    file_type: str = ""  # File extension/type
    web_url: Optional[HttpUrl] = None
    size: Optional[int] = None
    created_date_time: Optional[datetime] = None
    last_modified_date_time: Optional[datetime] = None
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None
    mime_type: Optional[str] = None
    download_url: Optional[HttpUrl] = None
    source: str = "sharepoint"  # "sharepoint" or "email" to distinguish source


class FolderMetadata(BaseModel):
    """Metadata for a SharePoint folder."""

    id: str
    name: str
    web_url: Optional[HttpUrl] = None
    created_date_time: Optional[datetime] = None
    last_modified_date_time: Optional[datetime] = None
    child_count: int = 0


class FolderNode(BaseModel):
    """A folder node in the hierarchical structure."""

    folder: FolderMetadata
    files: List[FileMetadata] = []
    subfolders: Dict[str, "FolderNode"] = {}
    path: str = ""

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class SiteIndex(BaseModel):
    """Index for a SharePoint site."""

    site_id: str
    site_name: str
    site_url: str
    root_folder: FolderNode
    total_files: int = 0
    total_folders: int = 0
    total_size: int = 0
    last_indexed: Optional[datetime] = None


class IndexStats(BaseModel):
    """Statistics about the overall index."""

    total_sites: int = 0
    total_files: int = 0
    total_folders: int = 0
    total_size: int = 0
    file_types: Dict[str, int] = {}  # File type breakdown (e.g., {"PDF": 10, "DOCX": 5})
    last_indexed: Optional[datetime] = None


class IndexStatus(BaseModel):
    """Status of an indexing job."""

    job_id: str
    status: str  # "running", "completed", "failed"
    progress: float = 0.0  # 0.0 to 1.0
    current_site: Optional[str] = None
    current_folder: Optional[str] = None
    sites_processed: int = 0
    total_sites: int = 0
    files_processed: int = 0
    folders_processed: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

