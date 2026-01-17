"""
RAG Konfigurasyon Yukleyici - rag_config.yaml dosyasini yukler ve yonetir.

Ozellikler:
- YAML konfigurasyon yuklemesi
- Varsayilan degerler
- Ortam degiskeni destegi
- Tip dogrulama
- Konfigurasyon birlestirme
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field, asdict
from copy import deepcopy

from ..utils.logger import get_rag_logger

logger = get_rag_logger("config_loader")


@dataclass
class EmbeddingConfig:
    """Embedding konfigurasyonu."""
    model: str = "intfloat/multilingual-e5-large"
    dimension: int = 1024
    batch_size: int = 32
    max_length: int = 512
    normalize: bool = True
    device: str = "auto"
    use_fp16: bool = False
    cache_embeddings: bool = True
    fallback_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    fallback_dimension: int = 384


@dataclass
class ChunkingConfig:
    """Chunking konfigurasyonu."""
    strategy: str = "semantic"
    chunk_size: int = 1200
    chunk_overlap: int = 240
    min_chunk_size: int = 200
    max_chunk_size: int = 2000
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True
    preserve_tables: bool = True
    preserve_lists: bool = True
    preserve_code_blocks: bool = True
    use_hierarchical: bool = True
    parent_chunk_size: int = 2000
    child_chunk_size: int = 500


@dataclass
class HybridSearchConfig:
    """Hybrid Search konfigurasyonu."""
    enabled: bool = True
    semantic_weight: float = 0.6
    bm25_weight: float = 0.4
    use_rrf: bool = True
    rrf_k: int = 60
    initial_fetch: int = 30
    final_top_k: int = 5
    min_score: float = 0.3


@dataclass
class RerankingConfig:
    """Re-ranking konfigurasyonu."""
    enabled: bool = True
    model_type: str = "multilingual"
    custom_model: Optional[str] = None
    top_k_to_rerank: int = 20
    min_score: float = 0.3
    batch_size: int = 32


@dataclass
class MMRConfig:
    """MMR konfigurasyonu."""
    enabled: bool = True
    lambda_param: float = 0.7
    diversity_threshold: float = 0.85


@dataclass
class QueryOptimizationConfig:
    """Query Optimization konfigurasyonu."""
    strategy: str = "auto"
    hyde_enabled: bool = True
    hyde_max_length: int = 150
    multi_query_count: int = 3


@dataclass
class ContextConfig:
    """Context Management konfigurasyonu."""
    max_tokens: int = 15000
    reserved_for_response: int = 4000
    safety_margin: float = 0.1
    compression_enabled: bool = True
    target_compression_ratio: float = 0.5
    format_style: str = "numbered"
    include_metadata: bool = True


@dataclass
class CachingConfig:
    """Cache konfigurasyonu."""
    enabled: bool = True
    query_cache_ttl_hours: int = 24
    query_cache_max_entries: int = 1000
    embedding_cache_ttl_days: int = 30
    embedding_cache_max_entries: int = 5000
    result_cache_ttl_minutes: int = 60
    result_cache_max_entries: int = 500
    use_redis: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379


@dataclass
class SourceAttributionConfig:
    """Source Attribution konfigurasyonu."""
    enabled: bool = True
    citation_style: str = "numeric"
    min_confidence_score: float = 0.4
    insert_inline_citations: bool = True


@dataclass
class VectorStoreConfig:
    """Vector Store konfigurasyonu."""
    persist_directory: str = ".chromadb"
    collection_name: str = "report_docs"
    parent_collection_name: str = "report_docs_parents"
    distance_metric: str = "cosine"
    hnsw_space: str = "cosine"
    hnsw_ef_construction: int = 200
    hnsw_m: int = 16


@dataclass
class BM25Config:
    """BM25 konfigurasyonu."""
    k1: float = 1.5
    b: float = 0.75
    use_stemming: bool = True
    remove_stopwords: bool = True
    min_token_length: int = 2


@dataclass
class PerformanceConfig:
    """Performans konfigurasyonu."""
    max_workers: int = 4
    batch_processing: bool = True
    embedding_timeout: int = 60
    search_timeout: int = 30
    rerank_timeout: int = 30


@dataclass
class LoggingConfig:
    """Logging konfigurasyonu."""
    level: str = "INFO"
    log_queries: bool = False
    log_results: bool = False
    log_cache_stats: bool = True


@dataclass
class RAGConfig:
    """Ana RAG konfigurasyonu."""
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    hybrid_search: HybridSearchConfig = field(default_factory=HybridSearchConfig)
    reranking: RerankingConfig = field(default_factory=RerankingConfig)
    mmr: MMRConfig = field(default_factory=MMRConfig)
    query_optimization: QueryOptimizationConfig = field(default_factory=QueryOptimizationConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    caching: CachingConfig = field(default_factory=CachingConfig)
    source_attribution: SourceAttributionConfig = field(default_factory=SourceAttributionConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    bm25: BM25Config = field(default_factory=BM25Config)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


class ConfigLoader:
    """
    RAG konfigurasyon yukleyici.

    Kullanim:
        loader = ConfigLoader("config/rag_config.yaml")
        config = loader.load()

        # veya
        config = ConfigLoader.load_default()
    """

    DEFAULT_CONFIG_PATHS = [
        "config/rag_config.yaml",
        "rag_config.yaml",
        "../config/rag_config.yaml",
    ]

    @staticmethod
    def _get_project_root() -> Path:
        """Proje root dizinini bul."""
        # Bu dosyanin konumu: src/rag/config_loader.py
        current_file = Path(__file__).resolve()
        # src/rag/ -> src/ -> project_root/
        return current_file.parent.parent.parent

    _instance: Optional['ConfigLoader'] = None
    _config: Optional[RAGConfig] = None

    def __init__(self, config_path: Optional[str] = None):
        """
        ConfigLoader olustur.

        Args:
            config_path: Konfigurasyon dosyasi yolu (opsiyonel)
        """
        self.config_path = config_path
        self._raw_config: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> 'ConfigLoader':
        """Singleton instance al."""
        if cls._instance is None:
            cls._instance = ConfigLoader(config_path)
        return cls._instance

    @classmethod
    def load_default(cls) -> RAGConfig:
        """Varsayilan konfigurasyonu yukle."""
        loader = cls.get_instance()
        return loader.load()

    @classmethod
    def get_config(cls) -> RAGConfig:
        """Mevcut konfigurasyonu al."""
        if cls._config is None:
            cls._config = cls.load_default()
        return cls._config

    def load(self) -> RAGConfig:
        """
        Konfigurasyonu yukle.

        Returns:
            RAGConfig: Yuklenen konfigurasyon
        """
        # Konfigurasyon dosyasini bul
        config_file = self._find_config_file()

        if config_file:
            logger.info(f"Konfigurasyon yukleniyor: {config_file}")
            self._raw_config = self._load_yaml(config_file)
        else:
            logger.warning("Konfigurasyon dosyasi bulunamadi, varsayilanlar kullaniliyor")
            self._raw_config = {}

        # Ortam degiskenlerini uygula
        self._apply_env_overrides()

        # Konfigurasyon nesnesini olustur
        config = self._build_config()

        # Singleton'a kaydet
        ConfigLoader._config = config

        return config

    def _find_config_file(self) -> Optional[Path]:
        """Konfigurasyon dosyasini bul."""
        project_root = self._get_project_root()

        # Belirtilmis yol varsa
        if self.config_path:
            # Once mutlak yol olarak dene
            path = Path(self.config_path)
            if path.exists():
                return path

            # Proje root'una gore dene
            path = project_root / self.config_path
            if path.exists():
                return path

            logger.warning(f"Belirtilen konfigurasyon dosyasi bulunamadi: {self.config_path}")

        # Varsayilan yollari dene - proje root'undan
        for default_path in self.DEFAULT_CONFIG_PATHS:
            # Proje root'una gore
            path = project_root / default_path
            if path.exists():
                return path

            # Mevcut dizine gore (fallback)
            path = Path(default_path)
            if path.exists():
                return path

        return None

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """YAML dosyasini yukle."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"YAML yuklemede hata: {e}")
            return {}

    def _apply_env_overrides(self):
        """Ortam degiskenlerinden override'lari uygula."""
        env_mappings = {
            "RAG_EMBEDDING_MODEL": ("embedding", "model"),
            "RAG_EMBEDDING_DEVICE": ("embedding", "device"),
            "RAG_CHUNK_SIZE": ("chunking", "chunk_size"),
            "RAG_CHUNK_STRATEGY": ("chunking", "strategy"),
            "RAG_HYBRID_SEARCH_ENABLED": ("hybrid_search", "enabled"),
            "RAG_SEMANTIC_WEIGHT": ("hybrid_search", "semantic_weight"),
            "RAG_BM25_WEIGHT": ("hybrid_search", "bm25_weight"),
            "RAG_RERANKING_ENABLED": ("reranking", "enabled"),
            "RAG_MAX_TOKENS": ("context", "max_tokens"),
            "RAG_CACHE_ENABLED": ("caching", "enabled"),
            "RAG_REDIS_HOST": ("caching", "redis_host"),
            "RAG_REDIS_PORT": ("caching", "redis_port"),
            "RAG_LOG_LEVEL": ("logging", "level"),
            "RAG_CHROMADB_DIR": ("vector_store", "persist_directory"),
        }

        for env_var, (section, key) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Section yoksa olustur
                if section not in self._raw_config:
                    self._raw_config[section] = {}

                # Tip donusumu
                converted = self._convert_env_value(value, section, key)
                self._raw_config[section][key] = converted
                logger.debug(f"Ortam degiskeni uygulandi: {env_var}={converted}")

    def _convert_env_value(self, value: str, section: str, key: str) -> Any:
        """Ortam degiskeni degerini uygun tipe donustur."""
        # Boolean
        if value.lower() in ("true", "false", "1", "0", "yes", "no"):
            return value.lower() in ("true", "1", "yes")

        # Integer
        try:
            if "." not in value:
                return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # String
        return value

    def _build_config(self) -> RAGConfig:
        """Konfigurasyon nesnesini olustur."""
        raw = self._raw_config

        return RAGConfig(
            embedding=self._build_section(EmbeddingConfig, raw.get("embedding", {})),
            chunking=self._build_section(ChunkingConfig, raw.get("chunking", {})),
            hybrid_search=self._build_section(HybridSearchConfig, raw.get("hybrid_search", {})),
            reranking=self._build_section(RerankingConfig, raw.get("reranking", {})),
            mmr=self._build_section(MMRConfig, raw.get("mmr", {})),
            query_optimization=self._build_section(QueryOptimizationConfig, raw.get("query_optimization", {})),
            context=self._build_section(ContextConfig, raw.get("context", {})),
            caching=self._build_section(CachingConfig, raw.get("caching", {})),
            source_attribution=self._build_section(SourceAttributionConfig, raw.get("source_attribution", {})),
            vector_store=self._build_section(VectorStoreConfig, raw.get("vector_store", {})),
            bm25=self._build_section(BM25Config, raw.get("bm25", {})),
            performance=self._build_section(PerformanceConfig, raw.get("performance", {})),
            logging=self._build_section(LoggingConfig, raw.get("logging", {})),
        )

    def _build_section(self, config_class: type, raw_data: Dict[str, Any]):
        """Konfigurasyon section'i olustur."""
        # Varsayilan degerleri al
        defaults = config_class()

        # Raw data'dan gecerli field'lari al
        valid_fields = {f.name for f in config_class.__dataclass_fields__.values()}

        kwargs = {}
        for key, value in raw_data.items():
            # YAML'daki 'lambda' -> 'lambda_param' donusumu (MMR icin)
            if key == "lambda" and config_class == MMRConfig:
                key = "lambda_param"

            if key in valid_fields:
                kwargs[key] = value

        # Varsayilanlarla birlestir
        for field_name in valid_fields:
            if field_name not in kwargs:
                kwargs[field_name] = getattr(defaults, field_name)

        return config_class(**kwargs)

    def get_raw_config(self) -> Dict[str, Any]:
        """Ham konfigurasyonu getir."""
        return deepcopy(self._raw_config)

    def to_dict(self) -> Dict[str, Any]:
        """Konfigurasyonu dict olarak getir."""
        if ConfigLoader._config is None:
            self.load()
        return asdict(ConfigLoader._config)

    def reload(self) -> RAGConfig:
        """Konfigurasyonu yeniden yukle."""
        ConfigLoader._config = None
        return self.load()


def load_rag_config(config_path: Optional[str] = None) -> RAGConfig:
    """
    RAG konfigurasyonunu yukle (kisa yol).

    Args:
        config_path: Opsiyonel konfigurasyon dosyasi yolu

    Returns:
        RAGConfig: Yuklenen konfigurasyon
    """
    loader = ConfigLoader(config_path)
    return loader.load()


def get_rag_config() -> RAGConfig:
    """Mevcut RAG konfigurasyonunu al (singleton)."""
    return ConfigLoader.get_config()
