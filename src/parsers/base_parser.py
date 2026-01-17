"""
Base Parser Module
==================
Tum parser'lar icin temel sinif.
Kod tekrarini onler ve tutarli API saglar.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Type alias
PathLike = Union[str, Path]
T = TypeVar('T')


@dataclass
class ParsedContent:
    """Parse edilmis icerik - tum parser'lar icin ortak."""
    source: str
    filename: str
    file_type: str
    text_content: str
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    page_count: int = 0
    parse_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.word_count and self.text_content:
            self.word_count = len(self.text_content.split())

    @property
    def has_content(self) -> bool:
        """Icerik var mi."""
        return bool(self.text_content.strip() or self.tables or self.images)

    @property
    def has_errors(self) -> bool:
        """Hata var mi."""
        return bool(self.errors)

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e cevir."""
        return {
            "source": self.source,
            "filename": self.filename,
            "file_type": self.file_type,
            "word_count": self.word_count,
            "page_count": self.page_count,
            "table_count": len(self.tables),
            "image_count": len(self.images),
            "parse_time_seconds": self.parse_time_seconds,
            "has_errors": self.has_errors,
            "metadata": self.metadata
        }


class BaseParser(ABC, Generic[T]):
    """
    Temel parser sinifi.

    Tum parser'lar bu siniftan turemeli:
    - PDFParser
    - ExcelParser
    - WordParser
    - ImageAnalyzer
    """

    # Alt siniflar tarafindan override edilecek
    SUPPORTED_EXTENSIONS: List[str] = []

    def __init__(self) -> None:
        self._closed: bool = False
        self._current_file: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def __enter__(self) -> 'BaseParser[T]':
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> bool:
        """Context manager exit."""
        self.close()
        return False

    def close(self) -> None:
        """Kaynaklari temizle."""
        self._closed = True
        self._current_file = None

    @property
    def is_closed(self) -> bool:
        """Parser kapali mi."""
        return self._closed

    def supports(self, file_path: PathLike) -> bool:
        """Dosya destekleniyor mu."""
        extension = Path(file_path).suffix.lower()
        return extension in self.SUPPORTED_EXTENSIONS

    def validate_file(self, file_path: PathLike) -> None:
        """
        Dosyayi dogrula.

        Raises:
            FileNotFoundError: Dosya bulunamadi
            ValueError: Desteklenmeyen format
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Dosya bulunamadi: {path}")

        if not path.is_file():
            raise ValueError(f"Gecerli bir dosya degil: {path}")

        if not self.supports(path):
            raise ValueError(
                f"Desteklenmeyen dosya formati: {path.suffix}. "
                f"Desteklenen formatlar: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

    @abstractmethod
    def parse(self, file_path: PathLike) -> T:
        """
        Dosyayi parse et.

        Args:
            file_path: Dosya yolu

        Returns:
            Parse edilmis icerik

        Raises:
            FileNotFoundError: Dosya bulunamadi
            ParsingError: Parse hatasi
        """
        pass

    def parse_safe(self, file_path: PathLike) -> Optional[T]:
        """
        Guvenli parse - hata durumunda None doner.

        Args:
            file_path: Dosya yolu

        Returns:
            Parse edilmis icerik veya None
        """
        try:
            return self.parse(file_path)
        except Exception as e:
            self.logger.error(f"Parse hatasi ({file_path}): {e}")
            return None

    def get_file_info(self, file_path: PathLike) -> Dict[str, Any]:
        """Dosya bilgilerini al."""
        path = Path(file_path)
        stat = path.stat()

        return {
            "path": str(path.absolute()),
            "name": path.name,
            "extension": path.suffix.lower(),
            "size": stat.st_size,
            "size_formatted": self._format_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Boyutu formatla."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def _clean_text(text: str) -> str:
        """Metni temizle."""
        if not text:
            return ""
        # Null karakterleri kaldir
        text = text.replace('\x00', '')
        # Fazla bosluklari temizle
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def _extract_tables_from_markdown(text: str) -> List[Dict[str, Any]]:
        """Markdown'dan tablo cikar."""
        import re

        tables: List[Dict[str, Any]] = []
        table_pattern = r'\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)+'

        for match in re.finditer(table_pattern, text):
            try:
                lines = match.group(0).strip().split('\n')
                if len(lines) >= 3:
                    # Header
                    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
                    # Data
                    data = []
                    for line in lines[2:]:
                        row = [c.strip() for c in line.split('|') if c.strip()]
                        if row:
                            data.append(row)

                    tables.append({
                        "headers": headers,
                        "data": data,
                        "row_count": len(data),
                        "column_count": len(headers)
                    })
            except Exception as e:
                logger.warning(f"Tablo parse hatasi: {e}")

        return tables


class ParserFactory:
    """Parser factory - dosya tipine gore parser olusturur."""

    _parsers: Dict[str, type] = {}

    @classmethod
    def register(cls, extensions: List[str], parser_class: type) -> None:
        """Parser kaydet."""
        for ext in extensions:
            cls._parsers[ext.lower()] = parser_class

    @classmethod
    def get_parser(cls, file_path: PathLike) -> Optional[BaseParser]:
        """Dosya icin uygun parser al."""
        ext = Path(file_path).suffix.lower()
        parser_class = cls._parsers.get(ext)

        if parser_class:
            return parser_class()
        return None

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """Desteklenen uzantilar."""
        return list(cls._parsers.keys())

    @classmethod
    def is_supported(cls, file_path: PathLike) -> bool:
        """Dosya destekleniyor mu."""
        ext = Path(file_path).suffix.lower()
        return ext in cls._parsers
