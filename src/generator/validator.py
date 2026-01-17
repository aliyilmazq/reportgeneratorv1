"""Rapor doğrulayıcı modülü - Çıktının kurallara uygunluğunu kontrol eder."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table
from rich import box

from ..processor.structurer import StructuredReport

console = Console()


@dataclass
class ValidationError:
    """Doğrulama hatası."""
    severity: str  # 'error', 'warning', 'info'
    code: str
    message: str
    section: str = ""
    details: str = ""


@dataclass
class ValidationResult:
    """Doğrulama sonucu."""
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    info: List[ValidationError] = field(default_factory=list)
    score: int = 100  # 0-100


class ReportValidator:
    """Rapor doğrulayıcı sınıfı."""

    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        """Kuralları yükle."""
        rules_path = Path(self.config_dir) / "rules.yaml"
        if rules_path.exists():
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def validate(self, report: StructuredReport) -> ValidationResult:
        """Raporu doğrula."""
        result = ValidationResult()

        # Yapı doğrulama
        self._validate_structure(report, result)

        # İçerik doğrulama
        self._validate_content(report, result)

        # Dil doğrulama
        self._validate_language(report, result)

        # Format doğrulama
        self._validate_format(report, result)

        # Sonuç hesapla
        result.is_valid = len(result.errors) == 0
        result.score = self._calculate_score(result)

        return result

    def _validate_structure(self, report: StructuredReport, result: ValidationResult):
        """Yapı doğrulama."""
        validation_rules = self.rules.get('validation', {})
        required_all = validation_rules.get('required_sections', {}).get('all', [])
        required_type = validation_rules.get('required_sections', {}).get(report.report_type, [])

        required_sections = set(required_all + required_type)
        existing_sections = {s.id for s in report.sections}

        # Eksik bölüm kontrolü
        for section_id in required_sections:
            if section_id not in existing_sections:
                result.errors.append(ValidationError(
                    severity='error',
                    code='MISSING_SECTION',
                    message=f"Zorunlu bölüm eksik: {section_id}",
                    section=section_id
                ))

        # Boş bölüm kontrolü
        for section in report.sections:
            if not section.content or len(section.content.strip()) < 10:
                result.warnings.append(ValidationError(
                    severity='warning',
                    code='EMPTY_SECTION',
                    message=f"Bölüm içeriği çok kısa veya boş",
                    section=section.title
                ))

    def _validate_content(self, report: StructuredReport, result: ValidationResult):
        """İçerik doğrulama."""
        validation_rules = self.rules.get('validation', {})
        min_content = validation_rules.get('min_content', {})

        for section in report.sections:
            section_rules = min_content.get(section.id, {})

            if section.content:
                word_count = len(section.content.split())

                # Minimum kelime kontrolü
                min_words = section_rules.get('min_words', 0)
                if word_count < min_words:
                    result.warnings.append(ValidationError(
                        severity='warning',
                        code='INSUFFICIENT_CONTENT',
                        message=f"İçerik çok kısa ({word_count} kelime, minimum {min_words})",
                        section=section.title
                    ))

                # Maksimum kelime kontrolü
                max_words = section_rules.get('max_words', float('inf'))
                if word_count > max_words:
                    result.info.append(ValidationError(
                        severity='info',
                        code='EXCESSIVE_CONTENT',
                        message=f"İçerik çok uzun ({word_count} kelime, maksimum {max_words})",
                        section=section.title
                    ))

    def _validate_language(self, report: StructuredReport, result: ValidationResult):
        """Dil doğrulama."""
        lang_rules = self.rules.get('language_rules', {})

        if report.language == 'tr':
            turkish_rules = lang_rules.get('turkish', {})
            turkish_chars = turkish_rules.get('characters', [])

            for section in report.sections:
                if section.content:
                    # Türkçe karakter kontrolü (sadece bilgi amaçlı)
                    has_turkish = any(char in section.content for char in turkish_chars)
                    if not has_turkish and len(section.content) > 100:
                        result.info.append(ValidationError(
                            severity='info',
                            code='NO_TURKISH_CHARS',
                            message="Türkçe karakter bulunamadı (içerik İngilizce olabilir)",
                            section=section.title
                        ))

    def _validate_format(self, report: StructuredReport, result: ValidationResult):
        """Format doğrulama."""
        fmt_rules = self.rules.get('format_rules', {})
        heading_rules = fmt_rules.get('headings', {})
        max_depth = heading_rules.get('max_depth', 3)

        for section in report.sections:
            # Başlık derinliği kontrolü
            if section.level > max_depth:
                result.warnings.append(ValidationError(
                    severity='warning',
                    code='HEADING_TOO_DEEP',
                    message=f"Başlık derinliği fazla (seviye {section.level}, maksimum {max_depth})",
                    section=section.title
                ))

            # İçerikte potansiyel format sorunları
            if section.content:
                # Çok uzun paragraf kontrolü
                paragraphs = section.content.split('\n\n')
                for para in paragraphs:
                    if len(para) > 2000:
                        result.info.append(ValidationError(
                            severity='info',
                            code='LONG_PARAGRAPH',
                            message="Çok uzun paragraf tespit edildi (2000+ karakter)",
                            section=section.title
                        ))
                        break

    def _calculate_score(self, result: ValidationResult) -> int:
        """Doğrulama skorunu hesapla."""
        score = 100

        # Hata başına -20 puan
        score -= len(result.errors) * 20

        # Uyarı başına -5 puan
        score -= len(result.warnings) * 5

        # Bilgi başına -1 puan
        score -= len(result.info) * 1

        return max(0, min(100, score))

    def print_result(self, result: ValidationResult):
        """Sonucu yazdır."""
        # Başlık
        if result.is_valid:
            console.print("\n[green]✓ Doğrulama Başarılı[/green]")
        else:
            console.print("\n[red]✗ Doğrulama Başarısız[/red]")

        # Skor
        score_color = "green" if result.score >= 80 else "yellow" if result.score >= 50 else "red"
        console.print(f"[{score_color}]Skor: {result.score}/100[/{score_color}]")

        # Detay tablosu
        if result.errors or result.warnings or result.info:
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("Seviye", style="bold")
            table.add_column("Kod")
            table.add_column("Mesaj")
            table.add_column("Bölüm")

            for error in result.errors:
                table.add_row(
                    "[red]HATA[/red]",
                    error.code,
                    error.message,
                    error.section
                )

            for warning in result.warnings:
                table.add_row(
                    "[yellow]UYARI[/yellow]",
                    warning.code,
                    warning.message,
                    warning.section
                )

            for info in result.info:
                table.add_row(
                    "[blue]BİLGİ[/blue]",
                    info.code,
                    info.message,
                    info.section
                )

            console.print(table)

    def to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """ValidationResult'u sözlüğe çevir."""
        return {
            "is_valid": result.is_valid,
            "score": result.score,
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
            "info_count": len(result.info),
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "section": e.section
                }
                for e in result.errors
            ],
            "warnings": [
                {
                    "code": w.code,
                    "message": w.message,
                    "section": w.section
                }
                for w in result.warnings
            ]
        }
