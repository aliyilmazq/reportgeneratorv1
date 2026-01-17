"""Re-ranking Modulu - Cross-Encoder ile yeniden siralama."""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from rich.console import Console

console = Console()

# sentence-transformers CrossEncoder import
try:
    from sentence_transformers import CrossEncoder
    CROSSENCODER_AVAILABLE = True
except ImportError:
    CrossEncoder = None
    CROSSENCODER_AVAILABLE = False


@dataclass
class RerankResult:
    """Rerank sonucu."""
    text: str
    original_score: float
    rerank_score: float
    combined_score: float
    metadata: Dict[str, Any]
    rank: int


# Desteklenen reranker modelleri
RERANKER_MODELS = {
    "fast": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "balanced": "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "multilingual": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    "large": "cross-encoder/ms-marco-TinyBERT-L-2-v2"
}


class CrossEncoderReranker:
    """Cross-Encoder tabanli reranker."""

    def __init__(
        self,
        model_type: str = "multilingual",
        custom_model: str = None,
        device: str = "auto",
        max_length: int = 512
    ):
        """
        Cross-Encoder reranker olustur.

        Args:
            model_type: Model tipi (fast, balanced, multilingual)
            custom_model: Ozel model adi
            device: cpu, cuda, mps veya auto
            max_length: Maksimum sequence uzunlugu
        """
        self.model = None
        self.model_name = custom_model or RERANKER_MODELS.get(model_type, RERANKER_MODELS["multilingual"])
        self.device = device
        self.max_length = max_length
        self._initialized = False

        self._initialize_model()

    def _initialize_model(self):
        """Modeli yukle."""
        if not CROSSENCODER_AVAILABLE:
            console.print("[yellow]sentence-transformers CrossEncoder yuklenmemis[/yellow]")
            return

        try:
            device = self._get_device()
            self.model = CrossEncoder(
                self.model_name,
                device=device,
                max_length=self.max_length
            )
            self._initialized = True
            console.print(f"[green]CrossEncoder yuklendi: {self.model_name}[/green]")

        except Exception as e:
            console.print(f"[yellow]CrossEncoder yuklenemedi: {e}[/yellow]")
            self._initialized = False

    def _get_device(self) -> str:
        """Uygun device'i sec."""
        if self.device != "auto":
            return self.device

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass

        return "cpu"

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        text_key: str = "text",
        score_key: str = "score",
        batch_size: int = 32,
        min_score: float = None
    ) -> List[RerankResult]:
        """
        Dokumanlari yeniden sirala.

        Args:
            query: Arama sorgusu
            documents: Dokuman listesi
            top_k: Dondurulecek sonuc sayisi
            text_key: Text alani adi
            score_key: Orijinal skor alani adi
            batch_size: Batch boyutu
            min_score: Minimum rerank skoru

        Returns:
            RerankResult listesi
        """
        if not documents:
            return []

        if not self._initialized:
            # Model yuklenemediyse orijinal siralama ile dondur
            return self._fallback_rerank(documents, top_k, text_key, score_key)

        # Query-document cifti olustur
        pairs = []
        for doc in documents:
            text = doc.get(text_key, "")
            # Cok uzun metinleri kisalt
            if len(text) > 2000:
                text = text[:2000]
            pairs.append([query, text])

        try:
            # Cross-encoder skorlari
            scores = self.model.predict(pairs, batch_size=batch_size)

            # Sonuclari olustur
            results = []
            for i, (doc, rerank_score) in enumerate(zip(documents, scores)):
                original_score = doc.get(score_key, 0)

                # Combined score: rerank agirlikli
                combined = rerank_score * 0.7 + original_score * 0.3

                results.append(RerankResult(
                    text=doc.get(text_key, ""),
                    original_score=original_score,
                    rerank_score=float(rerank_score),
                    combined_score=combined,
                    metadata=doc,
                    rank=0  # Sonra atanacak
                ))

            # Sirala
            results.sort(key=lambda x: x.combined_score, reverse=True)

            # Rank ata
            for i, r in enumerate(results):
                r.rank = i + 1

            # Min score filtresi
            if min_score is not None:
                results = [r for r in results if r.rerank_score >= min_score]

            return results[:top_k]

        except Exception as e:
            console.print(f"[red]Rerank hatasi: {e}[/red]")
            return self._fallback_rerank(documents, top_k, text_key, score_key)

    def _fallback_rerank(
        self,
        documents: List[Dict[str, Any]],
        top_k: int,
        text_key: str,
        score_key: str
    ) -> List[RerankResult]:
        """Fallback: Orijinal siralama."""
        results = []

        sorted_docs = sorted(
            documents,
            key=lambda x: x.get(score_key, 0),
            reverse=True
        )

        for i, doc in enumerate(sorted_docs[:top_k]):
            score = doc.get(score_key, 0)
            results.append(RerankResult(
                text=doc.get(text_key, ""),
                original_score=score,
                rerank_score=score,  # Ayni skor
                combined_score=score,
                metadata=doc,
                rank=i + 1
            ))

        return results

    def rerank_with_diversity(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        lambda_param: float = 0.7,
        text_key: str = "text"
    ) -> List[RerankResult]:
        """
        Diversity ile rerank (MMR benzeri).

        Args:
            lambda_param: Relevance vs diversity dengesi (1.0 = pure relevance)
        """
        # Once normal rerank
        reranked = self.rerank(query, documents, top_k=len(documents), text_key=text_key)

        if len(reranked) <= top_k:
            return reranked

        # MMR ile secim
        selected = []
        remaining = reranked.copy()

        while len(selected) < top_k and remaining:
            best_score = float('-inf')
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # Relevance
                relevance = candidate.rerank_score

                # Diversity (en yakin selected'a uzaklik)
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

        # Rank guncelle
        for i, r in enumerate(selected):
            r.rank = i + 1

        return selected

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Basit Jaccard benzerlik."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0

    def is_available(self) -> bool:
        """Reranker kullanilabilir mi?"""
        return self._initialized


class MMRReranker:
    """Maximal Marginal Relevance ile reranking."""

    def __init__(self, embedder=None):
        """
        MMR Reranker.

        Args:
            embedder: Embedding olusturucu (None ise basit text similarity kullanilir)
        """
        self.embedder = embedder

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        lambda_param: float = 0.7,
        text_key: str = "text",
        score_key: str = "score"
    ) -> List[Dict[str, Any]]:
        """
        MMR ile yeniden sirala.

        MMR = lambda * Sim(doc, query) - (1-lambda) * max(Sim(doc, selected))
        """
        if not documents:
            return []

        # Orijinal skorlari al
        doc_scores = {
            i: doc.get(score_key, 0)
            for i, doc in enumerate(documents)
        }

        # Embedding'leri hesapla (varsa)
        embeddings = None
        if self.embedder:
            try:
                texts = [doc.get(text_key, "") for doc in documents]
                results = self.embedder.embed_batch(texts)
                embeddings = [r.embedding for r in results]
            except Exception:
                embeddings = None

        selected_indices = []
        remaining_indices = list(range(len(documents)))

        while len(selected_indices) < top_k and remaining_indices:
            best_score = float('-inf')
            best_idx = None

            for idx in remaining_indices:
                # Relevance score
                relevance = doc_scores[idx]

                # Diversity penalty
                if selected_indices:
                    if embeddings:
                        max_sim = max(
                            self._cosine_similarity(embeddings[idx], embeddings[sel])
                            for sel in selected_indices
                        )
                    else:
                        max_sim = max(
                            self._jaccard_similarity(
                                documents[idx].get(text_key, ""),
                                documents[sel].get(text_key, "")
                            )
                            for sel in selected_indices
                        )
                else:
                    max_sim = 0

                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)

        return [documents[i] for i in selected_indices]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Cosine similarity hesapla."""
        import math

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot / (norm1 * norm2)

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Jaccard similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0


def create_reranker(
    model_type: str = "multilingual",
    use_mmr: bool = False,
    embedder=None
):
    """
    Reranker olustur.

    Args:
        model_type: CrossEncoder model tipi
        use_mmr: MMR reranker kullan
        embedder: Embedder (MMR icin)
    """
    if use_mmr:
        return MMRReranker(embedder)
    else:
        return CrossEncoderReranker(model_type=model_type)
