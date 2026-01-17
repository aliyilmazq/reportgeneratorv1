"""
Section Generator Module - Generates rich section content

Bu modül her rapor bölümü için zengin, paragraf tabanlı içerik üretir.
- Minimum 500-1000 kelime
- Kaynak referansları
- Profesyonel dil
"""

from dataclasses import dataclass, field
from typing import (
    List, Dict, Optional, Any, Callable, Union,
    ClassVar, Tuple, Sequence
)
from datetime import datetime
import re
import time
import logging

from anthropic import Anthropic

from .content_planner import SectionPlan
from ..research.citation_manager import CitationManager
from ..research.web_researcher import WebSource
from ..research.source_collector import CollectedSource

# Type imports
try:
    from ..types import (
        ProgressCallback, TableDict, MetadataDict, QualityLevel,
        get_quality_level
    )
except ImportError:
    # Fallback types
    ProgressCallback = Callable[[str, float, str], None]
    TableDict = Dict[str, Any]
    MetadataDict = Dict[str, Any]
    QualityLevel = str
    def get_quality_level(score: float) -> str:
        if score >= 0.9: return "excellent"
        elif score >= 0.7: return "high"
        elif score >= 0.5: return "medium"
        return "low"

logger = logging.getLogger(__name__)


@dataclass
class GeneratedSection:
    """Üretilmiş bölüm."""
    section_id: str
    title: str
    content: str
    level: int
    word_count: int
    paragraph_count: int
    citations_used: List[str]
    data_points_used: List[str]
    tables: List[TableDict]
    quality_score: float
    generation_time_seconds: float
    subsections: List["GeneratedSection"] = field(default_factory=list)
    metadata: MetadataDict = field(default_factory=dict)

    @property
    def quality_level(self) -> QualityLevel:
        """Kalite seviyesi."""
        return get_quality_level(self.quality_score)

    @property
    def is_valid(self) -> bool:
        """Gecerlilik kontrolu."""
        return self.word_count > 0 and self.quality_score >= 0.5

    def get_plain_text(self) -> str:
        """Duz metin olarak icerik."""
        # Markdown isarelerini temizle
        text = re.sub(r'#+ ', '', self.content)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\[(\d+)\]', '', text)
        return text.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "content": self.content,
            "level": self.level,
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "citations_used": self.citations_used,
            "data_points_used": self.data_points_used,
            "tables": self.tables,
            "quality_score": self.quality_score,
            "quality_level": str(self.quality_level),
            "generation_time_seconds": self.generation_time_seconds,
            "subsections": [s.to_dict() for s in self.subsections],
            "metadata": self.metadata
        }


class SectionGenerator:
    """
    Bölüm içeriği üretici.

    Her bölüm için:
    - Zengin paragraf içeriği (500-1000+ kelime)
    - Kaynak referansları ([1], [2], vb.)
    - Profesyonel iş dili
    - Tablo ve grafik önerileri
    """

    # Bölüm bazlı içerik şablonları
    SECTION_PROMPTS: ClassVar[Dict[str, str]] = {
        "yonetici_ozeti": """
Bu bölüm, raporun en kritik özet bölümüdür. Yöneticiler için hazırlanmış,
kısa ve öz ama bilgi dolu bir özet yazın.

İçerik yapısı:
1. İş modelinin özeti (1 paragraf)
2. Hedef pazar ve potansiyel (1 paragraf)
3. Rekabet avantajları (1 paragraf)
4. Finansal hedefler ve beklentiler (1 paragraf)
5. Kritik başarı faktörleri (1 paragraf)
""",

        "pazar_analizi": """
Bu bölüm, hedef pazarın kapsamlı analizini içermelidir.

İçerik yapısı:
1. Pazar tanımı ve büyüklüğü (sayısal verilerle)
2. Pazar segmentasyonu
3. Büyüme trendleri ve projeksiyonlar
4. Sektör dinamikleri ve itici güçler
5. Fırsatlar ve tehditler
6. Hedef müşteri profili

Her istatistik için kaynak referansı ekleyin.
""",

        "rekabet_analizi": """
Bu bölüm, rekabet ortamının detaylı analizini sunmalıdır.

İçerik yapısı:
1. Rekabet ortamına genel bakış
2. Başlıca rakiplerin analizi (tablo formatında)
3. Pazar payı dağılımı
4. Rakiplerin güçlü ve zayıf yönleri
5. Rekabet avantajlarımız
6. Farklılaşma stratejisi
""",

        "finansal_projeksiyonlar": """
Bu bölüm, finansal tahmin ve analizleri içermelidir.

İçerik yapısı:
1. Gelir modeli ve tahminleri
2. Maliyet yapısı analizi
3. Karlılık projeksiyonları
4. Nakit akış analizi
5. Yatırım gereksinimleri
6. Başabaş analizi
7. Finansal varsayımlar

Sayısal verileri tablo formatında sunun.
""",

        "risk_analizi": """
Bu bölüm, potansiyel riskleri ve yönetim stratejilerini açıklamalıdır.

İçerik yapısı:
1. Risk kategorileri (operasyonel, finansal, pazar, yasal)
2. Her kategori için başlıca riskler
3. Risk değerlendirme matrisi
4. Risk azaltma stratejileri
5. Acil durum planları
6. İzleme ve kontrol mekanizmaları
"""
    }

    def __init__(
        self,
        anthropic_client: Anthropic,
        citation_manager: CitationManager,
        language: str = "tr",
        rules_prompt: str = "",
        min_words: int = 500,
        min_paragraphs: int = 3,
        min_sources: int = 2,
        model: str = "claude-opus-4-5-20250514"
    ) -> None:
        self.client: Anthropic = anthropic_client
        self.citation_manager: CitationManager = citation_manager
        self.language: str = language
        self.current_date: str = datetime.now().strftime("%Y-%m-%d")
        self.current_year: int = datetime.now().year
        self.model: str = model

        # Kurallar
        self.rules_prompt: str = rules_prompt
        self.min_words: int = min_words
        self.min_paragraphs: int = min_paragraphs
        self.min_sources: int = min_sources

    def generate_section(
        self,
        section_plan: SectionPlan,
        sources: List[CollectedSource],
        data_points: Dict[str, Any],
        rag_context: str = "",
        file_content: str = "",
        progress_callback: Optional[ProgressCallback] = None
    ) -> GeneratedSection:
        """
        Tek bir bölüm için zengin içerik üret.

        Args:
            section_plan: Bölüm planı
            sources: İlgili kaynaklar
            data_points: Veri noktaları
            rag_context: RAG'dan gelen bağlam
            file_content: Kullanıcı dosyalarından içerik
            progress_callback: İlerleme callback'i

        Returns:
            GeneratedSection: Üretilen bölüm
        """
        start_time = time.time()

        if progress_callback:
            progress_callback(
                phase="section_generation",
                progress=0,
                detail=f"Üretiliyor: {section_plan.title}"
            )

        # Prompt'u oluştur
        prompt = self._build_section_prompt(
            section_plan,
            sources,
            data_points,
            rag_context,
            file_content
        )

        # Claude'dan içerik üret
        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

        except Exception as e:
            print(f"Claude API hatası: {e}")
            content = self._generate_fallback_content(section_plan)

        # İçeriği zenginleştir
        content = self._enrich_content(content, sources, section_plan)

        # Minimum kelime kontrolü
        word_count = len(content.split())
        if word_count < section_plan.min_words:
            content = self._expand_content(content, section_plan, sources)
            word_count = len(content.split())

        # Tabloları çıkar
        tables = self._extract_tables(content)

        # Paragraf sayısı
        paragraphs = [p for p in content.split("\n\n") if p.strip() and len(p) > 50]
        paragraph_count = len(paragraphs)

        # Kalite puanı hesapla
        quality_score = self._calculate_quality_score(
            content,
            section_plan,
            sources
        )

        duration = time.time() - start_time

        return GeneratedSection(
            section_id=section_plan.section_id,
            title=section_plan.title,
            content=content,
            level=section_plan.level,
            word_count=word_count,
            paragraph_count=paragraph_count,
            citations_used=[s.web_source.url if hasattr(s, 'web_source') else s.url for s in sources[:5]],
            data_points_used=list(data_points.keys())[:10],
            tables=tables,
            quality_score=quality_score,
            generation_time_seconds=duration
        )

    def _build_section_prompt(
        self,
        section_plan: SectionPlan,
        sources: List[CollectedSource],
        data_points: Dict[str, Any],
        rag_context: str,
        file_content: str
    ) -> str:
        """Bölüm için detaylı prompt oluştur."""

        # Kaynak metinlerini hazırla
        source_texts = []
        for i, source in enumerate(sources[:8], 1):
            if hasattr(source, 'web_source'):
                ws = source.web_source
                text = f"[{i}] {ws.title}\n"
                text += f"    URL: {ws.url}\n"
                text += f"    İçerik: {ws.snippet[:500]}"
                if ws.content:
                    text += f"\n    Detay: {ws.content[:800]}"
            elif hasattr(source, 'title'):
                text = f"[{i}] {source.title}\n"
                text += f"    URL: {source.url}\n"
                text += f"    İçerik: {getattr(source, 'snippet', '')[:500]}"
            else:
                continue
            source_texts.append(text)

        sources_section = "\n\n".join(source_texts) if source_texts else "Kaynak bulunamadı."

        # Veri noktalarını hazırla
        data_section = ""
        if data_points:
            data_lines = []
            for key, value in data_points.items():
                if hasattr(value, 'to_dict'):
                    v = value.to_dict()
                    data_lines.append(f"- {key}: {v.get('value_formatted', v.get('value', 'N/A'))} ({v.get('source', 'N/A')})")
                elif isinstance(value, dict):
                    data_lines.append(f"- {key}: {value.get('value', value)}")
                else:
                    data_lines.append(f"- {key}: {value}")
            data_section = "\n".join(data_lines)

        # Özel bölüm yönergesi
        section_guidance = self.SECTION_PROMPTS.get(
            section_plan.section_id,
            f"Bu bölüm {section_plan.title} konusunu kapsamlı şekilde ele almalıdır."
        )

        # Anahtar noktalar
        key_points_text = "\n".join([f"- {kp}" for kp in section_plan.key_points])

        # Kural bazlı minimum değerleri kullan
        effective_min_words = max(section_plan.min_words, self.min_words)
        effective_min_paragraphs = max(section_plan.paragraph_count, self.min_paragraphs)

        prompt = f"""Sen profesyonel bir iş analisti ve rapor yazarısın. Aşağıdaki bölüm için
yüksek kaliteli, detaylı ve profesyonel içerik üret.

{self.rules_prompt if self.rules_prompt else ""}

## BÖLÜM BİLGİLERİ
Başlık: {section_plan.title}
Hedef Kelime Sayısı: {section_plan.target_words} (minimum {effective_min_words})
Paragraf Sayısı: En az {effective_min_paragraphs}
Minimum Kaynak Referansı: {self.min_sources}
Tablo Gerekli: {"Evet" if section_plan.include_table else "Hayır"}

## BÖLÜM YÖNERGESİ
{section_guidance}

## ANAHTAR NOKTALAR (mutlaka ele alınacak)
{key_points_text}

## KAYNAKLAR (referans olarak kullan, [1], [2] şeklinde atıf yap)
{sources_section}

## VERİLER (doğru şekilde kullan)
{data_section if data_section else "Spesifik veri yok, kaynaklardan yararlan."}

## DOSYA İÇERİĞİ (varsa kullan)
{file_content[:2000] if file_content else "Kullanıcı dosyası yok."}

## RAG BAĞLAMI
{rag_context[:1500] if rag_context else "Ek bağlam yok."}

## YAZIM KURALLARI (ZORUNLU)
1. Profesyonel, resmi iş dili kullan
2. Her iddia için kaynak referansı ekle: [1], [2] vb.
3. Somut veriler ve istatistikler kullan
4. Paragraflar akıcı ve bağlantılı olsun
5. Madde işaretlerini minimum tut, PARAGRAF YAZIMINI tercih et
6. Tablolar için markdown formatı kullan
7. Teknik terimleri açıkla
8. Türkçe dil kurallarına uy
9. Tarih: {self.current_date}, Yıl: {self.current_year}

## KRİTİK KURALLAR
- MINIMUM {effective_min_words} kelime yaz - bu ZORUNLUDUR
- MINIMUM {effective_min_paragraphs} paragraf yaz - bu ZORUNLUDUR
- MINIMUM {self.min_sources} kaynak referansı kullan - bu ZORUNLUDUR
- Sadece kaynaklarda bulunan verileri kullan, UYDURMAK YASAKTIR
- Her veri için kaynak referansı ver
- Belirsiz ifadeler kullanma ("araştırmalar gösteriyor", "uzmanlar belirtiyor" gibi)
- İçerik bilgilendirici ve değer katıcı olsun

Şimdi "{section_plan.title}" bölümünü yaz:"""

        return prompt

    def _enrich_content(
        self,
        content: str,
        sources: List[CollectedSource],
        section_plan: SectionPlan
    ) -> str:
        """İçeriği kaynak referanslarıyla zenginleştir."""

        # Mevcut referansları kontrol et
        existing_refs = set(re.findall(r'\[(\d+)\]', content))

        # Referans yoksa ekle
        if not existing_refs and sources:
            paragraphs = content.split("\n\n")
            enriched = []

            for i, para in enumerate(paragraphs):
                if len(para) > 100 and i < len(sources):
                    # Paragrafın sonuna referans ekle
                    source = sources[i]
                    if hasattr(source, 'web_source'):
                        marker = self.citation_manager.add_citation(
                            source.web_source,
                            para[:100],
                            section_plan.section_id
                        )
                    para = para.rstrip() + f" {marker}"
                enriched.append(para)

            content = "\n\n".join(enriched)

        return content

    def _expand_content(
        self,
        content: str,
        section_plan: SectionPlan,
        sources: List[CollectedSource]
    ) -> str:
        """Yetersiz içeriği genişlet."""
        current_words = len(content.split())
        needed_words = section_plan.min_words - current_words

        if needed_words <= 0:
            return content

        # Ek içerik için prompt
        expansion_prompt = f"""Aşağıdaki içerik yetersiz. {needed_words} kelime daha ekleyerek zenginleştir.

MEVCUT İÇERİK:
{content}

BÖLÜM: {section_plan.title}
ANAHTAR NOKTALAR: {', '.join(section_plan.key_points)}

Ek paragraflar yazarak içeriği genişlet. Mevcut içerikle tutarlı ol."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": expansion_prompt}]
            )

            expansion = response.content[0].text

            # Genişletmeyi ekle
            content = content + "\n\n" + expansion

        except Exception as e:
            print(f"İçerik genişletme hatası: {e}")

        return content

    def _generate_fallback_content(self, section_plan: SectionPlan) -> str:
        """API hatası durumunda yedek içerik üret."""
        return f"""## {section_plan.title}

Bu bölüm {section_plan.title.lower()} konusunu ele almaktadır.

{chr(10).join(['- ' + kp for kp in section_plan.key_points])}

Detaylı analiz için ek araştırma gerekmektedir.
"""

    def _extract_tables(self, content: str) -> List[TableDict]:
        """İçerikten tabloları çıkar."""
        tables = []

        # Markdown tablo pattern'i
        table_pattern = r'\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)+'
        matches = re.findall(table_pattern, content)

        for i, match in enumerate(matches):
            lines = match.strip().split("\n")
            if len(lines) >= 3:
                # Header
                headers = [h.strip() for h in lines[0].split("|") if h.strip()]

                # Data rows
                data = []
                for line in lines[2:]:
                    row = [c.strip() for c in line.split("|") if c.strip()]
                    if row:
                        data.append(row)

                tables.append({
                    "index": i,
                    "headers": headers,
                    "data": data,
                    "raw": match
                })

        return tables

    def _calculate_quality_score(
        self,
        content: str,
        section_plan: SectionPlan,
        sources: List[CollectedSource]
    ) -> float:
        """İçerik kalite puanını hesapla (0-1)."""
        score = 0.0

        # Kelime sayısı (0-0.3)
        word_count = len(content.split())
        if word_count >= section_plan.target_words:
            score += 0.3
        elif word_count >= section_plan.min_words:
            score += 0.2
        else:
            score += 0.1 * (word_count / section_plan.min_words)

        # Paragraf sayısı (0-0.2)
        paragraphs = [p for p in content.split("\n\n") if len(p) > 50]
        if len(paragraphs) >= section_plan.paragraph_count:
            score += 0.2
        else:
            score += 0.1 * (len(paragraphs) / section_plan.paragraph_count)

        # Referans kullanımı (0-0.2)
        refs = set(re.findall(r'\[(\d+)\]', content))
        if len(refs) >= 3:
            score += 0.2
        elif len(refs) >= 1:
            score += 0.1

        # Tablo/liste varlığı (0-0.15)
        has_table = "|" in content and "---" in content
        has_list = bool(re.search(r'^\s*[-•*]\s+', content, re.MULTILINE))
        if has_table:
            score += 0.1
        if has_list:
            score += 0.05

        # İçerik çeşitliliği (0-0.15)
        has_numbers = bool(re.search(r'\d+', content))
        has_percentage = bool(re.search(r'%\d+|\d+%', content))
        if has_numbers:
            score += 0.075
        if has_percentage:
            score += 0.075

        return min(score, 1.0)

    def generate_all_sections(
        self,
        section_plans: List[SectionPlan],
        source_collector: Any,  # SourceCollector type
        data_points: Dict[str, Any],
        rag_context: str = "",
        file_contents: Optional[Dict[str, str]] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[GeneratedSection]:
        """Tüm bölümleri üret."""
        sections = []
        total = len(section_plans)

        for i, plan in enumerate(section_plans):
            if progress_callback:
                progress_callback(
                    phase="section_generation",
                    progress=(i / total) * 100,
                    detail=f"Bölüm {i+1}/{total}: {plan.title}"
                )

            # Bölüm için kaynakları al
            sources = source_collector.get_sources_for_section(plan.section_id) if source_collector else []

            # Dosya içeriği
            file_content = file_contents.get(plan.section_id, "") if file_contents else ""

            section = self.generate_section(
                section_plan=plan,
                sources=sources,
                data_points=data_points,
                rag_context=rag_context,
                file_content=file_content
            )

            sections.append(section)

            # Rate limiting
            time.sleep(1)

        return sections
