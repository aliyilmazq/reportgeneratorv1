"""
Report Orchestrator Module - Main workflow coordinator

Bu modül rapor üretiminin tüm fazlarını koordine eder:
0. KURAL YÜKLEME (ZORUNLU)
1. Dosya tarama ve işleme
2. Web araştırması (gerçek)
3. Veri toplama
4. İçerik planlama
5. Bölüm üretimi
6. Doğrulama ve iyileştirme
7. Belge oluşturma

ÖNEMLİ: Hiçbir rapor üretimi kurallar yüklenmeden BAŞLAYAMAZ!
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import os
import time

from anthropic import Anthropic

# Mevcut modüller
from .scanner import FileScanner
from .processor.aggregator import ContentAggregator
from .generator.docx_generator import DocxGenerator
from .generator.pdf_generator import PdfGenerator

# Yeni modüller
from .research.web_researcher import WebResearcher, ResearchResult
from .research.source_collector import SourceCollector
from .research.citation_manager import CitationManager
from .data_sources.web_data_fetcher import WebDataFetcher, DataPoint
from .content.content_planner import ContentPlanner, ContentPlan
from .content.section_generator import SectionGenerator, GeneratedSection
from .progress.phase_tracker import PhaseTracker, GenerationPhase
from .progress.progress_reporter import ProgressReporter, SimpleProgressReporter

# Kural yükleyici
from .rules.rules_loader import (
    RulesLoader,
    LoadedRules,
    RulesLoadError,
    ensure_rules_loaded
)


@dataclass
class UserInput:
    """Kullanıcı girdisi."""
    input_path: str
    output_type: str
    output_format: str
    language: str = "tr"
    special_notes: str = ""


@dataclass
class GeneratedReport:
    """Üretilen rapor."""
    title: str
    report_type: str
    language: str
    sections: List[GeneratedSection]
    output_files: List[str]
    citations: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    generation_time_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "report_type": self.report_type,
            "language": self.language,
            "sections": [s.to_dict() for s in self.sections],
            "output_files": self.output_files,
            "citations": self.citations,
            "sources": self.sources,
            "statistics": self.statistics,
            "generation_time_seconds": self.generation_time_seconds,
            "metadata": self.metadata
        }


class ReportOrchestrator:
    """
    Ana rapor uretim koordinatoru.

    Tum fazlari sirayla yonetir ve ilerleme takibi yapar.

    Fazlar:
        1. Baslatma - Kurallari yukle, sistemi hazirla
        2. Dosya Tarama - Giris dosyalarini tara
        3. Dosya Isleme - PDF, Excel, Word, gorsel parse
        4. Web Arastirmasi - Gercek web kaynaklarindan bilgi topla
        5. Veri Toplama - Ekonomik veriler, sektor istatistikleri
        6. Icerik Planlama - Rapor yapisini olustur
        7. Bolum Uretimi - Her bolum icin icerik uret
        8. Dogrulama - Kalite ve tutarlilik kontrol
        9. Belge Uretimi - DOCX/PDF cikti olustur
        10. Tamamlama - Istatistikleri derle

    Attributes:
        client: Anthropic API client
        output_dir: Cikti dizini
        rules_loader: Kural yukleyici
        scanner: Dosya tarayici
        web_researcher: Web arastirmaci
        content_planner: Icerik planlayici
        phase_tracker: Faz takipci

    Example:
        >>> orchestrator = ReportOrchestrator(output_dir="./output")
        >>> user_input = UserInput(
        ...     input_path="./data",
        ...     output_type="is_plani",
        ...     output_format="both",
        ...     language="tr"
        ... )
        >>> report = orchestrator.generate_report(user_input)
        >>> print(f"Rapor olusturuldu: {report.output_files}")
    """

    def __init__(
        self,
        anthropic_client: Optional[Anthropic] = None,
        output_dir: str = "./output",
        templates_path: Optional[str] = None,
        rules_dir: Optional[str] = None,
        use_live_progress: bool = True
    ) -> None:
        """
        ReportOrchestrator'u baslat.

        Args:
            anthropic_client: Anthropic API client. None ise ANTHROPIC_API_KEY
                environment variable'dan olusturulur.
            output_dir: Cikti dosyalarinin kaydedilecegi dizin.
            templates_path: Rapor sablonlari dizini.
            rules_dir: Kural dosyalari dizini.
            use_live_progress: Canli ilerleme gosterimi aktif mi.

        Raises:
            ValueError: ANTHROPIC_API_KEY bulunamazsa.
        """
        # Anthropic client
        if anthropic_client:
            self.client = anthropic_client
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable gerekli")
            self.client = Anthropic(api_key=api_key)

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.templates_path = templates_path

        # ═══════════════════════════════════════════════════════════════════
        # KURAL YÜKLEYİCİ - ZORUNLU
        # ═══════════════════════════════════════════════════════════════════
        self.rules_loader = RulesLoader(rules_dir)
        self.loaded_rules: Optional[LoadedRules] = None

        # Bileşenler
        self.scanner = FileScanner()
        self.aggregator = ContentAggregator()
        self.web_researcher = WebResearcher(anthropic_client=self.client)
        self.source_collector = SourceCollector()
        self.citation_manager = CitationManager()
        self.data_fetcher = WebDataFetcher(anthropic_client=self.client)
        self.content_planner = ContentPlanner(
            templates_path=templates_path,
            anthropic_client=self.client
        )

        # Progress tracking
        self.phase_tracker = PhaseTracker()
        self.use_live_progress = use_live_progress

        if use_live_progress:
            self.progress_reporter = ProgressReporter(self.phase_tracker)
        else:
            self.progress_reporter = SimpleProgressReporter(self.phase_tracker)

        # ═══════════════════════════════════════════════════════════════════
        # RAG SİSTEMİ - v5.0
        # ═══════════════════════════════════════════════════════════════════
        self._init_rag_system()

    def _init_rag_system(self):
        """RAG sistemini başlat ve yapılandır."""
        try:
            from .rag import (
                ConfigLoader,
                CacheManager,
                HybridRetriever,
                HybridSearchConfig,
                QueryOptimizer,
                ContextCompressor,
                SourceAttributor,
                TokenManager,
                DynamicContextManager,
                ChunkRanker,
                DocumentProcessor,
                SemanticChunker,
                ChunkConfig
            )

            # Konfigurasyon yükle
            self.rag_config = ConfigLoader("config/rag_config.yaml").load()

            # Cache Manager - singleton
            cache_dir = self.output_dir / ".rag_cache"
            self.cache_manager = CacheManager(
                cache_dir=str(cache_dir),
                query_ttl_hours=self.rag_config.caching.query_cache_ttl_hours,
                embedding_ttl_days=self.rag_config.caching.embedding_cache_ttl_days,
                result_ttl_minutes=self.rag_config.caching.result_cache_ttl_minutes
            )

            # Hybrid Retriever config
            self.hybrid_config = HybridSearchConfig(
                semantic_weight=self.rag_config.hybrid_search.semantic_weight,
                bm25_weight=self.rag_config.hybrid_search.bm25_weight,
                use_rrf=self.rag_config.hybrid_search.use_rrf,
                use_reranking=self.rag_config.reranking.enabled,
                use_mmr=self.rag_config.mmr.enabled,
                initial_fetch=self.rag_config.hybrid_search.initial_fetch,
                final_top_k=self.rag_config.hybrid_search.final_top_k
            )

            # Chunking config
            self.chunk_config = ChunkConfig(
                chunk_size=self.rag_config.chunking.chunk_size,
                chunk_overlap=self.rag_config.chunking.chunk_overlap,
                min_chunk_size=self.rag_config.chunking.min_chunk_size,
                max_chunk_size=self.rag_config.chunking.max_chunk_size,
                preserve_sentences=self.rag_config.chunking.preserve_sentences,
                preserve_paragraphs=self.rag_config.chunking.preserve_paragraphs
            )

            # Bileşenler - lazy init için None
            self._rag_retriever = None
            self._rag_indexed = False

            # Query Optimizer
            self.query_optimizer = QueryOptimizer(anthropic_client=self.client)

            # Context işleme
            self.context_compressor = ContextCompressor(anthropic_client=self.client)
            self.token_manager = TokenManager()
            self.context_manager = DynamicContextManager(self.token_manager)

            # Source attribution
            self.source_attributor = SourceAttributor()

            # Chunk ranker
            self.chunk_ranker = ChunkRanker()

            # Document processor
            self.document_processor = DocumentProcessor(
                anthropic_client=self.client,
                max_keywords=self.rag_config.chunking.chunk_size // 50,
                generate_summary=True
            )

            # Semantic chunker
            self.semantic_chunker = SemanticChunker(self.chunk_config)

            self._rag_initialized = True

            if self.use_live_progress:
                from rich.console import Console
                Console().print("[green]RAG sistemi başarıyla yüklendi[/green]")

        except Exception as e:
            self._rag_initialized = False
            if self.use_live_progress:
                from rich.console import Console
                Console().print(f"[yellow]RAG sistemi yüklenemedi: {e}[/yellow]")

    def _progress_callback(self, phase: str, progress: float, detail: str = ""):
        """İlerleme callback'i."""
        try:
            phase_enum = GenerationPhase(phase)
            self.phase_tracker.update_progress(phase_enum, progress, detail)
        except ValueError:
            pass

    def generate_report(self, user_input: UserInput) -> GeneratedReport:
        """
        Rapor üret.

        Args:
            user_input: Kullanıcı girdisi

        Returns:
            GeneratedReport: Üretilen rapor
        """
        start_time = time.time()

        # Progress başlat
        self.progress_reporter.start()

        try:
            # ═══════════════════════════════════════════════════════════
            # FAZ 0: KURAL YÜKLEME (ZORUNLU - İLK ADIM)
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.INITIALIZATION,
                "Kurallar yükleniyor..."
            )

            # TÜM KURALLAR YÜKLENMEDEN DEVAM EDİLEMEZ!
            try:
                self.loaded_rules = self.rules_loader.load_all_rules()
                self.phase_tracker.update_progress(
                    GenerationPhase.INITIALIZATION,
                    50,
                    f"6 kural dosyası yüklendi"
                )
            except RulesLoadError as e:
                raise RuntimeError(
                    f"RAPOR ÜRETİMİ BAŞLATILMADI!\n"
                    f"Kural dosyaları yüklenemedi:\n{str(e)}\n\n"
                    f"Kurallar yüklenmeden rapor üretimi YASAKLANMIŞTIR!"
                )

            # Kural özetini logla
            rules_summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                    KURALLAR YÜKLENDİ                         ║
╠══════════════════════════════════════════════════════════════╣
║ Minimum kelime/bölüm: {self.loaded_rules.min_words_per_section:<36} ║
║ Minimum paragraf/bölüm: {self.loaded_rules.min_paragraphs_per_section:<34} ║
║ Minimum kaynak/bölüm: {self.loaded_rules.min_sources_per_section:<36} ║
║ Toplam minimum kaynak: {self.loaded_rules.min_total_sources:<35} ║
║ Minimum kalite puanı: {self.loaded_rules.min_quality_score:<36} ║
╚══════════════════════════════════════════════════════════════╝
"""
            # Bu bilgiyi console'a yazdır
            if self.use_live_progress:
                from rich.console import Console
                console = Console()
                console.print(rules_summary, style="green")

            # ═══════════════════════════════════════════════════════════
            # FAZ 1: BAŞLATMA (devam)
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.update_progress(
                GenerationPhase.INITIALIZATION,
                100,
                "Sistem hazır"
            )
            time.sleep(0.3)
            self.phase_tracker.complete_phase(GenerationPhase.INITIALIZATION)

            # ═══════════════════════════════════════════════════════════
            # FAZ 2: DOSYA TARAMA
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.FILE_SCANNING,
                "Dosyalar taranıyor..."
            )

            scan_result = self.scanner.scan(user_input.input_path)
            total_files = scan_result.total_files if hasattr(scan_result, 'total_files') else len(scan_result.files if hasattr(scan_result, 'files') else [])

            self.phase_tracker.update_progress(
                GenerationPhase.FILE_SCANNING,
                100,
                f"{total_files} dosya bulundu"
            )
            self.phase_tracker.complete_phase(GenerationPhase.FILE_SCANNING)

            # ═══════════════════════════════════════════════════════════
            # FAZ 3: DOSYA İŞLEME
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.FILE_PARSING,
                "Dosyalar işleniyor..."
            )

            aggregated_content = self.aggregator.aggregate(
                scan_result,
                progress_callback=lambda p, d: self.phase_tracker.update_progress(
                    GenerationPhase.FILE_PARSING, p, d
                )
            )

            self.phase_tracker.complete_phase(GenerationPhase.FILE_PARSING)

            # ═══════════════════════════════════════════════════════════
            # FAZ 4: WEB ARAŞTIRMASI (GERÇEK)
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.WEB_RESEARCH,
                "Web araştırması yapılıyor..."
            )

            # Araştırma konularını belirle
            research_topics = self._extract_research_topics(
                user_input,
                aggregated_content
            )

            research_results = []
            for i, topic in enumerate(research_topics):
                self.phase_tracker.update_progress(
                    GenerationPhase.WEB_RESEARCH,
                    (i + 1) / len(research_topics) * 100,
                    f"Araştırılıyor: {topic}"
                )

                result = self.web_researcher.research_topic(
                    topic=topic,
                    context=user_input.special_notes,
                    progress_callback=self._progress_callback
                )
                research_results.append(result)

                # Kaynakları topla
                self.source_collector.add_sources_from_result(result)

                time.sleep(0.5)  # Rate limiting

            self.phase_tracker.complete_phase(GenerationPhase.WEB_RESEARCH)

            # ═══════════════════════════════════════════════════════════
            # FAZ 5: VERİ TOPLAMA
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.DATA_COLLECTION,
                "Ekonomik veriler toplanıyor..."
            )

            data_points = self.data_fetcher.get_all_macro_indicators(
                progress_callback=lambda p, d: self.phase_tracker.update_progress(
                    GenerationPhase.DATA_COLLECTION, p, d
                )
            )

            # Sektör verilerini de topla
            sector = self._detect_sector(user_input, aggregated_content)
            if sector:
                sector_data = self.data_fetcher.get_sector_data(sector)
                if sector_data:
                    data_points["sector"] = sector_data

            self.phase_tracker.complete_phase(GenerationPhase.DATA_COLLECTION)

            # ═══════════════════════════════════════════════════════════
            # FAZ 6: İÇERİK PLANLAMA
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.CONTENT_PLANNING,
                "İçerik planlanıyor..."
            )

            content_plan = self.content_planner.create_plan(
                report_type=user_input.output_type,
                collected_sources=list(self.source_collector.sources.values()),
                aggregated_content=aggregated_content,
                data_points=data_points,
                special_notes=user_input.special_notes,
                language=user_input.language
            )

            self.phase_tracker.update_progress(
                GenerationPhase.CONTENT_PLANNING,
                100,
                f"{content_plan.total_sections} bölüm planlandı"
            )
            self.phase_tracker.complete_phase(GenerationPhase.CONTENT_PLANNING)

            # ═══════════════════════════════════════════════════════════
            # FAZ 7: BÖLÜM ÜRETİMİ
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.SECTION_GENERATION,
                "Bölümler üretiliyor..."
            )

            # Kuralları prompt için hazırla
            rules_prompt = self.rules_loader.get_rules_for_prompt()

            section_generator = SectionGenerator(
                anthropic_client=self.client,
                citation_manager=self.citation_manager,
                language=user_input.language,
                rules_prompt=rules_prompt,  # Kuralları geçir
                min_words=self.loaded_rules.min_words_per_section,
                min_paragraphs=self.loaded_rules.min_paragraphs_per_section,
                min_sources=self.loaded_rules.min_sources_per_section
            )

            # RAG context oluştur
            rag_context = self._build_rag_context(aggregated_content)

            # Dosya içeriklerini hazırla
            file_contents = self._prepare_file_contents(aggregated_content)

            sections = section_generator.generate_all_sections(
                section_plans=content_plan.section_plans,
                source_collector=self.source_collector,
                data_points=data_points,
                rag_context=rag_context,
                file_contents=file_contents,
                progress_callback=lambda p, d: self.phase_tracker.update_progress(
                    GenerationPhase.SECTION_GENERATION, p, d
                )
            )

            self.phase_tracker.complete_phase(GenerationPhase.SECTION_GENERATION)

            # ═══════════════════════════════════════════════════════════
            # FAZ 8: DOĞRULAMA
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.VALIDATION,
                "İçerik doğrulanıyor..."
            )

            validation_results = self._validate_sections(sections)

            self.phase_tracker.update_progress(
                GenerationPhase.VALIDATION,
                100,
                f"Kalite puanı: {validation_results['average_quality']:.0f}%"
            )
            self.phase_tracker.complete_phase(GenerationPhase.VALIDATION)

            # ═══════════════════════════════════════════════════════════
            # FAZ 9: BELGE ÜRETİMİ
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.DOCUMENT_GENERATION,
                "Belge oluşturuluyor..."
            )

            output_files = self._generate_documents(
                sections=sections,
                user_input=user_input,
                content_plan=content_plan
            )

            self.phase_tracker.complete_phase(GenerationPhase.DOCUMENT_GENERATION)

            # ═══════════════════════════════════════════════════════════
            # FAZ 10: TAMAMLAMA
            # ═══════════════════════════════════════════════════════════
            self.phase_tracker.start_phase(
                GenerationPhase.COMPLETION,
                "Tamamlanıyor..."
            )

            # İstatistikleri derle
            statistics = self._compile_statistics(
                sections=sections,
                research_results=research_results,
                data_points=data_points,
                validation_results=validation_results
            )

            self.phase_tracker.complete_phase(GenerationPhase.COMPLETION)

            duration = time.time() - start_time

            # Sonuç raporu
            report = GeneratedReport(
                title=self._generate_title(user_input, aggregated_content),
                report_type=user_input.output_type,
                language=user_input.language,
                sections=sections,
                output_files=output_files,
                citations=self.citation_manager.export_citations(format="json"),
                sources=[s.to_dict() for s in self.source_collector.sources.values()],
                statistics=statistics,
                generation_time_seconds=duration,
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "total_words": sum(s.word_count for s in sections),
                    "total_sources": len(self.source_collector.sources),
                    "total_citations": len(self.citation_manager.citations)
                }
            )

            return report

        except Exception as e:
            # Hata durumunda fazı fail olarak işaretle
            if self.phase_tracker.current_phase:
                self.phase_tracker.fail_phase(
                    self.phase_tracker.current_phase,
                    str(e)
                )
            raise

        finally:
            # Progress'i durdur
            self.progress_reporter.stop()
            self.progress_reporter.print_summary()

    def _extract_research_topics(
        self,
        user_input: UserInput,
        aggregated_content: Any
    ) -> List[str]:
        """Araştırma konularını çıkar."""
        topics = []

        # Rapor tipine göre temel konular
        report_topics = {
            "is_plani": [
                "iş planı hazırlama",
                "pazar analizi yöntemleri",
                "finansal projeksiyon",
                "rekabet analizi"
            ],
            "proje_raporu": [
                "proje yönetimi",
                "proje planlama",
                "risk yönetimi"
            ],
            "analiz_raporu": [
                "sektör analizi",
                "trend analizi",
                "veri analizi"
            ],
            "on_fizibilite": [
                "fizibilite çalışması",
                "yatırım analizi",
                "maliyet-fayda analizi"
            ]
        }

        # Temel konuları ekle
        base_topics = report_topics.get(user_input.output_type, ["iş analizi"])
        topics.extend(base_topics[:2])

        # Kullanıcı notlarından konu çıkar
        if user_input.special_notes:
            # İlk 100 karakteri konu olarak ekle
            notes_topic = user_input.special_notes[:100].strip()
            if notes_topic:
                topics.append(notes_topic)

        # Dosya içeriğinden konu çıkar
        if hasattr(aggregated_content, 'all_text'):
            text = aggregated_content.all_text[:500]
            # Basit anahtar kelime çıkarımı
            if text:
                topics.append(f"{text[:100]} sektör analizi")

        return topics[:5]  # Maximum 5 konu

    def _detect_sector(
        self,
        user_input: UserInput,
        aggregated_content: Any
    ) -> Optional[str]:
        """Sektörü tespit et."""
        text = ""
        if user_input.special_notes:
            text += user_input.special_notes.lower()
        if hasattr(aggregated_content, 'all_text'):
            text += aggregated_content.all_text[:1000].lower()

        # Sektör anahtar kelimeleri
        sector_keywords = {
            "e_ticaret": ["e-ticaret", "online", "internet satış", "dijital ticaret"],
            "fintech": ["fintech", "finansal teknoloji", "ödeme sistemi", "dijital bankacılık"],
            "yazilim": ["yazılım", "software", "uygulama geliştirme", "bilişim"],
            "turizm": ["turizm", "otel", "seyahat", "konaklama"],
            "saglik": ["sağlık", "hastane", "medikal", "ilaç"],
            "egitim": ["eğitim", "okul", "öğrenci", "kurs"],
            "insaat": ["inşaat", "yapı", "konut", "gayrimenkul"],
            "enerji": ["enerji", "elektrik", "güneş", "rüzgar"],
            "tarim": ["tarım", "hayvancılık", "gıda üretimi"]
        }

        for sector, keywords in sector_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return sector

        return None

    def _build_rag_context(
        self,
        aggregated_content: Any,
        section_id: str = None,
        use_advanced: bool = True
    ) -> str:
        """
        RAG baglami olustur.

        Args:
            aggregated_content: Toplanmis icerik
            section_id: Bolum ID (bolume ozel retrieval icin)
            use_advanced: Gelismis RAG kullan (v5.0)
        """
        # Gelismis RAG kullan
        if use_advanced:
            try:
                return self._build_advanced_rag_context(
                    aggregated_content, section_id
                )
            except Exception as e:
                self.progress_reporter.report_warning(
                    f"Gelismis RAG hatasi, basit mod kullaniliyor: {e}"
                )

        # Fallback: Basit RAG
        context_parts = []

        if hasattr(aggregated_content, 'all_text'):
            context_parts.append(aggregated_content.all_text[:3000])

        if hasattr(aggregated_content, 'all_tables'):
            for table in aggregated_content.all_tables[:3]:
                if isinstance(table, dict):
                    context_parts.append(str(table))

        return "\n\n".join(context_parts)

    def _build_advanced_rag_context(
        self,
        aggregated_content: Any,
        section_id: str = None
    ) -> str:
        """
        Gelismis RAG baglami (v5.0).

        Ozellikler:
        - Semantic chunking ile dokuman parcalama
        - Query optimization (HyDE, multi-query)
        - Hybrid search (BM25 + Semantic)
        - Context compression
        - Source attribution
        - Token budgeting
        - Caching
        """
        from .rag import (
            HybridRetriever,
            SectionQueryBuilder
        )

        # RAG sistemi yuklenmemisse fallback
        if not getattr(self, '_rag_initialized', False):
            return self._simple_rag_context(aggregated_content)

        # ═══════════════════════════════════════════════════════════════════
        # 1. CACHE KONTROLU
        # ═══════════════════════════════════════════════════════════════════
        cache_key = f"rag_context_{section_id or 'general'}_{hash(str(aggregated_content)[:500])}"
        cached_result = self.cache_manager.query_cache.get(cache_key)
        if cached_result:
            return cached_result

        # ═══════════════════════════════════════════════════════════════════
        # 2. DOKUMAN HAZIRLAMA VE CHUNKING
        # ═══════════════════════════════════════════════════════════════════
        documents = []

        # Ana metin chunking
        if hasattr(aggregated_content, 'all_text') and aggregated_content.all_text:
            # Semantic chunker kullan
            chunks = self.semantic_chunker.chunk(aggregated_content.all_text)
            for i, chunk in enumerate(chunks):
                # Document processor ile zenginlestir
                try:
                    processed = self.document_processor.process(
                        chunk.text,
                        doc_id=f"chunk_{i}",
                        metadata={"source": "main_content", "chunk_index": i}
                    )
                    documents.append({
                        "text": chunk.text,
                        "source": f"content_chunk_{i}",
                        "type": "text",
                        "keywords": processed.keywords[:5],
                        "category": processed.category
                    })
                except Exception:
                    documents.append({
                        "text": chunk.text,
                        "source": f"content_chunk_{i}",
                        "type": "text"
                    })

        # Tablolar
        if hasattr(aggregated_content, 'all_tables'):
            for i, table in enumerate(aggregated_content.all_tables[:5]):
                if isinstance(table, dict):
                    documents.append({
                        "text": str(table),
                        "source": f"table_{i}",
                        "type": "table"
                    })

        if not documents:
            return ""

        # ═══════════════════════════════════════════════════════════════════
        # 3. HYBRID RETRIEVER INDEX
        # ═══════════════════════════════════════════════════════════════════
        # Her seferinde yeni retriever (dokuman bazli)
        retriever = HybridRetriever(config=self.hybrid_config)
        retriever.index_documents(documents, show_progress=False)

        # ═══════════════════════════════════════════════════════════════════
        # 4. QUERY OPTIMIZATION
        # ═══════════════════════════════════════════════════════════════════
        if section_id:
            section_query_builder = SectionQueryBuilder()
            base_query = section_query_builder.build_query(
                section_id=section_id,
                section_title=section_id.replace("_", " ").title()
            )
        else:
            base_query = "proje ozeti ana hedefler sonuclar finansal analiz"

        # Query optimization - HyDE, multi-query stratejileri
        optimized_queries = self.query_optimizer.optimize(
            query=base_query,
            strategy=self.rag_config.query_optimization.strategy
        )

        # ═══════════════════════════════════════════════════════════════════
        # 5. HYBRID RETRIEVAL (Optimize edilmis sorgularla)
        # ═══════════════════════════════════════════════════════════════════
        all_results = []
        queries_to_use = optimized_queries.queries[:3] if optimized_queries.queries else [base_query]

        for opt_query in queries_to_use:
            results = retriever.retrieve(
                query=opt_query,
                top_k=self.rag_config.hybrid_search.final_top_k
            )
            all_results.extend(results)

        if not all_results:
            return ""

        # ═══════════════════════════════════════════════════════════════════
        # 6. DEDUPLICATE VE RANK
        # ═══════════════════════════════════════════════════════════════════
        docs = [
            {"text": r.text, "score": r.score, "source": r.source}
            for r in all_results
        ]
        ranked_docs = self.chunk_ranker.deduplicate(docs)
        ranked_docs = self.chunk_ranker.rank_chunks(
            ranked_docs, base_query, top_k=10
        )

        # ═══════════════════════════════════════════════════════════════════
        # 7. SOURCE ATTRIBUTION
        # ═══════════════════════════════════════════════════════════════════
        self.source_attributor = type(self.source_attributor)()  # Reset
        for doc in ranked_docs:
            self.source_attributor.add_source(
                text=doc.get("text", "")[:300],
                source_type="file",
                file_name=doc.get("source", ""),
                relevance_score=doc.get("combined_score", doc.get("score", 0))
            )

        # ═══════════════════════════════════════════════════════════════════
        # 8. CONTEXT COMPRESSION
        # ═══════════════════════════════════════════════════════════════════
        compressed_chunks = self.context_compressor.compress_for_query(
            documents=ranked_docs,
            query=base_query,
            max_output_tokens=self.rag_config.context.max_tokens // 2
        )

        # ═══════════════════════════════════════════════════════════════════
        # 9. TOKEN BUDGETING VE CONTEXT OLUSTURMA
        # ═══════════════════════════════════════════════════════════════════
        compressed_docs = [
            {
                "text": chunk.compressed_text,
                "score": chunk.relevance_score,
                "source": ranked_docs[i].get("source", "") if i < len(ranked_docs) else "",
                "key_points": chunk.key_points
            }
            for i, chunk in enumerate(compressed_chunks)
        ]

        # Token butcesi ile context olustur
        max_context_tokens = (
            self.rag_config.context.max_tokens -
            self.rag_config.context.reserved_for_response
        )
        context_window = self.context_manager.build_context(
            documents=compressed_docs,
            max_tokens=max_context_tokens
        )

        # ═══════════════════════════════════════════════════════════════════
        # 10. FORMATLAMA VE KAYNAKCA
        # ═══════════════════════════════════════════════════════════════════
        formatted_context = self.context_manager.format_context(
            context_window,
            format_style=self.rag_config.context.format_style,
            include_metadata=self.rag_config.context.include_metadata
        )

        # Kaynakca ekle
        if self.source_attributor.sources:
            bibliography = self.source_attributor.generate_bibliography(
                style=self.rag_config.source_attribution.citation_style
            )
            formatted_context += f"\n\n{bibliography}"

        # ═══════════════════════════════════════════════════════════════════
        # 11. CACHE'E KAYDET
        # ═══════════════════════════════════════════════════════════════════
        self.cache_manager.query_cache.set(cache_key, formatted_context)

        return formatted_context

    def _simple_rag_context(self, aggregated_content: Any) -> str:
        """Basit RAG context (fallback)."""
        context_parts = []

        if hasattr(aggregated_content, 'all_text'):
            context_parts.append(aggregated_content.all_text[:5000])

        if hasattr(aggregated_content, 'all_tables'):
            for table in aggregated_content.all_tables[:3]:
                if isinstance(table, dict):
                    context_parts.append(str(table))

        return "\n\n".join(context_parts)

    def _prepare_file_contents(
        self,
        aggregated_content: Any
    ) -> Dict[str, str]:
        """Dosya içeriklerini bölümlere göre hazırla."""
        contents = {}

        if hasattr(aggregated_content, 'all_text'):
            # Genel içerik
            contents["general"] = aggregated_content.all_text[:5000]

            # Finansal bölüm için sayısal içerik
            contents["finansal_projeksiyonlar"] = aggregated_content.all_text[:3000]

        return contents

    def _validate_sections(
        self,
        sections: List[GeneratedSection]
    ) -> Dict[str, Any]:
        """
        Bölümleri KURALLARA göre doğrula.

        Kurallar yüklenmemişse hata verir.
        """
        if not self.loaded_rules:
            raise RuntimeError("Doğrulama yapılamaz: Kurallar yüklenmemiş!")

        results = {
            "sections": [],
            "issues": [],
            "average_quality": 0,
            "passed": True
        }

        total_quality = 0
        for section in sections:
            section_result = {
                "section_id": section.section_id,
                "word_count": section.word_count,
                "quality_score": section.quality_score,
                "has_citations": len(section.citations_used) > 0,
                "issues": []
            }

            # Kurallara göre doğrula
            rule_violations = self.rules_loader.validate_content_against_rules(
                content=section.content,
                section_name=section.section_id
            )
            section_result["issues"].extend(rule_violations)

            # Minimum kelime kontrolü (kurallardan)
            if section.word_count < self.loaded_rules.min_words_per_section:
                section_result["issues"].append(
                    f"Kelime sayısı yetersiz: {section.word_count} < {self.loaded_rules.min_words_per_section}"
                )

            # Referans kontrolü (kurallardan)
            if len(section.citations_used) < self.loaded_rules.min_sources_per_section:
                section_result["issues"].append(
                    f"Kaynak referansı yetersiz: {len(section.citations_used)} < {self.loaded_rules.min_sources_per_section}"
                )

            results["sections"].append(section_result)
            results["issues"].extend(section_result["issues"])
            total_quality += section.quality_score

        results["average_quality"] = (total_quality / len(sections)) * 100 if sections else 0

        # Kalite puanı kontrolü
        if results["average_quality"] < self.loaded_rules.min_quality_score:
            results["issues"].append(
                f"Ortalama kalite puanı yetersiz: {results['average_quality']:.0f}% < {self.loaded_rules.min_quality_score}%"
            )
            results["passed"] = False

        # Toplam kaynak kontrolü
        total_sources = len(self.source_collector.sources)
        if total_sources < self.loaded_rules.min_total_sources:
            results["issues"].append(
                f"Toplam kaynak sayısı yetersiz: {total_sources} < {self.loaded_rules.min_total_sources}"
            )
            results["passed"] = False

        return results

    def _generate_documents(
        self,
        sections: List[GeneratedSection],
        user_input: UserInput,
        content_plan: ContentPlan
    ) -> List[str]:
        """Belgeleri oluştur."""
        output_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Rapor başlığı
        title = self._generate_title(user_input, None)

        # Structured report oluştur
        structured_report = self._create_structured_report(
            sections=sections,
            title=title,
            report_type=user_input.output_type,
            language=user_input.language
        )

        # DOCX
        if user_input.output_format in ["docx", "both"]:
            docx_path = self.output_dir / f"rapor_{timestamp}.docx"
            docx_generator = DocxGenerator()
            docx_generator.generate(structured_report, str(docx_path))
            output_files.append(str(docx_path))

        # PDF
        if user_input.output_format in ["pdf", "both"]:
            pdf_path = self.output_dir / f"rapor_{timestamp}.pdf"
            pdf_generator = PdfGenerator()
            pdf_generator.generate(structured_report, str(pdf_path))
            output_files.append(str(pdf_path))

        # Kaynakça dosyası
        refs_path = self.output_dir / f"kaynakca_{timestamp}.txt"
        with open(refs_path, "w", encoding="utf-8") as f:
            f.write(self.citation_manager.generate_references_section())
        output_files.append(str(refs_path))

        return output_files

    def _create_structured_report(
        self,
        sections: List[GeneratedSection],
        title: str,
        report_type: str,
        language: str
    ) -> Any:
        """Generator'lar için yapılandırılmış rapor oluştur."""
        # Mevcut StructuredReport formatına uyumlu nesne
        from dataclasses import dataclass, field
        from typing import List as TList

        @dataclass
        class ReportSection:
            id: str
            title: str
            content: str
            level: int
            subsections: TList = field(default_factory=list)

        @dataclass
        class StructuredReport:
            title: str
            report_type: str
            language: str
            sections: TList
            metadata: Dict = field(default_factory=dict)

        report_sections = []
        for section in sections:
            report_sections.append(ReportSection(
                id=section.section_id,
                title=section.title,
                content=section.content,
                level=section.level,
                subsections=[]
            ))

        return StructuredReport(
            title=title,
            report_type=report_type,
            language=language,
            sections=report_sections,
            metadata={
                "created_at": datetime.now().isoformat(),
                "total_words": sum(s.word_count for s in sections),
                "total_sections": len(sections)
            }
        )

    def _generate_title(
        self,
        user_input: UserInput,
        aggregated_content: Any
    ) -> str:
        """Rapor başlığı oluştur."""
        report_type_names = {
            "is_plani": "İş Planı",
            "proje_raporu": "Proje Raporu",
            "sunum": "Sunum",
            "on_fizibilite": "Ön Fizibilite Raporu",
            "teknik_dok": "Teknik Dokümantasyon",
            "analiz_raporu": "Analiz Raporu",
            "kisa_not": "Özet Rapor"
        }

        base_name = report_type_names.get(user_input.output_type, "Rapor")
        date_str = datetime.now().strftime("%Y")

        if user_input.special_notes:
            # Notlardan başlık çıkar
            words = user_input.special_notes.split()[:5]
            topic = " ".join(words)
            return f"{topic} - {base_name} {date_str}"

        return f"{base_name} {date_str}"

    def _compile_statistics(
        self,
        sections: List[GeneratedSection],
        research_results: List[ResearchResult],
        data_points: Dict[str, DataPoint],
        validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """İstatistikleri derle."""
        return {
            "total_sections": len(sections),
            "total_words": sum(s.word_count for s in sections),
            "total_paragraphs": sum(s.paragraph_count for s in sections),
            "total_tables": sum(len(s.tables) for s in sections),
            "total_sources": len(self.source_collector.sources),
            "total_citations": len(self.citation_manager.citations),
            "total_data_points": len(data_points),
            "average_quality_score": validation_results.get("average_quality", 0),
            "research_queries": len(research_results),
            "validation_issues": len(validation_results.get("issues", []))
        }
