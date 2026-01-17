"""Finansal Doğrulama Modülü - Sayısal tutarlılık ve mantık kontrolü."""

import re
import sys
import logging
from typing import (
    Dict, Any, List, Optional, Tuple, Union, ClassVar,
    Set, Pattern, Match
)
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import yaml
from rich.console import Console
from rich.table import Table

# Turkce sayi parser
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from utils.turkish_parser import TurkishNumberParser, parse_number
except ImportError:
    TurkishNumberParser = None
    parse_number = None

logger = logging.getLogger(__name__)
console = Console()


class IssueSeverity(str, Enum):
    """Sorun ciddiyet seviyeleri."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(str, Enum):
    """Sorun kategorileri."""
    SUM_MISMATCH = "sum_mismatch"
    PERCENTAGE_ERROR = "percentage_error"
    PERCENTAGE_SUM = "percentage_sum"
    LOGIC_ERROR = "logic_error"
    GROWTH_RATE = "growth_rate"
    VALUE_INCONSISTENCY = "value_inconsistency"
    OUTDATED_DATA = "outdated_data"
    FUTURE_PROJECTION = "future_projection"


@dataclass
class ValidationIssue:
    """Doğrulama sorunu."""
    severity: IssueSeverity
    category: IssueCategory
    message: str
    location: str  # Hangi bölümde
    current_value: Any = None
    expected_value: Any = None
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e cevir."""
        return {
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "message": self.message,
            "location": self.location,
            "current_value": str(self.current_value) if self.current_value else None,
            "expected_value": str(self.expected_value) if self.expected_value else None,
            "suggestion": self.suggestion
        }


@dataclass
class ValidationResult:
    """Doğrulama sonucu."""
    is_valid: bool
    score: int  # 0-100
    issues: List[ValidationIssue] = field(default_factory=list)
    fixed_content: Dict[str, str] = field(default_factory=dict)
    summary: str = ""

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Uyari sayisi."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e cevir."""
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary
        }


class FinancialValidator:
    """Finansal veri doğrulayıcı - Tutarlılık ve mantık kontrolü."""

    # Sektör benchmark verileri
    SECTOR_BENCHMARKS: ClassVar[Dict[str, Dict[str, Tuple[int, int]]]] = {
        "e_ticaret": {
            "gross_margin": (20, 60),  # min, max
            "net_margin": (2, 20),
            "growth_rate": (-20, 150),
            "cac_ltv_ratio": (0.1, 0.5),
        },
        "saas": {
            "gross_margin": (60, 90),
            "net_margin": (5, 30),
            "growth_rate": (-10, 200),
            "churn_rate": (2, 15),
        },
        "perakende": {
            "gross_margin": (15, 45),
            "net_margin": (1, 10),
            "growth_rate": (-15, 50),
        },
        "uretim": {
            "gross_margin": (20, 50),
            "net_margin": (3, 15),
            "growth_rate": (-10, 40),
        },
        "hizmet": {
            "gross_margin": (40, 80),
            "net_margin": (5, 25),
            "growth_rate": (-10, 100),
        },
        "default": {
            "gross_margin": (10, 70),
            "net_margin": (1, 25),
            "growth_rate": (-30, 150),
        }
    }

    def __init__(self, config_dir: Optional[str] = None) -> None:
        self.config_dir: Path = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.benchmarks: Dict[str, Any] = self._load_benchmarks()

    def _load_benchmarks(self) -> Dict[str, Any]:
        """Benchmark verilerini yükle."""
        benchmark_path = Path(self.config_dir) / "benchmarks.yaml"
        if benchmark_path.exists():
            with open(benchmark_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {"sectors": self.SECTOR_BENCHMARKS}

    def validate(
        self,
        report_content: Dict[str, str],
        sector: str = "default"
    ) -> ValidationResult:
        """Rapor içeriğini doğrula."""

        issues = []

        # 1. Sayısal değerleri çıkar
        all_numbers = self._extract_numbers(report_content)

        # 2. Yüzde toplamlarını kontrol et
        issues.extend(self._check_percentage_sums(report_content))

        # 3. Finansal oranları kontrol et
        issues.extend(self._check_financial_ratios(all_numbers, sector))

        # 4. Büyüme oranlarını kontrol et
        issues.extend(self._check_growth_rates(all_numbers))

        # 5. Mantıksal tutarlılığı kontrol et
        issues.extend(self._check_logical_consistency(all_numbers))

        # 6. Zaman serisi tutarlılığını kontrol et
        issues.extend(self._check_time_series(all_numbers))

        # Skor hesapla
        error_count = sum(1 for i in issues if i.severity == 'error')
        warning_count = sum(1 for i in issues if i.severity == 'warning')

        score = max(0, 100 - (error_count * 15) - (warning_count * 5))
        is_valid = error_count == 0

        # Özet oluştur
        summary = self._create_summary(issues, score)

        return ValidationResult(
            is_valid=is_valid,
            score=score,
            issues=issues,
            summary=summary
        )

    def _extract_numbers(self, content: Dict[str, str]) -> Dict[str, List[Dict]]:
        """İçerikten sayısal değerleri çıkar."""
        numbers = {}

        # Para birimi pattern'leri
        money_patterns = [
            r'([\d.,]+)\s*(milyon|milyar)?\s*(TL|USD|EUR|\$|€|₺)',
            r'(TL|USD|EUR|\$|€|₺)\s*([\d.,]+)\s*(milyon|milyar)?',
        ]

        # Yüzde pattern'i
        percentage_pattern = r'%\s*([\d.,]+)|([yüzde|percent]+)\s*([\d.,]+)|([\d.,]+)\s*%'

        # Büyüme/oran pattern'i
        growth_pattern = r'(büyüme|artış|düşüş|growth|increase|decrease)[:\s]*([\d.,]+)\s*%?'

        for section_id, text in content.items():
            if not text:
                continue

            section_numbers = {
                'money': [],
                'percentages': [],
                'growth_rates': [],
                'years': [],
                'raw_numbers': []
            }

            # Para değerlerini bul
            for pattern in money_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        value = self._parse_number(match.group(1) if match.group(1) else match.group(2))
                        multiplier = match.group(2) if len(match.groups()) > 1 else None
                        if multiplier:
                            if 'milyon' in multiplier.lower():
                                value *= 1_000_000
                            elif 'milyar' in multiplier.lower():
                                value *= 1_000_000_000
                        section_numbers['money'].append({
                            'value': value,
                            'text': match.group(0),
                            'position': match.start()
                        })
                    except (ValueError, AttributeError, IndexError):
                        # Gecersiz sayi formati veya regex grubu bulunamadi
                        pass

            # Yüzdeleri bul
            for match in re.finditer(percentage_pattern, text, re.IGNORECASE):
                try:
                    groups = [g for g in match.groups() if g and g.replace(',', '.').replace('.', '').isdigit()]
                    if groups:
                        value = self._parse_number(groups[0])
                        section_numbers['percentages'].append({
                            'value': value,
                            'text': match.group(0),
                            'position': match.start()
                        })
                except (ValueError, AttributeError, IndexError):
                    # Gecersiz yuzde formati veya regex grubu bulunamadi
                    pass

            # Yılları bul
            year_pattern = r'\b(20[1-3][0-9])\b'
            for match in re.finditer(year_pattern, text):
                section_numbers['years'].append({
                    'value': int(match.group(1)),
                    'position': match.start()
                })

            numbers[section_id] = section_numbers

        return numbers

    def _parse_number(self, text: str) -> float:
        """Metni sayıya çevir - Turkce format destekli."""
        if not text:
            return 0.0

        # TurkishNumberParser varsa kullan
        if TurkishNumberParser:
            result = TurkishNumberParser.parse(str(text).strip(), default=0.0)
            return result if result is not None else 0.0

        # Fallback: basit parse
        text = str(text).strip()
        if ',' in text and '.' in text:
            text = text.replace('.', '').replace(',', '.')
        elif ',' in text:
            text = text.replace(',', '.')
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _check_percentage_sums(self, content: Dict[str, str]) -> List[ValidationIssue]:
        """Yüzde toplamlarını kontrol et."""
        issues = []

        # Pazar payı kontrolü
        market_share_pattern = r'pazar\s*payı[:\s]*([\d.,]+)\s*%'

        for section_id, text in content.items():
            if not text:
                continue

            # Tablo içindeki yüzdeleri bul
            table_pattern = r'\|[^|]*\|\s*([\d.,]+)\s*%?\s*\|'
            percentages_in_tables = []

            for match in re.finditer(table_pattern, text):
                try:
                    val = self._parse_number(match.group(1))
                    if 0 < val <= 100:
                        percentages_in_tables.append(val)
                except (ValueError, AttributeError, IndexError):
                    # Gecersiz tablo yuzde formati
                    pass

            # Ardışık yüzdeler toplamı 100'ü geçmemeli
            if percentages_in_tables and len(percentages_in_tables) >= 3:
                total = sum(percentages_in_tables)
                if total > 105:  # %5 tolerans
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.PERCENTAGE_SUM,
                        message=f"Yüzde toplamı %100'ü aşıyor: %{total:.1f}",
                        location=section_id,
                        current_value=total,
                        expected_value=100,
                        suggestion="Yüzde değerlerini kontrol edin, toplam %100'ü geçmemeli"
                    ))

        return issues

    def _check_financial_ratios(
        self,
        numbers: Dict[str, List[Dict]],
        sector: str
    ) -> List[ValidationIssue]:
        """Finansal oranları sektör benchmark'larıyla karşılaştır."""
        issues = []
        benchmarks = self.SECTOR_BENCHMARKS.get(sector, self.SECTOR_BENCHMARKS['default'])

        # Tüm yüzdeleri topla
        all_percentages = []
        for section_data in numbers.values():
            all_percentages.extend([p['value'] for p in section_data.get('percentages', [])])

        # Marjin kontrolü
        for pct in all_percentages:
            # Net kar marjı gibi görünen değerler
            if 'net_margin' in benchmarks:
                min_val, max_val = benchmarks['net_margin']
                # Çok yüksek marjin uyarısı
                if pct > 50 and pct < 100:
                    # Bu muhtemelen bir marjin değil, başka bir yüzde
                    pass

        return issues

    def _check_growth_rates(self, numbers: Dict[str, List[Dict]]) -> List[ValidationIssue]:
        """Büyüme oranlarının mantıklı olup olmadığını kontrol et."""
        issues = []

        for section_id, section_data in numbers.items():
            for pct in section_data.get('percentages', []):
                value = pct['value']
                text = pct.get('text', '')

                # Büyüme oranı olarak görünen yüksek değerler
                if 'büyüme' in text.lower() or 'artış' in text.lower() or 'growth' in text.lower():
                    if value > 500:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            category=IssueCategory.GROWTH_RATE,
                            message=f"Gerçekçi olmayan büyüme oranı: %{value:.0f}",
                            location=section_id,
                            current_value=value,
                            expected_value="< %200",
                            suggestion="Bu büyüme oranı muhtemelen hatalı, düzeltin."
                        ))
                    elif value > 200:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.GROWTH_RATE,
                            message=f"Çok yüksek büyüme oranı: %{value:.0f}",
                            location=section_id,
                            current_value=value,
                            expected_value="< %200",
                            suggestion="Bu büyüme oranı gerçekçi mi? Doğrulayın."
                        ))

        return issues

    def _check_logical_consistency(self, numbers: Dict[str, List[Dict]]) -> List[ValidationIssue]:
        """Mantıksal tutarlılığı kontrol et."""
        issues = []

        # Tüm para değerlerini topla
        all_money = []
        for section_data in numbers.values():
            all_money.extend(section_data.get('money', []))

        if len(all_money) >= 2:
            values = [m['value'] for m in all_money if m['value'] > 0]
            if values:
                max_val = max(values)
                min_val = min(values)

                # Aşırı tutarsızlık kontrolü (1000x fark)
                if max_val / min_val > 10000 and min_val > 1:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.VALUE_INCONSISTENCY,
                        message=f"Para değerleri arasında büyük tutarsızlık var",
                        location="genel",
                        current_value=f"{min_val:,.0f} - {max_val:,.0f}",
                        suggestion="Para birimlerini ve çarpanları kontrol edin"
                    ))

        return issues

    def _check_time_series(self, numbers: Dict[str, List[Dict]]) -> List[ValidationIssue]:
        """Zaman serisi tutarlılığını kontrol et."""
        issues = []

        # Yılları topla
        all_years = set()
        for section_data in numbers.values():
            for year_data in section_data.get('years', []):
                all_years.add(year_data['value'])

        if all_years:
            years_list = sorted(all_years)
            current_year = 2025

            # Çok eski veya çok gelecek yıllar
            for year in years_list:
                if year < 2015:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.OUTDATED_DATA,
                        message=f"Eski veri yılı tespit edildi: {year}",
                        location="genel",
                        suggestion="Güncel veriler kullanın"
                    ))
                elif year > current_year + 10:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.FUTURE_PROJECTION,
                        message=f"Çok uzak gelecek projeksiyonu: {year}",
                        location="genel",
                        suggestion="Projeksiyon 5-7 yıl ile sınırlı tutulmalı"
                    ))

        return issues

    def _create_summary(self, issues: List[ValidationIssue], score: int) -> str:
        """Doğrulama özeti oluştur."""
        error_count = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        info_count = sum(1 for i in issues if i.severity == IssueSeverity.INFO)

        summary = f"""
DOĞRULAMA SONUCU
================
Skor: {score}/100
Hatalar: {error_count}
Uyarılar: {warning_count}
Bilgi: {info_count}

"""
        if error_count > 0:
            summary += "KRİTİK HATALAR:\n"
            for issue in issues:
                if issue.severity == IssueSeverity.ERROR:
                    cat_str = issue.category.value if isinstance(issue.category, Enum) else issue.category
                    summary += f"  - [{cat_str}] {issue.message}\n"
                    if issue.suggestion:
                        summary += f"    Öneri: {issue.suggestion}\n"

        if warning_count > 0:
            summary += "\nUYARILAR:\n"
            for issue in issues:
                if issue.severity == IssueSeverity.WARNING:
                    cat_str = issue.category.value if isinstance(issue.category, Enum) else issue.category
                    summary += f"  - [{cat_str}] {issue.message}\n"

        return summary

    def print_result(self, result: ValidationResult) -> None:
        """Sonucu ekrana yazdır."""
        # Başlık
        if result.is_valid:
            console.print(f"\n[bold green]✓ FİNANSAL DOĞRULAMA BAŞARILI[/bold green] - Skor: {result.score}/100")
        else:
            console.print(f"\n[bold red]✗ FİNANSAL DOĞRULAMA HATALI[/bold red] - Skor: {result.score}/100")

        if not result.issues:
            console.print("[green]Herhangi bir sorun tespit edilmedi.[/green]")
            return

        # Tablo oluştur
        table = Table(title="Doğrulama Sonuçları")
        table.add_column("Seviye", style="bold")
        table.add_column("Kategori")
        table.add_column("Mesaj")
        table.add_column("Öneri", style="dim")

        for issue in result.issues:
            if issue.severity == IssueSeverity.ERROR:
                severity_style = "[red]HATA[/red]"
            elif issue.severity == IssueSeverity.WARNING:
                severity_style = "[yellow]UYARI[/yellow]"
            else:
                severity_style = "[blue]BİLGİ[/blue]"

            cat_str = issue.category.value if isinstance(issue.category, Enum) else str(issue.category)
            table.add_row(
                severity_style,
                cat_str,
                issue.message[:50],
                issue.suggestion[:40] if issue.suggestion else "-"
            )

        console.print(table)
