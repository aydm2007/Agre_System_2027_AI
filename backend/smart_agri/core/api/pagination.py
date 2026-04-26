from rest_framework.pagination import CursorPagination

class YemenMobilePagination(CursorPagination):
    """
    AgriAsset Yemen: Ultra-Lightweight Pagination.
    Optimized for 2G/Edge networks.
    Protocol XXIII: Data Austerity Standard.
    """
    page_size = 10  # Strict limit for mobile lists (2G optimized)
    page_size_query_param = 'page_size'
    max_page_size = 50 # Never allow fetching 1000 items at once
    ordering = '-created_at' # Consistent ordering for cursor logic

class DropdownPagination(CursorPagination):
    """
    Specific for offline dropdown syncing.
    Allows slightly larger batches for setup data.
    """
    page_size = 100
    ordering = 'id'
