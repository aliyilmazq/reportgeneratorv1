"""BM25 Index Modulu - Keyword-based search."""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from rich.console import Console

console = Console()

# rank_bm25 import
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25Okapi = None
    BM25_AVAILABLE = False


# Turkce stop words
TURKISH_STOP_WORDS = {
    "ve", "veya", "ile", "icin", "bir", "bu", "su", "o", "da", "de",
    "ki", "mi", "mu", "mi", "mu", "ne", "gibi", "kadar", "daha",
    "en", "cok", "az", "her", "hem", "ya", "ama", "ancak", "fakat",
    "lakin", "oysa", "ise", "zira", "cunku", "dolayisiyla", "yani",
    "oyle", "boyle", "soyle", "nasil", "neden", "niye", "kim", "ne",
    "hangi", "kac", "nerede", "nereden", "nereye", "ne zaman",
    "olan", "olarak", "olmak", "etmek", "yapmak", "edilmek",
    "tarafindan", "uzerinde", "altinda", "icinde", "disinda",
    "arasinda", "sonra", "once", "sirasinda", "boyunca", "gore",
    "karsi", "dolayi", "ragmen", "kayin", "beri", "itibaren",
    "ben", "sen", "biz", "siz", "onlar", "bunlar", "sunlar",
    "benim", "senin", "onun", "bizim", "sizin", "onlarin"
}


@dataclass
class BM25Result:
    """BM25 arama sonucu."""
    doc_index: int
    score: float
    text: str
    metadata: Dict[str, Any]


class BM25Index:
    """BM25 keyword-based search index."""

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        use_stemming: bool = True,
        remove_stopwords: bool = True,
        min_token_length: int = 2
    ):
        """
        BM25 index olustur.

        Args:
            k1: Term frequency saturation parametresi
            b: Document length normalization parametresi
            use_stemming: Basit stemming uygula
            remove_stopwords: Stop words cikar
            min_token_length: Minimum token uzunlugu
        """
        self.k1 = k1
        self.b = b
        self.use_stemming = use_stemming
        self.remove_stopwords = remove_stopwords
        self.min_token_length = min_token_length

        self.bm25 = None
        self.documents: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self._indexed = False

    def build_index(self, documents: List[Dict[str, Any]], text_key: str = "text"):
        """
        Dokumanlari indeksle.

        Args:
            documents: Dokuman listesi (her biri 'text' icermeli)
            text_key: Text alani adi
        """
        if not BM25_AVAILABLE:
            console.print("[yellow]rank-bm25 yuklenmemis, BM25 devre disi[/yellow]")
            return

        if not documents:
            return

        self.documents = documents
        self.tokenized_corpus = []

        for doc in documents:
            text = doc.get(text_key, "")
            tokens = self._tokenize(text)
            self.tokenized_corpus.append(tokens)

        # BM25 index olustur
        self.bm25 = BM25Okapi(
            self.tokenized_corpus,
            k1=self.k1,
            b=self.b
        )

        self._indexed = True
        console.print(f"[green]BM25 index olusturuldu: {len(documents)} dokuman[/green]")

    def search(
        self,
        query: str,
        top_k: int = 20
    ) -> List[BM25Result]:
        """
        Query'ye gore arama yap.

        Args:
            query: Arama sorgusu
            top_k: En iyi k sonuc

        Returns:
            BM25Result listesi
        """
        if not self._indexed or not self.bm25:
            return []

        # Query'yi tokenize et
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # BM25 skorlari
        scores = self.bm25.get_scores(query_tokens)

        # En yuksek skorlu dokumanlari bul
        scored_docs = list(enumerate(scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_docs = scored_docs[:top_k]

        # Sonuclari olustur
        results = []
        for doc_idx, score in top_docs:
            if score > 0:
                doc = self.documents[doc_idx]
                results.append(BM25Result(
                    doc_index=doc_idx,
                    score=score,
                    text=doc.get("text", ""),
                    metadata=doc
                ))

        return results

    def search_with_filter(
        self,
        query: str,
        top_k: int = 20,
        filter_fn: callable = None
    ) -> List[BM25Result]:
        """Filtreli arama."""
        results = self.search(query, top_k * 2)  # Daha fazla al, sonra filtrele

        if filter_fn:
            results = [r for r in results if filter_fn(r.metadata)]

        return results[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """
        Metni tokenize et.

        Args:
            text: Giris metni

        Returns:
            Token listesi
        """
        if not text:
            return []

        # Kucuk harfe cevir
        text = text.lower()

        # Noktalama isaretlerini cikar
        text = re.sub(r'[^\w\s]', ' ', text)

        # Sayilari koru ama normalize et
        text = re.sub(r'\d+', ' NUM ', text)

        # Tokenize
        tokens = text.split()

        # Filtreleme
        filtered_tokens = []
        for token in tokens:
            # Minimum uzunluk kontrolu
            if len(token) < self.min_token_length:
                continue

            # Stop words kontrolu
            if self.remove_stopwords and token in TURKISH_STOP_WORDS:
                continue

            # Basit stemming (Turkce icin suffix removal)
            if self.use_stemming:
                token = self._simple_stem(token)

            filtered_tokens.append(token)

        return filtered_tokens

    def _simple_stem(self, token: str) -> str:
        """
        Basit Turkce stemming.
        NOT: Tam bir stemmer degil, sadece yaygin son ekleri cikarir.
        """
        # Yaygin son ekler (uzundan kisaya)
        suffixes = [
            "lerin", "larin", "ler", "lar",
            "sin", "sın", "sun", "sün",
            "dan", "den", "tan", "ten",
            "in", "ın", "un", "ün",
            "da", "de", "ta", "te",
            "la", "le",
            "li", "lı", "lu", "lü",
            "ca", "ce", "ça", "çe",
        ]

        for suffix in suffixes:
            if len(token) > len(suffix) + 2 and token.endswith(suffix):
                return token[:-len(suffix)]

        return token

    def get_document_frequencies(self) -> Dict[str, int]:
        """Her terimin kac dokumanda gectigini dondur."""
        if not self._indexed:
            return {}

        df = {}
        for tokens in self.tokenized_corpus:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                df[token] = df.get(token, 0) + 1

        return df

    def get_top_terms(self, n: int = 20) -> List[Tuple[str, int]]:
        """En sik gecen terimleri dondur."""
        df = self.get_document_frequencies()
        sorted_terms = sorted(df.items(), key=lambda x: x[1], reverse=True)
        return sorted_terms[:n]

    def add_documents(
        self,
        new_documents: List[Dict[str, Any]],
        text_key: str = "text"
    ):
        """Mevcut indexe yeni dokumanlar ekle."""
        if not new_documents:
            return

        # Yeni dokumanlari ekle
        self.documents.extend(new_documents)

        for doc in new_documents:
            text = doc.get(text_key, "")
            tokens = self._tokenize(text)
            self.tokenized_corpus.append(tokens)

        # Index'i yeniden olustur
        if BM25_AVAILABLE:
            self.bm25 = BM25Okapi(
                self.tokenized_corpus,
                k1=self.k1,
                b=self.b
            )

    def clear(self):
        """Index'i temizle."""
        self.bm25 = None
        self.documents = []
        self.tokenized_corpus = []
        self._indexed = False

    def get_stats(self) -> Dict[str, Any]:
        """Index istatistiklerini dondur."""
        return {
            "indexed": self._indexed,
            "document_count": len(self.documents),
            "total_tokens": sum(len(t) for t in self.tokenized_corpus),
            "avg_doc_length": (
                sum(len(t) for t in self.tokenized_corpus) / len(self.tokenized_corpus)
                if self.tokenized_corpus else 0
            ),
            "unique_terms": len(self.get_document_frequencies()) if self._indexed else 0,
            "bm25_available": BM25_AVAILABLE
        }


class TurkishTokenizer:
    """Turkce icin optimize edilmis tokenizer."""

    def __init__(
        self,
        remove_stopwords: bool = True,
        use_stemming: bool = True,
        lowercase: bool = True,
        remove_numbers: bool = False,
        min_length: int = 2
    ):
        self.remove_stopwords = remove_stopwords
        self.use_stemming = use_stemming
        self.lowercase = lowercase
        self.remove_numbers = remove_numbers
        self.min_length = min_length

    def tokenize(self, text: str) -> List[str]:
        """Metni tokenize et."""
        if not text:
            return []

        # Kucuk harf
        if self.lowercase:
            text = text.lower()

        # Noktalama cikar
        text = re.sub(r'[^\w\s]', ' ', text)

        # Sayilari isle
        if self.remove_numbers:
            text = re.sub(r'\d+', '', text)

        tokens = text.split()

        # Filtrele
        result = []
        for token in tokens:
            if len(token) < self.min_length:
                continue

            if self.remove_stopwords and token in TURKISH_STOP_WORDS:
                continue

            if self.use_stemming:
                token = self._stem(token)

            result.append(token)

        return result

    def _stem(self, word: str) -> str:
        """Basit stemming."""
        # En yaygin Turkce son ekler
        suffixes = [
            "maktadir", "mektedir", "iyordu", "yordu",
            "acak", "ecek", "iyor", "uyor",
            "mak", "mek", "lik", "luk", "lar", "ler",
            "dan", "den", "tan", "ten",
            "in", "un", "da", "de"
        ]

        for suffix in suffixes:
            if len(word) > len(suffix) + 3 and word.endswith(suffix):
                return word[:-len(suffix)]

        return word

    def tokenize_batch(self, texts: List[str]) -> List[List[str]]:
        """Batch tokenization."""
        return [self.tokenize(text) for text in texts]
