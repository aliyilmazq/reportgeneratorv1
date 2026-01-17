"""Çapraz Referans Kontrolü - Bölümler arası tutarlılık."""

import re
import sys
from typing import Dict, Any, List, Set
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

# Turkce sayi parser
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from utils.turkish_parser import TurkishNumberParser, parse_number
except ImportError:
    TurkishNumberParser = None
    parse_number = None

console = Console()


@dataclass
class CrossRefIssue:
    """Çapraz referans sorunu."""
    source_section: str
    target_section: str
    metric: str
    source_value: Any
    target_value: Any
    message: str
    severity: str = "warning"


class CrossReferenceChecker:
    """Bölümler arası tutarlılık kontrolcüsü."""

    # Kontrol edilecek metrikler ve bulunması beklenen bölümler
    METRIC_SECTIONS = {
        "pazar_buyuklugu": ["yonetici_ozeti", "pazar_analizi", "finansal_projeksiyonlar"],
        "hedef_gelir": ["yonetici_ozeti", "finansal_projeksiyonlar"],
        "hedef_musteri": ["yonetici_ozeti", "pazarlama_stratejisi", "operasyon_plani"],
        "yatirim_ihtiyaci": ["yonetici_ozeti", "finansal_projeksiyonlar"],
        "buyume_orani": ["yonetici_ozeti", "pazar_analizi", "finansal_projeksiyonlar"],
        "basa_bas_suresi": ["yonetici_ozeti", "finansal_projeksiyonlar"],
        "personel_sayisi": ["yonetim_ekibi", "operasyon_plani"],
    }

    # Metrik çıkarma pattern'leri
    METRIC_PATTERNS = {
        "pazar_buyuklugu": [
            r'pazar\s*büyüklüğü[:\s]*([\d.,]+)\s*(milyon|milyar)?\s*(TL|USD)?',
            r'([\d.,]+)\s*(milyon|milyar)?\s*(TL|USD)?\s*(?:büyüklüğünde|değerinde)\s*pazar',
        ],
        "hedef_gelir": [
            r'hedef\s*(?:gelir|ciro)[:\s]*([\d.,]+)\s*(milyon|milyar)?',
            r'(?:gelir|ciro)\s*hedef[i]?[:\s]*([\d.,]+)',
        ],
        "hedef_musteri": [
            r'hedef[:\s]*([\d.,]+)\s*(?:müşteri|kullanıcı|mağaza)',
            r'([\d.,]+)\s*(?:aktif\s*)?(?:müşteri|kullanıcı|mağaza)\s*hedef',
        ],
        "yatirim_ihtiyaci": [
            r'yatırım\s*(?:ihtiyacı|tutarı|gereksinimi)[:\s]*([\d.,]+)',
            r'([\d.,]+)\s*(?:milyon|milyar)?\s*(?:TL|USD)?\s*yatırım',
        ],
        "buyume_orani": [
            r'(?:yıllık\s*)?büyüme[:\s]*%?\s*([\d.,]+)',
            r'%\s*([\d.,]+)\s*büyüme',
        ],
        "basa_bas_suresi": [
            r'başa\s*baş[:\s]*([\d]+)\s*(?:ay|yıl)',
            r'([\d]+)\s*(?:ay|yıl)[a-z]*\s*(?:içinde\s*)?başa\s*baş',
        ],
    }

    def __init__(self):
        pass

    def check(self, report_content: Dict[str, str]) -> List[CrossRefIssue]:
        """Çapraz referans kontrolü yap."""
        issues = []

        # Her metrik için değerleri topla
        metric_values = self._extract_all_metrics(report_content)

        # Tutarsızlıkları tespit et
        for metric_name, section_values in metric_values.items():
            if len(section_values) < 2:
                continue

            # Değerleri karşılaştır
            values_list = list(section_values.items())
            base_section, base_value = values_list[0]

            for other_section, other_value in values_list[1:]:
                if not self._values_match(base_value, other_value, metric_name):
                    issues.append(CrossRefIssue(
                        source_section=base_section,
                        target_section=other_section,
                        metric=metric_name,
                        source_value=base_value,
                        target_value=other_value,
                        message=f"'{metric_name}' değeri tutarsız: {base_section}={base_value} vs {other_section}={other_value}",
                        severity="warning" if self._is_close(base_value, other_value) else "error"
                    ))

        return issues

    def _extract_all_metrics(self, content: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """Tüm bölümlerden metrikleri çıkar."""
        metric_values = {}

        for metric_name, patterns in self.METRIC_PATTERNS.items():
            metric_values[metric_name] = {}

            for section_id, text in content.items():
                if not text:
                    continue

                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        try:
                            value = self._parse_value(match)
                            if value is not None:
                                metric_values[metric_name][section_id] = value
                                break
                        except (ValueError, TypeError, AttributeError):
                            # Metrik degeri parse edilemedi
                            pass

        # Boş metrikleri temizle
        metric_values = {k: v for k, v in metric_values.items() if v}

        return metric_values

    def _parse_value(self, match) -> float:
        """Regex eşleşmesinden sayısal değer çıkar - Turkce format destekli."""
        groups = match.groups()
        full_match = match.group(0).lower()

        # İlk sayısal grubu bul
        for group in groups:
            if group:
                # TurkishNumberParser varsa kullan (carpanli destek dahil)
                if TurkishNumberParser:
                    # Carpanli text olustur
                    text_to_parse = group
                    if 'milyar' in full_match:
                        text_to_parse = f"{group} milyar"
                    elif 'milyon' in full_match:
                        text_to_parse = f"{group} milyon"

                    result = TurkishNumberParser.parse(text_to_parse)
                    if result is not None:
                        return result

                # Fallback
                if group.replace(',', '.').replace('.', '').isdigit():
                    value = float(group.replace(',', '.'))

                    # Çarpan kontrolü
                    if 'milyar' in full_match:
                        value *= 1_000_000_000
                    elif 'milyon' in full_match:
                        value *= 1_000_000

                    return value

        return None

    def _values_match(self, val1: Any, val2: Any, metric_name: str) -> bool:
        """İki değerin eşleşip eşleşmediğini kontrol et."""
        if val1 is None or val2 is None:
            return True

        try:
            v1 = float(val1)
            v2 = float(val2)

            # Tolerans: %10
            tolerance = 0.1

            if v1 == 0 and v2 == 0:
                return True

            if v1 == 0 or v2 == 0:
                return False

            ratio = abs(v1 - v2) / max(abs(v1), abs(v2))
            return ratio <= tolerance

        except (TypeError, ValueError):
            return str(val1).lower() == str(val2).lower()

    def _is_close(self, val1: Any, val2: Any, tolerance: float = 0.2) -> bool:
        """İki değerin yakın olup olmadığını kontrol et."""
        try:
            v1 = float(val1)
            v2 = float(val2)

            if v1 == 0 and v2 == 0:
                return True

            if v1 == 0 or v2 == 0:
                return False

            ratio = abs(v1 - v2) / max(abs(v1), abs(v2))
            return ratio <= tolerance

        except (ValueError, TypeError, ZeroDivisionError):
            # Sayisal karsilastirma yapilamadi
            return False

    def generate_consistency_report(
        self,
        content: Dict[str, str]
    ) -> str:
        """Tutarlılık raporu oluştur."""
        issues = self.check(content)
        metric_values = self._extract_all_metrics(content)

        report = []
        report.append("=" * 60)
        report.append("ÇAPRAZ REFERANS TUTARLILIK RAPORU")
        report.append("=" * 60)
        report.append("")

        # Metrik özeti
        report.append("TESPİT EDİLEN METRİKLER:")
        report.append("-" * 40)

        for metric_name, section_values in metric_values.items():
            if section_values:
                report.append(f"\n{metric_name}:")
                for section, value in section_values.items():
                    report.append(f"  - {section}: {value:,.2f}" if isinstance(value, float) else f"  - {section}: {value}")

        # Sorunlar
        if issues:
            report.append("\n" + "=" * 60)
            report.append("TESPİT EDİLEN TUTARSIZLIKLAR:")
            report.append("-" * 40)

            for issue in issues:
                severity_marker = "❌" if issue.severity == "error" else "⚠️"
                report.append(f"\n{severity_marker} {issue.message}")
                report.append(f"   Kaynak: {issue.source_section} = {issue.source_value}")
                report.append(f"   Hedef: {issue.target_section} = {issue.target_value}")
        else:
            report.append("\n✅ Tüm bölümler tutarlı!")

        return "\n".join(report)

    def print_issues(self, issues: List[CrossRefIssue]):
        """Sorunları ekrana yazdır."""
        if not issues:
            console.print("[green]✓ Çapraz referans kontrolü başarılı - tutarsızlık yok[/green]")
            return

        console.print(f"\n[yellow]⚠ {len(issues)} tutarsızlık tespit edildi:[/yellow]")

        for issue in issues:
            if issue.severity == "error":
                console.print(f"  [red]✗[/red] {issue.message}")
            else:
                console.print(f"  [yellow]![/yellow] {issue.message}")
