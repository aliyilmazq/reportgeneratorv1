"""Gelismis Embedding Modulu - BGE-M3 ve E5-large destegi."""

import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console

console = Console()


@dataclass
class EmbeddingConfig:
    """Embedding konfigurasyonu."""
    model_name: str = "intfloat/multilingual-e5-large"
    dimension: int = 1024
    batch_size: int = 32
    max_length: int = 512
    normalize: bool = True
    device: str = "auto"  # cpu, cuda, mps, auto
    use_fp16: bool = False
    cache_embeddings: bool = True

    # Instruction prefixes (E5 ve BGE icin)
    query_instruction: str = "query: "
    passage_instruction: str = "passage: "


@dataclass
class EmbeddingResult:
    """Embedding sonucu."""
    text: str
    embedding: List[float]
    model: str
    dimension: int
    is_query: bool = False


# Desteklenen modeller
SUPPORTED_MODELS = {
    "e5-large": {
        "name": "intfloat/multilingual-e5-large",
        "dimension": 1024,
        "max_length": 512,
        "query_instruction": "query: ",
        "passage_instruction": "passage: "
    },
    "e5-base": {
        "name": "intfloat/multilingual-e5-base",
        "dimension": 768,
        "max_length": 512,
        "query_instruction": "query: ",
        "passage_instruction": "passage: "
    },
    "bge-m3": {
        "name": "BAAI/bge-m3",
        "dimension": 1024,
        "max_length": 8192,
        "query_instruction": "",
        "passage_instruction": ""
    },
    "minilm": {
        "name": "paraphrase-multilingual-MiniLM-L12-v2",
        "dimension": 384,
        "max_length": 512,
        "query_instruction": "",
        "passage_instruction": ""
    }
}


class AdvancedEmbedder:
    """Gelismis embedding sinifi - E5-large ve BGE-M3 destegi."""

    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or EmbeddingConfig()
        self.model = None
        self.model_info = None
        self._initialized = False

        self._initialize_model()

    def _initialize_model(self):
        """Modeli yukle."""
        try:
            from sentence_transformers import SentenceTransformer

            # Model bilgisini bul
            model_key = self._find_model_key(self.config.model_name)
            if model_key:
                self.model_info = SUPPORTED_MODELS[model_key]
                model_name = self.model_info["name"]
            else:
                model_name = self.config.model_name
                self.model_info = {
                    "name": model_name,
                    "dimension": self.config.dimension,
                    "max_length": self.config.max_length,
                    "query_instruction": self.config.query_instruction,
                    "passage_instruction": self.config.passage_instruction
                }

            # Device secimi
            device = self._get_device()

            # Modeli yukle
            self.model = SentenceTransformer(model_name, device=device)

            # FP16 kullan (GPU varsa)
            if self.config.use_fp16 and device != "cpu":
                self.model = self.model.half()

            self._initialized = True
            console.print(f"[green]Gelismis embedding modeli yuklendi: {model_name}[/green]")
            console.print(f"[dim]Dimension: {self.model_info['dimension']}, Device: {device}[/dim]")

        except ImportError:
            console.print("[yellow]sentence-transformers yuklenmemis, fallback kullanilacak[/yellow]")
            self._use_fallback()
        except Exception as e:
            console.print(f"[yellow]Model yuklenemedi: {e}, fallback kullanilacak[/yellow]")
            self._use_fallback()

    def _find_model_key(self, model_name: str) -> Optional[str]:
        """Model anahtar adini bul."""
        model_name_lower = model_name.lower()

        for key, info in SUPPORTED_MODELS.items():
            if key in model_name_lower or info["name"].lower() in model_name_lower:
                return key

        return None

    def _get_device(self) -> str:
        """Uygun device'i sec."""
        if self.config.device != "auto":
            return self.config.device

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass

        return "cpu"

    def _use_fallback(self):
        """Fallback: MiniLM modeli."""
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self.model_info = SUPPORTED_MODELS["minilm"]
            self._initialized = True
            console.print("[yellow]Fallback model kullaniliyor: MiniLM[/yellow]")

        except Exception as e:
            console.print(f"[red]Fallback da basarisiz: {e}[/red]")
            self._initialized = False

    def _add_instruction(self, text: str, is_query: bool = False) -> str:
        """Instruction prefix ekle (E5 ve BGE icin)."""
        if not self.model_info:
            return text

        if is_query:
            instruction = self.model_info.get("query_instruction", "")
        else:
            instruction = self.model_info.get("passage_instruction", "")

        if instruction and not text.startswith(instruction):
            return instruction + text

        return text

    def embed(self, text: str, is_query: bool = False) -> Optional[EmbeddingResult]:
        """Tek metin icin embedding olustur."""
        results = self.embed_batch([text], is_query=is_query)
        return results[0] if results else None

    def embed_batch(
        self,
        texts: List[str],
        is_query: bool = False,
        show_progress: bool = False
    ) -> List[EmbeddingResult]:
        """Batch embedding olustur."""
        if not self._initialized or not self.model:
            return self._fallback_embed_batch(texts, is_query)

        try:
            # Instruction ekle
            processed_texts = [self._add_instruction(t, is_query) for t in texts]

            # Embedding olustur
            embeddings = self.model.encode(
                processed_texts,
                batch_size=self.config.batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=self.config.normalize
            )

            # Sonuclari dondur
            results = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                results.append(EmbeddingResult(
                    text=text,
                    embedding=embedding.tolist(),
                    model=self.model_info["name"],
                    dimension=len(embedding),
                    is_query=is_query
                ))

            return results

        except Exception as e:
            console.print(f"[red]Embedding hatasi: {e}[/red]")
            return self._fallback_embed_batch(texts, is_query)

    def _fallback_embed_batch(
        self,
        texts: List[str],
        is_query: bool = False
    ) -> List[EmbeddingResult]:
        """Fallback: Hash tabanli embedding."""
        import hashlib

        results = []
        for text in texts:
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            # 64 boyutlu vektor
            embedding = [float(b) / 255.0 for b in hash_bytes[:64]]

            results.append(EmbeddingResult(
                text=text,
                embedding=embedding,
                model="hash-fallback",
                dimension=64,
                is_query=is_query
            ))

        return results

    def get_dimension(self) -> int:
        """Embedding boyutunu dondur."""
        if self.model_info:
            return self.model_info["dimension"]
        return 64  # Fallback

    def get_model_name(self) -> str:
        """Model adini dondur."""
        if self.model_info:
            return self.model_info["name"]
        return "hash-fallback"


class AsyncBatchProcessor:
    """Buyuk batch'ler icin async isleyici."""

    def __init__(
        self,
        embedder: AdvancedEmbedder,
        max_concurrent: int = 4
    ):
        self.embedder = embedder
        self.max_concurrent = max_concurrent
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._closed = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - executor'u duzgun kapat."""
        self.close()
        return False

    def close(self):
        """Executor'u guvenlice kapat."""
        if not self._closed:
            self.executor.shutdown(wait=True)
            self._closed = True

    async def process_documents(
        self,
        documents: List[str],
        batch_size: int = 32,
        is_query: bool = False,
        progress_callback: callable = None
    ) -> List[EmbeddingResult]:
        """Buyuk dokuman setleri icin paralel embedding."""

        # Batch'lere bol
        batches = [
            documents[i:i + batch_size]
            for i in range(0, len(documents), batch_size)
        ]

        all_results = []
        loop = asyncio.get_event_loop()

        for i, batch in enumerate(batches):
            # Batch'i isle
            results = await loop.run_in_executor(
                self.executor,
                lambda b=batch: self.embedder.embed_batch(b, is_query=is_query)
            )
            all_results.extend(results)

            # Progress callback
            if progress_callback:
                progress = (i + 1) / len(batches) * 100
                progress_callback(progress, len(all_results), len(documents))

        return all_results

    def process_documents_sync(
        self,
        documents: List[str],
        batch_size: int = 32,
        is_query: bool = False
    ) -> List[EmbeddingResult]:
        """Senkron batch isleme."""
        return asyncio.run(
            self.process_documents(documents, batch_size, is_query)
        )

    def __del__(self):
        """Executor'u kapat (fallback)."""
        if not self._closed:
            try:
                self.executor.shutdown(wait=False)
            except (RuntimeError, TypeError):
                # Interpreter shutdown sirasinda hata olabilir
                pass


def create_embedder(model_type: str = "e5-large") -> AdvancedEmbedder:
    """Kolayca embedder olustur."""
    if model_type in SUPPORTED_MODELS:
        config = EmbeddingConfig(
            model_name=SUPPORTED_MODELS[model_type]["name"],
            dimension=SUPPORTED_MODELS[model_type]["dimension"],
            max_length=SUPPORTED_MODELS[model_type]["max_length"],
            query_instruction=SUPPORTED_MODELS[model_type]["query_instruction"],
            passage_instruction=SUPPORTED_MODELS[model_type]["passage_instruction"]
        )
    else:
        config = EmbeddingConfig(model_name=model_type)

    return AdvancedEmbedder(config)
