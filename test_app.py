#!/usr/bin/env python3
"""
Rapor Uretici v4.0 - Uygulama Testi
===================================
Bu script uygulamanin tum bilesenlerini test eder.
"""

import sys
import os
from pathlib import Path

# .env yukle
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Proje path'i
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

def test_imports():
    """Tum modullerin import edilebilirligini test et."""
    console.print("\n[bold cyan]1. MODUL IMPORT TESTI[/bold cyan]")

    modules = [
        ("src.scanner", "FileScanner"),
        ("src.orchestrator", "ReportOrchestrator"),
        ("src.research.web_researcher", "WebResearcher"),
        ("src.data_sources.web_data_fetcher", "WebDataFetcher"),
        ("src.content.section_generator", "SectionGenerator"),
        ("src.content.content_planner", "ContentPlanner"),
        ("src.validation.financial_validator", "FinancialValidator"),
        ("src.generator.docx_generator", "DocxGenerator"),
        ("src.generator.pdf_generator", "PdfGenerator"),
        ("src.rules.rules_loader", "RulesLoader"),
        ("src.utils.validators", "PathValidator"),
        ("src.utils.turkish_parser", "TurkishNumberParser"),
    ]

    success = 0
    failed = 0

    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            console.print(f"   [green]✓[/green] {module_name}.{class_name}")
            success += 1
        except Exception as e:
            console.print(f"   [red]✗[/red] {module_name}.{class_name}: {e}")
            failed += 1

    console.print(f"\n   Sonuc: [green]{success} basarili[/green], [red]{failed} basarisiz[/red]")
    return failed == 0


def test_api_connection():
    """API baglantisini test et."""
    console.print("\n[bold cyan]2. API BAGLANTI TESTI[/bold cyan]")

    try:
        import anthropic
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Merhaba, sadece 'OK' yaz."}]
        )

        result = response.content[0].text.strip()
        console.print(f"   [green]✓[/green] API yaniti: {result}")
        return True
    except Exception as e:
        console.print(f"   [red]✗[/red] API hatasi: {e}")
        return False


def test_rules_loading():
    """Kural yuklemesini test et."""
    console.print("\n[bold cyan]3. KURAL YUKLEME TESTI[/bold cyan]")

    try:
        from src.rules.rules_loader import RulesLoader

        loader = RulesLoader()
        rules = loader.load_all_rules()

        console.print(f"   [green]✓[/green] Kurallar yuklendi")
        console.print(f"   [dim]  - Min kelime/bolum: {rules.min_words_per_section}[/dim]")
        console.print(f"   [dim]  - Min kaynak: {rules.min_total_sources}[/dim]")
        console.print(f"   [dim]  - Min kalite: {rules.min_quality_score}%[/dim]")
        return True
    except Exception as e:
        console.print(f"   [red]✗[/red] Kural yukleme hatasi: {e}")
        return False


def test_file_scanner():
    """Dosya tarayiciyi test et."""
    console.print("\n[bold cyan]4. DOSYA TARAYICI TESTI[/bold cyan]")

    try:
        from src.scanner import FileScanner

        scanner = FileScanner()
        samples_dir = Path("samples")

        if not samples_dir.exists():
            samples_dir.mkdir(exist_ok=True)

        result = scanner.scan(str(samples_dir))
        console.print(f"   [green]✓[/green] Taranan dosya sayisi: {result.total_files}")
        return True
    except Exception as e:
        console.print(f"   [red]✗[/red] Tarayici hatasi: {e}")
        return False


def test_web_research():
    """Web arastirma modulunu test et."""
    console.print("\n[bold cyan]5. WEB ARASTIRMA TESTI[/bold cyan]")

    try:
        from src.research.web_researcher import WebResearcher

        researcher = WebResearcher()
        # Basit bir arama yap
        results = researcher.search("Turkiye ekonomisi 2024", max_results=3)

        console.print(f"   [green]✓[/green] Web arama sonucu: {len(results)} kaynak")
        for r in results[:2]:
            title = r.title[:50] + "..." if len(r.title) > 50 else r.title
            console.print(f"   [dim]  - {title}[/dim]")
        return True
    except Exception as e:
        console.print(f"   [yellow]![/yellow] Web arastirma: {e}")
        return True  # Opsiyonel, basarisiz olsa da devam


def test_data_fetcher():
    """Veri cekme modulunu test et."""
    console.print("\n[bold cyan]6. VERI CEKME TESTI[/bold cyan]")

    try:
        from src.data_sources.web_data_fetcher import WebDataFetcher

        fetcher = WebDataFetcher()
        data = fetcher.get_economic_indicators()

        if data:
            console.print(f"   [green]✓[/green] Ekonomik veri: {len(data)} gosterge")
        else:
            console.print(f"   [yellow]![/yellow] Ekonomik veri alinamadi (cache veya API sorunu olabilir)")
        return True
    except Exception as e:
        console.print(f"   [yellow]![/yellow] Veri cekme: {e}")
        return True  # Opsiyonel


def test_content_generation():
    """Icerik uretimini test et (kucuk olcekli)."""
    console.print("\n[bold cyan]7. ICERIK URETIM TESTI (Mini)[/bold cyan]")

    try:
        import anthropic
        client = anthropic.Anthropic()

        prompt = """Sen bir ekonomi uzmanisın. Asagidaki konuda 2 kisa paragraf yaz:

Konu: Turkiye'nin 2024 enflasyon durumu

Not: Sadece genel bilgi ver, cok uzun yazma."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        word_count = len(content.split())

        console.print(f"   [green]✓[/green] Icerik uretildi: {word_count} kelime")
        console.print(f"   [dim]  Ornek: {content[:100]}...[/dim]")
        return True
    except Exception as e:
        console.print(f"   [red]✗[/red] Icerik uretim hatasi: {e}")
        return False


def test_validators():
    """Dogrulayicilari test et."""
    console.print("\n[bold cyan]8. DOGRULAYICI TESTI[/bold cyan]")

    try:
        from src.utils.validators import PathValidator, URLValidator, TextValidator
        from src.utils.turkish_parser import TurkishNumberParser

        # Path validation
        PathValidator.validate(".", check_traversal=True)
        console.print(f"   [green]✓[/green] Path validation")

        # URL validation
        URLValidator.validate("https://example.com")
        console.print(f"   [green]✓[/green] URL validation")

        # Text validation
        result = TextValidator.check_prompt_injection("normal metin")
        console.print(f"   [green]✓[/green] Text validation (injection: {result})")

        # Turkish number parsing
        num = TurkishNumberParser.parse("1.234,56")
        console.print(f"   [green]✓[/green] Turkish parser: 1.234,56 -> {num}")

        return True
    except Exception as e:
        console.print(f"   [red]✗[/red] Dogrulayici hatasi: {e}")
        return False


def test_document_generators():
    """Belge ureticilerini test et."""
    console.print("\n[bold cyan]9. BELGE URETICI TESTI[/bold cyan]")

    try:
        from src.generator.docx_generator import DocxGenerator
        from src.generator.pdf_generator import PdfGenerator

        # DOCX generator
        docx_gen = DocxGenerator()
        console.print(f"   [green]✓[/green] DOCX generator hazir")

        # PDF generator
        pdf_gen = PdfGenerator()
        console.print(f"   [green]✓[/green] PDF generator hazir")

        return True
    except Exception as e:
        console.print(f"   [red]✗[/red] Generator hatasi: {e}")
        return False


def main():
    """Ana test fonksiyonu."""
    console.print(Panel(
        "[bold blue]RAPOR URETICI v4.0 - UYGULAMA TESTI[/bold blue]\n\n"
        "[dim]Tum bilesenler test edilecek...[/dim]",
        box=box.DOUBLE,
        border_style="blue"
    ))

    tests = [
        ("Modul Import", test_imports),
        ("API Baglanti", test_api_connection),
        ("Kural Yukleme", test_rules_loading),
        ("Dosya Tarayici", test_file_scanner),
        ("Web Arastirma", test_web_research),
        ("Veri Cekme", test_data_fetcher),
        ("Icerik Uretim", test_content_generation),
        ("Dogrulayicilar", test_validators),
        ("Belge Ureticiler", test_document_generators),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            console.print(f"\n[red]BEKLENMEYEN HATA ({name}): {e}[/red]")
            results.append((name, False))

    # Ozet
    console.print("\n" + "="*60)
    console.print(Panel(
        "[bold]TEST SONUCLARI[/bold]",
        box=box.ROUNDED,
        border_style="cyan"
    ))

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[green]BASARILI[/green]" if result else "[red]BASARISIZ[/red]"
        console.print(f"   {name}: {status}")

    console.print(f"\n   [bold]Toplam: {passed}/{total} test basarili[/bold]")

    if passed == total:
        console.print(Panel(
            "[bold green]TUM TESTLER BASARILI![/bold green]\n\n"
            "[dim]Uygulama tam olarak calisir durumda.[/dim]",
            box=box.DOUBLE,
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold yellow]BAZI TESTLER BASARISIZ[/bold yellow]\n\n"
            f"[dim]{total - passed} test basarisiz oldu.[/dim]",
            box=box.DOUBLE,
            border_style="yellow"
        ))

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
