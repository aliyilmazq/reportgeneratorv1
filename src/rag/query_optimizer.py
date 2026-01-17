"""Query Optimizasyon Modulu - HyDE, Multi-Query, Decomposition."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class OptimizedQuery:
    """Optimize edilmis sorgu."""
    original: str
    optimized: str
    strategy: str
    embedding: Optional[List[float]] = None


@dataclass
class OptimizationResult:
    """Optimizasyon sonucu."""
    original_query: str
    strategy: str
    queries: List[str]
    optimized_queries: List[OptimizedQuery]

    def __iter__(self):
        return iter(self.queries)

    def __len__(self):
        return len(self.queries)


class QueryOptimizer:
    """Sorgu optimizasyonu ana sinifi."""

    def __init__(
        self,
        anthropic_client=None,
        embedder=None
    ):
        """
        Query optimizer.

        Args:
            anthropic_client: Anthropic API client (HyDE icin)
            embedder: Embedding olusturucu
        """
        self.client = anthropic_client
        self.embedder = embedder

        self.hyde_generator = HyDEGenerator(anthropic_client) if anthropic_client else None
        self.multi_query = MultiQueryGenerator(anthropic_client) if anthropic_client else None
        self.decomposer = QueryDecomposer()

    def optimize(
        self,
        query: str,
        strategy: str = "auto",
        section_context: str = ""
    ) -> OptimizationResult:
        """
        Sorguyu optimize et.

        Args:
            query: Orijinal sorgu
            strategy: Optimizasyon stratejisi
                - "hyde": Hypothetical Document Embeddings
                - "multi_query": Coklu sorgu uretimi
                - "decomposition": Sorgu parca lama
                - "expansion": Keyword expansion
                - "auto": Otomatik secim
            section_context: Bolum baglami

        Returns:
            OptimizationResult: Optimizasyon sonucu
        """
        if strategy == "auto":
            strategy = self._select_strategy(query)

        if strategy == "hyde" and self.hyde_generator:
            opt_queries = self._apply_hyde(query, section_context)
        elif strategy == "multi_query" and self.multi_query:
            opt_queries = self._apply_multi_query(query)
        elif strategy == "decomposition":
            opt_queries = self._apply_decomposition(query)
        elif strategy == "expansion":
            opt_queries = self._apply_expansion(query)
        else:
            # Fallback: orijinal sorgu
            opt_queries = [OptimizedQuery(
                original=query,
                optimized=query,
                strategy="none"
            )]

        return OptimizationResult(
            original_query=query,
            strategy=strategy,
            queries=[q.optimized for q in opt_queries],
            optimized_queries=opt_queries
        )

    def _select_strategy(self, query: str) -> str:
        """Sorguya gore strateji sec."""
        words = query.split()

        # Uzun sorgular icin decomposition
        if len(words) > 10:
            return "decomposition"

        # Kisa sorgular icin expansion
        if len(words) < 4:
            return "expansion"

        # Claude varsa multi_query
        if self.client:
            return "multi_query"

        return "expansion"

    def _apply_hyde(
        self,
        query: str,
        section_context: str
    ) -> List[OptimizedQuery]:
        """HyDE stratejisi uygula."""
        hypothetical = self.hyde_generator.generate_hypothetical_answer(
            query, section_context
        )

        # Embedding olustur
        embedding = None
        if self.embedder:
            result = self.embedder.embed(hypothetical, is_query=True)
            embedding = result.embedding

        return [OptimizedQuery(
            original=query,
            optimized=hypothetical,
            strategy="hyde",
            embedding=embedding
        )]

    def _apply_multi_query(self, query: str) -> List[OptimizedQuery]:
        """Multi-query stratejisi uygula."""
        variants = self.multi_query.generate_query_variants(query, count=3)

        results = []
        for variant in variants:
            embedding = None
            if self.embedder:
                result = self.embedder.embed(variant, is_query=True)
                embedding = result.embedding

            results.append(OptimizedQuery(
                original=query,
                optimized=variant,
                strategy="multi_query",
                embedding=embedding
            ))

        return results

    def _apply_decomposition(self, query: str) -> List[OptimizedQuery]:
        """Decomposition stratejisi uygula."""
        sub_queries = self.decomposer.decompose(query)

        results = []
        for sub_query in sub_queries:
            embedding = None
            if self.embedder:
                result = self.embedder.embed(sub_query, is_query=True)
                embedding = result.embedding

            results.append(OptimizedQuery(
                original=query,
                optimized=sub_query,
                strategy="decomposition",
                embedding=embedding
            ))

        return results

    def _apply_expansion(self, query: str) -> List[OptimizedQuery]:
        """Keyword expansion uygula."""
        expander = KeywordExpander()
        expanded = expander.expand(query)

        results = [
            OptimizedQuery(
                original=query,
                optimized=query,
                strategy="expansion"
            )
        ]

        for exp in expanded[:2]:  # Max 2 expansion
            if exp != query:
                embedding = None
                if self.embedder:
                    result = self.embedder.embed(exp, is_query=True)
                    embedding = result.embedding

                results.append(OptimizedQuery(
                    original=query,
                    optimized=exp,
                    strategy="expansion",
                    embedding=embedding
                ))

        return results


class HyDEGenerator:
    """Hypothetical Document Embeddings - hayali cevap olusturma."""

    def __init__(self, anthropic_client):
        self.client = anthropic_client

    def generate_hypothetical_answer(
        self,
        query: str,
        section_context: str = ""
    ) -> str:
        """
        Sorguya hayali/ideal cevap olustur.
        Bu cevap embedding'e donusturulerek arama yapilir.
        """
        if not self.client:
            return query

        prompt = f"""Sen bir uzman rapor yazarisin. Asagidaki soru icin
IDEAL bir cevap paragrafı yaz. Bu cevap veritabaninda olabilecek
dokumanlara benzer olmali. Kisa ve oz tut (max 150 kelime).

Soru: {query}
{"Baglam: " + section_context if section_context else ""}

SADECE cevap paragrafini yaz, aciklama ekleme. Turkce yaz."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            console.print(f"[yellow]HyDE olusturulamadi: {e}[/yellow]")
            return query

    def get_hyde_embedding(
        self,
        query: str,
        section_context: str,
        embedder
    ) -> List[float]:
        """Hayali cevabin embedding'ini dondur."""
        hypothetical = self.generate_hypothetical_answer(query, section_context)
        result = embedder.embed(hypothetical, is_query=True)
        return result.embedding


class MultiQueryGenerator:
    """Coklu sorgu olusturucu."""

    def __init__(self, anthropic_client):
        self.client = anthropic_client

    def generate_query_variants(
        self,
        query: str,
        count: int = 3
    ) -> List[str]:
        """
        Tek sorguyu birden fazla farkli sekilde yeniden yaz.
        """
        if not self.client:
            return [query]

        prompt = f"""Asagidaki arama sorgusunu {count} farkli sekilde yeniden yaz.
Her versiyon ayni anlami farkli kelimelerle ifade etmeli.
Turkce yaz.

Orijinal sorgu: {query}

Sadece sorgu listesi ver, her satira bir sorgu. Numara veya tire kullanma:"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text.strip()
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Orijinali de ekle
            queries = [query] + lines[:count - 1]
            return queries

        except Exception as e:
            console.print(f"[yellow]Multi-query olusturulamadi: {e}[/yellow]")
            return [query]


class QueryDecomposer:
    """Karmasik sorgulari alt sorgulara ayir."""

    # Turkce baglaclar
    CONJUNCTIONS = ["ve", "ile", "veya", "ayrica", "hem", "da", "de"]

    def decompose(self, complex_query: str) -> List[str]:
        """
        Karmasik sorguyu basit alt sorgulara ayir.
        """
        # Baglac bazli ayirma
        for conj in self.CONJUNCTIONS:
            if f" {conj} " in complex_query.lower():
                parts = complex_query.lower().split(f" {conj} ")
                if len(parts) > 1:
                    return [p.strip() for p in parts if len(p.strip()) > 5]

        # Virgul bazli ayirma
        if "," in complex_query:
            parts = complex_query.split(",")
            if len(parts) > 1:
                return [p.strip() for p in parts if len(p.strip()) > 5]

        # Ayirma yapilamadi
        return [complex_query]


class KeywordExpander:
    """Keyword expansion - esanlamli ve iliskili terimler."""

    # Turkce esanlamli sozluk
    SYNONYMS = {
        "pazar": ["sektor", "market", "pazaryeri", "ticaret"],
        "gelir": ["hasilat", "ciro", "kazanc", "income"],
        "maliyet": ["gider", "masraf", "harcama", "cost"],
        "kar": ["profit", "kazanc", "getiri"],
        "zarar": ["kayip", "loss", "hasar"],
        "musteri": ["tuketici", "alici", "client"],
        "urun": ["mamul", "product", "mal"],
        "hizmet": ["servis", "service"],
        "sirket": ["firma", "isletme", "kurum", "company"],
        "rekabet": ["yarisa", "competition", "rakip"],
        "strateji": ["plan", "yaklasim", "strategy"],
        "analiz": ["inceleme", "degerlendirme", "analysis"],
        "buyume": ["gelisme", "artis", "growth"],
        "risk": ["tehlike", "belirsizlik"],
        "firsat": ["olanak", "sans", "opportunity"],
        "hedef": ["amac", "goal", "target"],
        "performans": ["basari", "verimlilik", "performance"],
        "yatirim": ["investment", "sermaye"],
        "finans": ["mali", "finansal", "finance"],
        "operasyon": ["isletim", "faaliyet", "operation"]
    }

    def expand(self, query: str) -> List[str]:
        """Sorguyu genislet."""
        query_lower = query.lower()
        expansions = [query]

        for word, synonyms in self.SYNONYMS.items():
            if word in query_lower:
                for syn in synonyms[:2]:  # Max 2 synonym
                    expanded = query_lower.replace(word, syn)
                    if expanded not in expansions:
                        expansions.append(expanded)

        return expansions[:5]  # Max 5 expansion


class SectionQueryBuilder:
    """Bolum bazli optimize edilmis sorgular."""

    SECTION_TEMPLATES = {
        "yonetici_ozeti": [
            "{title} proje ozeti",
            "{title} ana hedefler ve sonuclar",
            "{title} kritik basari faktorleri"
        ],
        "sirket_tanimi": [
            "{title} sirket profili",
            "{title} misyon vizyon degerler",
            "{title} kurum tarihcesi"
        ],
        "pazar_analizi": [
            "{title} pazar buyuklugu istatistik",
            "{title} sektor trendleri",
            "{title} rekabet analizi",
            "{title} hedef kitle profili"
        ],
        "pazarlama_stratejisi": [
            "{title} pazarlama plani",
            "{title} fiyatlandirma stratejisi",
            "{title} dagitim kanallari",
            "{title} promosyon aktiviteleri"
        ],
        "finansal_projeksiyonlar": [
            "{title} gelir projeksiyonu",
            "{title} maliyet analizi",
            "{title} kar zarar tahmini",
            "{title} nakit akisi"
        ],
        "risk_analizi": [
            "{title} risk faktorleri",
            "{title} SWOT analizi",
            "{title} tehditler firsatlar"
        ],
        "operasyon_plani": [
            "{title} operasyonel surec",
            "{title} uretim plani",
            "{title} tedarik zinciri"
        ],
        "yonetim_ekibi": [
            "{title} yonetim kadrosu",
            "{title} organizasyon yapisi",
            "{title} insan kaynaklari"
        ]
    }

    def build_queries(
        self,
        section_id: str,
        section_title: str
    ) -> List[str]:
        """Bolum icin optimize edilmis sorgular olustur."""
        templates = self.SECTION_TEMPLATES.get(section_id, ["{title}"])

        queries = []
        for template in templates:
            query = template.format(title=section_title)
            queries.append(query)

        return queries

    def build_query(
        self,
        section_id: str,
        section_title: str
    ) -> str:
        """Bolum icin tek optimize edilmis sorgu olustur."""
        queries = self.build_queries(section_id, section_title)
        return queries[0] if queries else section_title
