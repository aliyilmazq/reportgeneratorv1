"""Vektör Veritabanı Modülü - ChromaDB ile vektör depolama."""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from rich.console import Console

console = Console()


class VectorStore:
    """ChromaDB tabanlı vektör veritabanı."""

    def __init__(
        self,
        collection_name: str = "report_docs",
        persist_directory: str = None
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory or str(
            Path(__file__).parent.parent.parent / ".chromadb"
        )
        self.client = None
        self.collection = None

        if chromadb:
            self._initialize_db()
        else:
            console.print("[yellow]ChromaDB yüklü değil, bellek içi depolama kullanılacak[/yellow]")
            self._use_memory_store()

    def _initialize_db(self):
        """ChromaDB'yi başlat."""
        try:
            # Persist directory oluştur
            os.makedirs(self.persist_directory, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Collection oluştur veya al
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            console.print(f"[green]ChromaDB aktif: {self.collection_name}[/green]")

        except Exception as e:
            console.print(f"[yellow]ChromaDB hatası: {e}, bellek içi mod kullanılıyor[/yellow]")
            self._use_memory_store()

    def _use_memory_store(self):
        """Bellek içi depolama kullan."""
        self._memory_store = {
            "documents": [],
            "embeddings": [],
            "metadatas": [],
            "ids": []
        }

    def add(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict] = None,
        ids: List[str] = None
    ):
        """Dökümanları ekle."""
        if not documents:
            return

        # ID'leri oluştur
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]

        # Metadata varsayılan
        if metadatas is None:
            metadatas = [{} for _ in documents]

        if self.collection:
            try:
                self.collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
            except Exception as e:
                console.print(f"[red]Ekleme hatası: {e}[/red]")
        else:
            # Memory store
            self._memory_store["documents"].extend(documents)
            self._memory_store["embeddings"].extend(embeddings)
            self._memory_store["metadatas"].extend(metadatas)
            self._memory_store["ids"].extend(ids)

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Dict = None,
        where_document: Dict = None
    ) -> Dict[str, Any]:
        """Benzer dökümanları sorgula."""
        if self.collection:
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=["documents", "metadatas", "distances"]
                )
                return {
                    "documents": results["documents"][0] if results["documents"] else [],
                    "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                    "distances": results["distances"][0] if results["distances"] else [],
                    "ids": results["ids"][0] if results["ids"] else []
                }
            except Exception as e:
                console.print(f"[red]Sorgu hatası: {e}[/red]")
                return {"documents": [], "metadatas": [], "distances": [], "ids": []}
        else:
            # Memory store - basit cosine similarity
            return self._memory_query(query_embedding, n_results)

    def _memory_query(
        self,
        query_embedding: List[float],
        n_results: int
    ) -> Dict[str, Any]:
        """Bellek içi sorgu."""
        if not self._memory_store["embeddings"]:
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}

        # Cosine similarity hesapla
        import math

        def cosine_similarity(v1, v2):
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            if norm1 == 0 or norm2 == 0:
                return 0
            return dot / (norm1 * norm2)

        similarities = []
        for i, emb in enumerate(self._memory_store["embeddings"]):
            sim = cosine_similarity(query_embedding, emb)
            similarities.append((i, sim))

        # En yüksek benzerlik
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, _ in similarities[:n_results]]

        return {
            "documents": [self._memory_store["documents"][i] for i in top_indices],
            "metadatas": [self._memory_store["metadatas"][i] for i in top_indices],
            "distances": [1 - similarities[i][1] for i in range(len(top_indices))],
            "ids": [self._memory_store["ids"][i] for i in top_indices]
        }

    def count(self) -> int:
        """Döküman sayısını döndür."""
        if self.collection:
            return self.collection.count()
        return len(self._memory_store["documents"])

    def delete_collection(self):
        """Collection'ı sil."""
        if self.client:
            try:
                self.client.delete_collection(self.collection_name)
                console.print(f"[yellow]Collection silindi: {self.collection_name}[/yellow]")
            except ValueError as e:
                # Collection bulunamadi
                console.print(f"[dim]Collection zaten yok: {self.collection_name}[/dim]")
            except Exception as e:
                console.print(f"[red]Collection silme hatasi: {e}[/red]")

    def reset(self):
        """Veritabanını sıfırla."""
        if self.client:
            try:
                self.client.reset()
            except Exception as e:
                console.print(f"[red]Veritabani reset hatasi: {e}[/red]")
        else:
            self._memory_store = {
                "documents": [],
                "embeddings": [],
                "metadatas": [],
                "ids": []
            }

    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri döndür."""
        return {
            "collection_name": self.collection_name,
            "document_count": self.count(),
            "persist_directory": self.persist_directory,
            "using_chromadb": self.collection is not None
        }
