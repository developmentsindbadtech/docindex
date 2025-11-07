"""Index service for managing and caching SharePoint index."""

from typing import Dict, Optional, List
from datetime import datetime
from cachetools import TTLCache
from app.config import settings
from app.utils.logger import setup_logger
from app.models.index_models import SiteIndex, IndexStats, FileMetadata, FolderNode

logger = setup_logger(__name__)


class IndexService:
    """Service for managing the SharePoint index with caching."""

    def __init__(self):
        """Initialize the index service."""
        # Cache for site indexes with TTL
        self._cache: TTLCache = TTLCache(
            maxsize=settings.cache_max_size,
            ttl=settings.cache_ttl_seconds,
        )
        self._index: Dict[str, SiteIndex] = {}
        self._last_indexed: Optional[datetime] = None

    def update_index(self, site_indexes: List[SiteIndex]) -> None:
        """Update the index with new site indexes.
        Merges with existing data - doesn't overwrite unless site is re-indexed.

        Args:
            site_indexes: List of SiteIndex objects to add/update
        """
        logger.info(f"Updating index with {len(site_indexes)} sites")
        for site_index in site_indexes:
            # Merge with existing site index if it exists (preserve partial data)
            existing_site = self._index.get(site_index.site_id)
            if existing_site and existing_site.root_folder:
                # Merge files: combine existing and new, avoiding duplicates
                existing_files = {f.id: f for f in existing_site.root_folder.files}
                new_files = {f.id: f for f in site_index.root_folder.files}
                # Update existing files with new data, add new files
                existing_files.update(new_files)
                # Create merged root folder
                merged_root = FolderNode(
                    folder=site_index.root_folder.folder,
                    files=list(existing_files.values()),
                    subfolders=site_index.root_folder.subfolders,
                    path=site_index.root_folder.path,
                )
                # Update totals
                site_index.root_folder = merged_root
                site_index.total_files = len(existing_files)
            
            self._index[site_index.site_id] = site_index
            # Also cache it
            self._cache[site_index.site_id] = site_index

        self._last_indexed = datetime.now()
        logger.info("Index updated successfully (merged with existing data)")

    def get_site_index(self, site_id: str) -> Optional[SiteIndex]:
        """Get index for a specific site.

        Args:
            site_id: SharePoint site ID

        Returns:
            SiteIndex or None if not found
        """
        # Check cache first
        if site_id in self._cache:
            return self._cache[site_id]

        # Check main index
        return self._index.get(site_id)

    def get_all_sites(self) -> List[SiteIndex]:
        """Get all indexed sites.

        Returns:
            List of all SiteIndex objects
        """
        return list(self._index.values())

    def get_stats(self) -> IndexStats:
        """Get statistics about the index.

        Returns:
            IndexStats with aggregated statistics including file type breakdown
        """
        total_sites = len(self._index)
        total_files = 0
        total_folders = 0
        total_size = 0
        file_types: Dict[str, int] = {}

        for site_index in self._index.values():
            total_files += site_index.total_files
            total_folders += site_index.total_folders
            total_size += site_index.total_size
            
            # Count file types
            for file_meta in site_index.root_folder.files:
                file_type = getattr(file_meta, 'file_type', '')
                if not file_type and file_meta.name and '.' in file_meta.name:
                    file_type = file_meta.name.split('.')[-1].upper()
                
                if file_type:
                    file_types[file_type] = file_types.get(file_type, 0) + 1
                else:
                    file_types['UNKNOWN'] = file_types.get('UNKNOWN', 0) + 1

        return IndexStats(
            total_sites=total_sites,
            total_files=total_files,
            total_folders=total_folders,
            total_size=total_size,
            file_types=file_types,
            last_indexed=self._last_indexed,
        )

    def search_files(
        self, query: str, limit: Optional[int] = None
    ) -> List[tuple[SiteIndex, FileMetadata, str]]:
        """Search for files across all sites (simplified flat search).
        Supports Arabic and Unicode characters.

        Args:
            query: Search query (case-insensitive substring match, Unicode-aware)
            limit: Maximum number of results (None = no limit)

        Returns:
            List of tuples (SiteIndex, FileMetadata, file_path)
        """
        # Normalize query for better Unicode matching (handles Arabic diacritics)
        import unicodedata
        query_normalized = unicodedata.normalize('NFKC', query)
        query_lower = query_normalized.lower()
        results = []

        # Simplified search - just search all files in root folder (flat structure)
        for site_index in self._index.values():
            for file_meta in site_index.root_folder.files:
                # Normalize file name for comparison (handles Arabic and Unicode)
                file_name_normalized = unicodedata.normalize('NFKC', file_meta.name)
                file_name_lower = file_name_normalized.lower()
                
                # Check if query matches (supports Arabic characters)
                if query_lower in file_name_lower or query_normalized in file_name_normalized:
                    # Use stored path or construct from name
                    file_path = file_meta.path if hasattr(file_meta, 'path') and file_meta.path else file_meta.name
                    results.append((site_index, file_meta, file_path))

                if limit and len(results) >= limit:
                    break
            
            if limit and len(results) >= limit:
                break

        # Sort by relevance (files with query at start of name first)
        # Use normalized names for sorting to handle Arabic properly
        results.sort(
            key=lambda x: (
                0 if unicodedata.normalize('NFKC', x[1].name).lower().startswith(query_lower) else 1,
                unicodedata.normalize('NFKC', x[1].name).lower(),
            )
        )

        if limit:
            results = results[:limit]

        return results

    def clear_index(self) -> None:
        """Clear the entire index."""
        logger.info("Clearing index")
        self._index.clear()
        self._cache.clear()
        self._last_indexed = None

    def get_index_size(self) -> int:
        """Get the number of sites in the index.

        Returns:
            Number of indexed sites
        """
        return len(self._index)

