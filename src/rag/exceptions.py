"""
RAG Hata Yonetimi Modulu.

Ozel exception siniflarini ve hata isleyicilerini tanimlar.
"""

from typing import Optional, Dict, Any
from functools import wraps
import traceback

from ..utils.logger import get_rag_logger

logger = get_rag_logger("exceptions")


# ============================================================
# Base Exception
# ============================================================

class RAGException(Exception):
    """RAG sistemi temel exception sinifi."""

    def __init__(
        self,
        message: str,
        error_code: str = "RAG_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Exception'i dict olarak dondur."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


# ============================================================
# Embedding Exceptions
# ============================================================

class EmbeddingException(RAGException):
    """Embedding islemleri hatasi."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EMBEDDING_ERROR", details)


class ModelLoadError(EmbeddingException):
    """Model yukleme hatasi."""

    def __init__(self, model_name: str, reason: str = ""):
        message = f"Model yuklenemedi: {model_name}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, {"model_name": model_name, "reason": reason})


class EmbeddingTimeoutError(EmbeddingException):
    """Embedding timeout hatasi."""

    def __init__(self, timeout_seconds: float, batch_size: int = 0):
        message = f"Embedding islemi {timeout_seconds}s timeout'a ulasti"
        super().__init__(message, {"timeout": timeout_seconds, "batch_size": batch_size})


# ============================================================
# Retrieval Exceptions
# ============================================================

class RetrievalException(RAGException):
    """Retrieval islemleri hatasi."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RETRIEVAL_ERROR", details)


class IndexNotFoundError(RetrievalException):
    """Index bulunamadi hatasi."""

    def __init__(self, index_name: str = ""):
        message = "Arama index'i bulunamadi"
        if index_name:
            message += f": {index_name}"
        super().__init__(message, {"index_name": index_name})


class EmptyQueryError(RetrievalException):
    """Bos sorgu hatasi."""

    def __init__(self):
        super().__init__("Arama sorgusu bos olamaz", {})


class NoResultsError(RetrievalException):
    """Sonuc bulunamadi hatasi."""

    def __init__(self, query: str):
        super().__init__(
            f"Sorgu icin sonuc bulunamadi: {query[:50]}...",
            {"query": query}
        )


# ============================================================
# Document Processing Exceptions
# ============================================================

class DocumentException(RAGException):
    """Dokuman isleme hatasi."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DOCUMENT_ERROR", details)


class DocumentParseError(DocumentException):
    """Dokuman parse hatasi."""

    def __init__(self, document_id: str, reason: str = ""):
        message = f"Dokuman parse edilemedi: {document_id}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, {"document_id": document_id, "reason": reason})


class ChunkingError(DocumentException):
    """Chunking hatasi."""

    def __init__(self, document_id: str, reason: str = ""):
        message = f"Dokuman parcalanamadi: {document_id}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, {"document_id": document_id, "reason": reason})


class EmptyDocumentError(DocumentException):
    """Bos dokuman hatasi."""

    def __init__(self, document_id: str = ""):
        message = "Dokuman icerigi bos"
        super().__init__(message, {"document_id": document_id})


# ============================================================
# Configuration Exceptions
# ============================================================

class ConfigurationException(RAGException):
    """Konfigurasyon hatasi."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class ConfigFileNotFoundError(ConfigurationException):
    """Konfigurasyon dosyasi bulunamadi."""

    def __init__(self, file_path: str):
        super().__init__(
            f"Konfigurasyon dosyasi bulunamadi: {file_path}",
            {"file_path": file_path}
        )


class InvalidConfigError(ConfigurationException):
    """Gecersiz konfigurasyon."""

    def __init__(self, key: str, value: Any, expected: str):
        super().__init__(
            f"Gecersiz konfigurasyon: {key}={value}, beklenen: {expected}",
            {"key": key, "value": value, "expected": expected}
        )


# ============================================================
# Cache Exceptions
# ============================================================

class CacheException(RAGException):
    """Cache hatasi."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CACHE_ERROR", details)


class CacheConnectionError(CacheException):
    """Cache baglanti hatasi."""

    def __init__(self, cache_type: str, host: str = ""):
        message = f"Cache'e baglanılamadı: {cache_type}"
        if host:
            message += f" ({host})"
        super().__init__(message, {"cache_type": cache_type, "host": host})


# ============================================================
# LLM Exceptions
# ============================================================

class LLMException(RAGException):
    """LLM API hatasi."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "LLM_ERROR", details)


class LLMRateLimitError(LLMException):
    """Rate limit hatasi."""

    def __init__(self, retry_after: int = 0):
        message = "API rate limit asildi"
        if retry_after:
            message += f", {retry_after}s sonra tekrar deneyin"
        super().__init__(message, {"retry_after": retry_after})


class LLMContextLengthError(LLMException):
    """Context uzunluk hatasi."""

    def __init__(self, current_tokens: int, max_tokens: int):
        super().__init__(
            f"Context cok uzun: {current_tokens} > {max_tokens} token",
            {"current_tokens": current_tokens, "max_tokens": max_tokens}
        )


# ============================================================
# Validation Exceptions
# ============================================================

class ValidationException(RAGException):
    """Dogrulama hatasi."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class InputValidationError(ValidationException):
    """Girdi dogrulama hatasi."""

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Gecersiz girdi: {field} - {reason}",
            {"field": field, "value": str(value)[:100], "reason": reason}
        )


# ============================================================
# Error Handler Decorator
# ============================================================

def handle_rag_errors(
    default_return: Any = None,
    log_error: bool = True,
    reraise: bool = False
):
    """
    RAG hatalarini yoneten decorator.

    Kullanim:
        @handle_rag_errors(default_return=[], log_error=True)
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RAGException as e:
                if log_error:
                    logger.error(str(e), error_code=e.error_code, details=e.details)
                if reraise:
                    raise
                return default_return
            except Exception as e:
                if log_error:
                    logger.error(
                        f"Beklenmeyen hata: {str(e)}",
                        exc_info=True,
                        traceback=traceback.format_exc()
                    )
                if reraise:
                    raise RAGException(str(e), "UNEXPECTED_ERROR")
                return default_return
        return wrapper
    return decorator


def safe_execute(
    func,
    *args,
    default: Any = None,
    exception_types: tuple = (Exception,),
    **kwargs
) -> Any:
    """
    Guvenlı fonksiyon calistirma.

    Args:
        func: Calistirilacak fonksiyon
        *args: Pozisyonel argumanlar
        default: Hata durumunda dondurulecek deger
        exception_types: Yakalanacak exception tipleri
        **kwargs: Keyword argumanlar

    Returns:
        Fonksiyon sonucu veya default
    """
    try:
        return func(*args, **kwargs)
    except exception_types as e:
        logger.warning(f"Guvenli calistirma hatasi: {e}")
        return default


class ErrorContext:
    """
    Error context manager.

    Kullanim:
        with ErrorContext("embedding islem"):
            # islem
    """

    def __init__(self, operation: str, reraise: bool = True):
        self.operation = operation
        self.reraise = reraise
        self.error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error = exc_val

            if isinstance(exc_val, RAGException):
                logger.error(f"{self.operation} hatasi: {exc_val}")
            else:
                logger.error(
                    f"{self.operation} hatasi: {exc_val}",
                    exc_info=True
                )

            if not self.reraise:
                return True  # Exception'i yut

        return False
