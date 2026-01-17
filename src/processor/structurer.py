"""Rapor yapılandırıcı modülü - Claude ile içeriği yapılandırır."""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:
    import anthropic
except ImportError:
    anthropic = None

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Security: Text validation for prompt injection prevention
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from utils.validators import TextValidator
    from utils.exceptions import PromptInjectionError
    from utils.retry_helper import retry_with_backoff, retry_api_call
    HAS_RETRY = True
except ImportError:
    TextValidator = None
    PromptInjectionError = Exception
    HAS_RETRY = False

logger = logging.getLogger(__name__)

# Researcher modülünü import et
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from src.researcher import WebResearcher, ResearchResult
except ImportError:
    WebResearcher = None
    ResearchResult = None

console = Console()


@dataclass
class ReportSection:
    """Rapor bölümü."""
    id: str
    title: str
    content: str
    level: int = 1
    subsections: List['ReportSection'] = field(default_factory=list)


@dataclass
class StructuredReport:
    """Yapılandırılmış rapor."""
    title: str
    report_type: str
    language: str
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportStructurer:
    """Rapor yapılandırıcı sınıfı - Claude API kullanır."""

    def __init__(self, api_key: Optional[str] = None, config_dir: str = None, demo_mode: bool = False):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.client = None
        self.demo_mode = demo_mode or (not self.api_key)
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self.templates_dir = Path(__file__).parent.parent.parent / "templates" / "structures"

        if self.demo_mode:
            console.print("[yellow]Demo modu aktif - API anahtarı olmadan örnek içerik üretiliyor[/yellow]")

        if anthropic is not None and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

        # Kuralları yükle
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        """Kuralları yükle."""
        rules_path = Path(self.config_dir) / "rules.yaml"
        if rules_path.exists():
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def _load_structure(self, report_type: str) -> Dict[str, Any]:
        """Rapor yapısını yükle."""
        structure_path = self.templates_dir / f"{report_type}.yaml"
        if structure_path.exists():
            with open(structure_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

        # Varsayılan yapı
        return {
            "sections": [
                {"id": "kapak", "title": "Kapak", "required": True},
                {"id": "ozet", "title": "Özet", "required": True},
                {"id": "icerik", "title": "İçerik", "required": True},
                {"id": "sonuc", "title": "Sonuç", "required": True}
            ]
        }

    def _get_language_rules(self, language: str) -> str:
        """Dil kurallarını metin olarak al."""
        lang_rules = self.rules.get('language_rules', {}).get(
            'turkish' if language == 'tr' else 'english', {}
        )

        rules_text = []

        if 'spelling' in lang_rules:
            rules_text.append("İmla Kuralları:")
            for rule in lang_rules['spelling']:
                rules_text.append(f"  - {rule}")

        if 'tone' in lang_rules:
            rules_text.append("\nTon ve Üslup:")
            for rule in lang_rules['tone']:
                rules_text.append(f"  - {rule}")

        return "\n".join(rules_text)

    def _get_format_rules(self) -> str:
        """Format kurallarını metin olarak al."""
        fmt_rules = self.rules.get('format_rules', {})
        rules_text = []

        if 'headings' in fmt_rules:
            rules_text.append("Başlık Formatı:")
            rules_text.append(f"  - Numaralandırma: {fmt_rules['headings'].get('format', '1.1.1')}")
            rules_text.append(f"  - Maksimum derinlik: {fmt_rules['headings'].get('max_depth', 3)}")

        if 'numbers' in fmt_rules:
            num_rules = fmt_rules['numbers'].get('tr', fmt_rules['numbers'])
            rules_text.append("\nSayı Formatı:")
            rules_text.append(f"  - Ondalık ayırıcı: {num_rules.get('decimal_separator', ',')}")
            rules_text.append(f"  - Binlik ayırıcı: {num_rules.get('thousand_separator', '.')}")

        return "\n".join(rules_text)

    def structure(
        self,
        aggregated_content: 'AggregatedContent',
        report_type: str,
        language: str,
        special_notes: str = "",
        show_progress: bool = True,
        research_data: Optional['ResearchResult'] = None
    ) -> StructuredReport:
        """İçeriği yapılandırılmış rapora dönüştür."""

        if not self.client and not self.demo_mode:
            raise ValueError("Anthropic API anahtarı gerekli. ANTHROPIC_API_KEY ortam değişkenini ayarlayın.")

        # Araştırma verilerini sakla
        self.research_data = research_data

        # Rapor yapısını yükle
        structure = self._load_structure(report_type)

        # Dil ve format kuralları
        lang_rules = self._get_language_rules(language)
        fmt_rules = self._get_format_rules()

        # Rapor türü başlıkları
        type_titles = {
            "is_plani": "İş Planı",
            "proje_raporu": "Proje Raporu",
            "sunum": "Sunum",
            "on_fizibilite": "Ön Fizibilite Raporu",
            "teknik_dok": "Teknik Dokümantasyon",
            "analiz_raporu": "Analiz Raporu",
            "kisa_not": "Kısa Not"
        }

        report = StructuredReport(
            title=type_titles.get(report_type, "Rapor"),
            report_type=report_type,
            language=language
        )

        # Her bölüm için içerik oluştur
        sections_to_generate = structure.get('sections', [])

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Rapor yapılandırılıyor...", total=len(sections_to_generate))

                for section_config in sections_to_generate:
                    section_id = section_config.get('id', '')
                    section_title = section_config.get('title', '')

                    progress.update(task, description=f"Oluşturuluyor: {section_title}...")

                    section = self._generate_section(
                        section_id=section_id,
                        section_title=section_title,
                        section_config=section_config,
                        aggregated_content=aggregated_content,
                        language=language,
                        lang_rules=lang_rules,
                        fmt_rules=fmt_rules,
                        special_notes=special_notes,
                        report_type=report_type
                    )

                    report.sections.append(section)
                    progress.advance(task)
        else:
            for section_config in sections_to_generate:
                section_id = section_config.get('id', '')
                section_title = section_config.get('title', '')

                section = self._generate_section(
                    section_id=section_id,
                    section_title=section_title,
                    section_config=section_config,
                    aggregated_content=aggregated_content,
                    language=language,
                    lang_rules=lang_rules,
                    fmt_rules=fmt_rules,
                    special_notes=special_notes,
                    report_type=report_type
                )

                report.sections.append(section)

        return report

    def _generate_section(
        self,
        section_id: str,
        section_title: str,
        section_config: Dict[str, Any],
        aggregated_content: 'AggregatedContent',
        language: str,
        lang_rules: str,
        fmt_rules: str,
        special_notes: str,
        report_type: str
    ) -> ReportSection:
        """Tek bir bölümü oluştur."""

        # Demo modda örnek içerik döndür
        if self.demo_mode:
            return self._generate_demo_section(section_id, section_title, section_config, aggregated_content, language)

        # İçerik özetini hazırla
        content_summary = self._prepare_content_summary(aggregated_content, section_id)

        # Araştırma verilerini hazırla
        research_summary = self._prepare_research_summary(section_id)

        # Prompt oluştur
        prompt = self._create_section_prompt(
            section_id=section_id,
            section_title=section_title,
            section_config=section_config,
            content_summary=content_summary,
            research_summary=research_summary,
            language=language,
            lang_rules=lang_rules,
            fmt_rules=fmt_rules,
            special_notes=special_notes,
            report_type=report_type
        )

        # Claude'dan içerik al - retry logic ile
        try:
            if HAS_RETRY:
                # Retry ile API cagir
                response = retry_api_call(
                    self.client.messages.create,
                    model="claude-opus-4-5-20250514",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}],
                    max_attempts=3
                )
            else:
                # Fallback: retry olmadan
                response = self.client.messages.create(
                    model="claude-opus-4-5-20250514",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}]
                )

            content = response.content[0].text

        except Exception as e:
            logger.error(f"Claude API hatasi: {e}")
            content = f"[Bu bölüm oluşturulurken hata oluştu: {str(e)}]"

        return ReportSection(
            id=section_id,
            title=section_title,
            content=content,
            level=section_config.get('level', 1)
        )

    def _sanitize_content_for_prompt(self, text: str, max_length: int = 10000) -> str:
        """Prompt icin icerigi guvenli hale getir."""
        if not text:
            return ""

        # TextValidator varsa kullan
        if TextValidator:
            # Prompt injection kontrolu
            if TextValidator.check_prompt_injection(text):
                logger.warning("Potential prompt injection detected in content, sanitizing...")
                text = TextValidator.sanitize(text, max_length=max_length, strip_html=True)
            else:
                text = TextValidator.sanitize(text, max_length=max_length)
        else:
            # Fallback: basit sanitization
            text = text[:max_length]

        return text

    def _prepare_content_summary(self, aggregated_content: 'AggregatedContent', section_id: str) -> str:
        """Bölüm için içerik özetini hazırla."""
        summary_parts = []

        # Metin içeriği (ilk 10000 karakter) - sanitized
        if aggregated_content.all_text:
            text_preview = self._sanitize_content_for_prompt(aggregated_content.all_text, 10000)
            if len(aggregated_content.all_text) > 10000:
                text_preview += "\n\n[... devamı kısaltıldı ...]"
            summary_parts.append(f"=== METİN İÇERİĞİ ===\n{text_preview}")

        # Tablo özeti (ilk 5 tablo)
        if aggregated_content.all_tables:
            tables_preview = []
            for i, table in enumerate(aggregated_content.all_tables[:5]):
                table_text = f"Tablo {i+1} (Kaynak: {table.get('source', 'Bilinmiyor')}):\n"
                table_text += f"  Başlıklar: {', '.join(table.get('headers', []))}\n"
                table_text += f"  Satır sayısı: {len(table.get('data', []))}"
                tables_preview.append(table_text)

            summary_parts.append(f"=== TABLOLAR ({len(aggregated_content.all_tables)} adet) ===\n" + "\n".join(tables_preview))

        # Görsel özeti
        if aggregated_content.image_contents:
            images_preview = []
            for img in aggregated_content.image_contents[:5]:
                img_text = f"- {img.get('filename', 'Görsel')}: {img.get('description', '')[:100]}"
                images_preview.append(img_text)

            summary_parts.append(f"=== GÖRSELLER ({len(aggregated_content.image_contents)} adet) ===\n" + "\n".join(images_preview))

        return "\n\n".join(summary_parts)

    def _prepare_research_summary(self, section_id: str) -> str:
        """Bölüm için araştırma verilerini hazırla."""
        if not hasattr(self, 'research_data') or not self.research_data:
            return ""

        research = self.research_data
        summary_parts = []

        # Bölüme göre ilgili araştırma verilerini seç
        section_research_mapping = {
            'yonetici_ozeti': ['web', 'statistics'],
            'sirket_tanimi': ['web'],
            'pazar_analizi': ['web', 'market', 'statistics'],
            'pazarlama_stratejisi': ['market', 'statistics'],
            'finansal_projeksiyonlar': ['market', 'statistics'],
            'risk_analizi': ['web', 'market'],
            'operasyon_plani': ['web'],
            'yonetim_ekibi': [],
            'ekler': ['academic', 'statistics'],
            'sonuc': ['web', 'market'],
            'oneriler': ['web', 'market', 'academic']
        }

        relevant_types = section_research_mapping.get(section_id, ['web', 'market'])

        # Web araştırması
        if 'web' in relevant_types and research.web_findings:
            for item in research.web_findings[:1]:  # İlk sonuç
                if item.get('content') and item.get('type') != 'error':
                    content = item['content'][:8000]  # İlk 8000 karakter
                    summary_parts.append(f"=== SEKTÖR ARAŞTIRMASI ===\n{content}")

        # Pazar verileri
        if 'market' in relevant_types and research.market_data:
            for item in research.market_data[:1]:
                if item.get('content') and item.get('type') != 'error':
                    content = item['content'][:8000]
                    summary_parts.append(f"=== PAZAR ANALİZİ ===\n{content}")

        # Akademik kaynaklar
        if 'academic' in relevant_types and research.academic_sources:
            for item in research.academic_sources[:1]:
                if item.get('content') and item.get('type') != 'error':
                    content = item['content'][:5000]
                    summary_parts.append(f"=== AKADEMİK LİTERATÜR ===\n{content}")

        # İstatistikler
        if 'statistics' in relevant_types and research.statistics:
            for item in research.statistics[:1]:
                if item.get('content') and item.get('type') != 'error':
                    content = item['content'][:6000]
                    summary_parts.append(f"=== İSTATİSTİKLER VE VERİLER ===\n{content}")

        return "\n\n".join(summary_parts) if summary_parts else ""

    def _create_section_prompt(
        self,
        section_id: str,
        section_title: str,
        section_config: Dict[str, Any],
        content_summary: str,
        research_summary: str,
        language: str,
        lang_rules: str,
        fmt_rules: str,
        special_notes: str,
        report_type: str
    ) -> str:
        """Bölüm için prompt oluştur - Uzman seviyesi içerik."""

        lang_name = "Türkçe" if language == "tr" else "İngilizce"

        # Araştırma verisi varsa ekle
        research_section = ""
        if research_summary:
            research_section = f"""
## ARAŞTIRMA VERİLERİ (Bu verileri mutlaka kullan!)
{research_summary}

"""

        prompt = f"""Sen, 25+ yıllık deneyime sahip bir yönetim danışmanı ve stratejik planlama uzmanısın. McKinsey, BCG ve Bain gibi üst düzey danışmanlık firmalarında çalışmış, birçok şirketi halka arza hazırlamış ve yatırımcı sunumları hazırlamışsın.

## GÖREV
"{section_title}" bölümünü {lang_name} olarak, yatırımcılara ve üst düzey yöneticilere sunulacak kalitede yaz.

## KRİTİK BAŞARI FAKTÖRLERİ
Bu bölümde şunları sağlamalısın:
1. **Özgün İçgörüler**: Sadece herkesin bildiği şeyleri değil, sektör içinden birinin fark edeceği detayları yaz
2. **Veri Destekli**: Her iddiayı mümkünse somut veri, rakam veya örnekle destekle
3. **Stratejik Perspektif**: CEO/CFO gözüyle bak, operasyonel detaylara değil stratejik kararlara odaklan
4. **Türkiye Özelinde**: Global trendleri Türkiye pazarı bağlamında yorumla
5. **Aksiyon Odaklı**: Sadece analiz değil, somut öneriler ve yol haritası sun

## DİL VE ÜSLUP KURALLARI
{lang_rules}

## FORMAT KURALLARI
{fmt_rules}

## BÖLÜM GEREKSİNİMLERİ
- Bölüm: {section_title}
- Beklenen içerik: {section_config.get('description', 'Kapsamlı ve derinlemesine analiz')}
- Minimum kelime: {section_config.get('min_words', 300)}
- Maksimum kelime: {section_config.get('max_words', 2000)}
{research_section}
## KULLANICININ SAĞLADIĞI İÇERİK
{content_summary if content_summary else 'Kullanıcı içeriği mevcut değil - araştırma verilerini kullan.'}

## ÖZEL NOTLAR VE YÖNLENDİRMELER
{self._sanitize_content_for_prompt(special_notes, 2000) if special_notes else 'Özel yönlendirme yok - en kapsamlı ve profesyonel içeriği üret.'}

## YAZIM TALİMATLARI
1. Araştırma verilerindeki spesifik rakamları, istatistikleri ve bulguları mutlaka kullan
2. Tablolar ve madde işaretleri ile görsel zenginlik kat
3. "Opsiyonel", "muhtemelen", "belki" gibi zayıf ifadelerden kaçın - net ve kararlı ol
4. Her paragraf bir değer katmalı - dolgu cümle kullanma
5. Başkalarının kolayca bulamayacağı "insider" bilgiler ve değerlendirmeler ekle
6. Sadece bölüm içeriğini yaz, bölüm başlığını ekleme

Şimdi "{section_title}" bölümünü uzman kalitesinde yaz:"""

        return prompt

    def _generate_demo_section(
        self,
        section_id: str,
        section_title: str,
        section_config: Dict[str, Any],
        aggregated_content: 'AggregatedContent',
        language: str
    ) -> ReportSection:
        """Demo modu için gerçek verilerden zengin içerik oluştur."""

        # Ham içeriği al
        all_text = getattr(aggregated_content, 'all_text', '') or ''
        all_tables = getattr(aggregated_content, 'all_tables', []) or []
        total_files = getattr(aggregated_content, 'total_files', 0)

        # Tablo verilerini formatla
        def format_table(table_data):
            if not table_data:
                return ""
            headers = table_data.get('headers', [])
            data = table_data.get('data', [])[:5]  # İlk 5 satır
            if not headers:
                return ""

            lines = []
            lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in data:
                lines.append("| " + " | ".join(str(c)[:20] for c in row) + " |")
            return "\n".join(lines)

        # İçerikten anahtar bilgileri çıkar
        text_excerpt = all_text[:1000] if all_text else ""

        # Tablo özeti
        table_summary = ""
        if all_tables:
            table_summary = f"\n\nAnaliz edilen veriler ({len(all_tables)} tablo):\n\n"
            for i, tbl in enumerate(all_tables[:2]):  # İlk 2 tablo
                formatted = format_table(tbl)
                if formatted:
                    source = tbl.get('source', f'Tablo {i+1}')
                    table_summary += f"**{source}**\n\n{formatted}\n\n"

        # Bölüme göre içerik
        demo_contents = {
            "yonetici_ozeti": f"""Bu iş planı, mevcut proje verilerinin kapsamlı bir analizini ve stratejik yol haritasını sunmaktadır.

## Kapsam

Toplam {total_files} kaynak doküman incelenmiş ve {len(all_tables)} veri tablosu analiz edilmiştir. Bu veriler, pazar fırsatlarını, finansal projeksiyonları ve operasyonel gereksinimleri değerlendirmek için kullanılmıştır.

## Temel Bulgular

İncelenen dokümanlardaki veriler doğrultusunda:

- Proje teknik ve finansal açıdan uygulanabilir görünmektedir
- Hedef pazarda önemli büyüme potansiyeli mevcuttur
- Risk faktörleri yönetilebilir seviyededir
- Yatırımın geri dönüş süresi makul aralıktadır

## Sonuç

Detaylı analizler, projenin başarı potansiyelinin yüksek olduğunu göstermektedir. Stratejik planlama ve doğru kaynak yönetimi ile hedeflere ulaşılması beklenmektedir.""",

            "sirket_tanimi": f"""## Kuruluş Hakkında

Şirketimiz, sektöründe yenilikçi çözümler sunan ve müşteri memnuniyetini ön planda tutan dinamik bir kuruluştur.

## Misyon

Müşterilerimize en yüksek kalitede hizmet sunarak, sektörde güvenilir bir partner olmak ve sürdürülebilir değer yaratmak.

## Vizyon

Teknoloji ve inovasyonu birleştirerek sektörde lider konuma ulaşmak, global pazarda rekabetçi ve tercih edilen bir marka olmak.

## Temel Değerler

- **Kalite**: Her projede en yüksek standartları hedeflemek
- **Güvenilirlik**: Taahhütleri zamanında ve eksiksiz yerine getirmek
- **Yenilikçilik**: Sürekli gelişim ve iyileştirme kültürü
- **Müşteri Odaklılık**: Müşteri ihtiyaçlarını öncelikli tutmak""",

            "pazar_analizi": f"""## Pazar Değerlendirmesi

Hedef sektörümüz, son yıllarda istikrarlı bir büyüme trendi göstermektedir. Dijitalleşme ve değişen tüketici davranışları, yeni fırsatlar yaratmaktadır.

## Kaynak Veriler

{text_excerpt[:500] if text_excerpt else 'Pazar verileri mevcut kaynaklardan derlenmiştir.'}{table_summary if table_summary else ''}

## Hedef Kitle

- Küçük ve orta ölçekli işletmeler
- Dijital dönüşüme açık organizasyonlar
- Yenilikçi çözümler arayan profesyoneller

## Pazar Fırsatları

1. Artan dijitalleşme talebi
2. Uzaktan çalışma modellerinin yaygınlaşması
3. Verimlilik odaklı çözümlere olan ihtiyaç
4. Rekabetçi fiyatlandırma avantajı""",

            "pazarlama_stratejisi": """## Pazarlama Yaklaşımı

Pazarlama stratejimiz, çok kanallı ve veri odaklı bir yaklaşım üzerine kurulmuştur.

## Pazarlama Kanalları

- **Dijital Pazarlama**: SEO, SEM ve sosyal medya reklamları
- **İçerik Pazarlaması**: Blog, video ve e-kitaplar
- **E-posta Pazarlaması**: Segmentasyona dayalı kampanyalar
- **Stratejik Ortaklıklar**: İş birliği ve affiliate programları

## Fiyatlandırma Stratejisi

| Paket | Özellikler | Fiyat |
| --- | --- | --- |
| Başlangıç | Temel özellikler | Ekonomik |
| Profesyonel | Gelişmiş özellikler | Orta segment |
| Kurumsal | Tam özellik seti | Premium |

## Hedefler

- İlk yıl: Marka bilinirliği oluşturma
- İkinci yıl: Pazar payı artırma
- Üçüncü yıl: Lider konuma ulaşma""",

            "finansal_projeksiyonlar": f"""## Finansal Özet

Finansal projeksiyonlar, mevcut veriler ve pazar trendleri ışığında hazırlanmıştır.
{table_summary if table_summary else ''}

## Gelir Projeksiyonu

| Dönem | Hedef Gelir | Büyüme |
| --- | --- | --- |
| 1. Yıl | Başlangıç | - |
| 2. Yıl | Büyüme | %50-70 |
| 3. Yıl | Olgunluk | %30-40 |

## Maliyet Yapısı

- Geliştirme maliyetleri: %40
- Operasyon maliyetleri: %25
- Pazarlama maliyetleri: %20
- Yönetim giderleri: %15

## Karlılık Hedefleri

- Başa baş noktası: 18-24 ay
- Pozitif nakit akışı: 2. yıl sonu
- Hedef kar marjı: %20-25 (3. yıl)""",

            "risk_analizi": """## Risk Değerlendirmesi

Proje riskleri sistematik olarak analiz edilmiş ve azaltma stratejileri belirlenmiştir.

## Risk Kategorileri

### 1. Pazar Riskleri

| Risk | Olasılık | Etki | Strateji |
| --- | --- | --- | --- |
| Rekabet artışı | Orta | Yüksek | Farklılaşma |
| Talep dalgalanması | Düşük | Orta | Esnek fiyatlama |
| Ekonomik belirsizlik | Orta | Orta | Maliyet kontrolü |

### 2. Operasyonel Riskler

- Teknik aksaklıklar → Yedekli sistemler
- İnsan kaynağı → Eğitim ve yedekleme
- Tedarik zinciri → Alternatif tedarikçiler

### 3. Finansal Riskler

- Nakit akışı yönetimi → Muhafazakar bütçeleme
- Kur riski → Hedging stratejileri
- Finansman riski → Çoklu finansman kaynakları""",

            "operasyon_plani": """## Operasyonel Strateji

Operasyon planı, verimlilik ve kalite yönetimi üzerine kurulmuştur.

## Temel Süreçler

1. **Müşteri Kazanımı**
   - Potansiyel müşteri belirleme
   - İletişim ve sunum
   - Sözleşme yönetimi

2. **Hizmet Sunumu**
   - Proje planlama
   - Uygulama ve takip
   - Kalite kontrolü

3. **Müşteri Desteği**
   - 7/24 destek hattı
   - Teknik yardım
   - Geri bildirim yönetimi

## Performans Göstergeleri

| KPI | Hedef |
| --- | --- |
| Müşteri memnuniyeti | %90+ |
| Proje zamanında teslim | %95+ |
| Destek yanıt süresi | <4 saat |""",

            "yonetim_ekibi": """## Organizasyon Yapısı

Yönetim ekibimiz, sektörde deneyimli ve kanıtlanmış profesyonellerden oluşmaktadır.

## Üst Yönetim

| Pozisyon | Sorumluluk |
| --- | --- |
| Genel Müdür | Strateji ve iş geliştirme |
| Operasyon Direktörü | Günlük operasyonlar |
| Finans Direktörü | Mali yönetim |
| Teknoloji Direktörü | Teknik altyapı |
| Pazarlama Direktörü | Marka ve satış |

## Organizasyon Şeması

- Yönetim Kurulu
  - Genel Müdür
    - Operasyon
    - Finans
    - Teknoloji
    - Pazarlama
    - İnsan Kaynakları

## İnsan Kaynakları Planı

- Mevcut kadro: Çekirdek ekip
- 1. Yıl sonu hedef: Büyüme
- 2. Yıl sonu hedef: Tam kadro"""
        }

        # Varsayılan içerik
        default_content = f"""## {section_title}

Bu bölüm, {section_title.lower()} konusundaki değerlendirmeleri içermektedir.

{text_excerpt[:300] if text_excerpt else 'Mevcut veriler analiz edilmiştir.'}{table_summary if table_summary else ''}

Detaylı bilgiler için ilgili ekler incelenebilir."""

        content = demo_contents.get(section_id, default_content)

        return ReportSection(
            id=section_id,
            title=section_title,
            content=content,
            level=section_config.get('level', 1)
        )

    def to_dict(self, report: StructuredReport) -> Dict[str, Any]:
        """StructuredReport'u sözlüğe çevir."""
        def section_to_dict(section: ReportSection) -> Dict[str, Any]:
            return {
                "id": section.id,
                "title": section.title,
                "content": section.content,
                "level": section.level,
                "subsections": [section_to_dict(s) for s in section.subsections]
            }

        return {
            "title": report.title,
            "report_type": report.report_type,
            "language": report.language,
            "sections": [section_to_dict(s) for s in report.sections],
            "metadata": report.metadata
        }
