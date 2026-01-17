"""
Merkezi Logging Modulu - Tum RAG bilesenleri icin.

Ozellikler:
- Yapılandırılmis log formati
- Farkli log seviyeleri (DEBUG, INFO, WARNING, ERROR)
- Dosya ve konsol ciktisi
- Performans metrikleri
- Opsiyonel JSON formati
"""

import logging
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from functools import wraps
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler

# Rich console
from rich.logging import RichHandler
from rich.console import Console

console = Console()


@dataclass
class LogConfig:
    """Logger konfigurasyonu."""
    name: str = "rag_system"
    level: str = "INFO"
    log_to_file: bool = True
    log_to_console: bool = True
    log_dir: str = "logs"
    use_rich: bool = True
    json_format: bool = False
    include_timestamp: bool = True
    include_module: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5


@dataclass
class PerformanceMetric:
    """Performans metrigi."""
    operation: str
    duration_ms: float
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RAGLogger:
    """
    RAG sistemi icin merkezi logger.

    Kullanim:
        logger = RAGLogger.get_logger("embedder")
        logger.info("Embedding islemi basladi")
        logger.debug("Detay bilgisi", extra={"batch_size": 32})
    """

    _loggers: Dict[str, 'RAGLogger'] = {}
    _config: Optional[LogConfig] = None
    _performance_metrics: list = []

    def __init__(self, name: str, config: Optional[LogConfig] = None):
        self.name = name
        self.config = config or RAGLogger._config or LogConfig()
        self._logger = self._setup_logger()
        self._metrics: list = []

    @classmethod
    def configure(cls, config: LogConfig):
        """Global konfigurasyon ayarla."""
        cls._config = config
        # Mevcut logger'lari guncelle
        for logger in cls._loggers.values():
            logger.config = config
            logger._logger = logger._setup_logger()

    @classmethod
    def get_logger(cls, name: str) -> 'RAGLogger':
        """Logger al veya olustur."""
        if name not in cls._loggers:
            cls._loggers[name] = RAGLogger(name)
        return cls._loggers[name]

    def _setup_logger(self) -> logging.Logger:
        """Logger'i konfigure et."""
        logger = logging.getLogger(f"rag.{self.name}")
        logger.setLevel(getattr(logging, self.config.level.upper()))

        # Mevcut handler'lari temizle
        logger.handlers.clear()

        # Formatter
        if self.config.json_format:
            formatter = JsonFormatter()
        else:
            format_parts = []
            if self.config.include_timestamp:
                format_parts.append("%(asctime)s")
            format_parts.append("[%(levelname)s]")
            if self.config.include_module:
                format_parts.append("[%(name)s]")
            format_parts.append("%(message)s")
            formatter = logging.Formatter(" ".join(format_parts))

        # Console handler
        if self.config.log_to_console:
            if self.config.use_rich:
                console_handler = RichHandler(
                    console=Console(stderr=True),
                    show_time=self.config.include_timestamp,
                    show_path=False,
                    rich_tracebacks=True
                )
            else:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # File handler
        if self.config.log_to_file:
            log_dir = Path(self.config.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / f"{self.config.name}_{datetime.now().strftime('%Y%m%d')}.log"

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.config.max_file_size_mb * 1024 * 1024,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def debug(self, msg: str, **kwargs):
        """Debug seviyesi log."""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """Info seviyesi log."""
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """Warning seviyesi log."""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, exc_info: bool = False, **kwargs):
        """Error seviyesi log."""
        self._log(logging.ERROR, msg, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, exc_info: bool = True, **kwargs):
        """Critical seviyesi log."""
        self._log(logging.CRITICAL, msg, exc_info=exc_info, **kwargs)

    def _log(self, level: int, msg: str, exc_info: bool = False, **kwargs):
        """Dahili log metodu."""
        extra = kwargs.pop('extra', {})
        extra.update(kwargs)

        if extra and not self.config.json_format:
            # Extra bilgileri mesaja ekle
            extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
            msg = f"{msg} ({extra_str})"

        self._logger.log(level, msg, exc_info=exc_info, extra={'extra_data': extra})

    @contextmanager
    def timer(self, operation: str, log_level: str = "INFO"):
        """
        Islem suresi olcumu.

        Kullanim:
            with logger.timer("embedding"):
                # islem
        """
        start = time.perf_counter()
        success = True
        error_msg = None

        try:
            yield
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000

            metric = PerformanceMetric(
                operation=operation,
                duration_ms=round(duration_ms, 2),
                success=success,
                details={"error": error_msg} if error_msg else {}
            )
            self._metrics.append(metric)
            RAGLogger._performance_metrics.append(metric)

            level = getattr(logging, log_level.upper())
            status = "tamamlandi" if success else "basarisiz"
            self._log(level, f"{operation} {status}", duration_ms=duration_ms)

    def log_performance(self, operation: str, duration_ms: float, **details):
        """Manuel performans logu."""
        metric = PerformanceMetric(
            operation=operation,
            duration_ms=duration_ms,
            success=True,
            details=details
        )
        self._metrics.append(metric)
        self.info(f"{operation} tamamlandi", duration_ms=duration_ms, **details)

    def get_metrics(self) -> list:
        """Bu logger'in metriklerini getir."""
        return self._metrics

    @classmethod
    def get_all_metrics(cls) -> list:
        """Tum metrikleri getir."""
        return cls._performance_metrics

    @classmethod
    def export_metrics(cls, filepath: str = None) -> str:
        """Metrikleri JSON olarak export et."""
        metrics_data = [asdict(m) for m in cls._performance_metrics]

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
            return filepath

        return json.dumps(metrics_data, indent=2, ensure_ascii=False)

    @classmethod
    def reset_metrics(cls):
        """Metrikleri sifirla."""
        cls._performance_metrics.clear()
        for logger in cls._loggers.values():
            logger._metrics.clear()


class JsonFormatter(logging.Formatter):
    """JSON formati log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Extra data varsa ekle
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data

        # Exception bilgisi
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def log_function_call(logger_name: str = None, log_args: bool = True, log_result: bool = False):
    """
    Fonksiyon cagrilarini loglayan decorator.

    Kullanim:
        @log_function_call("embedder")
        def embed_text(text: str) -> List[float]:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = logger_name or func.__module__
            logger = RAGLogger.get_logger(name)

            # Argumanlari logla
            if log_args:
                arg_info = []
                if args:
                    arg_info.append(f"args={len(args)}")
                if kwargs:
                    arg_info.append(f"kwargs={list(kwargs.keys())}")
                logger.debug(f"{func.__name__} cagriliyor: {', '.join(arg_info)}")

            # Fonksiyonu calistir
            with logger.timer(func.__name__, log_level="DEBUG"):
                result = func(*args, **kwargs)

            # Sonucu logla
            if log_result and result is not None:
                result_type = type(result).__name__
                if hasattr(result, '__len__'):
                    logger.debug(f"{func.__name__} sonuc: {result_type}[{len(result)}]")
                else:
                    logger.debug(f"{func.__name__} sonuc: {result_type}")

            return result
        return wrapper
    return decorator


# ============================================================
# Backward Compatibility - Eski API'yi koru
# ============================================================

def setup_logger(name: str = "rapor_uretici", level: int = logging.INFO) -> logging.Logger:
    """Ana logger'ı yapılandır (eski API)."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_time=False,
            show_path=False,
            markup=True
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger


def get_logger(name: str = "rapor_uretici") -> logging.Logger:
    """Mevcut logger'ı al (eski API)."""
    return logging.getLogger(name)


# ============================================================
# Yeni Kisa Yollar
# ============================================================

def get_rag_logger(name: str) -> RAGLogger:
    """RAG logger al."""
    return RAGLogger.get_logger(name)


def configure_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str = "logs",
    use_rich: bool = True,
    json_format: bool = False
):
    """
    Logging sistemini konfigure et.

    Args:
        level: Log seviyesi (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Dosyaya log yaz
        log_dir: Log dizini
        use_rich: Rich console kullan
        json_format: JSON formati kullan
    """
    config = LogConfig(
        level=level,
        log_to_file=log_to_file,
        log_dir=log_dir,
        use_rich=use_rich,
        json_format=json_format
    )
    RAGLogger.configure(config)


# Varsayilan logger
_default_logger = None


def log_info(msg: str, **kwargs):
    """Varsayilan logger ile info log."""
    global _default_logger
    if _default_logger is None:
        _default_logger = RAGLogger.get_logger("rag")
    _default_logger.info(msg, **kwargs)


def log_error(msg: str, exc_info: bool = False, **kwargs):
    """Varsayilan logger ile error log."""
    global _default_logger
    if _default_logger is None:
        _default_logger = RAGLogger.get_logger("rag")
    _default_logger.error(msg, exc_info=exc_info, **kwargs)


def log_debug(msg: str, **kwargs):
    """Varsayilan logger ile debug log."""
    global _default_logger
    if _default_logger is None:
        _default_logger = RAGLogger.get_logger("rag")
    _default_logger.debug(msg, **kwargs)


def log_warning(msg: str, **kwargs):
    """Varsayilan logger ile warning log."""
    global _default_logger
    if _default_logger is None:
        _default_logger = RAGLogger.get_logger("rag")
    _default_logger.warning(msg, **kwargs)
