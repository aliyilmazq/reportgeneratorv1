"""
Custom Exceptions Module
========================
Uygulama genelinde kullanilan ozel exception siniflari.
Her exception kategorisi icin ayri sinif tanimlanmistir.
"""

from typing import Optional, Dict, Any


class ReportGeneratorError(Exception):
    """
    Tum uygulama hatalarinin temel sinifi.
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or "UNKNOWN_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Exception'i dict'e cevir."""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


# ═══════════════════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

class FileOperationError(ReportGeneratorError):
    """Dosya islemleri hatalari."""
    pass


class FileNotFoundError(FileOperationError):
    """Dosya bulunamadi hatasi."""

    def __init__(self, path: str):
        super().__init__(
            message=f"Dosya bulunamadi: {path}",
            code="FILE_NOT_FOUND",
            details={"path": path}
        )


class FileReadError(FileOperationError):
    """Dosya okuma hatasi."""

    def __init__(self, path: str, reason: str = ""):
        super().__init__(
            message=f"Dosya okunamadi: {path}" + (f" - {reason}" if reason else ""),
            code="FILE_READ_ERROR",
            details={"path": path, "reason": reason}
        )


class FileWriteError(FileOperationError):
    """Dosya yazma hatasi."""

    def __init__(self, path: str, reason: str = ""):
        super().__init__(
            message=f"Dosya yazilamadi: {path}" + (f" - {reason}" if reason else ""),
            code="FILE_WRITE_ERROR",
            details={"path": path, "reason": reason}
        )


class FileSizeError(FileOperationError):
    """Dosya boyutu hatasi."""

    def __init__(self, path: str, size_mb: float, max_size_mb: int):
        super().__init__(
            message=f"Dosya cok buyuk: {path} ({size_mb:.1f}MB > {max_size_mb}MB)",
            code="FILE_SIZE_EXCEEDED",
            details={"path": path, "size_mb": size_mb, "max_size_mb": max_size_mb}
        )


# ═══════════════════════════════════════════════════════════════════════════
# PARSING ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class ParsingError(ReportGeneratorError):
    """Parsing hatalari."""
    pass


class PDFParsingError(ParsingError):
    """PDF parse hatasi."""

    def __init__(self, path: str, reason: str = ""):
        super().__init__(
            message=f"PDF parse edilemedi: {path}" + (f" - {reason}" if reason else ""),
            code="PDF_PARSE_ERROR",
            details={"path": path, "reason": reason}
        )


class ExcelParsingError(ParsingError):
    """Excel parse hatasi."""

    def __init__(self, path: str, sheet: str = "", reason: str = ""):
        super().__init__(
            message=f"Excel parse edilemedi: {path}" + (f" [{sheet}]" if sheet else "") + (f" - {reason}" if reason else ""),
            code="EXCEL_PARSE_ERROR",
            details={"path": path, "sheet": sheet, "reason": reason}
        )


class NumberParsingError(ParsingError):
    """Sayi parse hatasi."""

    def __init__(self, value: str, expected_format: str = ""):
        super().__init__(
            message=f"Sayi parse edilemedi: '{value}'" + (f" (beklenen format: {expected_format})" if expected_format else ""),
            code="NUMBER_PARSE_ERROR",
            details={"value": value, "expected_format": expected_format}
        )


class TableParsingError(ParsingError):
    """Tablo parse hatasi."""

    def __init__(self, reason: str = ""):
        super().__init__(
            message=f"Tablo parse edilemedi" + (f": {reason}" if reason else ""),
            code="TABLE_PARSE_ERROR",
            details={"reason": reason}
        )


# ═══════════════════════════════════════════════════════════════════════════
# API ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class APIError(ReportGeneratorError):
    """API hatalari."""
    pass


class APIConnectionError(APIError):
    """API baglanti hatasi."""

    def __init__(self, service: str, reason: str = ""):
        super().__init__(
            message=f"API'ye baglanamadi: {service}" + (f" - {reason}" if reason else ""),
            code="API_CONNECTION_ERROR",
            details={"service": service, "reason": reason}
        )


class APITimeoutError(APIError):
    """API timeout hatasi."""

    def __init__(self, service: str, timeout_seconds: int):
        super().__init__(
            message=f"API istegi zaman asimina ugradi: {service} ({timeout_seconds}s)",
            code="API_TIMEOUT",
            details={"service": service, "timeout_seconds": timeout_seconds}
        )


class APIRateLimitError(APIError):
    """API rate limit hatasi."""

    def __init__(self, service: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"API rate limit asildi: {service}" + (f" (tekrar dene: {retry_after}s)" if retry_after else ""),
            code="API_RATE_LIMIT",
            details={"service": service, "retry_after": retry_after}
        )


class APIAuthenticationError(APIError):
    """API authentication hatasi."""

    def __init__(self, service: str):
        super().__init__(
            message=f"API kimlik dogrulamasi basarisiz: {service}",
            code="API_AUTH_ERROR",
            details={"service": service}
        )


class APIResponseError(APIError):
    """API response hatasi."""

    def __init__(self, service: str, status_code: int, response: str = ""):
        super().__init__(
            message=f"API hatali yanit: {service} (HTTP {status_code})",
            code="API_RESPONSE_ERROR",
            details={"service": service, "status_code": status_code, "response": response[:500]}
        )


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class ValidationError(ReportGeneratorError):
    """Validation hatalari."""
    pass


class InputValidationError(ValidationError):
    """Input validation hatasi."""

    def __init__(self, field: str, value: Any, reason: str = ""):
        super().__init__(
            message=f"Gecersiz input: {field}" + (f" - {reason}" if reason else ""),
            code="INPUT_VALIDATION_ERROR",
            details={"field": field, "value": str(value)[:100], "reason": reason}
        )


class ContentValidationError(ValidationError):
    """Icerik validation hatasi."""

    def __init__(self, section: str, issue: str):
        super().__init__(
            message=f"Icerik dogrulamasi basarisiz: {section} - {issue}",
            code="CONTENT_VALIDATION_ERROR",
            details={"section": section, "issue": issue}
        )


class QualityValidationError(ValidationError):
    """Kalite validation hatasi."""

    def __init__(self, score: float, min_score: float):
        super().__init__(
            message=f"Kalite puani yetersiz: {score:.1%} < {min_score:.1%}",
            code="QUALITY_VALIDATION_ERROR",
            details={"score": score, "min_score": min_score}
        )


# ═══════════════════════════════════════════════════════════════════════════
# SECURITY ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class SecurityError(ReportGeneratorError):
    """Guvenlik hatalari."""
    pass


class PathTraversalError(SecurityError):
    """Path traversal hatasi."""

    def __init__(self, path: str):
        super().__init__(
            message=f"Guvenlik ihlali: Path traversal tespit edildi",
            code="PATH_TRAVERSAL",
            details={"attempted_path": path[:100]}
        )


class PromptInjectionError(SecurityError):
    """Prompt injection hatasi."""

    def __init__(self, pattern: str = ""):
        super().__init__(
            message="Guvenlik ihlali: Prompt injection tespit edildi",
            code="PROMPT_INJECTION",
            details={"pattern": pattern}
        )


class URLValidationError(SecurityError):
    """URL validation hatasi."""

    def __init__(self, url: str, reason: str = ""):
        super().__init__(
            message=f"Gecersiz URL" + (f": {reason}" if reason else ""),
            code="URL_VALIDATION_ERROR",
            details={"url": url[:200], "reason": reason}
        )


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class ConfigurationError(ReportGeneratorError):
    """Konfigurasyon hatalari."""
    pass


class RulesLoadError(ConfigurationError):
    """Kural yukleme hatasi."""

    def __init__(self, rule_file: str, reason: str = ""):
        super().__init__(
            message=f"Kural dosyasi yuklenemedi: {rule_file}" + (f" - {reason}" if reason else ""),
            code="RULES_LOAD_ERROR",
            details={"rule_file": rule_file, "reason": reason}
        )


class TemplateLoadError(ConfigurationError):
    """Template yukleme hatasi."""

    def __init__(self, template: str, reason: str = ""):
        super().__init__(
            message=f"Template yuklenemedi: {template}" + (f" - {reason}" if reason else ""),
            code="TEMPLATE_LOAD_ERROR",
            details={"template": template, "reason": reason}
        )


class ConfigFileError(ConfigurationError):
    """Config dosyasi hatasi."""

    def __init__(self, config_file: str, reason: str = ""):
        super().__init__(
            message=f"Config dosyasi okunamadi: {config_file}" + (f" - {reason}" if reason else ""),
            code="CONFIG_FILE_ERROR",
            details={"config_file": config_file, "reason": reason}
        )


# ═══════════════════════════════════════════════════════════════════════════
# CACHE ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class CacheError(ReportGeneratorError):
    """Cache hatalari."""
    pass


class CacheReadError(CacheError):
    """Cache okuma hatasi."""

    def __init__(self, key: str, reason: str = ""):
        super().__init__(
            message=f"Cache okunamadi: {key}" + (f" - {reason}" if reason else ""),
            code="CACHE_READ_ERROR",
            details={"key": key, "reason": reason}
        )


class CacheWriteError(CacheError):
    """Cache yazma hatasi."""

    def __init__(self, key: str, reason: str = ""):
        super().__init__(
            message=f"Cache yazilamadi: {key}" + (f" - {reason}" if reason else ""),
            code="CACHE_WRITE_ERROR",
            details={"key": key, "reason": reason}
        )


# ═══════════════════════════════════════════════════════════════════════════
# GENERATION ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class GenerationError(ReportGeneratorError):
    """Uretim hatalari."""
    pass


class ContentGenerationError(GenerationError):
    """Icerik uretim hatasi."""

    def __init__(self, section: str, reason: str = ""):
        super().__init__(
            message=f"Icerik uretilemedi: {section}" + (f" - {reason}" if reason else ""),
            code="CONTENT_GENERATION_ERROR",
            details={"section": section, "reason": reason}
        )


class DocumentGenerationError(GenerationError):
    """Dokuman uretim hatasi."""

    def __init__(self, format: str, reason: str = ""):
        super().__init__(
            message=f"Dokuman uretilemedi ({format})" + (f": {reason}" if reason else ""),
            code="DOCUMENT_GENERATION_ERROR",
            details={"format": format, "reason": reason}
        )


class ChartGenerationError(GenerationError):
    """Grafik uretim hatasi."""

    def __init__(self, chart_type: str, reason: str = ""):
        super().__init__(
            message=f"Grafik uretilemedi ({chart_type})" + (f": {reason}" if reason else ""),
            code="CHART_GENERATION_ERROR",
            details={"chart_type": chart_type, "reason": reason}
        )
