"""RAG bilesenleri icin unit testler."""

import pytest
from typing import List, Dict


class TestTurkishKeywordExtractor:
    """TurkishKeywordExtractor testleri."""

    def test_extract_keywords_basic(self, sample_turkish_text):
        """Temel keyword cikarimi testi."""
        from src.rag.document_processor import TurkishKeywordExtractor

        extractor = TurkishKeywordExtractor(max_keywords=10)
        keywords = extractor.extract_keywords(sample_turkish_text)

        assert len(keywords) > 0
        assert len(keywords) <= 10
        assert all(isinstance(kw, tuple) for kw in keywords)
        assert all(len(kw) == 2 for kw in keywords)

    def test_extract_keywords_empty_text(self):
        """Bos metin testi."""
        from src.rag.document_processor import TurkishKeywordExtractor

        extractor = TurkishKeywordExtractor()
        keywords = extractor.extract_keywords("")

        assert keywords == []

    def test_stop_words_filtered(self, sample_turkish_text):
        """Stop word filtreleme testi."""
        from src.rag.document_processor import TurkishKeywordExtractor, TURKISH_STOP_WORDS

        extractor = TurkishKeywordExtractor()
        keywords = extractor.extract_keywords(sample_turkish_text)

        keyword_words = [kw for kw, _ in keywords]
        for stop_word in ["ve", "bir", "için", "ile"]:
            assert stop_word not in keyword_words


class TestCategoryDetector:
    """CategoryDetector testleri."""

    def test_detect_finansal_category(self):
        """Finansal kategori tespiti."""
        from src.rag.document_processor import CategoryDetector

        detector = CategoryDetector()
        text = "Şirketin geliri 10 milyon TL, gideri 5 milyon TL, kar marjı %50."

        category, confidence = detector.detect_category(text)

        assert category == "finansal"
        assert confidence > 0

    def test_detect_pazar_analizi_category(self):
        """Pazar analizi kategori tespiti."""
        from src.rag.document_processor import CategoryDetector

        detector = CategoryDetector()
        text = "Pazar büyüklüğü 100 milyar TL. Rekabet analizi sonuçları. Hedef kitle segmentasyonu."

        category, confidence = detector.detect_category(text)

        assert category == "pazar_analizi"
        assert confidence > 0

    def test_detect_empty_returns_genel(self):
        """Bos metin genel kategori dondurur."""
        from src.rag.document_processor import CategoryDetector

        detector = CategoryDetector()
        category, confidence = detector.detect_category("")

        assert category == "genel"
        assert confidence == 0.5


class TestSimpleNER:
    """SimpleNER testleri."""

    def test_extract_money_entities(self):
        """Para entity cikarimi."""
        from src.rag.document_processor import SimpleNER

        ner = SimpleNER()
        text = "Yatırım tutarı 5 milyon TL ve $100,000 dolar."

        entities = ner.extract_entities(text)

        assert "money" in entities
        assert len(entities["money"]) > 0

    def test_extract_percentage_entities(self):
        """Yuzde entity cikarimi."""
        from src.rag.document_processor import SimpleNER

        ner = SimpleNER()
        text = "Büyüme oranı %25 ve kar marjı 15% olarak belirlendi."

        entities = ner.extract_entities(text)

        assert "percentage" in entities
        assert len(entities["percentage"]) > 0

    def test_extract_date_entities(self):
        """Tarih entity cikarimi."""
        from src.rag.document_processor import SimpleNER

        ner = SimpleNER()
        text = "Proje 01.01.2024 tarihinde başlayacak. Ocak 2024 döneminde tamamlanacak."

        entities = ner.extract_entities(text)

        assert "date" in entities


class TestDocumentProcessor:
    """DocumentProcessor testleri."""

    def test_process_document_basic(self, sample_turkish_text):
        """Temel dokuman isleme testi."""
        from src.rag.document_processor import DocumentProcessor

        processor = DocumentProcessor(generate_summary=False)
        result = processor.process(sample_turkish_text)

        assert result.id is not None
        assert result.cleaned_text is not None
        assert result.keywords is not None
        assert result.category is not None
        assert result.word_count > 0

    def test_process_document_with_id(self, sample_turkish_text):
        """Belirtilen ID ile dokuman isleme."""
        from src.rag.document_processor import DocumentProcessor

        processor = DocumentProcessor(generate_summary=False)
        result = processor.process(sample_turkish_text, doc_id="test_doc_1")

        assert result.id == "test_doc_1"

    def test_process_batch(self, sample_documents):
        """Toplu dokuman isleme."""
        from src.rag.document_processor import DocumentProcessor

        processor = DocumentProcessor(generate_summary=False)
        texts = [doc["text"] for doc in sample_documents]
        results = processor.process_batch(texts)

        assert len(results) == len(sample_documents)
        assert all(r.id is not None for r in results)

    def test_language_detection_turkish(self, sample_turkish_text):
        """Turkce dil tespiti."""
        from src.rag.document_processor import DocumentProcessor

        processor = DocumentProcessor(generate_summary=False)
        result = processor.process(sample_turkish_text)

        assert result.language == "tr"

    def test_language_detection_english(self, sample_english_text):
        """Ingilizce dil tespiti."""
        from src.rag.document_processor import DocumentProcessor

        processor = DocumentProcessor(generate_summary=False)
        result = processor.process(sample_english_text)

        assert result.language == "en"


class TestContextCompressor:
    """ContextCompressor testleri."""

    def test_compress_for_query(self, sample_chunks):
        """Sorgu icin sikistirma testi."""
        from src.rag.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        result = compressor.compress_for_query(
            documents=sample_chunks,
            query="pazar büyüklüğü"
        )

        assert len(result) > 0
        assert all(hasattr(r, 'compressed_text') for r in result)

    def test_extract_relevant_sentences(self, sample_turkish_text):
        """Ilgili cumle cikarimi testi."""
        from src.rag.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        sentences = compressor.extract_relevant_sentences(
            document=sample_turkish_text,
            query="büyüme hedefi",
            min_relevance=0.1
        )

        assert len(sentences) > 0


class TestChunkRanker:
    """ChunkRanker testleri."""

    def test_rank_chunks(self, sample_chunks):
        """Chunk siralama testi."""
        from src.rag.context_compressor import ChunkRanker

        ranker = ChunkRanker()
        ranked = ranker.rank_chunks(
            chunks=sample_chunks,
            query="pazar",
            top_k=3
        )

        assert len(ranked) <= 3
        assert all("combined_score" in c for c in ranked)

    def test_deduplicate(self, sample_chunks):
        """Deduplicate testi."""
        from src.rag.context_compressor import ChunkRanker

        # Ayni chunk'i iki kere ekle
        duplicated = sample_chunks + [sample_chunks[0]]

        ranker = ChunkRanker()
        unique = ranker.deduplicate(duplicated)

        assert len(unique) <= len(duplicated)

    def test_filter_by_relevance(self, sample_chunks):
        """Relevance filtreleme testi."""
        from src.rag.context_compressor import ChunkRanker

        ranker = ChunkRanker()
        filtered = ranker.filter_by_relevance(sample_chunks, min_score=0.7)

        assert all(c["score"] >= 0.7 for c in filtered)


class TestSourceAttributor:
    """SourceAttributor testleri."""

    def test_add_source(self):
        """Kaynak ekleme testi."""
        from src.rag.source_attribution import SourceAttributor

        attributor = SourceAttributor()
        source = attributor.add_source(
            text="Test icerik",
            source_type="file",
            file_name="test.pdf",
            relevance_score=0.8
        )

        assert source.id is not None
        assert source.confidence_score > 0

    def test_credibility_score_gov(self):
        """Gov domain guvenilirlik skoru."""
        from src.rag.source_attribution import SourceAttributor

        attributor = SourceAttributor()
        source = attributor.add_source(
            text="TCMB raporu",
            source_type="web",
            url="https://www.tcmb.gov.tr/rapor"
        )

        assert source.credibility_score >= 0.9

    def test_format_citations(self):
        """Citation formatlama testi."""
        from src.rag.source_attribution import SourceAttributor

        attributor = SourceAttributor()
        attributor.add_source(text="Source 1", source_type="file", file_name="doc1.pdf")
        attributor.add_source(text="Source 2", source_type="file", file_name="doc2.pdf")

        citations = attributor.format_citations(style="numeric")

        assert len(citations) == 2
        assert "[1]" in citations.values()
        assert "[2]" in citations.values()

    def test_generate_bibliography(self):
        """Kaynakca olusturma testi."""
        from src.rag.source_attribution import SourceAttributor

        attributor = SourceAttributor()
        attributor.add_source(text="Source 1", source_type="file", file_name="doc1.pdf")

        bibliography = attributor.generate_bibliography()

        assert "Kaynaklar" in bibliography
        assert "doc1.pdf" in bibliography


class TestTokenManager:
    """TokenManager testleri."""

    def test_count_tokens(self, sample_turkish_text):
        """Token sayma testi."""
        from src.rag.token_manager import TokenManager

        manager = TokenManager()
        count = manager.count_tokens(sample_turkish_text)

        assert count > 0
        assert isinstance(count, int)

    def test_truncate_to_limit(self, sample_turkish_text):
        """Token limit truncate testi."""
        from src.rag.token_manager import TokenManager

        manager = TokenManager()
        truncated = manager.truncate_to_tokens(sample_turkish_text, max_tokens=50)

        assert manager.count_tokens(truncated) <= 50


class TestDynamicContextManager:
    """DynamicContextManager testleri."""

    def test_build_context(self, sample_chunks):
        """Context olusturma testi."""
        from src.rag.token_manager import TokenManager, DynamicContextManager

        token_manager = TokenManager()
        context_manager = DynamicContextManager(token_manager)

        context = context_manager.build_context(
            documents=sample_chunks,
            max_tokens=1000
        )

        assert context is not None
        assert len(context.documents) > 0

    def test_format_context(self, sample_chunks):
        """Context formatlama testi."""
        from src.rag.token_manager import TokenManager, DynamicContextManager

        token_manager = TokenManager()
        context_manager = DynamicContextManager(token_manager)

        context = context_manager.build_context(documents=sample_chunks, max_tokens=1000)
        formatted = context_manager.format_context(context, format_style="numbered")

        assert "[1]" in formatted


class TestConfigLoader:
    """ConfigLoader testleri."""

    def test_load_default_config(self):
        """Varsayilan konfigurasyon yukleme."""
        from src.rag.config_loader import ConfigLoader, RAGConfig

        loader = ConfigLoader()
        config = loader.load()

        assert isinstance(config, RAGConfig)
        assert config.embedding.dimension > 0

    def test_config_from_file(self, temp_config_file):
        """Dosyadan konfigurasyon yukleme."""
        from src.rag.config_loader import ConfigLoader

        loader = ConfigLoader(str(temp_config_file))
        config = loader.load()

        assert config.embedding.dimension == 384
        assert config.chunking.chunk_size == 500


class TestQueryOptimizer:
    """QueryOptimizer testleri."""

    def test_optimize_basic(self):
        """Temel sorgu optimizasyonu."""
        from src.rag.query_optimizer import QueryOptimizer

        optimizer = QueryOptimizer()
        result = optimizer.optimize("pazar büyüklüğü nedir")

        assert result is not None
        assert len(result.queries) > 0

    def test_section_query_builder(self):
        """Section query builder testi."""
        from src.rag.query_optimizer import SectionQueryBuilder

        builder = SectionQueryBuilder()
        query = builder.build_query(
            section_id="finansal_projeksiyonlar",
            section_title="Finansal Projeksiyonlar"
        )

        assert query is not None
        assert len(query) > 0
