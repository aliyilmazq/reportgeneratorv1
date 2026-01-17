"""Hybrid Retriever Modulu - BM25 + Semantic + Reranking."""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console

from .advanced_embedder import AdvancedEmbedder, EmbeddingConfig
from .bm25_index import BM25Index
from .reranker import CrossEncoderReranker, MMRReranker
from .vector_store import VectorStore
from .cache_manager import QueryCache, EmbeddingCache

console = Console()


@dataclass
class HybridSearchConfig:
    """Hybrid search konfigurasyonu."""
    # Agirliklari
    semantic_weight: float = 0.6
    bm25_weight: float = 0.4

    # RRF parametreleri
    use_rrf: bool = True
    rrf_k: int = 60

    # Retrieval parametreleri
    initial_fetch: int = 30
    final_top_k: int = 5

    # Reranking
    use_reranking: bool = True
    rerank_top_k: int = 20
    min_rerank_score: float = 0.3

    # MMR
    use_mmr: bool = True
    mmr_lambda: float = 0.7

    # Cache
    use_cache: bool = True
    cache_ttl_hours: int = 24


@dataclass
class HybridResult:
    """Hybrid arama sonucu."""
    text: str
    score: float
    semantic_score: float
    bm25_score: float
    rerank_score: Optional[float]
    metadata: Dict[str, Any]
    source: str
    rank: int


@dataclass
class RetrievedDocument:
    """Cikarilan dokuman."""
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""


class HybridRetriever:
    """BM25 + Semantic + Reranking birlestiren retriever."""

    def __init__(
        self,
        config: HybridSearchConfig = None,
        collection_name: str = "report_docs",
        embedder: AdvancedEmbedder = None,
        vector_store: VectorStore = None
    ):
        self.config = config or HybridSearchConfig()
        self.collection_name = collection_name

        # Embedder
        self.embedder = embedder or AdvancedEmbedder()

        # Vector store
        self.vector_store = vector_store or VectorStore(collection_name=collection_name)

        # BM25 index
        self.bm25_index = BM25Index()
        self._bm25_indexed = False

        # Reranker
        self.reranker = None
        if self.config.use_reranking:
            self.reranker = CrossEncoderReranker(model_type="multilingual")

        # Cache
        self.query_cache = None
        self.embedding_cache = None
        if self.config.use_cache:
            self.query_cache = QueryCache(ttl_hours=self.config.cache_ttl_hours)
            self.embedding_cache = EmbeddingCache()

    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        text_key: str = "text",
        show_progress: bool = True
    ) -> int:
        """
        Dokumanlari hem semantic hem BM25 icin indeksle.
        """
        if not documents:
            return 0

        # Semantic index (VectorStore)
        texts = [doc.get(text_key, "") for doc in documents]

        # Embedding olustur
        if show_progress:
            console.print("[dim]Embedding olusturuluyor...[/dim]")

        embeddings = self.embedder.embed_batch(texts, is_query=False)

        # VectorStore'a ekle
        self.vector_store.add(
            documents=texts,
            embeddings=[e.embedding for e in embeddings],
            metadatas=[{k: v for k, v in doc.items() if k != text_key} for doc in documents]
        )

        # BM25 index
        if show_progress:
            console.print("[dim]BM25 index olusturuluyor...[/dim]")

        self.bm25_index.build_index(documents, text_key=text_key)
        self._bm25_indexed = True

        console.print(f"[green]Hybrid index olusturuldu: {len(documents)} dokuman[/green]")
        return len(documents)

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        filters: Dict[str, Any] = None
    ) -> List[HybridResult]:
        """
        Hybrid retrieval yap.

        Args:
            query: Arama sorgusu
            top_k: Dondurulecek sonuc sayisi
            filters: Metadata filtreleri

        Returns:
            HybridResult listesi
        """
        top_k = top_k or self.config.final_top_k

        # Cache kontrolu
        if self.query_cache:
            cache_key = f"{query}:{filters}"
            cached = self.query_cache.get(cache_key)
            if cached:
                return cached

        # Paralel arama
        semantic_results = []
        bm25_results = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(self._semantic_search, query, self.config.initial_fetch, filters): "semantic",
                executor.submit(self._bm25_search, query, self.config.initial_fetch): "bm25"
            }

            for future in as_completed(futures):
                search_type = futures[future]
                try:
                    results = future.result()
                    if search_type == "semantic":
                        semantic_results = results
                    else:
                        bm25_results = results
                except Exception as e:
                    console.print(f"[yellow]{search_type} arama hatasi: {e}[/yellow]")

        # Sonuclari birlestir
        if self.config.use_rrf:
            merged = self._rrf_fusion(semantic_results, bm25_results)
        else:
            merged = self._weighted_fusion(semantic_results, bm25_results)

        # Reranking
        if self.config.use_reranking and self.reranker and self.reranker.is_available():
            merged = self._apply_reranking(query, merged)

        # MMR
        if self.config.use_mmr:
            merged = self._apply_mmr(merged)

        # Top-k
        results = merged[:top_k]

        # Rank guncelle
        for i, r in enumerate(results):
            r.rank = i + 1

        # Cache
        if self.query_cache:
            self.query_cache.set(cache_key, results)

        return results

    def _semantic_search(
        self,
        query: str,
        top_k: int,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Semantic arama."""
        # Query embedding
        if self.embedding_cache:
            cached_emb = self.embedding_cache.get(query, self.embedder.get_model_name())
            if cached_emb:
                query_embedding = cached_emb
            else:
                result = self.embedder.embed(query, is_query=True)
                query_embedding = result.embedding
                self.embedding_cache.set(query, self.embedder.get_model_name(), query_embedding)
        else:
            result = self.embedder.embed(query, is_query=True)
            query_embedding = result.embedding

        # VectorStore sorgusu
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where=filters
        )

        # Formatlama
        formatted = []
        for i, doc_text in enumerate(results.get('documents', [])):
            distance = results['distances'][i] if results.get('distances') else 0
            score = 1 - distance  # Distance -> similarity

            formatted.append({
                "text": doc_text,
                "score": score,
                "metadata": results['metadatas'][i] if results.get('metadatas') else {},
                "source": "semantic"
            })

        return formatted

    def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """BM25 arama."""
        if not self._bm25_indexed:
            return []

        results = self.bm25_index.search(query, top_k=top_k)

        formatted = []
        for r in results:
            # BM25 skorunu 0-1 arasina normalize et
            normalized_score = min(1.0, r.score / 10.0)  # Yaklasik normalizasyon

            formatted.append({
                "text": r.text,
                "score": normalized_score,
                "metadata": r.metadata,
                "source": "bm25"
            })

        return formatted

    def _rrf_fusion(
        self,
        semantic_results: List[Dict],
        bm25_results: List[Dict]
    ) -> List[HybridResult]:
        """
        Reciprocal Rank Fusion ile birlestir.

        RRF(d) = sum(1 / (k + rank(d)))
        """
        k = self.config.rrf_k
        doc_scores = {}

        # Semantic skorlari
        for rank, doc in enumerate(semantic_results, 1):
            text_key = doc["text"][:200]  # Unique key
            if text_key not in doc_scores:
                doc_scores[text_key] = {
                    "doc": doc,
                    "semantic_rank": rank,
                    "bm25_rank": None,
                    "semantic_score": doc["score"],
                    "bm25_score": 0
                }
            doc_scores[text_key]["semantic_rank"] = rank
            doc_scores[text_key]["semantic_score"] = doc["score"]

        # BM25 skorlari
        for rank, doc in enumerate(bm25_results, 1):
            text_key = doc["text"][:200]
            if text_key not in doc_scores:
                doc_scores[text_key] = {
                    "doc": doc,
                    "semantic_rank": None,
                    "bm25_rank": rank,
                    "semantic_score": 0,
                    "bm25_score": doc["score"]
                }
            else:
                doc_scores[text_key]["bm25_rank"] = rank
                doc_scores[text_key]["bm25_score"] = doc["score"]

        # RRF skorlarini hesapla
        results = []
        for text_key, data in doc_scores.items():
            rrf_score = 0

            if data["semantic_rank"]:
                rrf_score += 1 / (k + data["semantic_rank"])

            if data["bm25_rank"]:
                rrf_score += 1 / (k + data["bm25_rank"])

            doc = data["doc"]
            results.append(HybridResult(
                text=doc["text"],
                score=rrf_score,
                semantic_score=data["semantic_score"],
                bm25_score=data["bm25_score"],
                rerank_score=None,
                metadata=doc.get("metadata", {}),
                source=doc.get("metadata", {}).get("source", ""),
                rank=0
            ))

        # Sirala
        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def _weighted_fusion(
        self,
        semantic_results: List[Dict],
        bm25_results: List[Dict]
    ) -> List[HybridResult]:
        """Agirlikli birlestirme."""
        doc_scores = {}

        # Semantic
        for doc in semantic_results:
            text_key = doc["text"][:200]
            score = doc["score"] * self.config.semantic_weight
            doc_scores[text_key] = {
                "doc": doc,
                "score": score,
                "semantic_score": doc["score"],
                "bm25_score": 0
            }

        # BM25
        for doc in bm25_results:
            text_key = doc["text"][:200]
            bm25_contribution = doc["score"] * self.config.bm25_weight

            if text_key in doc_scores:
                doc_scores[text_key]["score"] += bm25_contribution
                doc_scores[text_key]["bm25_score"] = doc["score"]
            else:
                doc_scores[text_key] = {
                    "doc": doc,
                    "score": bm25_contribution,
                    "semantic_score": 0,
                    "bm25_score": doc["score"]
                }

        # Sonuclari olustur
        results = []
        for text_key, data in doc_scores.items():
            doc = data["doc"]
            results.append(HybridResult(
                text=doc["text"],
                score=data["score"],
                semantic_score=data["semantic_score"],
                bm25_score=data["bm25_score"],
                rerank_score=None,
                metadata=doc.get("metadata", {}),
                source=doc.get("metadata", {}).get("source", ""),
                rank=0
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _apply_reranking(
        self,
        query: str,
        results: List[HybridResult]
    ) -> List[HybridResult]:
        """Reranking uygula."""
        if not results:
            return results

        # Top-k'yi rerank et
        to_rerank = results[:self.config.rerank_top_k]

        # Dict formatina cevir
        docs = [
            {"text": r.text, "score": r.score, "metadata": r.metadata}
            for r in to_rerank
        ]

        # Rerank
        reranked = self.reranker.rerank(
            query=query,
            documents=docs,
            top_k=len(docs),
            min_score=self.config.min_rerank_score
        )

        # Sonuclari guncelle
        new_results = []
        for rr in reranked:
            # Orijinal sonucu bul
            for orig in to_rerank:
                if orig.text == rr.text:
                    orig.rerank_score = rr.rerank_score
                    orig.score = rr.combined_score
                    new_results.append(orig)
                    break

        # Rerank edilmeyenleri ekle
        remaining = results[self.config.rerank_top_k:]
        new_results.extend(remaining)

        # Yeniden sirala
        new_results.sort(key=lambda x: x.score, reverse=True)

        return new_results

    def _apply_mmr(self, results: List[HybridResult]) -> List[HybridResult]:
        """MMR uygula (diversity)."""
        if len(results) <= 1:
            return results

        selected = []
        remaining = results.copy()
        lambda_param = self.config.mmr_lambda

        while remaining and len(selected) < len(results):
            best_score = float('-inf')
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # Relevance
                relevance = candidate.score

                # Diversity
                if selected:
                    max_sim = max(
                        self._text_similarity(candidate.text, s.text)
                        for s in selected
                    )
                else:
                    max_sim = 0

                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Basit Jaccard similarity."""
        words1 = set(text1.lower().split()[:50])
        words2 = set(text2.lower().split()[:50])

        if not words1 or not words2:
            return 0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0

    def retrieve_for_section(
        self,
        section_id: str,
        section_title: str,
        top_k: int = 5
    ) -> List[HybridResult]:
        """Bolum icin retrieval."""
        # Bolume ozel query
        section_queries = {
            'yonetici_ozeti': f"{section_title} proje ozeti hedefler sonuclar",
            'sirket_tanimi': f"{section_title} sirket misyon vizyon tarihce",
            'pazar_analizi': f"{section_title} pazar buyuklugu rekabet trend",
            'pazarlama_stratejisi': f"{section_title} pazarlama strateji fiyat dagitim",
            'finansal_projeksiyonlar': f"{section_title} gelir maliyet kar projeksiyon",
            'risk_analizi': f"{section_title} risk tehdit firsat SWOT",
            'operasyon_plani': f"{section_title} operasyon surec uretim",
            'yonetim_ekibi': f"{section_title} ekip yonetim organizasyon"
        }

        query = section_queries.get(section_id, section_title)
        return self.retrieve(query, top_k=top_k)

    def get_stats(self) -> Dict[str, Any]:
        """Istatistikleri dondur."""
        return {
            "vector_store": self.vector_store.get_stats(),
            "bm25_index": self.bm25_index.get_stats() if self._bm25_indexed else {},
            "reranker_available": self.reranker.is_available() if self.reranker else False,
            "config": {
                "semantic_weight": self.config.semantic_weight,
                "bm25_weight": self.config.bm25_weight,
                "use_rrf": self.config.use_rrf,
                "use_reranking": self.config.use_reranking,
                "use_mmr": self.config.use_mmr
            }
        }

    def clear(self):
        """Indexleri temizle."""
        self.vector_store.reset()
        self.bm25_index.clear()
        self._bm25_indexed = False

        if self.query_cache:
            self.query_cache.clear()

        console.print("[yellow]Hybrid index temizlendi[/yellow]")

    def close(self):
        """Tum kaynaklari temizle."""
        self.clear()
        # Cache'leri temizle
        if self.query_cache:
            self.query_cache.clear()
        if self.embedding_cache:
            self.embedding_cache.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - kaynaklari temizle."""
        self.close()
        return False
