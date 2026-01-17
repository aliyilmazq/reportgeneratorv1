"""RAG (Retrieval Augmented Generation) modulleri - v5.0."""

# Temel moduller (mevcut)
from .embedder import DocumentEmbedder, DocumentChunker
from .vector_store import VectorStore
from .retriever import DocumentRetriever, RetrievedDocument, RAGContext

# Gelismis Embedding
from .advanced_embedder import (
    AdvancedEmbedder,
    EmbeddingConfig,
    EmbeddingResult,
    AsyncBatchProcessor,
    create_embedder,
    SUPPORTED_MODELS
)

# Gelismis Chunking
from .advanced_chunker import (
    SemanticChunker,
    RecursiveTextSplitter,
    ParentDocumentChunker,
    ChunkConfig,
    DocumentChunk,
    create_chunker
)

# Hybrid Search
from .bm25_index import BM25Index, BM25Result, TurkishTokenizer
from .hybrid_retriever import HybridRetriever, HybridSearchConfig, HybridResult
from .reranker import CrossEncoderReranker, MMRReranker, RerankResult, create_reranker

# Query Optimization
from .query_optimizer import (
    QueryOptimizer,
    HyDEGenerator,
    MultiQueryGenerator,
    QueryDecomposer,
    KeywordExpander,
    SectionQueryBuilder,
    OptimizedQuery
)

# Context Management
from .token_manager import (
    TokenManager,
    DynamicContextManager,
    ContextOptimizer,
    TokenBudget,
    ContextWindow
)
from .context_compressor import (
    ContextCompressor,
    LLMBasedCompressor,
    ChunkRanker,
    CompressedChunk
)

# Source Attribution
from .source_attribution import (
    SourceAttributor,
    CitationInserter,
    SourceValidator,
    AttributedSource,
    InlineCitation
)

# Cache
from .cache_manager import (
    CacheManager,
    QueryCache,
    EmbeddingCache,
    ResultCache,
    CacheStats
)

# Validators
from .validators import (
    validate_query,
    validate_document,
    validate_documents,
    validate_top_k,
    validate_chunk_size,
    validate_score,
    contains_injection,
    sanitize_prompt,
    sanitize_html,
    truncate_safe,
    validate_inputs,
    validate_config,
    ValidationResult
)

# Exceptions
from .exceptions import (
    RAGException,
    EmbeddingException,
    ModelLoadError,
    EmbeddingTimeoutError,
    RetrievalException,
    IndexNotFoundError,
    EmptyQueryError,
    NoResultsError,
    DocumentException,
    DocumentParseError,
    ChunkingError,
    EmptyDocumentError,
    ConfigurationException,
    ConfigFileNotFoundError,
    InvalidConfigError,
    CacheException,
    CacheConnectionError,
    LLMException,
    LLMRateLimitError,
    LLMContextLengthError,
    ValidationException,
    InputValidationError,
    handle_rag_errors,
    safe_execute,
    ErrorContext
)

# Shared Utilities
from .utils import (
    jaccard_similarity,
    keyword_overlap_score,
    combined_relevance_score,
    split_sentences,
    clean_text,
    tokenize_turkish,
    remove_stop_words,
    simple_stem_turkish,
    normalize_score,
    weighted_average,
    batch_items,
    deduplicate_by_key,
    TURKISH_STOP_WORDS
)

# Document Processing
from .document_processor import (
    DocumentProcessor,
    ProcessedDocument,
    TurkishKeywordExtractor,
    CategoryDetector,
    SimpleNER,
    process_document
)

# Configuration
from .config_loader import (
    ConfigLoader,
    RAGConfig,
    EmbeddingConfig as EmbeddingConfigFull,
    ChunkingConfig,
    HybridSearchConfig as HybridSearchConfigFull,
    RerankingConfig,
    MMRConfig,
    QueryOptimizationConfig,
    ContextConfig,
    CachingConfig,
    SourceAttributionConfig,
    VectorStoreConfig,
    BM25Config,
    PerformanceConfig,
    LoggingConfig,
    load_rag_config,
    get_rag_config
)

__all__ = [
    # Temel
    'DocumentEmbedder',
    'DocumentChunker',
    'VectorStore',
    'DocumentRetriever',
    'RetrievedDocument',
    'RAGContext',

    # Gelismis Embedding
    'AdvancedEmbedder',
    'EmbeddingConfig',
    'EmbeddingResult',
    'AsyncBatchProcessor',
    'create_embedder',
    'SUPPORTED_MODELS',

    # Gelismis Chunking
    'SemanticChunker',
    'RecursiveTextSplitter',
    'ParentDocumentChunker',
    'ChunkConfig',
    'DocumentChunk',
    'create_chunker',

    # Hybrid Search
    'BM25Index',
    'BM25Result',
    'TurkishTokenizer',
    'HybridRetriever',
    'HybridSearchConfig',
    'HybridResult',
    'CrossEncoderReranker',
    'MMRReranker',
    'RerankResult',
    'create_reranker',

    # Query Optimization
    'QueryOptimizer',
    'HyDEGenerator',
    'MultiQueryGenerator',
    'QueryDecomposer',
    'KeywordExpander',
    'SectionQueryBuilder',
    'OptimizedQuery',

    # Context Management
    'TokenManager',
    'DynamicContextManager',
    'ContextOptimizer',
    'TokenBudget',
    'ContextWindow',
    'ContextCompressor',
    'LLMBasedCompressor',
    'ChunkRanker',
    'CompressedChunk',

    # Source Attribution
    'SourceAttributor',
    'CitationInserter',
    'SourceValidator',
    'AttributedSource',
    'InlineCitation',

    # Cache
    'CacheManager',
    'QueryCache',
    'EmbeddingCache',
    'ResultCache',
    'CacheStats',

    # Document Processing
    'DocumentProcessor',
    'ProcessedDocument',
    'TurkishKeywordExtractor',
    'CategoryDetector',
    'SimpleNER',
    'process_document',

    # Configuration
    'ConfigLoader',
    'RAGConfig',
    'EmbeddingConfigFull',
    'ChunkingConfig',
    'HybridSearchConfigFull',
    'RerankingConfig',
    'MMRConfig',
    'QueryOptimizationConfig',
    'ContextConfig',
    'CachingConfig',
    'SourceAttributionConfig',
    'VectorStoreConfig',
    'BM25Config',
    'PerformanceConfig',
    'LoggingConfig',
    'load_rag_config',
    'get_rag_config',
]

__version__ = "5.0.0"
