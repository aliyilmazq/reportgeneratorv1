"""
Centralized Configuration Constants
====================================
Tum uygulama genelinde kullanilan sabit degerler.
Magic number'lar ve hardcoded degerler burada tanimlanir.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


@dataclass(frozen=True)
class TimeoutConfig:
    """Timeout ayarlari."""
    API_TIMEOUT: int = 30  # Claude API timeout (saniye)
    HTTP_TIMEOUT: int = 15  # Web istekleri timeout
    FILE_OPERATION_TIMEOUT: int = 60  # Dosya islemleri timeout


@dataclass(frozen=True)
class RetryConfig:
    """Retry ayarlari."""
    MAX_ATTEMPTS: int = 3  # Maksimum deneme sayisi
    MIN_WAIT: int = 2  # Minimum bekleme (saniye)
    MAX_WAIT: int = 10  # Maksimum bekleme (saniye)
    MULTIPLIER: float = 1.5  # Exponential backoff carpani


@dataclass(frozen=True)
class LimitConfig:
    """Limit ayarlari."""
    MAX_FILE_SIZE_MB: int = 100  # Maksimum dosya boyutu
    MAX_CACHE_ENTRIES: int = 1000  # Cache'de maksimum girdi
    MAX_CONTENT_LENGTH: int = 10000  # Icerik maksimum uzunluk
    MAX_PROMPT_LENGTH: int = 50000  # Prompt maksimum uzunluk
    MAX_SOURCES_PER_SECTION: int = 8  # Bolum basina maksimum kaynak
    MAX_RETRY_CONTENT_LENGTH: int = 5000  # Retry icin icerik limiti

    # Pagination
    SEARCH_RESULTS_LIMIT: int = 10  # Arama sonucu limiti
    TABLE_ROWS_LIMIT: int = 50  # Tablo satir limiti

    # Text limits
    SNIPPET_LENGTH: int = 200  # Ozet metin uzunlugu
    TITLE_MAX_LENGTH: int = 100  # Baslik maksimum uzunluk
    URL_MAX_LENGTH: int = 2000  # URL maksimum uzunluk


@dataclass(frozen=True)
class ParsingConfig:
    """Parsing ayarlari."""
    # Turkce format
    TURKISH_DECIMAL_SEP: str = ","
    TURKISH_THOUSAND_SEP: str = "."

    # US format
    US_DECIMAL_SEP: str = "."
    US_THOUSAND_SEP: str = ","

    # Minimum degerler
    MIN_WORDS_PER_SECTION: int = 300
    MIN_PARAGRAPHS_PER_SECTION: int = 3
    MIN_SOURCES_PER_SECTION: int = 2
    MIN_QUALITY_SCORE: float = 0.6

    # Paragraph detection
    MIN_PARAGRAPH_LENGTH: int = 50
    PARAGRAPH_SEPARATOR: str = "\n\n"


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting ayarlari."""
    DELAY_BETWEEN_REQUESTS: float = 0.5  # Istekler arasi bekleme
    DELAY_BETWEEN_SEARCHES: float = 1.0  # Arama istekleri arasi
    DELAY_BETWEEN_API_CALLS: float = 0.3  # API cagrilari arasi
    MAX_REQUESTS_PER_MINUTE: int = 60  # Dakikada maksimum istek


@dataclass(frozen=True)
class SecurityConfig:
    """Guvenlik ayarlari."""
    # Izin verilen dosya uzantilari
    ALLOWED_EXTENSIONS: Set[str] = field(default_factory=lambda: {
        '.pdf', '.xlsx', '.xls', '.csv', '.docx', '.doc',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'
    })

    # Yasakli path pattern'leri
    FORBIDDEN_PATH_PATTERNS: List[str] = field(default_factory=lambda: [
        '..', '/etc/', '/var/', '/usr/', '/root/', '/home/',
        'passwd', 'shadow', '.ssh', '.env', 'credentials'
    ])

    # Prompt injection pattern'leri
    INJECTION_PATTERNS: List[str] = field(default_factory=lambda: [
        r'ignore.*previous.*instructions',
        r'forget.*everything',
        r'override.*system',
        r'new.*instructions',
        r'act.*as.*if',
        r'pretend.*to.*be'
    ])

    # Guvenilir domain'ler
    TRUSTED_DOMAINS: Set[str] = field(default_factory=lambda: {
        'tuik.gov.tr', 'tcmb.gov.tr', 'hazine.gov.tr',
        'tbb.org.tr', 'bddk.org.tr', 'spk.gov.tr',
        'reuters.com', 'bloomberg.com', 'imf.org',
        'worldbank.org', 'oecd.org', 'tradingeconomics.com'
    })


@dataclass(frozen=True)
class CacheConfig:
    """Cache ayarlari."""
    QUERY_TTL_HOURS: int = 24  # Sorgu cache suresi
    EMBEDDING_TTL_DAYS: int = 7  # Embedding cache suresi
    RESULT_TTL_MINUTES: int = 30  # Sonuc cache suresi

    # Cache dizinleri
    CACHE_BASE_DIR: str = ".cache"
    QUERY_CACHE_DIR: str = "query"
    EMBEDDING_CACHE_DIR: str = "embeddings"
    RESULT_CACHE_DIR: str = "results"


@dataclass(frozen=True)
class LoggingConfig:
    """Logging ayarlari."""
    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MAX_LOG_SIZE_MB: int = 10
    BACKUP_COUNT: int = 5


@dataclass(frozen=True)
class ModelConfig:
    """AI model ayarlari."""
    DEFAULT_MODEL: str = "claude-sonnet-4-20250514"
    FALLBACK_MODEL: str = "claude-sonnet-4-20250514"
    MAX_TOKENS_DEFAULT: int = 4000
    MAX_TOKENS_LARGE: int = 8000
    TEMPERATURE_DEFAULT: float = 0.7
    TEMPERATURE_CREATIVE: float = 0.9
    TEMPERATURE_PRECISE: float = 0.3


@dataclass
class AppConfig:
    """
    Ana uygulama konfigurasyonu.
    Tum alt konfigurasyonlari icerir.
    """
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    limits: LimitConfig = field(default_factory=LimitConfig)
    parsing: ParsingConfig = field(default_factory=ParsingConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    model: ModelConfig = field(default_factory=ModelConfig)

    # Paths
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    OUTPUT_DIR: Path = field(default_factory=lambda: Path("output"))
    TEMPLATES_DIR: Path = field(default_factory=lambda: Path("templates"))
    RULES_DIR: Path = field(default_factory=lambda: Path("rules"))


# Global singleton instance
CONFIG = AppConfig()


# Convenience accessors
def get_config() -> AppConfig:
    """Get global config instance."""
    return CONFIG


def get_timeout(key: str) -> int:
    """Get timeout value by key."""
    return getattr(CONFIG.timeouts, key, 30)


def get_limit(key: str) -> int:
    """Get limit value by key."""
    return getattr(CONFIG.limits, key, 1000)
