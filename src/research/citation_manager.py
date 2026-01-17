"""
Citation Manager Module - Manages citations and references

Bu modül rapor boyunca kullanılan tüm alıntıları ve referansları yönetir.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from .web_researcher import WebSource


@dataclass
class Citation:
    """Tek bir alıntı/referans."""
    id: str
    source_url: str
    source_title: str
    source_domain: str
    text_cited: str
    section_id: str
    accessed_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    page_or_section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "source_domain": self.source_domain,
            "text_cited": self.text_cited,
            "section_id": self.section_id,
            "accessed_date": self.accessed_date,
            "page_or_section": self.page_or_section
        }


class CitationManager:
    """
    Alıntı ve referans yöneticisi.

    Özellikleri:
    - Inline citation ekleme ([1], [2], vb.)
    - Kaynakça oluşturma
    - Bölüm bazlı referans takibi
    - Çoklu format desteği (numeric, APA, Harvard)
    """

    def __init__(self, style: str = "numeric"):
        """
        Args:
            style: Referans stili - "numeric", "apa", "harvard"
        """
        self.citations: List[Citation] = []
        self.style = style
        self.source_index: Dict[str, int] = {}  # URL -> citation number
        self.counter = 0

    def add_citation(
        self,
        source: WebSource,
        text_cited: str,
        section_id: str
    ) -> str:
        """
        Yeni alıntı ekle ve referans işareti döndür.

        Args:
            source: Kaynak WebSource nesnesi
            text_cited: Alıntılanan metin
            section_id: Alıntının kullanıldığı bölüm

        Returns:
            Referans işareti (ör. "[1]")
        """
        url = source.url

        # Kaynak daha önce kullanıldıysa aynı numarayı kullan
        if url in self.source_index:
            citation_num = self.source_index[url]
            marker = self._format_marker(citation_num)

            # Aynı kaynağın farklı bölümde kullanımını kaydet
            citation = Citation(
                id=marker,
                source_url=url,
                source_title=source.title,
                source_domain=source.domain,
                text_cited=text_cited,
                section_id=section_id,
                accessed_date=source.accessed_date
            )
            self.citations.append(citation)

            return marker

        # Yeni kaynak
        self.counter += 1
        self.source_index[url] = self.counter
        marker = self._format_marker(self.counter)

        citation = Citation(
            id=marker,
            source_url=url,
            source_title=source.title,
            source_domain=source.domain,
            text_cited=text_cited,
            section_id=section_id,
            accessed_date=source.accessed_date
        )
        self.citations.append(citation)

        return marker

    def _format_marker(self, num: int) -> str:
        """Alıntı işaretini formatla."""
        if self.style == "numeric":
            return f"[{num}]"
        elif self.style == "apa":
            return f"({num})"
        else:  # harvard
            return f"[{num}]"

    def get_section_citations(self, section_id: str) -> List[Citation]:
        """Belirli bir bölümdeki alıntıları getir."""
        return [c for c in self.citations if c.section_id == section_id]

    def get_unique_sources(self) -> List[Dict[str, Any]]:
        """Benzersiz kaynakların listesini getir."""
        unique = {}
        for url, num in sorted(self.source_index.items(), key=lambda x: x[1]):
            # Bu URL için ilk alıntıyı bul
            citation = next((c for c in self.citations if c.source_url == url), None)
            if citation:
                unique[url] = {
                    "number": num,
                    "url": url,
                    "title": citation.source_title,
                    "domain": citation.source_domain,
                    "accessed_date": citation.accessed_date
                }
        return list(unique.values())

    def generate_references_section(self, title: str = "Kaynakça") -> str:
        """
        Kaynakça bölümü oluştur.

        Returns:
            Formatlanmış kaynakça metni
        """
        lines = [f"## {title}\n"]

        unique_sources = self.get_unique_sources()

        for source in unique_sources:
            num = source["number"]
            entry = self._format_reference(source)
            lines.append(f"[{num}] {entry}")

        return "\n".join(lines)

    def _format_reference(self, source: Dict[str, Any]) -> str:
        """Tek bir referansı formatla."""
        title = source["title"]
        url = source["url"]
        domain = source["domain"]
        accessed = source["accessed_date"]

        if self.style == "apa":
            return f"{title}. (Erişim Tarihi: {accessed}). {domain}. Erişim adresi: {url}"

        elif self.style == "harvard":
            return f"{domain} ({accessed}) '{title}', Erişim: {url}"

        else:  # numeric
            return f"{title}. {domain}. {url} (Erişim: {accessed})"

    def generate_inline_references(self, content: str, sources: List[WebSource]) -> str:
        """
        İçeriğe inline referanslar ekle.

        Args:
            content: Orijinal içerik
            sources: Kullanılan kaynaklar

        Returns:
            Referans işaretleri eklenmiş içerik
        """
        # Bu fonksiyon içeriği analiz eder ve uygun yerlere
        # referans işaretleri ekler

        # Basit yaklaşım: her paragrafın sonuna ilgili kaynak ekle
        paragraphs = content.split("\n\n")
        result_paragraphs = []

        source_idx = 0
        for para in paragraphs:
            if para.strip() and len(para) > 100:  # Uzun paragraflar için
                if source_idx < len(sources):
                    # Paragrafın sonuna referans ekle
                    marker = self._format_marker(source_idx + 1)
                    para = para.rstrip() + f" {marker}"
                    source_idx += 1
            result_paragraphs.append(para)

        return "\n\n".join(result_paragraphs)

    def cite_statistic(
        self,
        value: str,
        unit: str,
        source: WebSource,
        section_id: str
    ) -> str:
        """
        İstatistiksel bir değeri alıntıla.

        Args:
            value: Değer (ör. "1.5")
            unit: Birim (ör. "milyar TL")
            source: Kaynak
            section_id: Bölüm ID

        Returns:
            Alıntı işareti ile formatlanmış istatistik
        """
        text = f"{value} {unit}"
        marker = self.add_citation(source, text, section_id)
        return f"{value} {unit} {marker}"

    def cite_fact(
        self,
        fact: str,
        source: WebSource,
        section_id: str
    ) -> str:
        """
        Bir bilgiyi alıntıla.

        Args:
            fact: Bilgi/gerçek
            source: Kaynak
            section_id: Bölüm ID

        Returns:
            Alıntı işareti ile formatlanmış bilgi
        """
        marker = self.add_citation(source, fact, section_id)
        return f"{fact} {marker}"

    def get_statistics(self) -> Dict[str, Any]:
        """Alıntı istatistiklerini getir."""
        sections = {}
        for citation in self.citations:
            section = citation.section_id
            if section not in sections:
                sections[section] = 0
            sections[section] += 1

        return {
            "total_citations": len(self.citations),
            "unique_sources": len(self.source_index),
            "citations_per_section": sections,
            "most_cited_source": self._get_most_cited_source()
        }

    def _get_most_cited_source(self) -> Optional[Dict[str, Any]]:
        """En çok alıntılanan kaynağı bul."""
        url_counts = {}
        for citation in self.citations:
            url = citation.source_url
            if url not in url_counts:
                url_counts[url] = {
                    "url": url,
                    "title": citation.source_title,
                    "count": 0
                }
            url_counts[url]["count"] += 1

        if not url_counts:
            return None

        return max(url_counts.values(), key=lambda x: x["count"])

    def export_citations(self, format: str = "json") -> Any:
        """Alıntıları dışa aktar."""
        if format == "json":
            return [c.to_dict() for c in self.citations]

        elif format == "markdown":
            lines = ["# Alıntılar\n"]
            current_section = None

            for citation in self.citations:
                if citation.section_id != current_section:
                    current_section = citation.section_id
                    lines.append(f"\n## {current_section}\n")

                lines.append(f"- {citation.id} {citation.text_cited[:100]}... ({citation.source_domain})")

            return "\n".join(lines)

        else:
            return self.citations

    def clear(self):
        """Tüm alıntıları temizle."""
        self.citations.clear()
        self.source_index.clear()
        self.counter = 0

    def merge(self, other: "CitationManager"):
        """Başka bir CitationManager'ın alıntılarını birleştir."""
        for citation in other.citations:
            # Kaynak zaten varsa numarayı koru
            if citation.source_url in self.source_index:
                new_citation = Citation(
                    id=self._format_marker(self.source_index[citation.source_url]),
                    source_url=citation.source_url,
                    source_title=citation.source_title,
                    source_domain=citation.source_domain,
                    text_cited=citation.text_cited,
                    section_id=citation.section_id,
                    accessed_date=citation.accessed_date,
                    page_or_section=citation.page_or_section
                )
            else:
                # Yeni kaynak
                self.counter += 1
                self.source_index[citation.source_url] = self.counter
                new_citation = Citation(
                    id=self._format_marker(self.counter),
                    source_url=citation.source_url,
                    source_title=citation.source_title,
                    source_domain=citation.source_domain,
                    text_cited=citation.text_cited,
                    section_id=citation.section_id,
                    accessed_date=citation.accessed_date,
                    page_or_section=citation.page_or_section
                )

            self.citations.append(new_citation)
