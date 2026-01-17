"""
Web Researcher Module - Real web research using DuckDuckGo Search

Bu modül gerçek internet araştırması yapar ve doğrulanabilir kaynaklarla
zengin içerik üretmek için veri toplar.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import asyncio
import re
import time
import sys
from pathlib import Path

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from anthropic import Anthropic

# Security: URL validation
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from utils.validators import URLValidator
    from utils.exceptions import URLValidationError
    HAS_URL_VALIDATOR = True
except ImportError:
    HAS_URL_VALIDATOR = False
    URLValidator = None
    URLValidationError = Exception

logger = logging.getLogger(__name__)


@dataclass
class WebSource:
    """Doğrulanmış web kaynağı."""
    url: str
    title: str
    snippet: str
    domain: str
    published_date: Optional[str] = None
    accessed_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    content: Optional[str] = None
    credibility_score: float = 0.5
    relevance_score: float = 0.5
    content_type: str = "article"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "domain": self.domain,
            "published_date": self.published_date,
            "accessed_date": self.accessed_date,
            "content": self.content,
            "credibility_score": self.credibility_score,
            "relevance_score": self.relevance_score,
            "content_type": self.content_type
        }


@dataclass
class ResearchResult:
    """Araştırma sonucu."""
    query: str
    sources: List[WebSource]
    summary: str
    key_facts: List[Dict[str, str]]
    statistics: List[Dict[str, str]]
    total_sources_found: int
    research_duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "sources": [s.to_dict() for s in self.sources],
            "summary": self.summary,
            "key_facts": self.key_facts,
            "statistics": self.statistics,
            "total_sources_found": self.total_sources_found,
            "research_duration_seconds": self.research_duration_seconds
        }


class WebResearcher:
    """
    Gerçek web araştırması yapan sınıf.

    DuckDuckGo Search API kullanarak internet üzerinden güncel ve
    doğrulanabilir bilgiler toplar.
    """

    # Güvenilir Türkiye kaynakları
    TRUSTED_DOMAINS = {
        # Resmi kurumlar
        "tuik.gov.tr": 1.0,
        "tcmb.gov.tr": 1.0,
        "bddk.org.tr": 1.0,
        "spk.gov.tr": 1.0,
        "tobb.org.tr": 0.95,
        "kosgeb.gov.tr": 0.95,
        "ticaret.gov.tr": 0.95,
        "sanayi.gov.tr": 0.95,
        "hazine.gov.tr": 0.95,

        # Finans ve ekonomi
        "borsaistanbul.com": 0.9,
        "bloomberght.com": 0.85,
        "ekonomim.com": 0.8,
        "dunya.com": 0.8,
        "para.com.tr": 0.75,

        # Uluslararası kaynaklar
        "worldbank.org": 0.95,
        "imf.org": 0.95,
        "oecd.org": 0.95,
        "statista.com": 0.85,
        "reuters.com": 0.9,
        "bloomberg.com": 0.9,

        # Haber kaynakları
        "aa.com.tr": 0.85,
        "ntv.com.tr": 0.75,
        "hurriyet.com.tr": 0.7,
        "milliyet.com.tr": 0.7,
    }

    def __init__(
        self,
        anthropic_client: Optional[Anthropic] = None,
        min_sources: int = 5,
        max_sources: int = 15,
        language: str = "tr"
    ):
        self.client = anthropic_client
        self.min_sources = min_sources
        self.max_sources = max_sources
        self.language = language
        self.current_year = datetime.now().year
        self.current_date = datetime.now().strftime("%Y-%m-%d")

        # DuckDuckGo search instance
        self.ddgs = DDGS() if HAS_DDGS else None

        # HTTP client for fetching pages
        self.http_client = httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        ) if HAS_HTTPX else None

    def _get_domain(self, url: str) -> str:
        """URL'den domain çıkar."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except (ValueError, AttributeError) as e:
            # Gecersiz URL formati
            return ""

    def _calculate_credibility(self, domain: str) -> float:
        """Domain'in güvenilirlik puanını hesapla."""
        if domain in self.TRUSTED_DOMAINS:
            return self.TRUSTED_DOMAINS[domain]

        # .gov.tr domainleri yüksek güvenilirlik
        if domain.endswith(".gov.tr"):
            return 0.9

        # .edu.tr domainleri
        if domain.endswith(".edu.tr"):
            return 0.85

        # .org.tr domainleri
        if domain.endswith(".org.tr"):
            return 0.75

        # Genel Türk domainleri
        if domain.endswith(".com.tr"):
            return 0.6

        # Uluslararası
        if domain.endswith(".org"):
            return 0.7

        return 0.5

    def _search_duckduckgo(
        self,
        query: str,
        max_results: int = 10,
        region: str = "tr-tr"
    ) -> List[Dict[str, Any]]:
        """DuckDuckGo ile arama yap."""
        if not self.ddgs:
            return []

        try:
            results = list(self.ddgs.text(
                query,
                region=region,
                max_results=max_results,
                safesearch="moderate"
            ))
            return results
        except Exception as e:
            print(f"DuckDuckGo arama hatası: {e}")
            return []

    def _validate_url(self, url: str) -> bool:
        """URL guvenlik kontrolu."""
        if not url:
            return False

        # URLValidator varsa kullan
        if HAS_URL_VALIDATOR and URLValidator:
            try:
                URLValidator.validate(url)
                return True
            except URLValidationError as e:
                logger.warning(f"Invalid URL rejected: {url} - {e}")
                return False

        # Fallback: basit kontrol
        if not url.startswith(('http://', 'https://')):
            return False

        return True

    def _fetch_page_content(self, url: str, max_chars: int = 5000) -> Optional[str]:
        """Web sayfasının içeriğini çek."""
        if not self.http_client or not HAS_BS4:
            return None

        # Security: URL validation
        if not self._validate_url(url):
            logger.warning(f"URL validation failed, skipping: {url}")
            return None

        try:
            response = self.http_client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Script ve style etiketlerini kaldır
                for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    tag.decompose()

                # Ana içeriği bul
                main_content = soup.find("main") or soup.find("article") or soup.find("body")
                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)
                    # Fazla boşlukları temizle
                    text = re.sub(r'\n\s*\n', '\n\n', text)
                    return text[:max_chars]
            return None
        except Exception as e:
            print(f"Sayfa çekme hatası ({url}): {e}")
            return None

    def _create_search_queries(
        self,
        topic: str,
        context: str,
        aspects: List[str] = None
    ) -> List[str]:
        """Araştırma için arama sorguları oluştur."""
        queries = []
        year = self.current_year

        # Ana sorgu
        queries.append(f"{topic} {year}")
        queries.append(f"{topic} Türkiye {year}")

        # İstatistik sorguları
        queries.append(f"{topic} istatistik {year}")
        queries.append(f"{topic} pazar büyüklüğü {year}")

        # Trend sorguları
        queries.append(f"{topic} büyüme oranı {year}")
        queries.append(f"{topic} sektör raporu {year}")

        # Spesifik yönler
        if aspects:
            for aspect in aspects[:3]:
                queries.append(f"{topic} {aspect} {year}")

        return queries

    def research_topic(
        self,
        topic: str,
        context: str = "",
        required_aspects: List[str] = None,
        progress_callback: callable = None
    ) -> ResearchResult:
        """
        Belirli bir konu hakkında kapsamlı web araştırması yap.

        Args:
            topic: Araştırılacak ana konu
            context: Ek bağlam bilgisi
            required_aspects: Araştırılması gereken spesifik yönler
            progress_callback: İlerleme bildirimi için callback

        Returns:
            ResearchResult: Toplanan kaynaklar ve özetler
        """
        start_time = time.time()
        all_sources: List[WebSource] = []
        seen_urls = set()

        # Arama sorgularını oluştur
        queries = self._create_search_queries(topic, context, required_aspects)

        total_queries = len(queries)
        for i, query in enumerate(queries):
            if progress_callback:
                progress_callback(
                    phase="web_research",
                    progress=(i + 1) / total_queries * 100,
                    detail=f"Aranıyor: {query}"
                )

            # DuckDuckGo'da ara
            results = self._search_duckduckgo(query, max_results=5)

            for result in results:
                url = result.get("href", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)

                    domain = self._get_domain(url)
                    credibility = self._calculate_credibility(domain)

                    # Yüksek güvenilirlikli kaynaklardan içerik çek
                    content = None
                    if credibility >= 0.8:
                        content = self._fetch_page_content(url)

                    source = WebSource(
                        url=url,
                        title=result.get("title", ""),
                        snippet=result.get("body", ""),
                        domain=domain,
                        content=content,
                        credibility_score=credibility,
                        relevance_score=0.7,
                        content_type="article"
                    )
                    all_sources.append(source)

            # Rate limiting
            time.sleep(0.5)

            # Yeterli kaynak toplandıysa dur
            if len(all_sources) >= self.max_sources:
                break

        # Kaynakları güvenilirlik ve alaka düzeyine göre sırala
        all_sources.sort(key=lambda x: (x.credibility_score, x.relevance_score), reverse=True)

        # En iyi kaynakları seç
        best_sources = all_sources[:self.max_sources]

        # Özet ve anahtar bilgileri çıkar
        summary, key_facts, statistics = self._extract_insights(topic, best_sources)

        duration = time.time() - start_time

        return ResearchResult(
            query=topic,
            sources=best_sources,
            summary=summary,
            key_facts=key_facts,
            statistics=statistics,
            total_sources_found=len(all_sources),
            research_duration_seconds=duration
        )

    def _extract_insights(
        self,
        topic: str,
        sources: List[WebSource]
    ) -> tuple[str, List[Dict[str, str]], List[Dict[str, str]]]:
        """Kaynaklardan özet ve anahtar bilgileri çıkar."""
        if not self.client:
            return self._extract_insights_basic(topic, sources)

        # Kaynak içeriklerini birleştir
        source_texts = []
        for i, source in enumerate(sources[:10], 1):
            text = f"[{i}] {source.title}\nURL: {source.url}\n"
            if source.content:
                text += f"İçerik: {source.content[:1500]}\n"
            else:
                text += f"Özet: {source.snippet}\n"
            source_texts.append(text)

        combined_text = "\n---\n".join(source_texts)

        prompt = f"""Aşağıdaki web kaynaklarını analiz et ve "{topic}" hakkında bilgi çıkar.

KAYNAKLAR:
{combined_text}

Lütfen aşağıdaki formatta yanıt ver:

## ÖZET
(3-5 cümlelik genel özet)

## ANAHTAR BİLGİLER
- Bilgi 1 [Kaynak numarası]
- Bilgi 2 [Kaynak numarası]
- Bilgi 3 [Kaynak numarası]
(en az 5 anahtar bilgi)

## İSTATİSTİKLER
- İstatistik 1: Değer [Kaynak numarası]
- İstatistik 2: Değer [Kaynak numarası]
(varsa sayısal veriler)

Önemli: Her bilgi için kaynak numarasını belirt. Sadece kaynaklarda bulunan bilgileri kullan, uydurmaman kritik."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse the response
            summary = ""
            key_facts = []
            statistics = []

            # Özet çıkar
            if "## ÖZET" in result_text:
                parts = result_text.split("## ANAHTAR BİLGİLER")
                summary_part = parts[0].replace("## ÖZET", "").strip()
                summary = summary_part

            # Anahtar bilgileri çıkar
            if "## ANAHTAR BİLGİLER" in result_text:
                facts_part = result_text.split("## ANAHTAR BİLGİLER")[1]
                if "## İSTATİSTİKLER" in facts_part:
                    facts_part = facts_part.split("## İSTATİSTİKLER")[0]

                for line in facts_part.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("- ") or line.startswith("• "):
                        # Kaynak numarasını çıkar
                        match = re.search(r'\[(\d+)\]', line)
                        source_idx = int(match.group(1)) - 1 if match else 0
                        source_url = sources[source_idx].url if source_idx < len(sources) else ""

                        key_facts.append({
                            "fact": re.sub(r'\[\d+\]', '', line[2:]).strip(),
                            "source_url": source_url
                        })

            # İstatistikleri çıkar
            if "## İSTATİSTİKLER" in result_text:
                stats_part = result_text.split("## İSTATİSTİKLER")[1]

                for line in stats_part.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("- ") or line.startswith("• "):
                        match = re.search(r'\[(\d+)\]', line)
                        source_idx = int(match.group(1)) - 1 if match else 0
                        source_url = sources[source_idx].url if source_idx < len(sources) else ""

                        statistics.append({
                            "stat": re.sub(r'\[\d+\]', '', line[2:]).strip(),
                            "source_url": source_url
                        })

            return summary, key_facts, statistics

        except Exception as e:
            print(f"Claude API hatası: {e}")
            return self._extract_insights_basic(topic, sources)

    def _extract_insights_basic(
        self,
        topic: str,
        sources: List[WebSource]
    ) -> tuple[str, List[Dict[str, str]], List[Dict[str, str]]]:
        """Claude olmadan basit bilgi çıkarımı."""
        summary = f"{topic} hakkında {len(sources)} kaynak bulundu."

        key_facts = []
        statistics = []

        for source in sources[:5]:
            key_facts.append({
                "fact": source.snippet[:200] if source.snippet else source.title,
                "source_url": source.url
            })

            # İstatistik pattern'leri ara
            if source.snippet:
                # Yüzde
                pct_match = re.search(r'%\s*(\d+[.,]?\d*)', source.snippet)
                if pct_match:
                    statistics.append({
                        "stat": f"{source.title}: %{pct_match.group(1)}",
                        "source_url": source.url
                    })

                # Para birimi
                money_match = re.search(r'(\d+[.,]?\d*)\s*(milyon|milyar|trilyon)?\s*(TL|dolar|USD|EUR)', source.snippet, re.IGNORECASE)
                if money_match:
                    statistics.append({
                        "stat": f"{money_match.group(0)}",
                        "source_url": source.url
                    })

        return summary, key_facts, statistics

    def search_statistics(
        self,
        indicator: str,
        year: int = None
    ) -> List[WebSource]:
        """Belirli bir gösterge için istatistik ara."""
        if year is None:
            year = self.current_year

        queries = [
            f"{indicator} Türkiye {year} TÜİK",
            f"{indicator} istatistik {year}",
            f"{indicator} veri {year}"
        ]

        sources = []
        seen_urls = set()

        for query in queries:
            results = self._search_duckduckgo(query, max_results=5)

            for result in results:
                url = result.get("href", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    domain = self._get_domain(url)

                    sources.append(WebSource(
                        url=url,
                        title=result.get("title", ""),
                        snippet=result.get("body", ""),
                        domain=domain,
                        credibility_score=self._calculate_credibility(domain),
                        content_type="statistics"
                    ))

            time.sleep(0.3)

        sources.sort(key=lambda x: x.credibility_score, reverse=True)
        return sources[:5]

    def search_market_data(
        self,
        sector: str,
        metrics: List[str] = None
    ) -> ResearchResult:
        """Sektör pazar verileri için araştırma yap."""
        if metrics is None:
            metrics = ["pazar büyüklüğü", "büyüme oranı", "oyuncular", "trendler"]

        return self.research_topic(
            topic=f"{sector} sektörü",
            context="pazar analizi",
            required_aspects=metrics
        )

    def search_competitor_data(
        self,
        industry: str,
        region: str = "Türkiye"
    ) -> ResearchResult:
        """Rekabet analizi için araştırma yap."""
        return self.research_topic(
            topic=f"{industry} rekabet analizi {region}",
            context="rakip analizi",
            required_aspects=["lider şirketler", "pazar payları", "stratejiler"]
        )

    def get_macro_economic_data(self) -> ResearchResult:
        """Makroekonomik göstergeler için araştırma yap."""
        return self.research_topic(
            topic="Türkiye ekonomi göstergeleri",
            context="makroekonomi",
            required_aspects=[
                "GSYİH",
                "enflasyon",
                "işsizlik",
                "döviz kuru",
                "faiz oranı",
                "cari açık"
            ]
        )

    def close(self):
        """Kaynakları temizle."""
        if self.http_client:
            self.http_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
