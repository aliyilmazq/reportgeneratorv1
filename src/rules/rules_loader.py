"""
Kural Yükleyici Modülü

Rapor üretiminden önce tüm kural dosyalarını okur ve sistemin
bu kurallara uygun çalışmasını sağlar.
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class RuleSection:
    """Bir kural bölümü."""
    title: str
    content: str
    subsections: List['RuleSection'] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    code_blocks: List[str] = field(default_factory=list)


@dataclass
class RuleFile:
    """Bir kural dosyası."""
    filename: str
    title: str
    description: str
    sections: List[RuleSection]
    raw_content: str
    loaded_at: datetime = field(default_factory=datetime.now)


@dataclass
class LoadedRules:
    """Yüklenmiş tüm kurallar."""
    general_rules: Optional[RuleFile] = None
    research_rules: Optional[RuleFile] = None
    content_rules: Optional[RuleFile] = None
    source_rules: Optional[RuleFile] = None
    validation_rules: Optional[RuleFile] = None
    quality_standards: Optional[RuleFile] = None

    # Çıkarılan önemli değerler
    min_words_per_section: int = 500
    min_paragraphs_per_section: int = 3
    min_sources_per_section: int = 2
    min_total_sources: int = 15
    min_quality_score: int = 70
    trusted_domains: List[str] = field(default_factory=list)
    forbidden_practices: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Tüm kurallar yüklendi mi?"""
        return all([
            self.general_rules,
            self.research_rules,
            self.content_rules,
            self.source_rules,
            self.validation_rules,
            self.quality_standards
        ])

    def get_all_rules_text(self) -> str:
        """Tüm kuralları tek metin olarak döndür."""
        texts = []
        for rule in [
            self.general_rules,
            self.research_rules,
            self.content_rules,
            self.source_rules,
            self.validation_rules,
            self.quality_standards
        ]:
            if rule:
                texts.append(f"# {rule.title}\n\n{rule.raw_content}")
        return "\n\n---\n\n".join(texts)

    def get_summary(self) -> str:
        """Kuralların özetini döndür."""
        return f"""
RAPOR ÜRETİM KURALLARI ÖZETİ
============================

Minimum Gereksinimler:
- Bölüm başına minimum kelime: {self.min_words_per_section}
- Bölüm başına minimum paragraf: {self.min_paragraphs_per_section}
- Bölüm başına minimum kaynak: {self.min_sources_per_section}
- Toplam minimum kaynak: {self.min_total_sources}
- Minimum kalite puanı: {self.min_quality_score}

Güvenilir Kaynaklar:
{chr(10).join('- ' + d for d in self.trusted_domains[:10])}

Yasak Uygulamalar:
{chr(10).join('- ' + f for f in self.forbidden_practices[:10])}
"""


class RulesLoader:
    """
    Kural dosyalarını yükleyen ve parse eden sınıf.

    Rapor üretimi başlamadan önce TÜM kuralların okunması zorunludur.
    """

    REQUIRED_FILES = {
        '01_genel_kurallar.md': 'general_rules',
        '02_arastirma_kurallari.md': 'research_rules',
        '03_icerik_uretim_kurallari.md': 'content_rules',
        '04_kaynak_kullanim_kurallari.md': 'source_rules',
        '05_dogrulama_kurallari.md': 'validation_rules',
        '06_kalite_standartlari.md': 'quality_standards'
    }

    TRUSTED_DOMAINS = [
        "gov.tr", "tuik.gov.tr", "tcmb.gov.tr", "bddk.org.tr", "spk.gov.tr",
        "worldbank.org", "imf.org", "oecd.org", "reuters.com", "bloomberg.com",
        "borsaistanbul.com", "aa.com.tr", "edu.tr"
    ]

    def __init__(self, rules_dir: Optional[str] = None):
        """
        Args:
            rules_dir: Kural dosyalarının bulunduğu dizin.
                      Belirtilmezse proje kökündeki 'rules' klasörü kullanılır.
        """
        if rules_dir:
            self.rules_dir = Path(rules_dir)
        else:
            # Proje kökünü bul
            current = Path(__file__).resolve()
            project_root = current.parent.parent.parent  # src/rules -> src -> project
            self.rules_dir = project_root / "rules"

        self.loaded_rules: Optional[LoadedRules] = None
        self._load_errors: List[str] = []

    def load_all_rules(self) -> LoadedRules:
        """
        Tüm kural dosyalarını yükle.

        Returns:
            LoadedRules: Yüklenmiş kurallar

        Raises:
            RulesLoadError: Kurallar yüklenemezse
        """
        if not self.rules_dir.exists():
            raise RulesLoadError(f"Kurallar dizini bulunamadı: {self.rules_dir}")

        self.loaded_rules = LoadedRules()
        self._load_errors = []

        # Her dosyayı yükle
        for filename, attr_name in self.REQUIRED_FILES.items():
            file_path = self.rules_dir / filename

            if not file_path.exists():
                self._load_errors.append(f"Dosya bulunamadı: {filename}")
                continue

            try:
                rule_file = self._parse_rule_file(file_path)
                setattr(self.loaded_rules, attr_name, rule_file)
            except Exception as e:
                self._load_errors.append(f"{filename} parse hatası: {str(e)}")

        # Hata kontrolü
        if self._load_errors:
            raise RulesLoadError(
                "Kural dosyaları yüklenirken hatalar oluştu:\n" +
                "\n".join(f"  - {e}" for e in self._load_errors)
            )

        # Kurallar tam mı kontrol et
        if not self.loaded_rules.is_complete():
            missing = [f for f, a in self.REQUIRED_FILES.items()
                      if getattr(self.loaded_rules, a) is None]
            raise RulesLoadError(
                f"Eksik kural dosyaları: {', '.join(missing)}"
            )

        # Önemli değerleri çıkar
        self._extract_key_values()

        return self.loaded_rules

    def _parse_rule_file(self, file_path: Path) -> RuleFile:
        """Bir kural dosyasını parse et."""
        content = file_path.read_text(encoding='utf-8')

        # Başlık ve açıklamayı çıkar
        lines = content.split('\n')
        title = ""
        description = ""

        for i, line in enumerate(lines):
            if line.startswith('# ') and not title:
                title = line[2:].strip()
            elif title and line.strip() and not line.startswith('#'):
                description = line.strip()
                break

        # Bölümleri parse et
        sections = self._parse_sections(content)

        return RuleFile(
            filename=file_path.name,
            title=title or file_path.stem,
            description=description,
            sections=sections,
            raw_content=content
        )

    def _parse_sections(self, content: str) -> List[RuleSection]:
        """İçerikteki bölümleri parse et."""
        sections = []
        current_section = None
        current_content_lines = []

        lines = content.split('\n')

        for line in lines:
            # Ana bölüm başlığı (## ile başlayan)
            if line.startswith('## '):
                # Önceki bölümü kaydet
                if current_section:
                    current_section.content = '\n'.join(current_content_lines)
                    self._extract_section_details(current_section)
                    sections.append(current_section)

                current_section = RuleSection(
                    title=line[3:].strip(),
                    content=""
                )
                current_content_lines = []

            elif current_section:
                current_content_lines.append(line)

        # Son bölümü kaydet
        if current_section:
            current_section.content = '\n'.join(current_content_lines)
            self._extract_section_details(current_section)
            sections.append(current_section)

        return sections

    def _extract_section_details(self, section: RuleSection):
        """Bölüm içinden detayları çıkar."""
        content = section.content

        # Madde işaretlerini çıkar
        section.items = re.findall(r'^[-*]\s+(.+)$', content, re.MULTILINE)

        # Kod bloklarını çıkar
        section.code_blocks = re.findall(r'```[\w]*\n(.*?)```', content, re.DOTALL)

        # Tabloları çıkar (basit)
        table_matches = re.findall(r'\|(.+)\|', content)
        if table_matches:
            section.tables = [{'raw': m} for m in table_matches]

    def _extract_key_values(self):
        """Kurallardan önemli değerleri çıkar."""
        if not self.loaded_rules:
            return

        # İçerik kurallarından minimum değerler
        if self.loaded_rules.content_rules:
            content = self.loaded_rules.content_rules.raw_content

            # Kelime sayısı
            match = re.search(r'word_count\s*>=\s*(\d+)', content)
            if match:
                self.loaded_rules.min_words_per_section = int(match.group(1))

            # Paragraf sayısı
            match = re.search(r'paragraph_count\s*>=\s*(\d+)', content)
            if match:
                self.loaded_rules.min_paragraphs_per_section = int(match.group(1))

        # Kaynak kurallarından
        if self.loaded_rules.source_rules:
            content = self.loaded_rules.source_rules.raw_content

            # Toplam kaynak
            match = re.search(r'TOPLAM RAPOR.*?(\d+)', content, re.DOTALL)
            if match:
                self.loaded_rules.min_total_sources = int(match.group(1))

        # Kalite standartlarından
        if self.loaded_rules.quality_standards:
            content = self.loaded_rules.quality_standards.raw_content

            # Minimum puan
            match = re.search(r'Toplam puan.*?\*\*(\d+)', content)
            if match:
                self.loaded_rules.min_quality_score = int(match.group(1))

        # Güvenilir domainler
        self.loaded_rules.trusted_domains = self.TRUSTED_DOMAINS.copy()

        # Araştırma kurallarından ek domainler çıkar
        if self.loaded_rules.research_rules:
            content = self.loaded_rules.research_rules.raw_content
            domains = re.findall(r'\|\s*([\w.]+\.(?:gov\.tr|org\.tr|com|org))\s*\|', content)
            for d in domains:
                if d not in self.loaded_rules.trusted_domains:
                    self.loaded_rules.trusted_domains.append(d)

        # Yasak uygulamalar
        forbidden = []
        for rule in [self.loaded_rules.general_rules,
                     self.loaded_rules.content_rules,
                     self.loaded_rules.source_rules]:
            if rule:
                # ❌ ile işaretli maddeleri bul
                matches = re.findall(r'❌\s*(.+?)(?:\n|$)', rule.raw_content)
                forbidden.extend(matches)

        self.loaded_rules.forbidden_practices = list(set(forbidden))

    def get_rules_for_prompt(self) -> str:
        """
        Claude prompt'una eklenecek kural metnini döndür.

        Bu metin her rapor üretimi öncesinde Claude'a gönderilir.
        """
        if not self.loaded_rules:
            raise RulesLoadError("Kurallar henüz yüklenmedi. Önce load_all_rules() çağırın.")

        return f"""
<RAPOR_URETIM_KURALLARI>

{self.loaded_rules.get_summary()}

DETAYLI KURALLAR:

{self.loaded_rules.get_all_rules_text()}

</RAPOR_URETIM_KURALLARI>

ÖNEMLİ: Yukarıdaki tüm kurallara HARFI HARFINE uymalısın. Kural ihlali tespit edilirse rapor reddedilecektir.
"""

    def validate_content_against_rules(
        self,
        content: str,
        section_name: str
    ) -> List[str]:
        """
        Üretilen içeriği kurallara göre doğrula.

        Args:
            content: Doğrulanacak içerik
            section_name: Bölüm adı

        Returns:
            List[str]: Kural ihlalleri listesi (boşsa uygun)
        """
        if not self.loaded_rules:
            return ["Kurallar yüklenmemiş"]

        violations = []

        # Kelime sayısı kontrolü
        word_count = len(content.split())
        if word_count < self.loaded_rules.min_words_per_section:
            violations.append(
                f"Yetersiz kelime sayısı: {word_count} < {self.loaded_rules.min_words_per_section}"
            )

        # Paragraf sayısı kontrolü
        paragraphs = [p for p in content.split('\n\n') if len(p.strip()) > 50]
        if len(paragraphs) < self.loaded_rules.min_paragraphs_per_section:
            violations.append(
                f"Yetersiz paragraf: {len(paragraphs)} < {self.loaded_rules.min_paragraphs_per_section}"
            )

        # Referans kontrolü
        citations = re.findall(r'\[\d+\]', content)
        if len(set(citations)) < self.loaded_rules.min_sources_per_section:
            violations.append(
                f"Yetersiz kaynak referansı: {len(set(citations))} < {self.loaded_rules.min_sources_per_section}"
            )

        # Yasak ifade kontrolü
        forbidden_phrases = [
            "araştırmalar gösteriyor",
            "bilindiği üzere",
            "uzmanlar belirtiyor",
            "malumunuz"
        ]
        content_lower = content.lower()
        for phrase in forbidden_phrases:
            if phrase in content_lower:
                violations.append(f"Yasak ifade kullanımı: '{phrase}'")

        # Kaynaksız istatistik kontrolü
        stats = re.findall(r'%\d+|\d+\s*(?:milyar|milyon|bin)', content)
        for stat in stats:
            # İstatistikten sonra referans var mı kontrol et
            stat_pos = content.find(stat)
            following_text = content[stat_pos:stat_pos+50]
            if not re.search(r'\[\d+\]', following_text):
                violations.append(f"Kaynaksız istatistik: '{stat}'")
                break  # Sadece bir uyarı yeterli

        return violations


class RulesLoadError(Exception):
    """Kural yükleme hatası."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL KURAL SİSTEMİ
# Bu değişkenler uygulama boyunca bellekte kalır
# ═══════════════════════════════════════════════════════════════════════════

_rules_loader: Optional[RulesLoader] = None
_global_rules: Optional[LoadedRules] = None  # Global kurallar - bellekte tutulur


def get_rules_loader(rules_dir: Optional[str] = None) -> RulesLoader:
    """
    Global RulesLoader instance'ı al veya oluştur.

    Args:
        rules_dir: Kural dizini (ilk çağrıda kullanılır)

    Returns:
        RulesLoader: Singleton instance
    """
    global _rules_loader

    if _rules_loader is None:
        _rules_loader = RulesLoader(rules_dir)

    return _rules_loader


def ensure_rules_loaded() -> LoadedRules:
    """
    Kuralların yüklendiğinden emin ol.

    Rapor üretimi başlamadan önce bu fonksiyon çağrılmalıdır.

    Returns:
        LoadedRules: Yüklenmiş kurallar

    Raises:
        RulesLoadError: Kurallar yüklenemezse
    """
    global _global_rules

    loader = get_rules_loader()

    if loader.loaded_rules is None:
        _global_rules = loader.load_all_rules()
    else:
        _global_rules = loader.loaded_rules

    return _global_rules


def set_global_rules(rules: LoadedRules):
    """
    Global kuralları ayarla.

    Bu fonksiyon main.py tarafından kurallar yüklendikten sonra çağrılır.
    """
    global _global_rules
    _global_rules = rules


def get_global_rules() -> LoadedRules:
    """
    Bellekte tutulan global kuralları döndür.

    Bu fonksiyon herhangi bir modülden çağrılabilir.

    Returns:
        LoadedRules: Bellekteki kurallar

    Raises:
        RulesLoadError: Kurallar yüklenmemişse
    """
    global _global_rules

    if _global_rules is None:
        raise RulesLoadError(
            "KURALLAR BELLEKTE DEĞİL!\n"
            "Uygulama başlangıcında kurallar yüklenmemiş olabilir.\n"
            "main.py'deki load_rules_at_startup() fonksiyonu çağrılmalıdır.\n\n"
            "KURALLAR YÜKLENMEDEN HİÇBİR İŞLEM YAPILAMAZ!"
        )

    return _global_rules


def rules_are_loaded() -> bool:
    """Kuralların bellekte olup olmadığını kontrol et."""
    return _global_rules is not None


def get_rules_summary() -> str:
    """Bellekteki kuralların özetini döndür."""
    rules = get_global_rules()
    return rules.get_summary()


def get_rules_for_claude() -> str:
    """Claude'a gönderilecek kural metnini döndür."""
    loader = get_rules_loader()
    if loader.loaded_rules is None:
        raise RulesLoadError("Kurallar yüklenmemiş!")
    return loader.get_rules_for_prompt()
