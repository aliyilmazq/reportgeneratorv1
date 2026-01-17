"""
Document Processor Modulu - Dokuman on isleme ve zenginlestirme.

Ozellikler:
- Otomatik ozet olusturma
- Anahtar kelime cikarimi (TF-IDF)
- Kategori tespiti
- Metadata zenginlestirme
- Named Entity Recognition (basit)
"""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
import math

from ..utils.logger import get_rag_logger

logger = get_rag_logger("document_processor")


# Turkce stop words
TURKISH_STOP_WORDS = {
    "bir", "bu", "ve", "ile", "için", "de", "da", "den", "dan", "ne",
    "ama", "ancak", "fakat", "veya", "ya", "hem", "ise", "ki", "gibi",
    "kadar", "sonra", "önce", "arasında", "üzerinde", "altında", "içinde",
    "dışında", "yanında", "karşısında", "hakkında", "dolayı", "rağmen",
    "göre", "olarak", "üzere", "itibaren", "boyunca", "ötürü", "dair",
    "olan", "olarak", "olmak", "etmek", "yapmak", "olup", "olduğu",
    "var", "yok", "çok", "daha", "en", "her", "tüm", "bütün", "bazı",
    "hiç", "aynı", "başka", "diğer", "öte", "beri", "hep", "sadece",
    "yalnız", "bile", "artık", "henüz", "hala", "şimdi", "şu", "o",
    "ben", "sen", "biz", "siz", "onlar", "bunlar", "şunlar", "kendi",
    "nasıl", "neden", "niçin", "niye", "hangi", "kim", "ne", "nerede",
    "zaman", "kaç", "şey", "yer", "ara", "kez", "yıl", "gün", "ay",
    "etti", "edildi", "yapıldı", "oldu", "olacak", "olmuş", "olmayan",
}


@dataclass
class ProcessedDocument:
    """Islenmis dokuman."""
    id: str
    original_text: str
    cleaned_text: str
    summary: str
    keywords: List[str]
    keyword_scores: Dict[str, float]
    category: str
    subcategory: Optional[str]
    entities: Dict[str, List[str]]
    word_count: int
    sentence_count: int
    paragraph_count: int
    language: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TurkishKeywordExtractor:
    """TF-IDF tabanli Turkce anahtar kelime cikaricisi."""

    def __init__(self, max_keywords: int = 20, min_word_length: int = 3):
        self.max_keywords = max_keywords
        self.min_word_length = min_word_length
        self.stop_words = TURKISH_STOP_WORDS
        self.document_frequencies: Dict[str, int] = {}
        self.total_documents = 0

    def extract_keywords(
        self,
        text: str,
        top_k: Optional[int] = None
    ) -> List[tuple]:
        """
        Metinden anahtar kelimeleri cikar.

        Args:
            text: Kaynak metin
            top_k: Dondurulecek keyword sayisi

        Returns:
            [(keyword, score), ...] listesi
        """
        if not text:
            return []

        top_k = top_k or self.max_keywords

        # Tokenize
        words = self._tokenize(text)

        if not words:
            return []

        # Term frequency hesapla
        tf = Counter(words)
        total_words = len(words)

        # TF-IDF skorlari
        scores = {}
        for word, count in tf.items():
            # TF: log normalized
            tf_score = 1 + math.log(count) if count > 0 else 0

            # IDF: document frequency varsa kullan
            df = self.document_frequencies.get(word, 1)
            idf_score = math.log(max(self.total_documents, 1) / df) if df > 0 else 1

            scores[word] = tf_score * idf_score

        # Sirala ve dondur
        sorted_keywords = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_keywords[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """Metni token'lara ayir."""
        # Kucuk harfe cevir
        text = text.lower()

        # Sadece harfleri koru (Turkce karakterler dahil)
        text = re.sub(r'[^a-zçğıöşü\s]', ' ', text)

        # Kelimelere ayir
        words = text.split()

        # Filtrele
        filtered = []
        for word in words:
            if len(word) >= self.min_word_length:
                if word not in self.stop_words:
                    # Basit stemming (son ekleri cikar)
                    stemmed = self._simple_stem(word)
                    filtered.append(stemmed)

        return filtered

    def _simple_stem(self, word: str) -> str:
        """Basit Turkce stemming."""
        # Yaygin ekleri cikar
        suffixes = [
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
        ]

        for suffix in sorted(suffixes, key=len, reverse=True):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[:-len(suffix)]

        return word

    def update_document_frequencies(self, documents: List[str]):
        """Dokuman frekanslarini guncelle (IDF icin)."""
        self.total_documents = len(documents)

        for doc in documents:
            words = set(self._tokenize(doc))
            for word in words:
                self.document_frequencies[word] = self.document_frequencies.get(word, 0) + 1


class CategoryDetector:
    """Dokuman kategori tespiti."""

    # Kategori anahtar kelimeleri
    CATEGORY_KEYWORDS = {
        "finansal": {
            "keywords": ["gelir", "gider", "kar", "zarar", "maliyet", "bütçe", "yatırım",
                        "sermaye", "nakit", "akış", "bilanço", "borç", "alacak", "varlık",
                        "özkaynak", "oran", "karlılık", "likidite", "finansman", "kredi",
                        "faiz", "döviz", "kur", "enflasyon", "tl", "usd", "eur"],
            "weight": 1.0
        },
        "pazar_analizi": {
            "keywords": ["pazar", "piyasa", "rekabet", "rakip", "segment", "hedef kitle",
                        "müşteri", "talep", "arz", "tüketici", "trend", "büyüme", "payı",
                        "penetrasyon", "kanal", "dağıtım", "fiyat", "pozisyon"],
            "weight": 1.0
        },
        "teknik": {
            "keywords": ["sistem", "yazılım", "donanım", "altyapı", "teknoloji", "platform",
                        "uygulama", "api", "veritabanı", "sunucu", "ağ", "güvenlik",
                        "entegrasyon", "mimari", "modül", "geliştirme", "test"],
            "weight": 1.0
        },
        "operasyonel": {
            "keywords": ["operasyon", "süreç", "iş akışı", "verimlilik", "kapasite",
                        "üretim", "tedarik", "lojistik", "stok", "envanter", "kalite",
                        "performans", "kpi", "metrik", "ölçüm", "iyileştirme"],
            "weight": 1.0
        },
        "yasal": {
            "keywords": ["kanun", "yönetmelik", "mevzuat", "düzenleme", "uyum", "lisans",
                        "izin", "ruhsat", "sözleşme", "anlaşma", "hukuk", "dava", "mahkeme",
                        "ceza", "para cezası", "yaptırım", "kvkk", "gdpr"],
            "weight": 1.0
        },
        "insan_kaynaklari": {
            "keywords": ["personel", "çalışan", "insan kaynakları", "ik", "işe alım",
                        "eğitim", "performans", "maaş", "ücret", "özlük", "organizasyon",
                        "kadro", "yetkinlik", "kariyer", "terfi"],
            "weight": 0.9
        },
        "pazarlama": {
            "keywords": ["pazarlama", "reklam", "kampanya", "marka", "iletişim", "sosyal medya",
                        "dijital", "içerik", "seo", "sem", "influencer", "pr", "etkinlik",
                        "lansman", "promosyon"],
            "weight": 0.9
        },
        "genel": {
            "keywords": [],
            "weight": 0.5
        }
    }

    def detect_category(self, text: str) -> tuple:
        """
        Dokuman kategorisini tespit et.

        Args:
            text: Analiz edilecek metin

        Returns:
            (kategori, guven_skoru) tuple
        """
        if not text:
            return ("genel", 0.5)

        text_lower = text.lower()
        scores = {}

        for category, config in self.CATEGORY_KEYWORDS.items():
            if category == "genel":
                continue

            keywords = config["keywords"]
            weight = config["weight"]

            # Keyword eslesme sayisi
            matches = sum(1 for kw in keywords if kw in text_lower)

            if matches > 0:
                # Normalize skor
                score = (matches / len(keywords)) * weight
                scores[category] = score

        if not scores:
            return ("genel", 0.5)

        # En yuksek skorlu kategori
        best_category = max(scores.items(), key=lambda x: x[1])

        # Guven skoru normalize et (0-1 arasi)
        confidence = min(best_category[1] * 2, 1.0)

        return (best_category[0], confidence)

    def detect_subcategory(self, text: str, main_category: str) -> Optional[str]:
        """Alt kategori tespiti."""
        # Alt kategori keyword'leri
        subcategories = {
            "finansal": {
                "nakit_akis": ["nakit", "akış", "cash flow", "likidite"],
                "yatirim": ["yatırım", "sermaye", "fon", "portföy"],
                "maliyet": ["maliyet", "gider", "masraf", "harcama"],
                "gelir": ["gelir", "satış", "ciro", "hasılat"]
            },
            "pazar_analizi": {
                "rekabet": ["rakip", "rekabet", "pazar payı"],
                "musteri": ["müşteri", "tüketici", "hedef kitle"],
                "trend": ["trend", "büyüme", "gelişme"]
            }
        }

        if main_category not in subcategories:
            return None

        text_lower = text.lower()
        best_match = None
        best_count = 0

        for subcat, keywords in subcategories[main_category].items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > best_count:
                best_count = matches
                best_match = subcat

        return best_match


class SimpleNER:
    """Basit Named Entity Recognition."""

    # Entity pattern'leri
    PATTERNS = {
        "money": [
            r'\d+[\.,]?\d*\s*(TL|tl|USD|usd|EUR|eur|dolar|euro|milyon|milyar|bin)',
            r'[\$€₺]\s*\d+[\.,]?\d*',
        ],
        "percentage": [
            r'%\s*\d+[\.,]?\d*',
            r'\d+[\.,]?\d*\s*%',
        ],
        "date": [
            r'\d{1,2}[./]\d{1,2}[./]\d{2,4}',
            r'\d{4}[./]\d{1,2}[./]\d{1,2}',
            r'(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}',
        ],
        "organization": [
            r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+(A\.?Ş\.?|Ltd\.?|Inc\.?|Corp\.?)',
            r'(T\.?C\.?|TCMB|BDDK|SPK|EPDK|BTK)\b',
        ],
    }

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Metinden entity'leri cikar.

        Args:
            text: Kaynak metin

        Returns:
            {entity_type: [entities]} dict
        """
        entities = {}

        for entity_type, patterns in self.PATTERNS.items():
            found = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if isinstance(matches[0], tuple):
                        # Grup iceren pattern
                        found.extend([m[0] if isinstance(m, tuple) else m for m in matches])
                    else:
                        found.extend(matches)

            if found:
                entities[entity_type] = list(set(found))[:10]  # Max 10 entity

        return entities


class DocumentProcessor:
    """
    Ana dokuman isleyici.

    Kullanim:
        processor = DocumentProcessor()
        result = processor.process("Dokuman metni...")
    """

    def __init__(
        self,
        anthropic_client=None,
        max_keywords: int = 20,
        generate_summary: bool = True,
        max_summary_length: int = 500
    ):
        self.client = anthropic_client
        self.keyword_extractor = TurkishKeywordExtractor(max_keywords=max_keywords)
        self.category_detector = CategoryDetector()
        self.ner = SimpleNER()
        self.generate_summary = generate_summary
        self.max_summary_length = max_summary_length
        self._doc_counter = 0

    def process(
        self,
        text: str,
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """
        Dokumani isle.

        Args:
            text: Dokuman metni
            doc_id: Dokuman ID (opsiyonel)
            metadata: Ek metadata (opsiyonel)

        Returns:
            ProcessedDocument
        """
        if not text:
            raise ValueError("Dokuman metni bos olamaz")

        logger.info("Dokuman isleniyor", doc_id=doc_id)

        # ID olustur
        self._doc_counter += 1
        doc_id = doc_id or f"doc_{self._doc_counter}"

        # Temizle
        cleaned = self._clean_text(text)

        # Istatistikler
        word_count = len(cleaned.split())
        sentences = re.split(r'[.!?]+', cleaned)
        sentence_count = len([s for s in sentences if s.strip()])
        paragraph_count = len([p for p in cleaned.split('\n\n') if p.strip()])

        # Anahtar kelimeler
        keywords_with_scores = self.keyword_extractor.extract_keywords(cleaned)
        keywords = [kw for kw, _ in keywords_with_scores]
        keyword_scores = dict(keywords_with_scores)

        # Kategori
        category, confidence = self.category_detector.detect_category(cleaned)
        subcategory = self.category_detector.detect_subcategory(cleaned, category)

        # Entity'ler
        entities = self.ner.extract_entities(text)

        # Ozet
        if self.generate_summary:
            summary = self._generate_summary(cleaned)
        else:
            summary = cleaned[:self.max_summary_length]

        # Dil tespiti (basit)
        language = self._detect_language(cleaned)

        return ProcessedDocument(
            id=doc_id,
            original_text=text,
            cleaned_text=cleaned,
            summary=summary,
            keywords=keywords,
            keyword_scores=keyword_scores,
            category=category,
            subcategory=subcategory,
            entities=entities,
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            language=language,
            metadata={
                "category_confidence": confidence,
                **(metadata or {})
            }
        )

    def process_batch(
        self,
        documents: List[str],
        doc_ids: Optional[List[str]] = None
    ) -> List[ProcessedDocument]:
        """Toplu dokuman isleme."""
        results = []
        doc_ids = doc_ids or [None] * len(documents)

        # IDF icin document frequencies guncelle
        self.keyword_extractor.update_document_frequencies(documents)

        for i, (text, doc_id) in enumerate(zip(documents, doc_ids)):
            try:
                result = self.process(text, doc_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Dokuman isleme hatasi: {e}", doc_id=doc_id)

        return results

    def _clean_text(self, text: str) -> str:
        """Metni temizle."""
        # Fazla bosluk temizle
        text = re.sub(r'\s+', ' ', text)

        # Ozel karakterleri normalize et
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u200b', '')   # Zero-width space

        # Baslangic/bitis bosluk temizle
        text = text.strip()

        return text

    def _generate_summary(self, text: str) -> str:
        """Ozet olustur."""
        if self.client:
            try:
                return self._llm_summary(text)
            except Exception as e:
                logger.warning(f"LLM ozet olusturulamadi: {e}")

        # Fallback: Extractive ozet
        return self._extractive_summary(text)

    def _llm_summary(self, text: str) -> str:
        """LLM ile ozet olustur."""
        prompt = f"""Asagidaki metni maksimum {self.max_summary_length} kelimeyle ozetle.
Turkce yaz. Onemli noktalari vurgula.

Metin:
{text[:5000]}

Ozet:"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=self.max_summary_length * 2,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    def _extractive_summary(self, text: str, max_sentences: int = 5) -> str:
        """Extractive ozet olustur."""
        sentences = re.split(r'(?<=[.!?])\s+', text)

        if len(sentences) <= max_sentences:
            return text[:self.max_summary_length]

        # Ilk ve son cumleler onemli
        selected = [sentences[0]]

        # Arada keyword iceren cumleler
        keywords = set(kw for kw, _ in self.keyword_extractor.extract_keywords(text, top_k=10))

        scored = []
        for i, sentence in enumerate(sentences[1:-1], 1):
            score = sum(1 for kw in keywords if kw in sentence.lower())
            scored.append((i, sentence, score))

        # En yuksek skorlu cumleler
        scored.sort(key=lambda x: x[2], reverse=True)
        for idx, sentence, _ in scored[:max_sentences-2]:
            selected.append(sentence)

        # Son cumle
        if len(sentences) > 1:
            selected.append(sentences[-1])

        return ' '.join(selected)[:self.max_summary_length]

    def _detect_language(self, text: str) -> str:
        """Basit dil tespiti."""
        turkish_chars = set('çğıöşüÇĞİÖŞÜ')
        sample = text[:1000]

        # Turkce karakter orani
        turkish_char_count = sum(1 for c in sample if c in turkish_chars)
        total_letters = sum(1 for c in sample if c.isalpha())

        if total_letters > 0:
            ratio = turkish_char_count / total_letters
            if ratio > 0.01:  # %1 uzerinde Turkce karakter
                return "tr"

        # Turkce kelime kontrolu
        turkish_words = ["ve", "bir", "için", "ile", "bu", "da", "de"]
        word_count = sum(1 for word in turkish_words if f" {word} " in sample.lower())

        if word_count >= 3:
            return "tr"

        return "en"


def process_document(
    text: str,
    anthropic_client=None,
    **kwargs
) -> ProcessedDocument:
    """
    Dokuman isle (kisa yol).

    Args:
        text: Dokuman metni
        anthropic_client: Anthropic client (ozet icin)
        **kwargs: DocumentProcessor parametreleri

    Returns:
        ProcessedDocument
    """
    processor = DocumentProcessor(anthropic_client=anthropic_client, **kwargs)
    return processor.process(text)
