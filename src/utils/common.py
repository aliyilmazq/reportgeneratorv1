"""
Common Utilities Module
=======================
Ortak yardimci fonksiyonlar ve siniflar.
Kod tekrarini onlemek icin merkezi utility'ler.
"""

import re
import time
import hashlib
import logging
from typing import (
    TypeVar, Generic, Optional, Any, Dict, List, Union,
    Callable, Tuple, Iterator
)
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Metni belirli uzunluga kisalt."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """Metni temizle - fazla bosluklar, null karakterler."""
    if not text:
        return ""
    # Null karakterleri kaldir
    text = text.replace('\x00', '')
    # Fazla bosluklari tek bosluga indir
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_first_sentence(text: str, max_length: int = 200) -> str:
    """Ilk cumleyi cikar."""
    if not text:
        return ""
    # Cumle sonu isaretleri
    match = re.search(r'^[^.!?]*[.!?]', text)
    if match:
        sentence = match.group(0).strip()
        return truncate_text(sentence, max_length)
    return truncate_text(text, max_length)


def word_count(text: str) -> int:
    """Kelime sayisi."""
    if not text:
        return 0
    return len(text.split())


def paragraph_count(text: str, min_length: int = 50) -> int:
    """Paragraf sayisi."""
    if not text:
        return 0
    paragraphs = [p for p in text.split('\n\n') if len(p.strip()) >= min_length]
    return len(paragraphs)


def normalize_whitespace(text: str) -> str:
    """Bosluk karakterlerini normalize et."""
    if not text:
        return ""
    # Tab -> space
    text = text.replace('\t', ' ')
    # Birden fazla space -> tek space
    text = re.sub(r' +', ' ', text)
    # Birden fazla newline -> iki newline (paragraf ayirici)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# NUMBER UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def format_number(value: Union[int, float], locale: str = "tr") -> str:
    """Sayiyi locale'e gore formatla."""
    if isinstance(value, int):
        if locale == "tr":
            return f"{value:,}".replace(",", ".")
        return f"{value:,}"
    else:
        if locale == "tr":
            formatted = f"{value:,.2f}"
            # 1,234.56 -> 1.234,56
            return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{value:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Yuzde formatla."""
    return f"%{value:.{decimals}f}"


def format_currency(
    value: Union[int, float],
    currency: str = "TRY",
    locale: str = "tr"
) -> str:
    """Para birimi formatla."""
    symbols = {"TRY": "₺", "USD": "$", "EUR": "€"}
    symbol = symbols.get(currency, currency)
    formatted = format_number(value, locale)
    if locale == "tr":
        return f"{formatted} {symbol}"
    return f"{symbol}{formatted}"


def safe_divide(
    numerator: Union[int, float],
    denominator: Union[int, float],
    default: float = 0.0
) -> float:
    """Guvenli bolme - sifira bolmeyi onle."""
    if denominator == 0:
        return default
    return numerator / denominator


# ═══════════════════════════════════════════════════════════════════════════════
# FILE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def format_file_size(size_bytes: int) -> str:
    """Dosya boyutunu okunabilir formata cevir."""
    if size_bytes < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_file_extension(file_path: Union[str, Path]) -> str:
    """Dosya uzantisini al (lowercase)."""
    return Path(file_path).suffix.lower()


def generate_unique_filename(
    base_name: str,
    extension: str,
    output_dir: Union[str, Path] = "."
) -> Path:
    """Benzersiz dosya adi olustur."""
    output_dir = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}{extension}"
    return output_dir / filename


def ensure_directory(path: Union[str, Path]) -> Path:
    """Dizinin var olmasini sagla."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# HASH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def generate_hash(content: str, algorithm: str = "md5") -> str:
    """Icerik hash'i olustur."""
    if algorithm == "md5":
        return hashlib.md5(content.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(content.encode()).hexdigest()
    else:
        return hashlib.md5(content.encode()).hexdigest()


def generate_cache_key(*args: Any, **kwargs: Any) -> str:
    """Cache anahtari olustur."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    combined = ":".join(key_parts)
    return generate_hash(combined)


# ═══════════════════════════════════════════════════════════════════════════════
# TIME UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def format_duration(seconds: float) -> str:
    """Sure formatla."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_timestamp() -> str:
    """Simdi icin timestamp al."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_date_str() -> str:
    """Bugunku tarihi al."""
    return datetime.now().strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

def timed(func: Callable[..., T]) -> Callable[..., Tuple[T, float]]:
    """Fonksiyon suresini olc."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Tuple[T, float]:
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        return result, duration
    return wrapper


def log_call(
    level: int = logging.DEBUG,
    include_args: bool = False
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Fonksiyon cagrisini logla."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            func_name = func.__name__
            if include_args:
                logger.log(level, f"Calling {func_name} with args={args}, kwargs={kwargs}")
            else:
                logger.log(level, f"Calling {func_name}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func_name} failed: {e}")
                raise
        return wrapper
    return decorator


def deprecated(reason: str = "") -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Fonksiyonu deprecated olarak isaretle."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import warnings
            msg = f"{func.__name__} is deprecated"
            if reason:
                msg += f": {reason}"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Result(Generic[T]):
    """Generic sonuc wrapper."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    duration: float = 0.0

    @classmethod
    def ok(cls, data: T, duration: float = 0.0) -> 'Result[T]':
        """Basarili sonuc."""
        return cls(success=True, data=data, duration=duration)

    @classmethod
    def fail(cls, error: str) -> 'Result[T]':
        """Basarisiz sonuc."""
        return cls(success=False, error=error)


@dataclass
class BatchResult(Generic[T]):
    """Toplu islem sonucu."""
    total: int
    succeeded: int
    failed: int
    results: List[Result[T]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Basari orani."""
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total


# ═══════════════════════════════════════════════════════════════════════════════
# ITERATION UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def chunked(iterable: List[T], size: int) -> Iterator[List[T]]:
    """Listeyi belirli boyutta parcalara bol."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def first_or_none(iterable: List[T]) -> Optional[T]:
    """Ilk elemani dondur veya None."""
    return iterable[0] if iterable else None


def unique_by(
    items: List[T],
    key: Callable[[T], Any]
) -> List[T]:
    """Key'e gore benzersiz elemanlar."""
    seen: set = set()
    result: List[T] = []
    for item in items:
        k = key(item)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result
