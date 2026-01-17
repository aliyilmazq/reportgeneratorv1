"""Döküman Retriever Modülü - RAG için döküman çekici."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .embedder import DocumentEmbedder, DocumentChunker
from .vector_store import VectorStore

console = Console()


@dataclass
class RetrievedDocument:
    """Çekilen döküman."""
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""


@dataclass
class RAGContext:
    """RAG bağlamı - Claude'a gönderilecek."""
    query: str
    documents: List[RetrievedDocument] = field(default_factory=list)
    total_tokens: int = 0
    sources: List[str] = field(default_factory=list)


class DocumentRetriever:
    """RAG döküman çekici - Dökümanları indeksler ve sorgular."""

    def __init__(
        self,
        collection_name: str = "report_docs",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.embedder = DocumentEmbedder()
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.vector_store = VectorStore(collection_name=collection_name)

        self._indexed = False

    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> int:
        """Dökümanları indeksle."""
        if not documents:
            return 0

        # Dökümanları parçala
        all_chunks = []
        for doc in documents:
            text = doc.get('text', doc.get('content', ''))
            if not text:
                continue

            metadata = {
                'source': doc.get('source', doc.get('filename', 'unknown')),
                'type': doc.get('type', 'text')
            }

            chunks = self.chunker.chunk(text, metadata)
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        # Embedding oluştur
        texts = [c['text'] for c in all_chunks]

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"Embedding oluşturuluyor ({len(texts)} parça)...", total=None)
                embeddings = self.embedder.embed_batch(texts)
                progress.update(task, description="Vektör veritabanına ekleniyor...")

                # Veritabanına ekle
                self.vector_store.add(
                    documents=texts,
                    embeddings=[e.embedding for e in embeddings],
                    metadatas=[{k: v for k, v in c.items() if k != 'text'} for c in all_chunks]
                )
        else:
            embeddings = self.embedder.embed_batch(texts)
            self.vector_store.add(
                documents=texts,
                embeddings=[e.embedding for e in embeddings],
                metadatas=[{k: v for k, v in c.items() if k != 'text'} for c in all_chunks]
            )

        self._indexed = True
        console.print(f"[green]✓ {len(all_chunks)} parça indekslendi[/green]")

        return len(all_chunks)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[RetrievedDocument]:
        """Sorguya en uygun dökümanları getir."""
        if not self._indexed and self.vector_store.count() == 0:
            console.print("[yellow]Henüz indekslenmiş döküman yok[/yellow]")
            return []

        # Sorgu embedding'i
        query_embedding = self.embedder.embed(query)
        if not query_embedding:
            return []

        # Veritabanından sorgula
        results = self.vector_store.query(
            query_embedding=query_embedding.embedding,
            n_results=top_k
        )

        # Sonuçları dönüştür
        documents = []
        for i, doc_text in enumerate(results.get('documents', [])):
            distance = results['distances'][i] if results.get('distances') else 0
            score = 1 - distance  # Cosine distance -> similarity

            if score >= min_score:
                metadata = results['metadatas'][i] if results.get('metadatas') else {}
                documents.append(RetrievedDocument(
                    text=doc_text,
                    score=score,
                    metadata=metadata,
                    source=metadata.get('source', 'unknown')
                ))

        return documents

    def retrieve_for_section(
        self,
        section_id: str,
        section_title: str,
        top_k: int = 5
    ) -> RAGContext:
        """Belirli bir rapor bölümü için döküman çek."""
        # Bölüme özel sorgu oluştur
        section_queries = {
            'yonetici_ozeti': "proje özeti hedefler sonuçlar",
            'sirket_tanimi': "şirket tanımı misyon vizyon tarihçe",
            'pazar_analizi': "pazar büyüklüğü rekabet tüketici trend",
            'pazarlama_stratejisi': "pazarlama strateji fiyat dağıtım promosyon",
            'finansal_projeksiyonlar': "gelir maliyet kar zarar projeksiyon bütçe",
            'risk_analizi': "risk tehdit fırsat SWOT",
            'operasyon_plani': "operasyon süreç üretim kaynak",
            'yonetim_ekibi': "ekip yönetim organizasyon personel",
        }

        query = section_queries.get(section_id, section_title)
        documents = self.retrieve(query, top_k=top_k)

        # RAG bağlamı oluştur
        sources = list(set(d.source for d in documents))
        total_tokens = sum(len(d.text.split()) for d in documents) * 1.3  # Yaklaşık token

        return RAGContext(
            query=query,
            documents=documents,
            total_tokens=int(total_tokens),
            sources=sources
        )

    def format_context_for_prompt(
        self,
        context: RAGContext,
        max_chars: int = 8000
    ) -> str:
        """RAG bağlamını Claude promptu için formatla."""
        if not context.documents:
            return ""

        formatted_parts = ["## İLGİLİ DÖKÜMAN PARÇALARI\n"]
        current_chars = 0

        for i, doc in enumerate(context.documents, 1):
            doc_text = f"\n### Kaynak {i} ({doc.source}, skor: {doc.score:.2f})\n{doc.text}\n"

            if current_chars + len(doc_text) > max_chars:
                break

            formatted_parts.append(doc_text)
            current_chars += len(doc_text)

        if context.sources:
            formatted_parts.append(f"\n**Kaynaklar:** {', '.join(context.sources)}")

        return "".join(formatted_parts)

    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri döndür."""
        store_stats = self.vector_store.get_stats()
        return {
            **store_stats,
            "indexed": self._indexed,
            "embedding_model": self.embedder.model_name,
            "embedding_dimension": self.embedder.get_dimension()
        }

    def clear(self):
        """İndeksi temizle."""
        self.vector_store.reset()
        self._indexed = False
        console.print("[yellow]İndeks temizlendi[/yellow]")
