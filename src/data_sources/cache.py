"""Veri Önbellek Modülü - API sonuçlarını cache'ler."""

import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console

# Logger setup
logger = logging.getLogger(__name__)
console = Console()


class DataCache:
    """Veri önbelleği - API yanıtlarını ve araştırma sonuçlarını cache'ler."""

    def __init__(
        self,
        cache_dir: str = None,
        default_ttl_hours: int = 24
    ):
        self.cache_dir = cache_dir or str(
            Path(__file__).parent.parent.parent / ".cache"
        )
        self.default_ttl = timedelta(hours=default_ttl_hours)

        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Cache dizini olusturulamadi: {self.cache_dir} - {e}")
            raise

    def _get_cache_key(self, key: str) -> str:
        """Cache anahtarı oluştur."""
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> str:
        """Cache dosya yolu."""
        cache_key = self._get_cache_key(key)
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def get(self, key: str) -> Optional[Any]:
        """Cache'den veri getir."""
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            # TTL kontrolü
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > self.default_ttl:
                # Cache süresi dolmuş
                try:
                    os.remove(cache_path)
                except OSError as e:
                    logger.warning(f"Suresi dolmus cache silinemedi: {cache_path} - {e}")
                return None

            return cached['data']

        except json.JSONDecodeError as e:
            logger.warning(f"Cache JSON parse hatasi: {cache_path} - {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.warning(f"Cache format hatasi: {cache_path} - {e}")
            return None
        except IOError as e:
            logger.error(f"Cache okuma IO hatasi: {cache_path} - {e}")
            return None

    def set(self, key: str, data: Any, ttl_hours: int = None) -> bool:
        """Cache'e veri kaydet."""
        cache_path = self._get_cache_path(key)

        try:
            cached = {
                'key': key,
                'timestamp': datetime.now().isoformat(),
                'ttl_hours': ttl_hours or self.default_ttl.total_seconds() / 3600,
                'data': data
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)

            return True

        except (TypeError, ValueError) as e:
            logger.error(f"Cache JSON serialize hatasi: {key} - {e}")
            return False
        except IOError as e:
            logger.error(f"Cache yazma IO hatasi: {cache_path} - {e}")
            return False
        except OSError as e:
            logger.error(f"Cache dosya hatasi: {cache_path} - {e}")
            return False

    def delete(self, key: str) -> bool:
        """Cache'den veri sil."""
        cache_path = self._get_cache_path(key)

        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except OSError as e:
                logger.warning(f"Cache silinemedi: {cache_path} - {e}")
                return False
        return False

    def clear(self) -> int:
        """Tüm cache'i temizle."""
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                        count += 1
                    except OSError as e:
                        logger.warning(f"Cache dosyasi silinemedi: {filename} - {e}")
        except OSError as e:
            logger.error(f"Cache dizini okunamadi: {self.cache_dir} - {e}")
        return count

    def clear_expired(self) -> int:
        """Süresi dolmuş cache'leri temizle."""
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue

                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cached = json.load(f)

                    cached_time = datetime.fromisoformat(cached['timestamp'])
                    ttl = timedelta(hours=cached.get('ttl_hours', 24))

                    if datetime.now() - cached_time > ttl:
                        os.remove(filepath)
                        count += 1

                except json.JSONDecodeError:
                    # Bozuk cache dosyasi, sil
                    try:
                        os.remove(filepath)
                        count += 1
                        logger.info(f"Bozuk cache dosyasi silindi: {filename}")
                    except OSError:
                        pass
                except (KeyError, ValueError) as e:
                    logger.debug(f"Cache format hatasi: {filename} - {e}")
                except IOError as e:
                    logger.debug(f"Cache okuma hatasi: {filename} - {e}")
        except OSError as e:
            logger.error(f"Cache dizini okunamadi: {self.cache_dir} - {e}")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Cache istatistiklerini getir."""
        total_files = 0
        total_size = 0
        expired_count = 0

        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue

                filepath = os.path.join(self.cache_dir, filename)
                total_files += 1

                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cached = json.load(f)

                    cached_time = datetime.fromisoformat(cached['timestamp'])
                    ttl = timedelta(hours=cached.get('ttl_hours', 24))

                    if datetime.now() - cached_time > ttl:
                        expired_count += 1
                except (json.JSONDecodeError, KeyError, ValueError, IOError):
                    # Istatistik icin hata onemli degil, atla
                    pass
        except OSError as e:
            logger.error(f"Cache dizini okunamadi: {self.cache_dir} - {e}")

        return {
            'cache_dir': self.cache_dir,
            'total_files': total_files,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'expired_count': expired_count,
            'default_ttl_hours': self.default_ttl.total_seconds() / 3600
        }

    def cache_research(self, topic: str, research_data: Dict) -> bool:
        """Araştırma sonucunu cache'le."""
        key = f"research:{topic}"
        return self.set(key, research_data, ttl_hours=48)  # 48 saat

    def get_cached_research(self, topic: str) -> Optional[Dict]:
        """Cache'lenmiş araştırma sonucunu getir."""
        key = f"research:{topic}"
        return self.get(key)

    def cache_web_search(self, query: str, results: Dict) -> bool:
        """Web arama sonucunu cache'le."""
        key = f"websearch:{query}"
        return self.set(key, results, ttl_hours=24)  # 24 saat

    def get_cached_web_search(self, query: str) -> Optional[Dict]:
        """Cache'lenmiş web arama sonucunu getir."""
        key = f"websearch:{query}"
        return self.get(key)
