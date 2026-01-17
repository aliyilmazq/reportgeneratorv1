"""Context Sikistirma Modulu - Ilgisiz icerigi cikar ve ozetle."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class CompressedChunk:
    """Sikistirilmis dokuman parcasi."""
    original_text: str
    compressed_text: str
    relevance_score: float
    compression_ratio: float
    key_points: List[str]


class ContextCompressor:
    """Context sikistirma ve optimizasyonu."""

    def __init__(self, anthropic_client=None):
        """
        Context compressor.

        Args:
            anthropic_client: Anthropic API client (LLM-based compression icin)
        """
        self.client = anthropic_client

    def compress_for_query(
        self,
        documents: List[Dict[str, Any]],
        query: str,
        max_output_tokens: int = 2000,
        text_key: str = "text"
    ) -> List[CompressedChunk]:
        """
        Dokumanlari sorguya gore sikistir.

        Args:
            documents: Dokuman listesi
            query: Arama sorgusu
            max_output_tokens: Maksimum cikti token sayisi
            text_key: Text alani adi

        Returns:
            CompressedChunk listesi
        """
        if not documents:
            return []

        results = []
        query_words = set(query.lower().split())

        for doc in documents:
            text = doc.get(text_key, "")

            # Ilgili cumleleri cikar
            relevant_sentences = self.extract_relevant_sentences(
                text, query, min_relevance=0.3
            )

            if relevant_sentences:
                compressed_text = " ".join(relevant_sentences)
            else:
                # Fallback: ilk 500 karakter
                compressed_text = text[:500]

            # Key points cikar
            key_points = self.extract_key_points(text, query_words)

            # Compression ratio hesapla
            original_len = len(text)
            compressed_len = len(compressed_text)
            ratio = compressed_len / original_len if original_len > 0 else 1

            results.append(CompressedChunk(
                original_text=text,
                compressed_text=compressed_text,
                relevance_score=doc.get("score", 0),
                compression_ratio=ratio,
                key_points=key_points
            ))

        return results

    def extract_relevant_sentences(
        self,
        document: str,
        query: str,
        min_relevance: float = 0.3
    ) -> List[str]:
        """
        Sadece ilgili cumleleri cikar.

        Args:
            document: Dokuman metni
            query: Sorgu
            min_relevance: Minimum relevance skoru

        Returns:
            Ilgili cumle listesi
        """
        if not document:
            return []

        # Cumlelere bol
        sentences = self._split_sentences(document)
        query_words = set(query.lower().split())

        relevant = []
        for sentence in sentences:
            sentence_words = set(sentence.lower().split())

            # Jaccard benzerligi
            intersection = len(query_words & sentence_words)
            union = len(query_words | sentence_words)
            similarity = intersection / union if union > 0 else 0

            # Keyword eslesmesi
            keyword_score = intersection / len(query_words) if query_words else 0

            # Combined score
            relevance = (similarity + keyword_score) / 2

            if relevance >= min_relevance:
                relevant.append(sentence)

        return relevant

    def _split_sentences(self, text: str) -> List[str]:
        """Metni cumlelere bol."""
        from .utils import split_sentences
        return split_sentences(text, min_length=20)

    def extract_key_points(
        self,
        text: str,
        query_words: set,
        max_points: int = 5
    ) -> List[str]:
        """Metinden anahtar noktalari cikar."""
        key_points = []

        # Sayi iceren cumleler (istatistik)
        number_pattern = r'[^.]*\d+[%.,]?\d*[^.]*\.'
        number_matches = re.findall(number_pattern, text)
        for match in number_matches[:2]:
            if any(word in match.lower() for word in query_words):
                key_points.append(match.strip())

        # Query kelimelerini iceren kisa cumleler
        sentences = self._split_sentences(text)
        for sentence in sentences:
            if len(sentence) < 200:
                sentence_lower = sentence.lower()
                match_count = sum(1 for w in query_words if w in sentence_lower)
                if match_count >= 2:
                    key_points.append(sentence)

        return key_points[:max_points]

    def summarize_chunk(
        self,
        chunk: str,
        target_length: int = 200,
        query: str = None
    ) -> str:
        """
        Chunk'i ozetle.

        Args:
            chunk: Ozutlenecek metin
            target_length: Hedef kelime sayisi
            query: Odaklanilacak sorgu

        Returns:
            Ozetlenmis metin
        """
        if not self.client:
            # LLM olmadan basit ozet
            return self._simple_summarize(chunk, target_length)

        try:
            prompt = f"""Asagidaki metni {target_length} kelimeye ozetle.
ONEMLI bilgileri koru, gereksiz detaylari cikar.
{"Odak: " + query if query else ""}

Metin:
{chunk[:3000]}

Ozet:"""

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=target_length * 2,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        except Exception as e:
            console.print(f"[yellow]Ozetleme hatasi: {e}[/yellow]")
            return self._simple_summarize(chunk, target_length)

    def _simple_summarize(self, text: str, target_words: int) -> str:
        """Basit ozetleme (LLM olmadan)."""
        sentences = self._split_sentences(text)

        result = []
        word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= target_words:
                result.append(sentence)
                word_count += sentence_words
            else:
                break

        return " ".join(result)


class LLMBasedCompressor:
    """LLM tabanli akilli sikistirma."""

    def __init__(self, anthropic_client):
        self.client = anthropic_client

    def compress_with_context(
        self,
        chunks: List[str],
        query: str,
        section_type: str,
        max_output_words: int = 500
    ) -> str:
        """
        Claude ile context-aware sikistirma.

        Args:
            chunks: Chunk listesi
            query: Arama sorgusu
            section_type: Bolum tipi
            max_output_words: Maksimum cikti kelime sayisi
        """
        if not self.client:
            return "\n\n".join(chunks)[:2000]

        section_guidance = self._get_section_guidance(section_type)

        combined_chunks = "\n\n---\n\n".join(chunks)

        prompt = f"""Asagidaki dokuman parcalarini "{query}" sorusu icin optimize et.
{section_guidance}

Kurallar:
1. Sadece ilgili bilgileri koru
2. Gereksiz tekrarlari cikar
3. Sayisal verileri mutlaka koru
4. Maksimum {max_output_words} kelime kullan
5. Turkce yaz

Dokuman Parcalari:
{combined_chunks[:6000]}

Sikistirilmis ve optimize edilmis cikti:"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_output_words * 2,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        except Exception as e:
            console.print(f"[yellow]LLM sikistirma hatasi: {e}[/yellow]")
            return "\n\n".join(chunks)[:2000]

    def _get_section_guidance(self, section_type: str) -> str:
        """Bolum tipine gore rehberlik."""
        guidance = {
            "finansal_projeksiyonlar": "Sayisal verileri ve finansal metrikleri mutlaka koru.",
            "pazar_analizi": "Pazar buyuklugu, trendler ve istatistikleri koru.",
            "risk_analizi": "Risk faktorleri ve etki degerlendirmelerini koru.",
            "yonetici_ozeti": "Ana hedefler, sonuclar ve kritik metrikleri koru.",
            "sirket_tanimi": "Sirket kimligini ve temel bilgileri koru.",
            "pazarlama_stratejisi": "Strateji detaylari ve hedef kitle bilgilerini koru.",
            "operasyon_plani": "Surec adimlari ve kaynak bilgilerini koru.",
            "yonetim_ekibi": "Isim, pozisyon ve deneyim bilgilerini koru."
        }
        return guidance.get(section_type, "Tum onemli bilgileri koru.")


class ChunkRanker:
    """Chunk'lari relevance'a gore sirala ve filtrele."""

    def __init__(self, embedder=None):
        self.embedder = embedder

    def rank_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        top_k: int = 10,
        text_key: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Chunk'lari query'ye gore sirala.
        """
        if not chunks:
            return []

        query_words = set(query.lower().split())
        scored_chunks = []

        for chunk in chunks:
            text = chunk.get(text_key, "")
            text_words = set(text.lower().split())

            # Keyword overlap skoru
            overlap = len(query_words & text_words)
            keyword_score = overlap / len(query_words) if query_words else 0

            # Mevcut skor varsa kullan
            existing_score = chunk.get("score", 0)

            # Combined score
            combined = keyword_score * 0.4 + existing_score * 0.6

            scored_chunks.append({
                **chunk,
                "combined_score": combined
            })

        # Sirala
        scored_chunks.sort(key=lambda x: x["combined_score"], reverse=True)

        return scored_chunks[:top_k]

    def filter_by_relevance(
        self,
        chunks: List[Dict[str, Any]],
        min_score: float = 0.3,
        score_key: str = "score"
    ) -> List[Dict[str, Any]]:
        """Dusuk skorlu chunk'lari filtrele."""
        return [c for c in chunks if c.get(score_key, 0) >= min_score]

    def deduplicate(
        self,
        chunks: List[Dict[str, Any]],
        text_key: str = "text",
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Benzer chunk'lari cikar."""
        if not chunks:
            return []

        unique = [chunks[0]]

        for chunk in chunks[1:]:
            text = chunk.get(text_key, "")
            is_duplicate = False

            for existing in unique:
                existing_text = existing.get(text_key, "")
                similarity = self._jaccard_similarity(text, existing_text)

                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(chunk)

        return unique

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Jaccard similarity hesapla."""
        from .utils import jaccard_similarity
        return jaccard_similarity(text1, text2, max_words=100)
