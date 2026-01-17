"""Source Attribution Modulu - Gelismis kaynak atfi ve guvenilirlik puanlama."""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console

console = Console()


@dataclass
class AttributedSource:
    """Atfedilmis kaynak."""
    id: str
    title: str
    source_type: str  # file, web, user
    file_name: str = ""
    url: str = ""
    domain: str = ""
    excerpt: str = ""
    page_number: Optional[int] = None

    # Skorlar
    relevance_score: float = 0.0
    credibility_score: float = 0.0
    recency_score: float = 0.0
    confidence_score: float = 0.0

    # Tarih
    date: Optional[str] = None
    accessed_date: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class InlineCitation:
    """Satir ici atif."""
    text: str
    source_id: str
    position: int
    confidence: float
    citation_type: str = "numeric"  # numeric, author, footnote


class SourceAttributor:
    """Gelismis kaynak atif yonetimi."""

    # Guvenilir domain'ler
    TRUSTED_DOMAINS = {
        # Resmi kurumlar
        "gov.tr": 0.95,
        "edu.tr": 0.90,
        "tuik.gov.tr": 1.0,
        "tcmb.gov.tr": 1.0,
        "hazine.gov.tr": 0.95,
        "sanayi.gov.tr": 0.95,

        # Uluslararasi kurumlar
        "worldbank.org": 0.95,
        "imf.org": 0.95,
        "oecd.org": 0.90,
        "un.org": 0.90,
        "ec.europa.eu": 0.90,

        # Guvenilir kaynaklar
        "statista.com": 0.85,
        "reuters.com": 0.85,
        "bloomberg.com": 0.85,

        # Akademik
        "scholar.google.com": 0.85,
        "researchgate.net": 0.80
    }

    def __init__(self):
        self.sources: Dict[str, AttributedSource] = {}
        self._source_counter = 0

    def add_source(
        self,
        text: str,
        source_type: str = "file",
        file_name: str = "",
        url: str = "",
        relevance_score: float = 0.0,
        date: str = None,
        page_number: int = None
    ) -> AttributedSource:
        """
        Kaynak ekle ve skorla.
        """
        self._source_counter += 1
        source_id = f"src_{self._source_counter}"

        # Domain cikar
        domain = self._extract_domain(url) if url else file_name

        # Guvenilirlik skoru
        credibility = self._calculate_credibility(domain, source_type)

        # Guncellik skoru
        recency = self._calculate_recency(date)

        # Genel guven skoru
        confidence = self._calculate_confidence(
            relevance_score, credibility, recency
        )

        source = AttributedSource(
            id=source_id,
            title=file_name or domain or f"Kaynak {self._source_counter}",
            source_type=source_type,
            file_name=file_name,
            url=url,
            domain=domain,
            excerpt=text[:300] if text else "",
            page_number=page_number,
            relevance_score=relevance_score,
            credibility_score=credibility,
            recency_score=recency,
            confidence_score=confidence,
            date=date
        )

        self.sources[source_id] = source
        return source

    def _extract_domain(self, url: str) -> str:
        """URL'den domain cikar."""
        if not url:
            return ""

        try:
            # Basit domain extraction
            url = url.replace("https://", "").replace("http://", "")
            url = url.replace("www.", "")
            domain = url.split("/")[0]
            return domain
        except Exception:
            return ""

    def _calculate_credibility(
        self,
        domain: str,
        source_type: str
    ) -> float:
        """Domain guvenilirlik puani hesapla."""
        # Dosya kaynaklari icin varsayilan
        if source_type == "file":
            return 0.8  # Kullanici dosyalari guvenilir kabul edilir

        if source_type == "user":
            return 0.7

        # Web kaynaklari icin domain kontrolu
        domain_lower = domain.lower()

        for trusted, score in self.TRUSTED_DOMAINS.items():
            if domain_lower.endswith(trusted):
                return score

        # Bilinmeyen domain
        return 0.5

    def _calculate_recency(self, date_str: Optional[str]) -> float:
        """Kaynak guncellik puani hesapla."""
        if not date_str:
            return 0.5  # Tarih bilinmiyor

        try:
            # ISO format parse
            if "T" in date_str:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                date = datetime.strptime(date_str[:10], "%Y-%m-%d")

            # Kac gun once?
            days_ago = (datetime.now() - date.replace(tzinfo=None)).days

            # Puanlama
            if days_ago < 30:  # 1 ay
                return 1.0
            elif days_ago < 180:  # 6 ay
                return 0.9
            elif days_ago < 365:  # 1 yil
                return 0.8
            elif days_ago < 730:  # 2 yil
                return 0.6
            elif days_ago < 1825:  # 5 yil
                return 0.4
            else:
                return 0.2

        except Exception:
            return 0.5

    def _calculate_confidence(
        self,
        relevance: float,
        credibility: float,
        recency: float
    ) -> float:
        """Genel guven skoru hesapla."""
        # Agirlikli ortalama
        confidence = (
            relevance * 0.4 +
            credibility * 0.4 +
            recency * 0.2
        )
        return round(confidence, 3)

    def get_source(self, source_id: str) -> Optional[AttributedSource]:
        """Kaynak getir."""
        return self.sources.get(source_id)

    def get_all_sources(self) -> List[AttributedSource]:
        """Tum kaynaklari getir."""
        return list(self.sources.values())

    def get_sources_by_confidence(
        self,
        min_confidence: float = 0.5
    ) -> List[AttributedSource]:
        """Minimum guven skoruna gore kaynaklar."""
        return [
            s for s in self.sources.values()
            if s.confidence_score >= min_confidence
        ]

    def format_citations(
        self,
        style: str = "numeric"
    ) -> Dict[str, str]:
        """
        Atif formatla.

        Args:
            style: numeric, apa, footnote

        Returns:
            {source_id: formatted_citation}
        """
        formatted = {}

        for i, (source_id, source) in enumerate(self.sources.items(), 1):
            if style == "numeric":
                formatted[source_id] = f"[{i}]"
            elif style == "apa":
                date_year = source.date[:4] if source.date else "t.y."
                formatted[source_id] = f"({source.title}, {date_year})"
            elif style == "footnote":
                formatted[source_id] = f"[^{i}]"
            else:
                formatted[source_id] = f"[{i}]"

        return formatted

    def generate_bibliography(
        self,
        style: str = "numeric"
    ) -> str:
        """Kaynakca olustur."""
        lines = ["## Kaynaklar\n"]

        for i, source in enumerate(self.sources.values(), 1):
            if style == "numeric":
                if source.url:
                    lines.append(f"[{i}] {source.title}. Erisim: {source.url}")
                else:
                    lines.append(f"[{i}] {source.title}")

                if source.page_number:
                    lines[-1] += f", s. {source.page_number}"

                lines[-1] += f" (Guven: {source.confidence_score:.0%})"

            elif style == "apa":
                date_year = source.date[:4] if source.date else "t.y."
                lines.append(f"- {source.title} ({date_year}).")
                if source.url:
                    lines[-1] += f" Erisim: {source.url}"

        return "\n".join(lines)


class CitationInserter:
    """Metne atif ekleme."""

    # Atif gerektiren pattern'ler
    CITATION_PATTERNS = [
        r'%\s*\d+[,.]?\d*',  # Yuzde: %15, %3.5
        r'\d+[,.]?\d*\s*%',  # Yuzde: 15%, 3,5%
        r'\d+[,.]?\d*\s*(milyon|milyar|trilyon)',  # Buyuk sayilar
        r'\d+[,.]?\d*\s*(TL|USD|EUR|dolar|euro)',  # Para
        r'(artti|azaldi|buyudu|daraldi|yükseldi|düştü)',  # Trend
        r'(toplam|ortalama|yaklasik|tahmini)\s+\d+',  # Istatistik
    ]

    def __init__(self, attributor: SourceAttributor):
        self.attributor = attributor

    def insert_citations(
        self,
        content: str,
        sources: List[AttributedSource],
        style: str = "numeric"
    ) -> str:
        """
        Icerikteki iddia ve verilere citation ekle.
        """
        if not sources:
            return content

        # Atif formatlarini al
        citation_map = self.attributor.format_citations(style)

        # Pattern'leri bul ve atif ekle
        for pattern in self.CITATION_PATTERNS:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))

            # Sondan basa isle (pozisyon kaymasi onleme)
            for match in reversed(matches):
                # Zaten atif var mi kontrol et
                end_pos = match.end()
                if end_pos < len(content) and content[end_pos] == '[':
                    continue

                # En uygun kaynagi bul
                best_source = self._find_best_source(
                    match.group(), sources
                )

                if best_source and best_source.id in citation_map:
                    citation = citation_map[best_source.id]
                    insert_pos = match.end()

                    # Cumle sonu kontrolu
                    if insert_pos < len(content) and content[insert_pos] in '.!?':
                        insert_pos = insert_pos
                    else:
                        # Kelime sonuna git
                        while insert_pos < len(content) and content[insert_pos].isalnum():
                            insert_pos += 1

                    content = content[:insert_pos] + f" {citation}" + content[insert_pos:]

        return content

    def _find_best_source(
        self,
        text_fragment: str,
        sources: List[AttributedSource]
    ) -> Optional[AttributedSource]:
        """En uygun kaynagi bul."""
        if not sources:
            return None

        # En yuksek confidence skorlu kaynagi sec
        best = max(sources, key=lambda s: s.confidence_score)

        # Minimum guven esigi
        if best.confidence_score >= 0.4:
            return best

        return None

    def generate_inline_references(
        self,
        content: str,
        sources: List[AttributedSource]
    ) -> Tuple[str, List[InlineCitation]]:
        """
        Inline referanslar olustur ve listele.

        Returns:
            (updated_content, citations)
        """
        citations = []
        updated_content = content

        for pattern in self.CITATION_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                best_source = self._find_best_source(match.group(), sources)

                if best_source:
                    citations.append(InlineCitation(
                        text=match.group(),
                        source_id=best_source.id,
                        position=match.start(),
                        confidence=best_source.confidence_score
                    ))

        return updated_content, citations


class SourceValidator:
    """Kaynak dogrulama."""

    def validate_source(
        self,
        source: AttributedSource,
        content: str
    ) -> Dict[str, Any]:
        """
        Kaynak guvenilirligini dogrula.

        Returns:
            Dogrulama raporu
        """
        issues = []
        score = 1.0

        # Guvenilirlik kontrolu
        if source.credibility_score < 0.5:
            issues.append("Dusuk guvenilirlik skoru")
            score -= 0.2

        # Guncellik kontrolu
        if source.recency_score < 0.4:
            issues.append("Eski kaynak")
            score -= 0.1

        # Icerik eslesmesi kontrolu
        if source.excerpt:
            if not self._content_matches(source.excerpt, content):
                issues.append("Kaynak icerigi uyusmuyor")
                score -= 0.3

        return {
            "source_id": source.id,
            "is_valid": score >= 0.5,
            "validation_score": max(0, score),
            "issues": issues
        }

    def _content_matches(self, excerpt: str, content: str) -> bool:
        """Kaynak icerigi ile ana icerik uyusumu kontrol."""
        # Basit kelime eslesmesi
        excerpt_words = set(excerpt.lower().split()[:20])
        content_words = set(content.lower().split())

        overlap = len(excerpt_words & content_words)
        return overlap >= len(excerpt_words) * 0.3
