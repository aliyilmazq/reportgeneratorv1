"""
Source Collector Module - Collects and organizes sources from research

Bu modül araştırma sırasında toplanan kaynakları organize eder,
doğrular ve bölümlere eşleştirir.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
import re

from .web_researcher import WebSource


@dataclass
class CollectedSource:
    """Toplanmış ve doğrulanmış kaynak."""
    web_source: WebSource
    verification_status: str = "unverified"  # verified, unverified, conflicting
    corroborating_sources: List[str] = field(default_factory=list)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    used_in_sections: List[str] = field(default_factory=list)
    query_origin: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.web_source.to_dict(),
            "verification_status": self.verification_status,
            "corroborating_sources": self.corroborating_sources,
            "extracted_data": self.extracted_data,
            "used_in_sections": self.used_in_sections,
            "query_origin": self.query_origin
        }


class SourceCollector:
    """
    Araştırma sırasında kaynakları toplayan ve organize eden sınıf.

    Kaynakları:
    - Benzersiz URL'ye göre depolar
    - Güvenilirliğe göre sıralar
    - Bölümlere eşleştirir
    - Çapraz doğrulama yapar
    """

    # Bölüm-konu eşleştirmeleri
    SECTION_TOPICS = {
        "yonetici_ozeti": ["genel", "özet", "sonuç"],
        "sirket_tanimi": ["şirket", "kuruluş", "organizasyon", "hakkında"],
        "pazar_analizi": ["pazar", "sektör", "endüstri", "büyüme", "trend"],
        "rekabet_analizi": ["rekabet", "rakip", "pazar payı", "lider"],
        "pazarlama_stratejisi": ["pazarlama", "strateji", "müşteri", "hedef kitle"],
        "operasyon_plani": ["operasyon", "üretim", "süreç", "tedarik"],
        "finansal_projeksiyonlar": ["finansal", "gelir", "gider", "kar", "zarar", "bütçe"],
        "risk_analizi": ["risk", "tehdit", "fırsat", "SWOT"],
        "teknik_altyapi": ["teknik", "teknoloji", "sistem", "altyapı"],
        "istatistikler": ["istatistik", "veri", "rakam", "oran", "yüzde"]
    }

    def __init__(self):
        self.sources: Dict[str, CollectedSource] = {}  # URL -> CollectedSource
        self.queries_performed: List[str] = []
        self.section_sources: Dict[str, List[str]] = {}  # section_id -> [urls]

    def add_source(self, source: WebSource, query: str) -> CollectedSource:
        """
        Yeni kaynak ekle veya mevcut kaynağı güncelle.

        Args:
            source: WebSource nesnesi
            query: Bu kaynağı bulan sorgu

        Returns:
            CollectedSource: Eklenen veya güncellenen kaynak
        """
        url = source.url

        if url in self.sources:
            # Mevcut kaynağı güncelle
            existing = self.sources[url]
            if query not in existing.query_origin:
                existing.query_origin += f", {query}"
            return existing

        # Yeni kaynak oluştur
        collected = CollectedSource(
            web_source=source,
            query_origin=query,
            verification_status="unverified"
        )

        self.sources[url] = collected

        if query not in self.queries_performed:
            self.queries_performed.append(query)

        # Otomatik bölüm eşleştirmesi
        self._auto_assign_sections(collected)

        return collected

    def add_sources_from_result(self, research_result) -> List[CollectedSource]:
        """ResearchResult'tan tüm kaynakları ekle."""
        added = []
        for source in research_result.sources:
            collected = self.add_source(source, research_result.query)
            added.append(collected)
        return added

    def _auto_assign_sections(self, collected: CollectedSource):
        """Kaynağı otomatik olarak ilgili bölümlere ata."""
        source = collected.web_source
        text = f"{source.title} {source.snippet}".lower()

        for section_id, keywords in self.SECTION_TOPICS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    if section_id not in self.section_sources:
                        self.section_sources[section_id] = []
                    if source.url not in self.section_sources[section_id]:
                        self.section_sources[section_id].append(source.url)
                        collected.used_in_sections.append(section_id)
                    break

    def get_sources_for_section(
        self,
        section_id: str,
        min_sources: int = 3,
        min_credibility: float = 0.5
    ) -> List[CollectedSource]:
        """
        Belirli bir bölüm için ilgili kaynakları getir.

        Args:
            section_id: Bölüm kimliği
            min_sources: Minimum kaynak sayısı
            min_credibility: Minimum güvenilirlik puanı

        Returns:
            İlgili kaynakların listesi
        """
        section_urls = self.section_sources.get(section_id, [])

        # Doğrudan eşleşen kaynaklar
        direct_sources = [
            self.sources[url]
            for url in section_urls
            if url in self.sources
            and self.sources[url].web_source.credibility_score >= min_credibility
        ]

        # Yeterli kaynak yoksa, genel kaynakları ekle
        if len(direct_sources) < min_sources:
            all_sources = sorted(
                self.sources.values(),
                key=lambda x: x.web_source.credibility_score,
                reverse=True
            )

            for source in all_sources:
                if source not in direct_sources:
                    if source.web_source.credibility_score >= min_credibility:
                        direct_sources.append(source)
                        if len(direct_sources) >= min_sources:
                            break

        return direct_sources[:min_sources * 2]

    def get_statistics_sources(self) -> List[CollectedSource]:
        """İstatistik içeren kaynakları getir."""
        stat_sources = []

        for collected in self.sources.values():
            source = collected.web_source
            text = f"{source.title} {source.snippet} {source.content or ''}"

            # İstatistik pattern'leri
            has_numbers = bool(re.search(r'\d+[.,]?\d*\s*(milyon|milyar|%|TL|USD)', text, re.IGNORECASE))
            has_stats_keywords = any(kw in text.lower() for kw in [
                "istatistik", "veri", "rakam", "oran", "rapor", "araştırma"
            ])

            if has_numbers or has_stats_keywords:
                stat_sources.append(collected)

        # Güvenilirliğe göre sırala
        stat_sources.sort(
            key=lambda x: x.web_source.credibility_score,
            reverse=True
        )

        return stat_sources

    def get_verified_sources(self) -> List[CollectedSource]:
        """Doğrulanmış kaynakları getir."""
        return [
            s for s in self.sources.values()
            if s.verification_status == "verified"
        ]

    def get_high_credibility_sources(
        self,
        min_score: float = 0.8
    ) -> List[CollectedSource]:
        """Yüksek güvenilirlikli kaynakları getir."""
        return sorted(
            [s for s in self.sources.values()
             if s.web_source.credibility_score >= min_score],
            key=lambda x: x.web_source.credibility_score,
            reverse=True
        )

    def verify_source(self, url: str) -> bool:
        """
        Bir kaynağı doğrula.

        Aynı bilgiyi içeren başka kaynaklar varsa doğrulanmış kabul et.
        """
        if url not in self.sources:
            return False

        source = self.sources[url]
        source_text = f"{source.web_source.title} {source.web_source.snippet}".lower()

        # Anahtar kelimeleri çıkar
        words = set(re.findall(r'\b[a-zA-ZğüşöçıİĞÜŞÖÇ]{4,}\b', source_text))

        # Diğer kaynaklarda eşleşme ara
        corroborating = []
        for other_url, other_source in self.sources.items():
            if other_url == url:
                continue

            other_text = f"{other_source.web_source.title} {other_source.web_source.snippet}".lower()
            other_words = set(re.findall(r'\b[a-zA-ZğüşöçıİĞÜŞÖÇ]{4,}\b', other_text))

            # Kelime örtüşmesi
            overlap = len(words & other_words)
            if overlap >= 3:
                corroborating.append(other_url)

        source.corroborating_sources = corroborating

        if len(corroborating) >= 2:
            source.verification_status = "verified"
            return True

        return False

    def verify_all_sources(self) -> int:
        """Tüm kaynakları doğrula ve doğrulanan sayısını döndür."""
        verified_count = 0
        for url in self.sources:
            if self.verify_source(url):
                verified_count += 1
        return verified_count

    def extract_data_from_source(self, url: str) -> Dict[str, Any]:
        """Kaynaktan yapılandırılmış veri çıkar."""
        if url not in self.sources:
            return {}

        source = self.sources[url]
        text = f"{source.web_source.snippet} {source.web_source.content or ''}"

        extracted = {
            "numbers": [],
            "percentages": [],
            "currencies": [],
            "dates": [],
            "entities": []
        }

        # Sayılar
        for match in re.finditer(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s*(milyon|milyar|trilyon)?', text, re.IGNORECASE):
            extracted["numbers"].append({
                "value": match.group(1),
                "unit": match.group(2) or "",
                "context": text[max(0, match.start()-30):min(len(text), match.end()+30)]
            })

        # Yüzdeler
        for match in re.finditer(r'%\s*(\d+[.,]?\d*)|(\d+[.,]?\d*)\s*%', text):
            pct = match.group(1) or match.group(2)
            extracted["percentages"].append({
                "value": pct,
                "context": text[max(0, match.start()-30):min(len(text), match.end()+30)]
            })

        # Para birimleri
        for match in re.finditer(r'(\d+[.,]?\d*)\s*(TL|USD|EUR|dolar|euro|₺|\$|€)', text, re.IGNORECASE):
            extracted["currencies"].append({
                "value": match.group(1),
                "currency": match.group(2),
                "context": text[max(0, match.start()-30):min(len(text), match.end()+30)]
            })

        # Tarihler
        for match in re.finditer(r'(20\d{2}|19\d{2})', text):
            extracted["dates"].append(match.group(1))

        source.extracted_data = extracted
        return extracted

    def export_bibliography(self, style: str = "apa") -> str:
        """Tüm kaynakları bibliyografya formatında dışa aktar."""
        lines = []

        sorted_sources = sorted(
            self.sources.values(),
            key=lambda x: x.web_source.title.lower()
        )

        for i, collected in enumerate(sorted_sources, 1):
            source = collected.web_source

            if style == "apa":
                # APA formatı: Yazar. (Tarih). Başlık. URL
                entry = f"[{i}] {source.title}. "
                if source.published_date:
                    entry += f"({source.published_date}). "
                else:
                    entry += f"(Erişim: {source.accessed_date}). "
                entry += f"{source.domain}. {source.url}"

            elif style == "numeric":
                entry = f"[{i}] {source.title}. {source.url}"

            else:  # harvard
                entry = f"{source.domain} ({source.accessed_date}) '{source.title}', Available at: {source.url}"

            lines.append(entry)

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """Kaynak koleksiyonunun özetini getir."""
        return {
            "total_sources": len(self.sources),
            "verified_sources": len([s for s in self.sources.values() if s.verification_status == "verified"]),
            "high_credibility_sources": len([s for s in self.sources.values() if s.web_source.credibility_score >= 0.8]),
            "queries_performed": len(self.queries_performed),
            "sections_covered": list(self.section_sources.keys()),
            "sources_per_section": {
                k: len(v) for k, v in self.section_sources.items()
            }
        }

    def clear(self):
        """Tüm kaynakları temizle."""
        self.sources.clear()
        self.queries_performed.clear()
        self.section_sources.clear()
