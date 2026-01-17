# Research module - Real web research and source management
from .web_researcher import WebResearcher, WebSource, ResearchResult
from .source_collector import SourceCollector, CollectedSource
from .citation_manager import CitationManager, Citation

__all__ = [
    'WebResearcher',
    'WebSource',
    'ResearchResult',
    'SourceCollector',
    'CollectedSource',
    'CitationManager',
    'Citation'
]
