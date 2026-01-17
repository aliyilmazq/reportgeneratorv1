"""
Type Definitions Module
=======================
Merkezi type tanimlari ve protokoller.
mypy ve IDE support icin kapsamli type hints.
"""

from typing import (
    TypeVar, Generic, Protocol, runtime_checkable,
    Dict, List, Optional, Any, Union, Callable, Tuple,
    Sequence, Mapping, Iterator, Awaitable
)
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum, auto


# ═══════════════════════════════════════════════════════════════════════════════
# GENERIC TYPE VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)

# Document types
DocumentT = TypeVar('DocumentT', bound='DocumentBase')
SectionT = TypeVar('SectionT', bound='SectionBase')

# Result types
ResultT = TypeVar('ResultT')
ErrorT = TypeVar('ErrorT', bound=Exception)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ReportType(str, Enum):
    """Rapor tipleri."""
    IS_PLANI = "is_plani"
    PROJE_RAPORU = "proje_raporu"
    ANALIZ_RAPORU = "analiz_raporu"
    ON_FIZIBILITE = "on_fizibilite"
    TEKNIK_DOK = "teknik_dok"
    SUNUM = "sunum"
    KISA_NOT = "kisa_not"


class OutputFormat(str, Enum):
    """Cikti formatlari."""
    DOCX = "docx"
    PDF = "pdf"
    BOTH = "both"


class FileCategory(str, Enum):
    """Dosya kategorileri."""
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    IMAGE = "image"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    """Kaynak tipleri."""
    WEB = "web"
    FILE = "file"
    API = "api"
    USER = "user"


class QualityLevel(str, Enum):
    """Kalite seviyeleri."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXCELLENT = "excellent"


# ═══════════════════════════════════════════════════════════════════════════════
# TYPE ALIASES
# ═══════════════════════════════════════════════════════════════════════════════

# JSON-compatible types
JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, List['JsonValue'], Dict[str, 'JsonValue']]
JsonDict = Dict[str, JsonValue]
JsonList = List[JsonValue]

# Path types
PathLike = Union[str, Path]

# Callback types
ProgressCallback = Callable[[str, float, str], None]
ErrorCallback = Callable[[Exception], None]
SuccessCallback = Callable[[Any], None]

# Content types
ContentDict = Dict[str, Any]
MetadataDict = Dict[str, Union[str, int, float, bool, List[str]]]

# Table types
TableRow = List[str]
TableData = List[TableRow]
TableDict = Dict[str, Union[List[str], TableData]]


# ═══════════════════════════════════════════════════════════════════════════════
# PROTOCOLS (Duck Typing Interfaces)
# ═══════════════════════════════════════════════════════════════════════════════

@runtime_checkable
class Serializable(Protocol):
    """to_dict metoduna sahip nesneler."""
    def to_dict(self) -> Dict[str, Any]: ...


@runtime_checkable
class Parseable(Protocol):
    """parse metoduna sahip nesneler."""
    def parse(self, content: str) -> Any: ...


@runtime_checkable
class Validatable(Protocol):
    """validate metoduna sahip nesneler."""
    def validate(self) -> Tuple[bool, List[str]]: ...


@runtime_checkable
class Closeable(Protocol):
    """close metoduna sahip nesneler."""
    def close(self) -> None: ...


@runtime_checkable
class ContextManager(Protocol[T_co]):
    """Context manager protokolu."""
    def __enter__(self) -> T_co: ...
    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> Optional[bool]: ...


@runtime_checkable
class DocumentParser(Protocol):
    """Dokuman parser protokolu."""
    def parse(self, file_path: PathLike) -> 'ParsedDocument': ...
    def supports(self, extension: str) -> bool: ...


@runtime_checkable
class ContentGenerator(Protocol):
    """Icerik uretici protokolu."""
    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 4000
    ) -> str: ...


@runtime_checkable
class Retriever(Protocol):
    """RAG retriever protokolu."""
    def retrieve(
        self,
        query: str,
        top_k: int = 10
    ) -> List['RetrievalResult']: ...

    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
# BASE DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DocumentBase:
    """Temel dokuman dataclass'i."""
    id: str
    title: str
    content: str
    metadata: MetadataDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SectionBase:
    """Temel bolum dataclass'i."""
    section_id: str
    title: str
    content: str
    level: int = 1
    order: int = 0


@dataclass
class ParsedDocument:
    """Parse edilmis dokuman."""
    file_path: str
    file_name: str
    file_type: FileCategory
    text_content: str
    tables: List[TableDict] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    metadata: MetadataDict = field(default_factory=dict)
    word_count: int = 0
    page_count: int = 0
    parse_time_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.word_count:
            self.word_count = len(self.text_content.split())


@dataclass
class RetrievalResult:
    """RAG retrieval sonucu."""
    text: str
    score: float
    source: str
    metadata: MetadataDict = field(default_factory=dict)
    chunk_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Dogrulama sonucu."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationResult(Generic[T]):
    """Generic operasyon sonucu."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: T, duration: float = 0.0) -> 'OperationResult[T]':
        """Basarili sonuc olustur."""
        return cls(success=True, data=data, duration_seconds=duration)

    @classmethod
    def fail(
        cls,
        error: str,
        error_type: Optional[str] = None
    ) -> 'OperationResult[T]':
        """Basarisiz sonuc olustur."""
        return cls(
            success=False,
            error=error,
            error_type=error_type or "UnknownError"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SPECIALIZED TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FileInfo:
    """Dosya bilgisi."""
    path: str
    name: str
    extension: str
    size: int
    category: FileCategory
    modified_time: datetime

    @property
    def size_formatted(self) -> str:
        """Okunabilir boyut."""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


@dataclass
class SourceInfo:
    """Kaynak bilgisi."""
    url: str
    title: str
    source_type: SourceType
    snippet: str = ""
    content: str = ""
    relevance_score: float = 0.0
    accessed_at: datetime = field(default_factory=datetime.now)
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class DataPoint:
    """Veri noktasi."""
    name: str
    value: Union[int, float, str]
    unit: str = ""
    source: str = ""
    timestamp: Optional[datetime] = None
    confidence: float = 1.0

    @property
    def value_formatted(self) -> str:
        """Formatli deger."""
        if isinstance(self.value, float):
            return f"{self.value:,.2f} {self.unit}".strip()
        return f"{self.value} {self.unit}".strip()


@dataclass
class ChunkInfo:
    """Chunk bilgisi."""
    text: str
    start_index: int
    end_index: int
    chunk_index: int
    metadata: MetadataDict = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    @property
    def length(self) -> int:
        return len(self.text)


# ═══════════════════════════════════════════════════════════════════════════════
# API RESPONSE TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class APIResponse(Generic[T]):
    """API yanit tipi."""
    data: Optional[T]
    status_code: int
    success: bool
    message: str = ""
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaginatedResponse(Generic[T]):
    """Sayfalanmis yanit."""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RetryConfig:
    """Retry konfigurasyonu."""
    max_attempts: int = 3
    min_wait: float = 2.0
    max_wait: float = 10.0
    multiplier: float = 1.5
    exceptions: Tuple[type, ...] = (Exception,)


@dataclass
class CacheConfig:
    """Cache konfigurasyonu."""
    enabled: bool = True
    max_size: int = 1000
    ttl_seconds: int = 3600
    directory: Optional[str] = None


@dataclass
class GeneratorConfig:
    """Generator konfigurasyonu."""
    model: str = "claude-opus-4-5-20250514"
    max_tokens: int = 4000
    temperature: float = 0.7
    min_words: int = 500
    min_paragraphs: int = 3
    min_sources: int = 2


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def is_serializable(obj: Any) -> bool:
    """Nesnenin Serializable protokolunu destekleyip desteklemedigini kontrol et."""
    return isinstance(obj, Serializable)


def is_validatable(obj: Any) -> bool:
    """Nesnenin Validatable protokolunu destekleyip desteklemedigini kontrol et."""
    return isinstance(obj, Validatable)


def ensure_path(path: PathLike) -> Path:
    """PathLike'i Path'e cevir."""
    return Path(path) if isinstance(path, str) else path


def get_quality_level(score: float) -> QualityLevel:
    """Skora gore kalite seviyesi dondur."""
    if score >= 0.9:
        return QualityLevel.EXCELLENT
    elif score >= 0.7:
        return QualityLevel.HIGH
    elif score >= 0.5:
        return QualityLevel.MEDIUM
    return QualityLevel.LOW
