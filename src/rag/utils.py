"""
RAG Ortak Yardimci Fonksiyonlar.

Bu modul, RAG bilesenleri arasinda paylasilan ortak fonksiyonlari icerir.
Kod duplikasyonunu onlemek icin merkezi bir yer saglar.
"""

import re
from typing import List, Set, Dict, Any, Optional
from functools import lru_cache


# ============================================================
# Metin Benzerlik Fonksiyonlari
# ============================================================

def jaccard_similarity(text1: str, text2: str, max_words: int = 100) -> float:
    """
    Iki metin arasindaki Jaccard benzerligini hesapla.

    Args:
        text1: Birinci metin
        text2: Ikinci metin
        max_words: Karsilastirilacak maksimum kelime sayisi

    Returns:
        0-1 arasi benzerlik skoru
    """
    if not text1 or not text2:
        return 0.0

    words1 = set(text1.lower().split()[:max_words])
    words2 = set(text2.lower().split()[:max_words])

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def keyword_overlap_score(query_words: Set[str], text_words: Set[str]) -> float:
    """
    Keyword overlap skoru hesapla.

    Args:
        query_words: Sorgu kelimeleri seti
        text_words: Metin kelimeleri seti

    Returns:
        0-1 arasi overlap skoru
    """
    if not query_words:
        return 0.0

    overlap = len(query_words & text_words)
    return overlap / len(query_words)


def combined_relevance_score(
    jaccard: float,
    keyword_score: float,
    existing_score: float = 0.0,
    weights: tuple = (0.3, 0.4, 0.3)
) -> float:
    """
    Birlesik relevance skoru hesapla.

    Args:
        jaccard: Jaccard benzerlik skoru
        keyword_score: Keyword overlap skoru
        existing_score: Mevcut skor (varsa)
        weights: (jaccard, keyword, existing) agirliklari

    Returns:
        Birlesik skor
    """
    w_j, w_k, w_e = weights
    return (jaccard * w_j) + (keyword_score * w_k) + (existing_score * w_e)


# ============================================================
# Metin Isleme Fonksiyonlari
# ============================================================

def split_sentences(text: str, min_length: int = 20) -> List[str]:
    """
    Metni cumlelere bol.

    Args:
        text: Kaynak metin
        min_length: Minimum cumle uzunlugu

    Returns:
        Cumle listesi
    """
    if not text:
        return []

    # Turkce ve Ingilizce cumle sonu
    pattern = r'(?<=[.!?])\s+'
    sentences = re.split(pattern, text)

    return [s.strip() for s in sentences if s.strip() and len(s.strip()) >= min_length]


def clean_text(text: str) -> str:
    """
    Metni temizle ve normalize et.

    Args:
        text: Kaynak metin

    Returns:
        Temizlenmis metin
    """
    if not text:
        return ""

    # Fazla bosluk temizle
    text = re.sub(r'\s+', ' ', text)

    # Ozel karakterleri normalize et
    text = text.replace('\u00a0', ' ')  # Non-breaking space
    text = text.replace('\u200b', '')   # Zero-width space

    return text.strip()


def tokenize_turkish(text: str, min_length: int = 2) -> List[str]:
    """
    Turkce metin tokenizasyonu.

    Args:
        text: Kaynak metin
        min_length: Minimum token uzunlugu

    Returns:
        Token listesi
    """
    if not text:
        return []

    # Kucuk harfe cevir
    text = text.lower()

    # Sadece harfleri koru (Turkce karakterler dahil)
    text = re.sub(r'[^a-zçğıöşü\s]', ' ', text)

    # Kelimelere ayir
    words = text.split()

    return [w for w in words if len(w) >= min_length]


# ============================================================
# Turkce Stop Words
# ============================================================

TURKISH_STOP_WORDS = frozenset({
    "bir", "bu", "ve", "ile", "için", "de", "da", "den", "dan", "ne",
    "ama", "ancak", "fakat", "veya", "ya", "hem", "ise", "ki", "gibi",
    "kadar", "sonra", "önce", "arasında", "üzerinde", "altında", "içinde",
    "dışında", "yanında", "karşısında", "hakkında", "dolayı", "rağmen",
    "göre", "olarak", "üzere", "itibaren", "boyunca", "ötürü", "dair",
    "olan", "olmak", "etmek", "yapmak", "olup", "olduğu",
    "var", "yok", "çok", "daha", "en", "her", "tüm", "bütün", "bazı",
    "hiç", "aynı", "başka", "diğer", "öte", "beri", "hep", "sadece",
    "yalnız", "bile", "artık", "henüz", "hala", "şimdi", "şu", "o",
    "ben", "sen", "biz", "siz", "onlar", "bunlar", "şunlar", "kendi",
    "nasıl", "neden", "niçin", "niye", "hangi", "kim", "nerede",
    "zaman", "kaç", "şey", "yer", "ara", "kez", "yıl", "gün", "ay",
    "etti", "edildi", "yapıldı", "oldu", "olacak", "olmuş", "olmayan",
})


def remove_stop_words(words: List[str], stop_words: Set[str] = None) -> List[str]:
    """
    Stop word'leri cikar.

    Args:
        words: Kelime listesi
        stop_words: Stop word seti (varsayilan: Turkce)

    Returns:
        Filtrelenmis kelime listesi
    """
    if stop_words is None:
        stop_words = TURKISH_STOP_WORDS

    return [w for w in words if w.lower() not in stop_words]


# ============================================================
# Basit Turkce Stemming
# ============================================================

TURKISH_SUFFIXES = (
    'lar', 'ler', 'lık', 'lik', 'luk', 'lük',
    'cı', 'ci', 'cu', 'cü', 'çı', 'çi', 'çu', 'çü',
    'sız', 'siz', 'suz', 'süz',
    'lı', 'li', 'lu', 'lü',
    'ca', 'ce', 'ça', 'çe',
    'dan', 'den', 'tan', 'ten',
    'da', 'de', 'ta', 'te',
    'ın', 'in', 'un', 'ün',
    'nın', 'nin', 'nun', 'nün',
    'ım', 'im', 'um', 'üm',
)


def simple_stem_turkish(word: str, min_stem_length: int = 3) -> str:
    """
    Basit Turkce stemming.

    Args:
        word: Kaynak kelime
        min_stem_length: Minimum kok uzunlugu

    Returns:
        Stem edilmis kelime
    """
    for suffix in sorted(TURKISH_SUFFIXES, key=len, reverse=True):
        if word.endswith(suffix) and len(word) - len(suffix) >= min_stem_length:
            return word[:-len(suffix)]

    return word


# ============================================================
# Skor Hesaplama Yardimcilari
# ============================================================

def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Skoru normalize et.

    Args:
        score: Ham skor
        min_val: Minimum deger
        max_val: Maksimum deger

    Returns:
        Normalize edilmis skor
    """
    return max(min_val, min(max_val, score))


def weighted_average(scores: List[float], weights: List[float] = None) -> float:
    """
    Agirlikli ortalama hesapla.

    Args:
        scores: Skor listesi
        weights: Agirlik listesi (varsayilan: esit agirlik)

    Returns:
        Agirlikli ortalama
    """
    if not scores:
        return 0.0

    if weights is None:
        weights = [1.0] * len(scores)

    if len(scores) != len(weights):
        raise ValueError("Skor ve agirlik sayisi esit olmali")

    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0

    return sum(s * w for s, w in zip(scores, weights)) / total_weight


# ============================================================
# Batch Isleme Yardimcilari
# ============================================================

def batch_items(items: List[Any], batch_size: int) -> List[List[Any]]:
    """
    Ogeleri batch'lere bol.

    Args:
        items: Oge listesi
        batch_size: Batch boyutu

    Returns:
        Batch listesi
    """
    if batch_size <= 0:
        raise ValueError("Batch boyutu pozitif olmali")

    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def deduplicate_by_key(
    items: List[Dict[str, Any]],
    key: str,
    similarity_threshold: float = 0.8,
    text_key: str = "text"
) -> List[Dict[str, Any]]:
    """
    Benzer ogeleri cikararak deduplicate et.

    Args:
        items: Oge listesi
        key: Karsilastirilacak anahtar
        similarity_threshold: Esik degeri
        text_key: Metin alani adi

    Returns:
        Deduplicate edilmis liste
    """
    if not items:
        return []

    unique = [items[0]]

    for item in items[1:]:
        is_duplicate = False

        for existing in unique:
            text1 = item.get(text_key, "")
            text2 = existing.get(text_key, "")

            if jaccard_similarity(text1, text2) >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(item)

    return unique


# ============================================================
# Cache Yardimcilari
# ============================================================

@lru_cache(maxsize=1000)
def cached_tokenize(text: str) -> tuple:
    """
    Tokenizasyon sonucunu cache'le.

    Args:
        text: Kaynak metin

    Returns:
        Token tuple'i
    """
    return tuple(tokenize_turkish(text))


def get_text_hash(text: str) -> str:
    """
    Metin hash'i olustur.

    Args:
        text: Kaynak metin

    Returns:
        Hash string
    """
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()
