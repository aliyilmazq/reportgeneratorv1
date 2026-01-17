"""Web Araştırma Modülü - Claude bilgi tabanı ile araştırma."""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class WebSource:
    """Web kaynağı."""
    title: str
    url: str
    content: str
    score: float = 0.0
    published_date: str = ""
    domain: str = ""


@dataclass
class WebSearchResult:
    """Web araştırma sonucu."""
    query: str
    sources: List[WebSource] = field(default_factory=list)
    summary: str = ""
    search_time: float = 0.0
    total_results: int = 0


class WebSearcher:
    """Web araştırması - Claude bilgi tabanı kullanılır."""

    def __init__(self, api_key: Optional[str] = None):
        """WebSearcher - harici API kullanmaz."""
        pass

    def is_available(self) -> bool:
        """Her zaman kullanılabilir (mock veri)."""
        return True

    def search(
        self,
        query: str,
        search_depth: str = "advanced",
        max_results: int = 10,
        include_domains: List[str] = None,
        exclude_domains: List[str] = None,
        language: str = "tr"
    ) -> WebSearchResult:
        """Araştırma sonucu döndür - Claude researcher modülü asıl işi yapar."""
        return self._create_placeholder(query)

    def search_multiple(
        self,
        queries: List[str],
        show_progress: bool = True
    ) -> Dict[str, WebSearchResult]:
        """Birden fazla sorgu için araştırma yap."""
        results = {}
        for query in queries:
            results[query] = self.search(query)
        return results

    def search_for_report(
        self,
        topic: str,
        report_type: str,
        language: str = "tr"
    ) -> Dict[str, WebSearchResult]:
        """Rapor türüne göre özelleştirilmiş araştırma."""

        # Rapor türüne göre arama sorguları
        query_templates = {
            "is_plani": [
                f"{topic} pazar büyüklüğü Türkiye 2024",
                f"{topic} sektör analizi rakipler",
                f"{topic} iş modeli başarılı örnekler",
                f"{topic} yatırım fırsatları Türkiye",
                f"{topic} SWOT analizi sektör",
            ],
            "pazar_analizi": [
                f"{topic} pazar araştırması Türkiye 2024",
                f"{topic} tüketici davranışları",
                f"{topic} rekabet analizi lider şirketler",
                f"{topic} büyüme trendleri",
            ],
            "fizibilite": [
                f"{topic} fizibilite çalışması",
                f"{topic} maliyet analizi",
                f"{topic} yatırım geri dönüş süresi",
                f"{topic} risk faktörleri",
            ],
            "default": [
                f"{topic} Türkiye 2024",
                f"{topic} sektör raporu",
                f"{topic} istatistikler veriler",
            ]
        }

        queries = query_templates.get(report_type, query_templates["default"])

        return self.search_multiple(queries)

    def _extract_domain(self, url: str) -> str:
        """URL'den domain çıkar."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return ""

    def _create_placeholder(self, query: str) -> WebSearchResult:
        """Placeholder sonuç döndür - asıl araştırma Claude researcher ile yapılır."""
        return WebSearchResult(
            query=query,
            sources=[],
            summary=f"Araştırma: {query} - Claude Opus 4.5 ile detaylı analiz yapılacak",
            total_results=0
        )

    def format_sources_for_report(self, results: Dict[str, WebSearchResult]) -> str:
        """Kaynakları rapor formatına dönüştür."""
        formatted = []

        for query, result in results.items():
            if result.sources:
                formatted.append(f"\n### {query}\n")

                if result.summary:
                    formatted.append(f"{result.summary}\n")

                formatted.append("\n**Kaynaklar:**\n")
                for i, source in enumerate(result.sources[:5], 1):
                    formatted.append(f"{i}. [{source.title}]({source.url})")
                    if source.content:
                        # İlk 200 karakter
                        preview = source.content[:200].replace('\n', ' ')
                        formatted.append(f"   > {preview}...")
                    formatted.append("")

        return "\n".join(formatted)

    def get_citations(self, results: Dict[str, WebSearchResult]) -> List[Dict]:
        """Kaynak listesi oluştur."""
        citations = []
        seen_urls = set()

        for result in results.values():
            for source in result.sources:
                if source.url not in seen_urls:
                    citations.append({
                        'title': source.title,
                        'url': source.url,
                        'domain': source.domain,
                        'accessed_date': datetime.now().strftime("%d.%m.%Y")
                    })
                    seen_urls.add(source.url)

        return citations
