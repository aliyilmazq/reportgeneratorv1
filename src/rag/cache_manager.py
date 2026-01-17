"""Cache Yonetim Modulu - Query, Embedding ve Result cache."""

import hashlib
import json
import time
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from rich.console import Console

console = Console()


@dataclass
class CacheEntry:
    """Cache girisi."""
    key: str
    value: Any
    created_at: float
    ttl_seconds: int
    hit_count: int = 0
    last_accessed: float = 0


@dataclass
class CacheStats:
    """Cache istatistikleri."""
    total_entries: int
    hit_count: int
    miss_count: int
    hit_rate: float
    memory_entries: int
    disk_entries: int


class QueryCache:
    """Sorgu sonuclari cache'i."""

    def __init__(
        self,
        cache_dir: str = None,
        ttl_hours: int = 24,
        max_entries: int = 1000
    ):
        if cache_dir is None:
            cache_dir = str(Path(__file__).parent.parent.parent / ".cache" / "query")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_hours * 3600
        self.max_entries = max_entries
        self._memory_cache: Dict[str, CacheEntry] = {}

        # Istatistikler
        self._hits = 0
        self._misses = 0

    def _hash_query(self, query: str, params: Dict = None) -> str:
        """Sorgu icin unique hash olustur."""
        data = json.dumps({
            "query": query.lower().strip(),
            "params": params or {}
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get(self, query: str, params: Dict = None) -> Optional[Any]:
        """Cache'den sonuc getir."""
        key = self._hash_query(query, params)

        # Memory cache kontrol
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry.created_at < entry.ttl_seconds:
                entry.hit_count += 1
                entry.last_accessed = time.time()
                self._hits += 1
                return entry.value
            else:
                # TTL gecmis, sil
                del self._memory_cache[key]

        # Disk cache kontrol
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry_data = json.load(f)
                    if time.time() - entry_data['created_at'] < entry_data['ttl_seconds']:
                        # Memory'ye de ekle
                        self._memory_cache[key] = CacheEntry(**entry_data)
                        self._hits += 1
                        return entry_data['value']
                    else:
                        # TTL gecmis, sil
                        cache_file.unlink()
            except (json.JSONDecodeError, IOError, KeyError) as e:
                # Cache dosyasi okuma/parse hatasi
                pass

        self._misses += 1
        return None

    def set(
        self,
        query: str,
        value: Any,
        params: Dict = None,
        ttl_hours: int = None
    ):
        """Cache'e kaydet."""
        key = self._hash_query(query, params)
        ttl = (ttl_hours * 3600) if ttl_hours else self.ttl

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl,
            last_accessed=time.time()
        )

        # Memory cache
        self._memory_cache[key] = entry

        # Disk cache
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(entry), f, ensure_ascii=False)
        except Exception as e:
            console.print(f"[yellow]Cache yazma hatasi: {e}[/yellow]")

        # Max entry kontrolu
        self._cleanup_if_needed()

    def invalidate(self, query: str, params: Dict = None):
        """Cache'i gecersiz kil."""
        key = self._hash_query(query, params)

        # Memory'den sil
        self._memory_cache.pop(key, None)

        # Disk'ten sil
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()

    def clear(self):
        """Tum cache'i temizle."""
        self._memory_cache.clear()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except (OSError, PermissionError) as e:
                # Dosya silme hatasi
                pass

        self._hits = 0
        self._misses = 0

    def _cleanup_if_needed(self):
        """Gerekirse eski entryleri temizle."""
        if len(self._memory_cache) > self.max_entries:
            # En eski %20'yi sil
            entries = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1].last_accessed
            )
            to_remove = entries[:len(entries) // 5]

            for key, _ in to_remove:
                del self._memory_cache[key]
                cache_file = self.cache_dir / f"{key}.json"
                if cache_file.exists():
                    cache_file.unlink()

    def get_stats(self) -> CacheStats:
        """Istatistikleri dondur."""
        disk_count = len(list(self.cache_dir.glob("*.json")))
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return CacheStats(
            total_entries=len(self._memory_cache),
            hit_count=self._hits,
            miss_count=self._misses,
            hit_rate=hit_rate,
            memory_entries=len(self._memory_cache),
            disk_entries=disk_count
        )


class EmbeddingCache:
    """Embedding sonuclari cache'i."""

    def __init__(
        self,
        cache_dir: str = None,
        ttl_days: int = 30,
        max_memory_entries: int = 5000
    ):
        if cache_dir is None:
            cache_dir = str(Path(__file__).parent.parent.parent / ".cache" / "embeddings")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_days * 86400
        self.max_memory_entries = max_memory_entries
        self._memory_cache: Dict[str, Dict] = {}

        # Istatistikler
        self._hits = 0
        self._misses = 0

    def _hash_text(self, text: str, model: str) -> str:
        """Text icin unique hash."""
        data = f"{model}:{text.strip()}"
        return hashlib.sha256(data.encode()).hexdigest()[:20]

    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Cache'den embedding getir."""
        key = self._hash_text(text, model)

        # Memory cache kontrol
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry['created_at'] < self.ttl:
                self._hits += 1
                return entry['embedding']
            else:
                del self._memory_cache[key]

        # Disk cache kontrol
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if time.time() - data['created_at'] < self.ttl:
                        embedding = data['embedding']
                        # Memory'ye de ekle
                        if len(self._memory_cache) < self.max_memory_entries:
                            self._memory_cache[key] = data
                        self._hits += 1
                        return embedding
                    else:
                        cache_file.unlink()
            except (json.JSONDecodeError, IOError, KeyError) as e:
                # Embedding cache okuma hatasi
                pass

        self._misses += 1
        return None

    def set(self, text: str, model: str, embedding: List[float]):
        """Embedding'i cache'le."""
        key = self._hash_text(text, model)

        data = {
            'created_at': time.time(),
            'model': model,
            'embedding': embedding,
            'text_hash': key
        }

        # Memory cache
        if len(self._memory_cache) < self.max_memory_entries:
            self._memory_cache[key] = data

        # Disk cache
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except (IOError, OSError, TypeError) as e:
            # Embedding cache yazma hatasi
            pass

    def get_batch(
        self,
        texts: List[str],
        model: str
    ) -> Dict[str, Optional[List[float]]]:
        """Batch halinde embedding getir."""
        results = {}
        for text in texts:
            results[text] = self.get(text, model)
        return results

    def set_batch(
        self,
        texts: List[str],
        model: str,
        embeddings: List[List[float]]
    ):
        """Batch halinde embedding kaydet."""
        for text, embedding in zip(texts, embeddings):
            self.set(text, model, embedding)

    def clear(self):
        """Cache'i temizle."""
        self._memory_cache.clear()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except (OSError, PermissionError) as e:
                # Embedding cache silme hatasi
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Istatistikleri dondur."""
        disk_count = len(list(self.cache_dir.glob("*.json")))
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": disk_count,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate
        }


class ResultCache:
    """RAG sonuc cache'i (TTL ile)."""

    def __init__(
        self,
        ttl_minutes: int = 60,
        max_entries: int = 500,
        use_redis: bool = False,
        redis_host: str = "localhost",
        redis_port: int = 6379
    ):
        self.ttl = ttl_minutes * 60
        self.max_entries = max_entries
        self.use_redis = use_redis
        self.redis_client = None

        if use_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=0,
                    decode_responses=True
                )
                self.redis_client.ping()
                console.print("[green]Redis cache aktif[/green]")
            except Exception as e:
                console.print(f"[yellow]Redis baglanti hatasi: {e}, memory cache kullanilacak[/yellow]")
                self.use_redis = False
                self.redis_client = None

        if not self.use_redis:
            self._memory_cache: Dict[str, Dict] = {}

        # Istatistikler
        self._hits = 0
        self._misses = 0

    def _make_key(self, cache_key: str) -> str:
        """Redis key olustur."""
        return f"rag:result:{cache_key}"

    def get(self, cache_key: str) -> Optional[Any]:
        """Sonuc getir."""
        if self.use_redis and self.redis_client:
            try:
                key = self._make_key(cache_key)
                data = self.redis_client.get(key)
                if data:
                    self._hits += 1
                    return json.loads(data)
            except (json.JSONDecodeError, ConnectionError) as e:
                # Redis okuma hatasi
                pass
            self._misses += 1
            return None

        # Memory cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if time.time() - entry['created_at'] < self.ttl:
                self._hits += 1
                return entry['value']
            else:
                del self._memory_cache[cache_key]

        self._misses += 1
        return None

    def set(self, cache_key: str, value: Any, ttl_minutes: int = None):
        """Sonuc kaydet."""
        ttl = (ttl_minutes * 60) if ttl_minutes else self.ttl

        if self.use_redis and self.redis_client:
            try:
                key = self._make_key(cache_key)
                self.redis_client.setex(
                    key,
                    int(ttl),
                    json.dumps(value, ensure_ascii=False, default=str)
                )
                return
            except (json.JSONDecodeError, ConnectionError, TypeError) as e:
                # Redis yazma hatasi
                pass

        # Memory cache
        self._memory_cache[cache_key] = {
            'value': value,
            'created_at': time.time()
        }

        # Max entry kontrolu
        if len(self._memory_cache) > self.max_entries:
            # En eski %20'yi sil
            entries = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1]['created_at']
            )
            to_remove = entries[:len(entries) // 5]
            for key, _ in to_remove:
                del self._memory_cache[key]

    def invalidate(self, cache_key: str):
        """Cache'i gecersiz kil."""
        if self.use_redis and self.redis_client:
            try:
                key = self._make_key(cache_key)
                self.redis_client.delete(key)
                return
            except ConnectionError as e:
                # Redis silme hatasi
                pass

        self._memory_cache.pop(cache_key, None)

    def clear(self):
        """Tum cache'i temizle."""
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys("rag:result:*")
                if keys:
                    self.redis_client.delete(*keys)
            except ConnectionError as e:
                # Redis temizleme hatasi
                pass
        else:
            self._memory_cache.clear()

        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Istatistikleri dondur."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        entry_count = 0
        if self.use_redis and self.redis_client:
            try:
                entry_count = len(self.redis_client.keys("rag:result:*"))
            except ConnectionError as e:
                # Redis istatistik hatasi
                pass
        else:
            entry_count = len(self._memory_cache)

        return {
            "backend": "redis" if self.use_redis else "memory",
            "entries": entry_count,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl
        }


class CacheManager:
    """Tum cache'leri yoneten sinif."""

    def __init__(
        self,
        base_dir: str = None,
        query_ttl_hours: int = 24,
        embedding_ttl_days: int = 30,
        result_ttl_minutes: int = 60,
        use_redis: bool = False
    ):
        if base_dir is None:
            base_dir = str(Path(__file__).parent.parent.parent / ".cache")

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.query_cache = QueryCache(
            cache_dir=str(self.base_dir / "query"),
            ttl_hours=query_ttl_hours
        )

        self.embedding_cache = EmbeddingCache(
            cache_dir=str(self.base_dir / "embeddings"),
            ttl_days=embedding_ttl_days
        )

        self.result_cache = ResultCache(
            ttl_minutes=result_ttl_minutes,
            use_redis=use_redis
        )

    def clear_all(self):
        """Tum cache'leri temizle."""
        self.query_cache.clear()
        self.embedding_cache.clear()
        self.result_cache.clear()
        console.print("[yellow]Tum cache'ler temizlendi[/yellow]")

    def get_all_stats(self) -> Dict[str, Any]:
        """Tum istatistikleri dondur."""
        return {
            "query_cache": self.query_cache.get_stats(),
            "embedding_cache": self.embedding_cache.get_stats(),
            "result_cache": self.result_cache.get_stats()
        }

    def print_stats(self):
        """Istatistikleri yazdir."""
        stats = self.get_all_stats()

        console.print("\n[bold]Cache Istatistikleri[/bold]")
        console.print("-" * 40)

        for cache_name, cache_stats in stats.items():
            console.print(f"\n[cyan]{cache_name}:[/cyan]")
            if isinstance(cache_stats, dict):
                for key, value in cache_stats.items():
                    if isinstance(value, float):
                        console.print(f"  {key}: {value:.2%}")
                    else:
                        console.print(f"  {key}: {value}")
            else:
                console.print(f"  entries: {cache_stats.total_entries}")
                console.print(f"  hit_rate: {cache_stats.hit_rate:.2%}")
