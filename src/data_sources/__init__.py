# Data sources module - Web-based data fetching
from .web_data_fetcher import WebDataFetcher, DataPoint
from .cache import DataCache

__all__ = [
    'WebDataFetcher',
    'DataPoint',
    'DataCache'
]
