"""
Input Validation Module
=======================
Tum input validation islemleri icin merkezi modul.
Guvenlik kontrolleri, format dogrulamalari ve sanitization.
"""

import re
import os
from pathlib import Path
from typing import Optional, List, Any, Union
from urllib.parse import urlparse

from .exceptions import (
    InputValidationError,
    PathTraversalError,
    URLValidationError,
    PromptInjectionError,
    FileSizeError
)

# Config import - lazy to avoid circular imports
_config = None

def _get_config():
    """Config'i guvenli sekilde yukle."""
    global _config
    if _config is None:
        try:
            from ..config.constants import CONFIG
            _config = CONFIG
        except (ImportError, ValueError):
            # Fallback: Test veya standalone kullanim icin
            class DefaultConfig:
                class security:
                    ALLOWED_BASE_DIR = Path.cwd()
                    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
                    BLOCKED_DOMAINS = ["localhost", "127.0.0.1", "0.0.0.0"]
                    BLOCKED_EXTENSIONS = [".exe", ".bat", ".sh", ".ps1"]
                    FORBIDDEN_PATH_PATTERNS = [
                        r'\.\.',
                        r'\.\./',
                        r'/\.\.',
                        r'\\\.\\.',
                    ]
                    INJECTION_PATTERNS = [
                        r'ignore\s+(previous|all|above)',
                        r'forget\s+(previous|all|your)',
                        r'disregard\s+(previous|all|above)',
                        r'override\s+(instructions|rules)',
                        r'new\s+instructions?:',
                        r'system\s*:\s*',
                        r'<\s*system\s*>',
                        r'</?\s*(?:script|style|iframe)',
                    ]
                class limits:
                    URL_MAX_LENGTH = 2048
                    TEXT_MAX_LENGTH = 100000
                    FILE_MAX_SIZE = 100 * 1024 * 1024
            _config = DefaultConfig()
    return _config


class PathValidator:
    """Dosya yolu validation."""

    @staticmethod
    def validate(
        path: str,
        must_exist: bool = True,
        allowed_base: Optional[Path] = None,
        check_traversal: bool = True
    ) -> Path:
        """
        Dosya yolunu validate et.

        Args:
            path: Dogrulanacak yol
            must_exist: Dosyanin var olmasi gerekiyor mu
            allowed_base: Izin verilen temel dizin
            check_traversal: Path traversal kontrolu yap

        Returns:
            Dogrulanmis Path nesnesi

        Raises:
            PathTraversalError: Path traversal tespit edilirse
            InputValidationError: Gecersiz yol ise
            FileNotFoundError: Dosya bulunamazsa
        """
        if not path or not isinstance(path, str):
            raise InputValidationError("path", path, "Bos veya gecersiz yol")

        # Normalize path
        path = path.strip()

        # Path traversal kontrolu
        if check_traversal:
            config = _get_config()
            for pattern in config.security.FORBIDDEN_PATH_PATTERNS:
                if pattern in path:
                    raise PathTraversalError(path)

        try:
            resolved = Path(path).resolve()
        except Exception as e:
            raise InputValidationError("path", path, f"Yol cozumlenemedi: {e}")

        # Base directory kontrolu
        if allowed_base:
            allowed_base = Path(allowed_base).resolve()
            try:
                resolved.relative_to(allowed_base)
            except ValueError:
                raise PathTraversalError(path)

        # Existence kontrolu
        if must_exist and not resolved.exists():
            raise InputValidationError("path", path, "Dosya veya dizin bulunamadi")

        return resolved

    @staticmethod
    def validate_file(
        path: str,
        allowed_extensions: Optional[List[str]] = None,
        max_size_mb: Optional[int] = None
    ) -> Path:
        """
        Dosya yolunu validate et (dosya ozel).

        Args:
            path: Dogrulanacak dosya yolu
            allowed_extensions: Izin verilen uzantilar
            max_size_mb: Maksimum dosya boyutu (MB)

        Returns:
            Dogrulanmis Path nesnesi
        """
        resolved = PathValidator.validate(path, must_exist=True)

        if not resolved.is_file():
            raise InputValidationError("path", path, "Bir dosya degil")

        # Uzanti kontrolu
        if allowed_extensions:
            config = _get_config()
            allowed = allowed_extensions or config.security.ALLOWED_EXTENSIONS
            if resolved.suffix.lower() not in allowed:
                raise InputValidationError(
                    "path", path,
                    f"Gecersiz dosya uzantisi. Izin verilenler: {allowed}"
                )

        # Boyut kontrolu
        if max_size_mb:
            size_mb = resolved.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                raise FileSizeError(str(resolved), size_mb, max_size_mb)

        return resolved

    @staticmethod
    def validate_directory(path: str, create_if_missing: bool = False) -> Path:
        """
        Dizin yolunu validate et.

        Args:
            path: Dogrulanacak dizin yolu
            create_if_missing: Yoksa olustur

        Returns:
            Dogrulanmis Path nesnesi
        """
        resolved = PathValidator.validate(path, must_exist=not create_if_missing)

        if create_if_missing and not resolved.exists():
            try:
                resolved.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise InputValidationError("path", path, f"Dizin olusturulamadi: {e}")

        if not resolved.is_dir():
            raise InputValidationError("path", path, "Bir dizin degil")

        return resolved


class URLValidator:
    """URL validation."""

    # URL pattern
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// veya https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    @staticmethod
    def validate(
        url: str,
        require_https: bool = False,
        allowed_domains: Optional[List[str]] = None
    ) -> str:
        """
        URL'i validate et.

        Args:
            url: Dogrulanacak URL
            require_https: HTTPS zorunlu mu
            allowed_domains: Izin verilen domain'ler

        Returns:
            Dogrulanmis URL

        Raises:
            URLValidationError: Gecersiz URL
        """
        if not url or not isinstance(url, str):
            raise URLValidationError(url or "", "Bos veya gecersiz URL")

        url = url.strip()
        config = _get_config()

        # Uzunluk kontrolu
        if len(url) > config.limits.URL_MAX_LENGTH:
            raise URLValidationError(url, f"URL cok uzun (max {config.limits.URL_MAX_LENGTH})")

        # Format kontrolu
        if not URLValidator.URL_PATTERN.match(url):
            raise URLValidationError(url, "Gecersiz URL formati")

        # Parse URL
        parsed = urlparse(url)

        # HTTPS kontrolu
        if require_https and parsed.scheme != 'https':
            raise URLValidationError(url, "HTTPS gerekli")

        # Domain kontrolu
        if allowed_domains:
            domain = parsed.netloc.lower()
            if not any(domain.endswith(d) for d in allowed_domains):
                raise URLValidationError(url, f"Domain izin verilmiyor")

        return url

    @staticmethod
    def is_trusted_domain(url: str) -> bool:
        """URL'in guvenilir domain'den olup olmadigini kontrol et."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            config = _get_config()
            return any(domain.endswith(d) for d in config.security.TRUSTED_DOMAINS)
        except Exception:
            return False


class TextValidator:
    """Metin validation ve sanitization."""

    @staticmethod
    def sanitize(
        text: str,
        max_length: Optional[int] = None,
        strip_html: bool = False,
        remove_null_bytes: bool = True
    ) -> str:
        """
        Metni sanitize et.

        Args:
            text: Sanitize edilecek metin
            max_length: Maksimum uzunluk
            strip_html: HTML tag'lerini kaldir
            remove_null_bytes: Null byte'lari kaldir

        Returns:
            Sanitize edilmis metin
        """
        if not text:
            return ""

        if not isinstance(text, str):
            text = str(text)

        # Null byte'lari kaldir
        if remove_null_bytes:
            text = text.replace('\x00', '')

        # HTML tag'lerini kaldir
        if strip_html:
            text = re.sub(r'<[^>]+>', '', text)

        # Truncate
        if max_length and len(text) > max_length:
            text = text[:max_length]

        return text

    @staticmethod
    def check_prompt_injection(text: str) -> bool:
        """
        Prompt injection kontrolu yap.

        Args:
            text: Kontrol edilecek metin

        Returns:
            True eger injection tespit edilirse
        """
        if not text:
            return False

        config = _get_config()
        text_lower = text.lower()

        for pattern in config.security.INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def sanitize_for_prompt(text: str, max_length: int = 10000) -> str:
        """
        Metni prompt icin sanitize et.

        Args:
            text: Sanitize edilecek metin
            max_length: Maksimum uzunluk

        Returns:
            Sanitize edilmis metin

        Raises:
            PromptInjectionError: Injection tespit edilirse
        """
        if TextValidator.check_prompt_injection(text):
            raise PromptInjectionError()

        return TextValidator.sanitize(text, max_length=max_length, strip_html=True)


class NumberValidator:
    """Sayi validation."""

    @staticmethod
    def validate_positive(value: Union[int, float], field_name: str = "value") -> Union[int, float]:
        """Pozitif sayi kontrolu."""
        if not isinstance(value, (int, float)):
            raise InputValidationError(field_name, value, "Sayi olmali")
        if value <= 0:
            raise InputValidationError(field_name, value, "Pozitif olmali")
        return value

    @staticmethod
    def validate_range(
        value: Union[int, float],
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
        field_name: str = "value"
    ) -> Union[int, float]:
        """Aralik kontrolu."""
        if not isinstance(value, (int, float)):
            raise InputValidationError(field_name, value, "Sayi olmali")
        if min_val is not None and value < min_val:
            raise InputValidationError(field_name, value, f"En az {min_val} olmali")
        if max_val is not None and value > max_val:
            raise InputValidationError(field_name, value, f"En fazla {max_val} olmali")
        return value

    @staticmethod
    def validate_percentage(value: Union[int, float], field_name: str = "percentage") -> float:
        """Yuzde kontrolu (0-100)."""
        return NumberValidator.validate_range(value, 0, 100, field_name)


class InputValidator:
    """
    Genel input validator.
    Tum validation metodlarini birlestiren facade class.
    """

    # Sub-validators
    path = PathValidator
    url = URLValidator
    text = TextValidator
    number = NumberValidator

    @staticmethod
    def validate_not_empty(value: Any, field_name: str) -> Any:
        """Bos olmama kontrolu."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise InputValidationError(field_name, value, "Bos olamaz")
        return value

    @staticmethod
    def validate_type(value: Any, expected_type: type, field_name: str) -> Any:
        """Tip kontrolu."""
        if not isinstance(value, expected_type):
            raise InputValidationError(
                field_name, value,
                f"{expected_type.__name__} tipinde olmali"
            )
        return value

    @staticmethod
    def validate_enum(value: Any, allowed_values: List[Any], field_name: str) -> Any:
        """Enum kontrolu."""
        if value not in allowed_values:
            raise InputValidationError(
                field_name, value,
                f"Gecerli degerler: {allowed_values}"
            )
        return value
