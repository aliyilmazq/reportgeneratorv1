# Rapor Uretici - Ana Modul
"""
Report Generator v4.0 PRO
=========================
Kapsamli rapor uretim sistemi.
"""

from typing import TYPE_CHECKING

# Version info
__version__ = "4.0.0"
__author__ = "Report Generator Team"

# Type exports (lazy import for performance)
if TYPE_CHECKING:
    from .types import (
        # Enums
        ReportType,
        OutputFormat,
        FileCategory,
        SourceType,
        QualityLevel,
        # Type aliases
        PathLike,
        ProgressCallback,
        JsonDict,
        ContentDict,
        MetadataDict,
        TableDict,
        # Protocols
        Serializable,
        Parseable,
        Validatable,
        DocumentParser,
        ContentGenerator,
        Retriever,
        # Dataclasses
        DocumentBase,
        SectionBase,
        ParsedDocument,
        RetrievalResult,
        ValidationResult,
        OperationResult,
        FileInfo,
        SourceInfo,
        DataPoint,
        ChunkInfo,
        APIResponse,
        # Config types
        RetryConfig,
        CacheConfig,
        GeneratorConfig,
    )

__all__ = [
    "__version__",
    "__author__",
]
