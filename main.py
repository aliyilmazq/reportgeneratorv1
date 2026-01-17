#!/usr/bin/env python3
"""
Rapor Üretici v4.0 PRO - Ana Program
=====================================
Gerçek web araştırması ve zengin içerik üretimi ile kurumsal rapor üretici.

Yenilikler v4.0:
- Gerçek web araştırması (DuckDuckGo API)
- Web tabanlı TÜİK/TCMB verileri
- Çok fazlı içerik üretimi
- Kaynak referansları ve kaynakça
- İlerleme takibi ve tahmini süre
- Minimum 500+ kelime/bölüm
- Paragraf tabanlı zengin içerik

ÖNEMLİ: Uygulama başlarken TÜM KURALLAR yüklenir ve bellekte tutulur.
Kurallar yüklenmeden hiçbir işlem YAPILAMAZ!
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent))

# .env dosyasini yukle (varsa)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv yuklu degil, devam et

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL KURAL SİSTEMİ - UYGULAMA BOYUNCA BELLEKTE KALIR
# ═══════════════════════════════════════════════════════════════════════════
LOADED_RULES = None  # Global kurallar - uygulama boyunca bellekte


def print_banner():
    """Başlık banner'ı."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║              RAPOR ÜRETİCİ v4.0 PRO                          ║
║         Claude Opus 4.5 + Gerçek Web Araştırması             ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Gerçek Web Araştırması (DuckDuckGo)                       ║
║  ✓ Güncel TÜİK/TCMB Verileri (Web Tabanlı)                   ║
║  ✓ Kaynak Referansları ve Kaynakça                           ║
║  ✓ Zengin Paragraf İçerik (500+ kelime/bölüm)                ║
║  ✓ Çok Fazlı İçerik Üretimi                                  ║
║  ✓ Gerçek Zamanlı İlerleme Takibi                            ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold blue")


def check_dependencies():
    """Gerekli kütüphanelerin yüklü olduğunu kontrol et."""
    missing = []
    optional_missing = []

    # Zorunlu
    required = [
        ("pdfplumber", "pdfplumber"),
        ("pandas", "pandas"),
        ("openpyxl", "openpyxl"),
        ("docx", "python-docx"),
        ("anthropic", "anthropic"),
        ("rich", "rich"),
        ("yaml", "PyYAML"),
        ("reportlab", "reportlab"),
        ("PIL", "Pillow"),
    ]

    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    # Yeni v4.0 bağımlılıkları
    new_required = [
        ("duckduckgo_search", "duckduckgo_search", "Web araştırması"),
        ("httpx", "httpx", "Web istekleri"),
        ("bs4", "beautifulsoup4", "HTML işleme"),
    ]

    for module, package, feature in new_required:
        try:
            __import__(module)
        except ImportError:
            optional_missing.append((package, feature))

    # Opsiyonel
    optional = [
        ("chromadb", "chromadb", "RAG sistemi"),
        ("matplotlib", "matplotlib", "Grafik üretimi"),
        ("plotly", "plotly", "Gelişmiş grafikler"),
        ("sentence_transformers", "sentence-transformers", "Local embedding"),
    ]

    for module, package, feature in optional:
        try:
            __import__(module)
        except ImportError:
            optional_missing.append((package, feature))

    if missing:
        console.print("[red]Eksik zorunlu kütüphaneler![/red]")
        console.print(f"Yüklemek için: [cyan]pip install {' '.join(missing)}[/cyan]")
        return False

    if optional_missing:
        console.print("[yellow]Bazı kütüphaneler eksik (bazı özellikler sınırlı çalışabilir):[/yellow]")
        for pkg, feature in optional_missing[:5]:  # İlk 5'i göster
            console.print(f"  - {pkg}: {feature}")
        all_packages = ' '.join(p for p, _ in optional_missing)
        console.print(f"[dim]Yüklemek için: pip install {all_packages}[/dim]")
        console.print()

    return True


def check_api_keys():
    """API anahtarlarını kontrol et."""
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')

    if not anthropic_key:
        console.print("[red]ANTHROPIC_API_KEY ortam değişkeni ayarlanmamış![/red]")
        console.print("API anahtarınızı şu şekilde ayarlayın:")
        console.print("[cyan]export ANTHROPIC_API_KEY='your-api-key-here'[/cyan]")
        return False

    return True


def load_rules_at_startup():
    """
    UYGULAMA BAŞLANGIÇINDA TÜM KURALLARI YÜKLE.

    Bu fonksiyon:
    1. rules/ klasöründeki 6 kural dosyasını tek tek okur
    2. Her dosyayı parse eder ve doğrular
    3. Kuralları global LOADED_RULES değişkenine yükler
    4. Kurallar bellekte kalır ve uygulama boyunca erişilebilir olur

    KURALLAR YÜKLENMEDEN UYGULAMA DEVAM ETMEZ!
    """
    global LOADED_RULES

    from src.rules.rules_loader import RulesLoader, RulesLoadError, set_global_rules

    console.print()
    console.print(Panel(
        "[bold yellow]KURALLAR YÜKLENİYOR[/bold yellow]\n\n"
        "[dim]Uygulama başlamadan önce tüm kurallar okunmalıdır.[/dim]\n"
        "[dim]Kurallar yüklenmeden hiçbir işlem yapılamaz![/dim]",
        box=box.ROUNDED,
        border_style="yellow"
    ))
    console.print()

    rules_loader = RulesLoader()

    # Kural dosyalarını tek tek oku ve göster
    rule_files = [
        ("01_genel_kurallar.md", "Genel Kurallar"),
        ("02_arastirma_kurallari.md", "Araştırma Kuralları"),
        ("03_icerik_uretim_kurallari.md", "İçerik Üretim Kuralları"),
        ("04_kaynak_kullanim_kurallari.md", "Kaynak Kullanım Kuralları"),
        ("05_dogrulama_kurallari.md", "Doğrulama Kuralları"),
        ("06_kalite_standartlari.md", "Kalite Standartları"),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Kurallar okunuyor...", total=len(rule_files))

        for filename, description in rule_files:
            progress.update(task, description=f"[cyan]Okunuyor: {description}")
            time.sleep(0.3)  # Her dosya için kısa bekleme (görsel feedback)
            progress.advance(task)

    try:
        # Tüm kuralları yükle
        LOADED_RULES = rules_loader.load_all_rules()

        # Global olarak da kaydet (diğer modüller için)
        set_global_rules(LOADED_RULES)

        # Başarı mesajı ve kural özeti
        console.print()
        console.print(Panel(
            f"[bold green]✅ TÜM KURALLAR BAŞARIYLA YÜKLENDİ[/bold green]\n\n"
            f"[white]Yüklenen Kurallar:[/white]\n"
            f"  • Genel Kurallar: [green]✓[/green]\n"
            f"  • Araştırma Kuralları: [green]✓[/green]\n"
            f"  • İçerik Üretim Kuralları: [green]✓[/green]\n"
            f"  • Kaynak Kullanım Kuralları: [green]✓[/green]\n"
            f"  • Doğrulama Kuralları: [green]✓[/green]\n"
            f"  • Kalite Standartları: [green]✓[/green]\n\n"
            f"[white]Aktif Minimum Gereksinimler:[/white]\n"
            f"  • Kelime/Bölüm: [cyan]{LOADED_RULES.min_words_per_section}[/cyan]\n"
            f"  • Paragraf/Bölüm: [cyan]{LOADED_RULES.min_paragraphs_per_section}[/cyan]\n"
            f"  • Kaynak/Bölüm: [cyan]{LOADED_RULES.min_sources_per_section}[/cyan]\n"
            f"  • Toplam Kaynak: [cyan]{LOADED_RULES.min_total_sources}[/cyan]\n"
            f"  • Min Kalite Puanı: [cyan]{LOADED_RULES.min_quality_score}%[/cyan]\n\n"
            f"[dim]Kurallar bellekte tutulacak ve tüm işlemlerde kullanılacak.[/dim]",
            box=box.DOUBLE,
            border_style="green",
            title="Kural Sistemi"
        ))
        console.print()

        return True

    except RulesLoadError as e:
        console.print()
        console.print(Panel(
            f"[bold red]❌ KURALLAR YÜKLENEMEDİ![/bold red]\n\n"
            f"[white]Hata:[/white]\n{str(e)}\n\n"
            f"[yellow]Çözüm:[/yellow]\n"
            f"  1. 'rules/' klasörünün var olduğundan emin olun\n"
            f"  2. Tüm kural dosyalarının mevcut olduğunu kontrol edin\n"
            f"  3. Dosya izinlerini kontrol edin\n\n"
            f"[bold red]UYGULAMA BAŞLATILMADI![/bold red]\n"
            f"[dim]Kurallar yüklenmeden rapor üretimi yasaktır.[/dim]",
            box=box.DOUBLE,
            border_style="red",
            title="Kritik Hata"
        ))
        return False

    except Exception as e:
        console.print(f"[red]Beklenmeyen hata: {str(e)}[/red]")
        return False


def get_loaded_rules():
    """
    Global olarak yüklenmiş kuralları döndür.

    Bu fonksiyon diğer modüller tarafından kuralları erişmek için kullanılır.
    """
    global LOADED_RULES
    if LOADED_RULES is None:
        raise RuntimeError(
            "KURALLAR YÜKLENMEMİŞ!\n"
            "Uygulama doğru başlatılmamış olabilir.\n"
            "load_rules_at_startup() fonksiyonu çağrılmalıdır."
        )
    return LOADED_RULES


def main():
    """Ana program."""

    # Banner
    print_banner()

    # Bağımlılık kontrolü
    if not check_dependencies():
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════════════════
    # KURAL YÜKLEME - EN ÖNCELİKLİ ADIM
    # Kurallar yüklenmeden hiçbir işlem yapılamaz!
    # ═══════════════════════════════════════════════════════════════════════
    if not load_rules_at_startup():
        console.print("\n[bold red]Program sonlandırıldı: Kurallar yüklenemedi.[/bold red]")
        sys.exit(1)

    # Kurallar başarıyla yüklendi, şimdi API kontrolü yapılabilir
    # API anahtarı kontrolü
    if not check_api_keys():
        sys.exit(1)

    # Modülleri import et
    try:
        from src.cli import get_user_input
        from src.orchestrator import ReportOrchestrator, UserInput
    except ImportError as e:
        console.print(f"[red]Modül import hatası: {e}[/red]")
        console.print("[dim]Lütfen tüm bağımlılıkların yüklü olduğundan emin olun.[/dim]")
        sys.exit(1)

    try:
        # Kullanıcı girdilerini al
        user_input_raw = get_user_input()

        if user_input_raw is None:
            console.print("[yellow]Program sonlandırıldı.[/yellow]")
            sys.exit(0)

        # Kuralların bellekte olduğunu doğrula
        rules = get_loaded_rules()
        console.print()
        console.print(Panel(
            "[bold]Rapor üretimi başlıyor...[/bold]\n\n"
            f"[green]✓ Kurallar bellekte aktif[/green]\n"
            f"[dim]  - Min kelime/bölüm: {rules.min_words_per_section}[/dim]\n"
            f"[dim]  - Min kaynak: {rules.min_total_sources}[/dim]\n"
            f"[dim]  - Min kalite: {rules.min_quality_score}%[/dim]\n\n"
            "[dim]Bu işlem 30-60 dakika sürebilir.[/dim]\n"
            "[dim]Gerçek web araştırması ve zengin içerik üretimi yapılacak.[/dim]",
            box=box.DOUBLE,
            style="bold blue"
        ))
        console.print()

        # UserInput oluştur
        user_input = UserInput(
            input_path=user_input_raw.input_path,
            output_type=user_input_raw.output_type,
            output_format=user_input_raw.output_format,
            language=user_input_raw.language,
            special_notes=user_input_raw.special_notes or ""
        )

        # Output dizini
        output_dir = Path(user_input_raw.output_path).parent if hasattr(user_input_raw, 'output_path') else Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Orchestrator oluştur ve rapor üret
        # NOT: Kurallar zaten global LOADED_RULES'da bellekte tutuluyor
        orchestrator = ReportOrchestrator(
            output_dir=str(output_dir),
            use_live_progress=True
        )

        report = orchestrator.generate_report(user_input)

        # Sonuç paneli
        console.print()
        console.print(Panel(
            f"[bold green]✅ RAPOR BAŞARIYLA OLUŞTURULDU[/bold green]\n\n"
            f"📊 Toplam Süre: {report.generation_time_seconds/60:.1f} dakika\n"
            f"📝 Toplam Kelime: {report.statistics.get('total_words', 0):,}\n"
            f"📄 Bölüm Sayısı: {report.statistics.get('total_sections', 0)}\n"
            f"🔗 Kaynak Sayısı: {report.statistics.get('total_sources', 0)}\n"
            f"📚 Alıntı Sayısı: {report.statistics.get('total_citations', 0)}\n"
            f"📈 Kalite Puanı: {report.statistics.get('average_quality_score', 0):.0f}/100\n\n"
            f"📁 Oluşturulan Dosyalar:\n" + "\n".join(f"   • {f}" for f in report.output_files),
            box=box.DOUBLE,
            title="Rapor Üretici v4.0 Pro",
            border_style="green"
        ))

    except KeyboardInterrupt:
        console.print("\n[yellow]İşlem kullanıcı tarafından iptal edildi.[/yellow]")
        sys.exit(0)

    except Exception as e:
        console.print(f"\n[red]Hata oluştu: {str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
