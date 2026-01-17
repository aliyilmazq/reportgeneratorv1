"""
Input Validation ve Guvenlik Modulu.

Ozellikler:
- Girdi dogrulama
- Prompt injection koruması
- Metin sanitizasyonu
- Boyut limitleri
"""

import re
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from functools import wraps

from .exceptions import InputValidationError, ValidationException
from ..utils.logger import get_rag_logger

logger = get_rag_logger("validators")


# ============================================================
# Sabitler ve Limitler
# ============================================================

MAX_QUERY_LENGTH = 10000  # Maksimum sorgu uzunlugu
MAX_DOCUMENT_LENGTH = 1000000  # Maksimum dokuman uzunlugu (1M karakter)
MAX_BATCH_SIZE = 1000  # Maksimum batch boyutu
MAX_TOP_K = 100  # Maksimum top_k degeri
MIN_CHUNK_SIZE = 50  # Minimum chunk boyutu
MAX_CHUNK_SIZE = 10000  # Maksimum chunk boyutu


# Prompt injection pattern'leri
INJECTION_PATTERNS = [
    r'ignore\s+(previous|all|above)\s+instructions?',
    r'disregard\s+(previous|all|above)',
    r'forget\s+(previous|all|everything)',
    r'new\s+instructions?:',
    r'system\s*:\s*you\s+are',
    r'<\s*system\s*>',
    r'\[\s*system\s*\]',
    r'```\s*system',
    r'IGNORE\s+INSTRUCTIONS',
    r'OVERRIDE\s+SAFETY',
]


# ============================================================
# Validator Functions
# ============================================================

def validate_query(query: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    """
    Arama sorgusunu dogrula ve temizle.

    Args:
        query: Arama sorgusu
        max_length: Maksimum uzunluk

    Returns:
        Temizlenmis sorgu

    Raises:
        InputValidationError: Gecersiz sorgu
    """
    if query is None:
        raise InputValidationError("query", None, "Sorgu None olamaz")

    if not isinstance(query, str):
        raise InputValidationError("query", type(query), "Sorgu string olmali")

    query = query.strip()

    if not query:
        raise InputValidationError("query", "", "Sorgu bos olamaz")

    if len(query) > max_length:
        raise InputValidationError(
            "query",
            f"len={len(query)}",
            f"Sorgu {max_length} karakterden uzun olamaz"
        )

    # Prompt injection kontrolu
    if contains_injection(query):
        logger.warning("Potansiyel prompt injection tespit edildi", query=query[:100])
        query = sanitize_prompt(query)

    return query


def validate_document(
    document: str,
    max_length: int = MAX_DOCUMENT_LENGTH,
    allow_empty: bool = False
) -> str:
    """
    Dokumani dogrula.

    Args:
        document: Dokuman metni
        max_length: Maksimum uzunluk
        allow_empty: Bos dokumana izin ver

    Returns:
        Temizlenmis dokuman

    Raises:
        InputValidationError: Gecersiz dokuman
    """
    if document is None:
        raise InputValidationError("document", None, "Dokuman None olamaz")

    if not isinstance(document, str):
        raise InputValidationError("document", type(document), "Dokuman string olmali")

    document = document.strip()

    if not document and not allow_empty:
        raise InputValidationError("document", "", "Dokuman bos olamaz")

    if len(document) > max_length:
        raise InputValidationError(
            "document",
            f"len={len(document)}",
            f"Dokuman {max_length} karakterden uzun olamaz"
        )

    return document


def validate_documents(
    documents: List[Dict[str, Any]],
    max_count: int = MAX_BATCH_SIZE,
    text_key: str = "text"
) -> List[Dict[str, Any]]:
    """
    Dokuman listesini dogrula.

    Args:
        documents: Dokuman listesi
        max_count: Maksimum dokuman sayisi
        text_key: Metin alani adi

    Returns:
        Dogrulanmis dokuman listesi

    Raises:
        InputValidationError: Gecersiz liste
    """
    if documents is None:
        raise InputValidationError("documents", None, "Dokuman listesi None olamaz")

    if not isinstance(documents, list):
        raise InputValidationError("documents", type(documents), "Dokuman listesi list olmali")

    if len(documents) > max_count:
        raise InputValidationError(
            "documents",
            f"count={len(documents)}",
            f"Maksimum {max_count} dokuman"
        )

    validated = []
    for i, doc in enumerate(documents):
        if not isinstance(doc, dict):
            raise InputValidationError(
                f"documents[{i}]",
                type(doc),
                "Her dokuman dict olmali"
            )

        if text_key in doc:
            doc[text_key] = validate_document(doc[text_key], allow_empty=True)

        validated.append(doc)

    return validated


def validate_top_k(top_k: int, max_value: int = MAX_TOP_K) -> int:
    """
    top_k degerini dogrula.

    Args:
        top_k: Top-k degeri
        max_value: Maksimum deger

    Returns:
        Dogrulanmis top_k

    Raises:
        InputValidationError: Gecersiz deger
    """
    if not isinstance(top_k, int):
        raise InputValidationError("top_k", type(top_k), "top_k integer olmali")

    if top_k < 1:
        raise InputValidationError("top_k", top_k, "top_k en az 1 olmali")

    if top_k > max_value:
        raise InputValidationError("top_k", top_k, f"top_k en fazla {max_value} olabilir")

    return top_k


def validate_chunk_size(chunk_size: int) -> int:
    """
    Chunk boyutunu dogrula.

    Args:
        chunk_size: Chunk boyutu

    Returns:
        Dogrulanmis chunk_size

    Raises:
        InputValidationError: Gecersiz deger
    """
    if not isinstance(chunk_size, int):
        raise InputValidationError("chunk_size", type(chunk_size), "chunk_size integer olmali")

    if chunk_size < MIN_CHUNK_SIZE:
        raise InputValidationError(
            "chunk_size",
            chunk_size,
            f"chunk_size en az {MIN_CHUNK_SIZE} olmali"
        )

    if chunk_size > MAX_CHUNK_SIZE:
        raise InputValidationError(
            "chunk_size",
            chunk_size,
            f"chunk_size en fazla {MAX_CHUNK_SIZE} olabilir"
        )

    return chunk_size


def validate_score(score: float, field_name: str = "score") -> float:
    """
    Skor degerini dogrula.

    Args:
        score: Skor degeri
        field_name: Alan adi

    Returns:
        Dogrulanmis skor

    Raises:
        InputValidationError: Gecersiz deger
    """
    if not isinstance(score, (int, float)):
        raise InputValidationError(field_name, type(score), "Skor numeric olmali")

    if score < 0 or score > 1:
        raise InputValidationError(field_name, score, "Skor 0-1 arasinda olmali")

    return float(score)


# ============================================================
# Security Functions
# ============================================================

def contains_injection(text: str) -> bool:
    """
    Metinde prompt injection pattern'i var mi kontrol et.

    Args:
        text: Kontrol edilecek metin

    Returns:
        True eger injection pattern bulunursa
    """
    if not text:
        return False

    text_lower = text.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return False


def sanitize_prompt(text: str) -> str:
    """
    Prompt'u temizle ve guvenli hale getir.

    Args:
        text: Temizlenecek metin

    Returns:
        Temizlenmis metin
    """
    if not text:
        return ""

    # Injection pattern'leri kaldir
    for pattern in INJECTION_PATTERNS:
        text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)

    # Tehlikeli karakterleri escape et
    text = text.replace("```", "'''")
    text = text.replace("<script", "&lt;script")
    text = text.replace("</script", "&lt;/script")

    return text


def sanitize_html(text: str) -> str:
    """
    HTML tag'lerini temizle.

    Args:
        text: Temizlenecek metin

    Returns:
        Temizlenmis metin
    """
    if not text:
        return ""

    # HTML tag'lerini kaldir
    text = re.sub(r'<[^>]+>', '', text)

    # HTML entity'lerini decode et
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    return text


def truncate_safe(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Metni guvenli sekilde kes.

    Args:
        text: Kesilecek metin
        max_length: Maksimum uzunluk
        suffix: Ek suffix

    Returns:
        Kesilmis metin
    """
    if not text or len(text) <= max_length:
        return text

    # Kelime sinirindan kes
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')

    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated + suffix


# ============================================================
# Decorator
# ============================================================

def validate_inputs(**validators):
    """
    Input dogrulama decorator'u.

    Kullanim:
        @validate_inputs(query=validate_query, top_k=validate_top_k)
        def search(query: str, top_k: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Keyword argumanlari dogrula
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    kwargs[param_name] = validator(kwargs[param_name])

            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# Dataclass Validators
# ============================================================

@dataclass
class ValidationResult:
    """Dogrulama sonucu."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_value: Any = None

    def __bool__(self) -> bool:
        return self.is_valid


def validate_config(config: Dict[str, Any]) -> ValidationResult:
    """
    RAG konfigurasyonunu dogrula.

    Args:
        config: Konfigurasyon dict

    Returns:
        ValidationResult
    """
    errors = []
    warnings = []

    # Embedding config
    if "embedding" in config:
        emb = config["embedding"]
        if "dimension" in emb:
            dim = emb["dimension"]
            if not isinstance(dim, int) or dim < 1:
                errors.append(f"embedding.dimension gecersiz: {dim}")

        if "batch_size" in emb:
            bs = emb["batch_size"]
            if not isinstance(bs, int) or bs < 1:
                errors.append(f"embedding.batch_size gecersiz: {bs}")

    # Chunking config
    if "chunking" in config:
        chunk = config["chunking"]
        if "chunk_size" in chunk:
            cs = chunk["chunk_size"]
            if not isinstance(cs, int) or cs < MIN_CHUNK_SIZE:
                errors.append(f"chunking.chunk_size gecersiz: {cs}")

    # Hybrid search config
    if "hybrid_search" in config:
        hs = config["hybrid_search"]
        if "semantic_weight" in hs and "bm25_weight" in hs:
            total = hs["semantic_weight"] + hs["bm25_weight"]
            if abs(total - 1.0) > 0.01:
                warnings.append(f"hybrid_search agirliklari toplami 1.0 olmali: {total}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
