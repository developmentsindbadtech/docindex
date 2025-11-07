"""Pagination utilities for API responses."""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


def paginate(
    items: List[T],
    page: int = 1,
    page_size: int = 50,
    max_page_size: int = 500,
) -> PaginatedResponse[T]:
    """Paginate a list of items.

    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page
        max_page_size: Maximum allowed page size

    Returns:
        PaginatedResponse with paginated items and metadata
    """
    # Validate and clamp page_size
    page_size = min(max(1, page_size), max_page_size)
    page = max(1, page)

    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    page = min(page, total_pages)

    # Calculate slice indices
    start = (page - 1) * page_size
    end = start + page_size

    paginated_items = items[start:end]

    return PaginatedResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

