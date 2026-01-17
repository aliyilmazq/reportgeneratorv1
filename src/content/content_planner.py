"""
Content Planner Module - Plans content structure before generation

Bu modül rapor içeriğini planlar:
- Her bölüm için hedef kelime sayısı
- Kaynak-bölüm eşleştirmesi
- Anahtar noktalar
- Paragraf yapısı
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import yaml

from anthropic import Anthropic


@dataclass
class SectionPlan:
    """Tek bir bölüm için plan."""
    section_id: str
    title: str
    level: int = 1
    required: bool = True
    min_words: int = 300
    max_words: int = 800
    target_words: int = 500
    key_points: List[str] = field(default_factory=list)
    required_data: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    subsection_ids: List[str] = field(default_factory=list)
    paragraph_count: int = 3
    include_table: bool = False
    include_chart: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "level": self.level,
            "required": self.required,
            "min_words": self.min_words,
            "max_words": self.max_words,
            "target_words": self.target_words,
            "key_points": self.key_points,
            "required_data": self.required_data,
            "source_urls": self.source_urls,
            "subsection_ids": self.subsection_ids,
            "paragraph_count": self.paragraph_count,
            "include_table": self.include_table,
            "include_chart": self.include_chart
        }


@dataclass
class ContentPlan:
    """Tüm rapor için içerik planı."""
    report_type: str
    language: str
    total_sections: int
    total_target_words: int
    section_plans: List[SectionPlan]
    source_allocation: Dict[str, List[str]]  # section_id -> [urls]
    data_requirements: Dict[str, List[str]]  # section_id -> [data types]
    special_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_type": self.report_type,
            "language": self.language,
            "total_sections": self.total_sections,
            "total_target_words": self.total_target_words,
            "section_plans": [s.to_dict() for s in self.section_plans],
            "source_allocation": self.source_allocation,
            "data_requirements": self.data_requirements,
            "special_notes": self.special_notes
        }

    def get_section_plan(self, section_id: str) -> Optional[SectionPlan]:
        """Belirli bir bölümün planını getir."""
        for plan in self.section_plans:
            if plan.section_id == section_id:
                return plan
        return None


class ContentPlanner:
    """
    İçerik planlayıcı.

    Rapor tipine göre bölümleri planlar, kaynak ve veri gereksinimlerini
    belirler, kelime hedeflerini ayarlar.
    """

    # Bölüm bazlı minimum kelime sayıları (kaliteli içerik için)
    SECTION_WORD_TARGETS = {
        "yonetici_ozeti": {"min": 300, "max": 600, "paragraphs": 3},
        "sirket_tanimi": {"min": 400, "max": 800, "paragraphs": 4},
        "pazar_analizi": {"min": 600, "max": 1200, "paragraphs": 5},
        "rekabet_analizi": {"min": 500, "max": 1000, "paragraphs": 4},
        "pazarlama_stratejisi": {"min": 500, "max": 1000, "paragraphs": 4},
        "operasyon_plani": {"min": 400, "max": 800, "paragraphs": 4},
        "yonetim_organizasyon": {"min": 300, "max": 600, "paragraphs": 3},
        "finansal_projeksiyonlar": {"min": 500, "max": 1000, "paragraphs": 4},
        "risk_analizi": {"min": 400, "max": 800, "paragraphs": 4},
        "teknik_altyapi": {"min": 400, "max": 800, "paragraphs": 4},
        "sonuc": {"min": 200, "max": 400, "paragraphs": 2},
        "ekler": {"min": 100, "max": 500, "paragraphs": 2}
    }

    # Bölüm-veri gereksinimleri
    SECTION_DATA_REQUIREMENTS = {
        "yonetici_ozeti": ["genel_ozet"],
        "pazar_analizi": ["pazar_buyuklugu", "buyume_orani", "trendler", "sektor_verileri"],
        "rekabet_analizi": ["rakipler", "pazar_paylari", "swot"],
        "finansal_projeksiyonlar": ["gelir", "gider", "kar", "yatirim", "break_even"],
        "risk_analizi": ["riskler", "firsatlar", "tehditler"]
    }

    def __init__(
        self,
        templates_path: str = None,
        anthropic_client: Optional[Anthropic] = None
    ):
        self.templates_path = templates_path or Path(__file__).parent.parent.parent / "templates" / "structures"
        self.client = anthropic_client
        self.templates: Dict[str, Any] = {}
        self._load_templates()

    def _load_templates(self):
        """YAML şablonlarını yükle."""
        templates_dir = Path(self.templates_path)
        if templates_dir.exists():
            for yaml_file in templates_dir.glob("*.yaml"):
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        template = yaml.safe_load(f)
                        if template:
                            # Dosya adından rapor tipini çıkar
                            report_type = yaml_file.stem
                            self.templates[report_type] = template
                except Exception as e:
                    print(f"Şablon yükleme hatası ({yaml_file}): {e}")

    def create_plan(
        self,
        report_type: str,
        collected_sources: List[Any],
        aggregated_content: Any,
        data_points: Dict[str, Any],
        special_notes: str = "",
        language: str = "tr"
    ) -> ContentPlan:
        """
        Rapor için içerik planı oluştur.

        Args:
            report_type: Rapor tipi (is_plani, proje_raporu, vb.)
            collected_sources: Toplanan kaynaklar
            aggregated_content: Birleştirilmiş dosya içeriği
            data_points: Toplanan veri noktaları
            special_notes: Kullanıcı notları
            language: Dil

        Returns:
            ContentPlan: Oluşturulan plan
        """
        # Şablonu yükle
        template = self.templates.get(report_type, self.templates.get("is_plani", {}))
        sections_config = template.get("sections", [])

        section_plans = []
        source_allocation = {}
        data_requirements = {}
        total_words = 0

        for section_config in sections_config:
            section_id = section_config.get("id", "")
            if not section_id:
                continue

            # Kelime hedeflerini belirle
            word_targets = self.SECTION_WORD_TARGETS.get(
                section_id,
                {"min": 300, "max": 600, "paragraphs": 3}
            )

            # Şablondaki değerleri kullan (varsa)
            min_words = section_config.get("min_words", word_targets["min"])
            max_words = section_config.get("max_words", word_targets["max"])
            target_words = (min_words + max_words) // 2

            # Kalite için minimum 300 kelime
            if min_words < 300 and section_config.get("required", True):
                min_words = 300
                target_words = max(target_words, 400)

            # Kaynak eşleştirmesi
            section_sources = self._allocate_sources_to_section(
                section_id,
                collected_sources
            )
            source_allocation[section_id] = section_sources

            # Veri gereksinimleri
            section_data = self.SECTION_DATA_REQUIREMENTS.get(section_id, [])
            data_requirements[section_id] = section_data

            # Anahtar noktaları belirle
            key_points = self._determine_key_points(
                section_id,
                section_config,
                collected_sources,
                data_points
            )

            plan = SectionPlan(
                section_id=section_id,
                title=section_config.get("title", section_id.replace("_", " ").title()),
                level=section_config.get("level", 1),
                required=section_config.get("required", True),
                min_words=min_words,
                max_words=max_words,
                target_words=target_words,
                key_points=key_points,
                required_data=section_data,
                source_urls=section_sources,
                paragraph_count=word_targets["paragraphs"],
                include_table=section_id in ["pazar_analizi", "finansal_projeksiyonlar", "rekabet_analizi"],
                include_chart=section_id in ["pazar_analizi", "finansal_projeksiyonlar"]
            )

            section_plans.append(plan)
            total_words += target_words

        return ContentPlan(
            report_type=report_type,
            language=language,
            total_sections=len(section_plans),
            total_target_words=total_words,
            section_plans=section_plans,
            source_allocation=source_allocation,
            data_requirements=data_requirements,
            special_notes=special_notes
        )

    def _allocate_sources_to_section(
        self,
        section_id: str,
        collected_sources: List[Any]
    ) -> List[str]:
        """Bölüme uygun kaynakları eşleştir."""
        # Bölüm-anahtar kelime eşleştirmesi
        section_keywords = {
            "pazar_analizi": ["pazar", "sektör", "büyüme", "trend", "endüstri"],
            "rekabet_analizi": ["rekabet", "rakip", "pazar payı", "lider"],
            "finansal_projeksiyonlar": ["finansal", "gelir", "kar", "bütçe"],
            "risk_analizi": ["risk", "fırsat", "tehdit", "SWOT"],
            "yonetici_ozeti": ["genel", "özet", "sonuç"],
            "sirket_tanimi": ["şirket", "hakkında", "vizyon", "misyon"],
            "pazarlama_stratejisi": ["pazarlama", "müşteri", "hedef", "strateji"],
            "operasyon_plani": ["operasyon", "süreç", "üretim"],
            "teknik_altyapi": ["teknik", "teknoloji", "sistem"]
        }

        keywords = section_keywords.get(section_id, [])
        matching_urls = []

        for source in collected_sources:
            # Source objesinin yapısına göre kontrol
            if hasattr(source, 'web_source'):
                title = source.web_source.title.lower()
                snippet = source.web_source.snippet.lower()
                url = source.web_source.url
            elif hasattr(source, 'title'):
                title = source.title.lower()
                snippet = getattr(source, 'snippet', '').lower()
                url = source.url
            else:
                continue

            text = f"{title} {snippet}"

            for keyword in keywords:
                if keyword.lower() in text:
                    matching_urls.append(url)
                    break

        return matching_urls[:5]  # En fazla 5 kaynak

    def _determine_key_points(
        self,
        section_id: str,
        section_config: Dict[str, Any],
        collected_sources: List[Any],
        data_points: Dict[str, Any]
    ) -> List[str]:
        """Bölüm için anahtar noktaları belirle."""
        key_points = []

        # Şablondan gelen açıklama
        description = section_config.get("description", "")
        if description:
            key_points.append(description)

        # Veri noktalarından
        if section_id == "pazar_analizi":
            if "pazar_buyuklugu" in data_points:
                key_points.append("Pazar büyüklüğü ve değerlendirmesi")
            if "buyume_orani" in data_points:
                key_points.append("Büyüme oranları ve trendler")
            key_points.extend([
                "Hedef pazar segmentleri",
                "Sektör dinamikleri",
                "Fırsatlar ve tehditler"
            ])

        elif section_id == "finansal_projeksiyonlar":
            key_points.extend([
                "Gelir tahminleri",
                "Maliyet yapısı",
                "Karlılık analizi",
                "Yatırım gereksinimleri",
                "Başabaş noktası"
            ])

        elif section_id == "rekabet_analizi":
            key_points.extend([
                "Başlıca rakipler",
                "Pazar payı dağılımı",
                "Rekabet avantajları",
                "Farklılaşma stratejisi"
            ])

        elif section_id == "risk_analizi":
            key_points.extend([
                "Operasyonel riskler",
                "Finansal riskler",
                "Pazar riskleri",
                "Risk azaltma stratejileri"
            ])

        elif section_id == "yonetici_ozeti":
            key_points.extend([
                "İş modeli özeti",
                "Hedef pazar",
                "Rekabet avantajı",
                "Finansal hedefler"
            ])

        return key_points[:6]  # En fazla 6 anahtar nokta

    def enhance_plan_with_ai(
        self,
        plan: ContentPlan,
        context: str
    ) -> ContentPlan:
        """Planı AI ile zenginleştir."""
        if not self.client:
            return plan

        # Claude'dan anahtar noktalar için öneriler al
        prompt = f"""Aşağıdaki rapor planını incele ve her bölüm için ek anahtar noktalar öner.

RAPOR TİPİ: {plan.report_type}
BAĞLAM: {context[:2000]}

BÖLÜMLER:
{chr(10).join([f"- {s.title}: {', '.join(s.key_points[:3])}" for s in plan.section_plans])}

Her bölüm için 2-3 ek anahtar nokta öner. Format:
BÖLÜM_ID: nokta1, nokta2, nokta3"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Yanıtı parse et ve plana ekle
            result = response.content[0].text
            for line in result.split("\n"):
                if ":" in line:
                    section_id, points = line.split(":", 1)
                    section_id = section_id.strip().lower().replace(" ", "_")

                    for section in plan.section_plans:
                        if section.section_id == section_id:
                            new_points = [p.strip() for p in points.split(",") if p.strip()]
                            section.key_points.extend(new_points[:3])
                            break

        except Exception as e:
            print(f"Plan zenginleştirme hatası: {e}")

        return plan

    def validate_plan(self, plan: ContentPlan) -> List[str]:
        """Planı doğrula ve uyarıları döndür."""
        warnings = []

        # Minimum toplam kelime kontrolü
        if plan.total_target_words < 2000:
            warnings.append(f"Toplam hedef kelime sayısı düşük: {plan.total_target_words}")

        # Her bölüm için kontrol
        for section in plan.section_plans:
            if section.required and section.target_words < 300:
                warnings.append(f"{section.title}: Hedef kelime sayısı düşük ({section.target_words})")

            if not section.key_points:
                warnings.append(f"{section.title}: Anahtar nokta belirlenmemiş")

            if section.section_id in ["pazar_analizi", "finansal_projeksiyonlar"]:
                if not section.source_urls:
                    warnings.append(f"{section.title}: Kaynak eşleşmesi yok")

        return warnings

    def get_section_order(self, report_type: str) -> List[str]:
        """Rapor tipi için bölüm sırasını getir."""
        template = self.templates.get(report_type, {})
        sections = template.get("sections", [])
        return [s.get("id", "") for s in sections if s.get("id")]
