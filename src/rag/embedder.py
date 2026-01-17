"""Döküman Embedding Modülü - Metinleri vektörlere dönüştürür."""

import os
from typing import List, Optional
from dataclasses import dataclass

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from rich.console import Console

console = Console()


@dataclass
class EmbeddingResult:
    """Embedding sonucu."""
    text: str
    embedding: List[float]
    model: str
    dimension: int


class DocumentEmbedder:
    """Döküman embedding sınıfı - Local model veya hash fallback kullanır."""

    def __init__(
        self,
        model_name: str = "local-multilingual",
        api_key: Optional[str] = None,
        use_local: bool = True
    ):
        self.model_name = model_name
        self.local_model = None

        # Local SentenceTransformer kullan
        if SentenceTransformer:
            try:
                self.local_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self.model_name = "local-multilingual"
                console.print("[green]Local embedding modeli aktif[/green]")
            except Exception as e:
                console.print(f"[yellow]Local model yüklenemedi: {e}[/yellow]")

        if not self.local_model:
            console.print("[yellow]Embedding modeli bulunamadı, basit hash kullanılacak[/yellow]")

    def embed(self, text: str) -> EmbeddingResult:
        """Tek metin için embedding oluştur."""
        embeddings = self.embed_batch([text])
        return embeddings[0] if embeddings else None

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Batch embedding oluştur."""
        results = []

        if self.local_model:
            # Local SentenceTransformer
            try:
                embeddings = self.local_model.encode(texts)
                for text, embedding in zip(texts, embeddings):
                    results.append(EmbeddingResult(
                        text=text,
                        embedding=embedding.tolist(),
                        model=self.model_name,
                        dimension=len(embedding)
                    ))
            except Exception as e:
                console.print(f"[red]Local embedding hatası: {e}[/red]")
                return self._fallback_embed(texts)
        else:
            # Fallback: basit hash
            return self._fallback_embed(texts)

        return results

    def _fallback_embed(self, texts: List[str]) -> List[EmbeddingResult]:
        """Fallback: Basit hash tabanlı embedding."""
        import hashlib

        results = []
        for text in texts:
            # Basit bir hash tabanlı "embedding"
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            # 256 bit hash'i 64 boyutlu vektöre dönüştür
            embedding = [float(b) / 255.0 for b in hash_bytes[:64]]

            results.append(EmbeddingResult(
                text=text,
                embedding=embedding,
                model="hash-fallback",
                dimension=64
            ))

        return results

    def get_dimension(self) -> int:
        """Embedding boyutunu döndür."""
        if self.local_model:
            return 384  # MiniLM default
        else:
            return 64  # Fallback (hash)


class DocumentChunker:
    """Döküman parçalayıcı."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n\n"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk(self, text: str, metadata: dict = None) -> List[dict]:
        """Metni parçalara ayır."""
        if not text:
            return []

        chunks = []
        metadata = metadata or {}

        # Önce paragraflara böl
        paragraphs = text.split(self.separator)

        current_chunk = ""
        current_position = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Eğer paragraf çok uzunsa, cümlelere böl
            if len(para) > self.chunk_size:
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= self.chunk_size:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk.strip():
                            chunks.append({
                                "text": current_chunk.strip(),
                                "position": current_position,
                                **metadata
                            })
                            current_position += 1

                        # Overlap için son kısmı tut
                        overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                        current_chunk = overlap_text + sentence + " "
            else:
                if len(current_chunk) + len(para) <= self.chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk.strip():
                        chunks.append({
                            "text": current_chunk.strip(),
                            "position": current_position,
                            **metadata
                        })
                        current_position += 1

                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                    current_chunk = overlap_text + para + "\n\n"

        # Son chunk
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "position": current_position,
                **metadata
            })

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Metni cümlelere ayır."""
        import re
        # Türkçe ve İngilizce cümle sonu
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_documents(
        self,
        documents: List[dict]
    ) -> List[dict]:
        """Birden fazla dökümanı parçala."""
        all_chunks = []

        for doc in documents:
            text = doc.get('text', doc.get('content', ''))
            metadata = {k: v for k, v in doc.items() if k not in ['text', 'content']}

            chunks = self.chunk(text, metadata)
            all_chunks.extend(chunks)

        return all_chunks
