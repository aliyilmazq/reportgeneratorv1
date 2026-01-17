"""Kullanıcı etkileşim modülü - Sorular ve girdiler."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

# Security validators
from .utils.validators import PathValidator, TextValidator
from .utils.exceptions import PathTraversalError, InputValidationError

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class UserInput:
    """Kullanıcı girdilerini tutan sınıf."""
    input_path: str
    output_path: str
    output_type: str
    output_type_name: str
    language: str
    output_format: str
    special_notes: str
    file_stats: Dict[str, int]


class CLI:
    """Komut satırı arayüzü."""

    OUTPUT_TYPES = [
        ("is_plani", "İş Planı", "Kapsamlı iş planı dokümanı"),
        ("proje_raporu", "Proje Raporu", "Proje durumu ve sonuç raporu"),
        ("sunum", "Sunum", "Özet sunum dokümanı"),
        ("on_fizibilite", "Ön Fizibilite", "Fizibilite değerlendirme raporu"),
        ("teknik_dok", "Teknik Dokümantasyon", "Teknik detay dokümanı"),
        ("analiz_raporu", "Analiz Raporu", "Veri analizi ve bulgular raporu"),
        ("kisa_not", "Kısa Not / Özet", "Kısa özet dokümanı"),
    ]

    LANGUAGES = [
        ("tr", "Türkçe"),
        ("en", "İngilizce"),
    ]

    OUTPUT_FORMATS = [
        ("docx", "DOCX (Word)"),
        ("pdf", "PDF"),
        ("both", "Her ikisi"),
    ]

    SUPPORTED_EXTENSIONS = {
        'documents': ['.pdf', '.docx', '.doc'],
        'spreadsheets': ['.xlsx', '.xls', '.csv'],
        'images': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
    }

    def __init__(self):
        self.console = console

    def show_header(self):
        """Başlık göster."""
        header = Panel(
            "[bold blue]RAPOR ÜRETİCİ[/bold blue] [dim]v1.0[/dim]\n"
            "[dim]Dokümanlarınızı kurumsal rapora dönüştürün[/dim]",
            box=box.DOUBLE,
            padding=(1, 2)
        )
        self.console.print(header)
        self.console.print()

    def get_language(self) -> str:
        """Dil seçimi - İLK SORU."""
        self.console.print("[bold cyan][1/5][/bold cyan] [bold]Çıktı dilini seçin:[/bold]")

        for i, (lang_id, name) in enumerate(self.LANGUAGES, 1):
            self.console.print(f"      [cyan]{i}.[/cyan] {name}")

        while True:
            choice = Prompt.ask("      [green]>[/green]").strip()

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.LANGUAGES):
                    selected = self.LANGUAGES[idx]
                    self.console.print(f"      [green]✓[/green] Seçildi: {selected[1]}\n")
                    return selected[0]
            except ValueError:
                pass

            self.console.print(f"      [red]Geçersiz seçim. 1-{len(self.LANGUAGES)} arası bir sayı girin.[/red]")

    def _normalize_path(self, path: str) -> str:
        """Terminale sürüklenen yolları normalize et."""
        # Baş ve sondaki boşlukları temizle
        path = path.strip()

        # Tırnak işaretlerini kaldır (tek veya çift)
        if (path.startswith('"') and path.endswith('"')) or \
           (path.startswith("'") and path.endswith("'")):
            path = path[1:-1]

        # Backslash escape'lerini kaldır (örn: '\ ' -> ' ')
        path = path.replace('\\ ', ' ')
        path = path.replace("\\'", "'")
        path = path.replace('\\(', '(')
        path = path.replace('\\)', ')')
        path = path.replace('\\&', '&')

        # ~ işaretini genişlet
        path = os.path.expanduser(path)

        return path

    def get_input_path(self) -> str:
        """Girdi klasörü yolunu al."""
        self.console.print("[bold cyan][2/5][/bold cyan] [bold]Girdi klasörü yolunu girin:[/bold]")
        self.console.print("[dim]Taranacak dokümanların bulunduğu klasör[/dim]")

        while True:
            path = Prompt.ask("      [green]>[/green]").strip()

            # Yolu normalize et (escape karakterleri, tırnaklar vb.)
            path = self._normalize_path(path)

            if not path:
                self.console.print("      [red]Lütfen bir yol girin.[/red]")
                continue

            # Security: Path traversal kontrolu
            try:
                validated_path = PathValidator.validate_directory(path, create_if_missing=False)
                return str(validated_path)
            except PathTraversalError:
                self.console.print("      [red]Guvenlik hatasi: Gecersiz yol tespit edildi.[/red]")
                logger.warning(f"Path traversal attempt: {path}")
                continue
            except InputValidationError as e:
                if not os.path.exists(path):
                    self.console.print(f"      [red]Klasör bulunamadı: {path}[/red]")
                elif not os.path.isdir(path):
                    self.console.print("      [red]Bu bir klasör değil.[/red]")
                else:
                    self.console.print(f"      [red]Gecersiz yol: {e.message}[/red]")
                continue

    def scan_and_show_stats(self, input_path: str) -> Dict[str, int]:
        """Dosyaları tara ve istatistik göster."""
        stats = {
            'pdf': 0,
            'excel': 0,
            'word': 0,
            'image': 0,
            'total': 0
        }

        all_extensions = []
        for ext_list in self.SUPPORTED_EXTENSIONS.values():
            all_extensions.extend(ext_list)

        for root, dirs, files in os.walk(input_path):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in all_extensions:
                    stats['total'] += 1
                    if ext == '.pdf':
                        stats['pdf'] += 1
                    elif ext in ['.xlsx', '.xls', '.csv']:
                        stats['excel'] += 1
                    elif ext in ['.docx', '.doc']:
                        stats['word'] += 1
                    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                        stats['image'] += 1

        if stats['total'] == 0:
            self.console.print("\n      [red]Desteklenen dosya bulunamadı![/red]")
            self.console.print("      [dim]Desteklenen formatlar: PDF, Excel, Word, Görsel[/dim]\n")
            return stats

        # İstatistik tablosu
        self.console.print()
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Tür", style="cyan")
        table.add_column("Adet", justify="right", style="green")

        if stats['pdf'] > 0:
            table.add_row("PDF", str(stats['pdf']))
        if stats['excel'] > 0:
            table.add_row("Excel", str(stats['excel']))
        if stats['word'] > 0:
            table.add_row("Word", str(stats['word']))
        if stats['image'] > 0:
            table.add_row("Görsel", str(stats['image']))
        table.add_row("─" * 10, "─" * 5)
        table.add_row("[bold]Toplam[/bold]", f"[bold]{stats['total']}[/bold]")

        self.console.print("      [green]✓[/green] Bulunan dosyalar:")
        self.console.print(table)
        self.console.print()

        return stats

    def get_output_path(self) -> str:
        """Çıktı klasörü yolunu al."""
        self.console.print("[bold cyan][3/6][/bold cyan] [bold]Çıktı klasörü yolunu girin:[/bold]")
        self.console.print("[dim]Rapor bu klasöre kaydedilecek[/dim]")

        while True:
            path = Prompt.ask("      [green]>[/green]").strip()

            # Yolu normalize et (escape karakterleri, tırnaklar vb.)
            path = self._normalize_path(path)

            if not path:
                self.console.print("      [red]Lütfen bir yol girin.[/red]")
                continue

            # Security: Path traversal kontrolu
            try:
                # Klasör yoksa oluştur
                if not os.path.exists(path):
                    create = Confirm.ask(f"      [yellow]Klasör mevcut değil. Oluşturulsun mu?[/yellow]")
                    if create:
                        validated_path = PathValidator.validate_directory(path, create_if_missing=True)
                        self.console.print(f"      [green]✓[/green] Klasör oluşturuldu: {validated_path}")
                        return str(validated_path)
                    else:
                        continue
                else:
                    validated_path = PathValidator.validate_directory(path, create_if_missing=False)
                    return str(validated_path)
            except PathTraversalError:
                self.console.print("      [red]Guvenlik hatasi: Gecersiz yol tespit edildi.[/red]")
                logger.warning(f"Path traversal attempt: {path}")
                continue
            except InputValidationError as e:
                self.console.print(f"      [red]Klasör oluşturulamadı: {e.message}[/red]")
                continue

    def get_output_type(self) -> tuple:
        """Çıktı türünü seç."""
        self.console.print("[bold cyan][3/5][/bold cyan] [bold]Çıktı türünü seçin:[/bold]")

        for i, (type_id, name, desc) in enumerate(self.OUTPUT_TYPES, 1):
            self.console.print(f"      [cyan]{i}.[/cyan] {name}")
            self.console.print(f"         [dim]{desc}[/dim]")

        while True:
            choice = Prompt.ask("      [green]>[/green]").strip()

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.OUTPUT_TYPES):
                    selected = self.OUTPUT_TYPES[idx]
                    self.console.print(f"      [green]✓[/green] Seçildi: {selected[1]}\n")
                    return selected[0], selected[1]
            except ValueError:
                pass

            self.console.print(f"      [red]Geçersiz seçim. 1-{len(self.OUTPUT_TYPES)} arası bir sayı girin.[/red]")

    def get_output_format(self) -> str:
        """Çıktı formatını seç."""
        self.console.print("[bold cyan][4/5][/bold cyan] [bold]Çıktı formatını seçin:[/bold]")

        for i, (fmt_id, name) in enumerate(self.OUTPUT_FORMATS, 1):
            self.console.print(f"      [cyan]{i}.[/cyan] {name}")

        while True:
            choice = Prompt.ask("      [green]>[/green]").strip()

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.OUTPUT_FORMATS):
                    selected = self.OUTPUT_FORMATS[idx]
                    self.console.print(f"      [green]✓[/green] Seçildi: {selected[1]}\n")
                    return selected[0]
            except ValueError:
                pass

            self.console.print(f"      [red]Geçersiz seçim. 1-{len(self.OUTPUT_FORMATS)} arası bir sayı girin.[/red]")

    def get_special_notes(self) -> str:
        """Özel notları al."""
        self.console.print("[bold cyan][5/5][/bold cyan] [bold]Konu hakkında özel notlarınız:[/bold]")
        self.console.print("[dim]Dikkat edilmesi gerekenler, vurgular, özel talepler[/dim]")
        self.console.print("[dim](Boş bırakmak için Enter'a basın)[/dim]")

        notes = Prompt.ask("      [green]>[/green]", default="").strip()

        if notes:
            # Security: Prompt injection kontrolu
            if TextValidator.check_prompt_injection(notes):
                self.console.print("      [yellow]Uyari: Gecersiz karakterler temizlendi[/yellow]")
                notes = TextValidator.sanitize(notes, max_length=5000, strip_html=True)
                logger.warning("Prompt injection attempt detected in special notes")
            else:
                notes = TextValidator.sanitize(notes, max_length=5000)
            self.console.print(f"      [green]✓[/green] Notlar kaydedildi\n")
        else:
            self.console.print(f"      [dim]Özel not girilmedi[/dim]\n")

        return notes

    def show_summary(self, user_input: UserInput):
        """Seçimlerin özetini göster."""
        self.console.print()
        summary = Table(title="Seçimleriniz", box=box.ROUNDED, show_header=False)
        summary.add_column("Alan", style="cyan")
        summary.add_column("Değer", style="white")

        summary.add_row("Klasör", user_input.input_path)
        summary.add_row("Rapor Türü", user_input.output_type_name)
        summary.add_row("Dil", "Türkçe" if user_input.language == "tr" else "İngilizce")
        summary.add_row("Format", user_input.output_format.upper())
        summary.add_row("Dosya Sayısı", str(user_input.file_stats['total']))

        if user_input.special_notes:
            notes_display = user_input.special_notes[:50]
            if len(user_input.special_notes) > 50:
                notes_display += "..."
            summary.add_row("Özel Notlar", notes_display)

        self.console.print(summary)
        self.console.print()

    def confirm_start(self) -> bool:
        """Başlamak için onay al."""
        return Confirm.ask("[bold]Rapor oluşturma işlemi başlatılsın mı?[/bold]")

    def run(self) -> Optional[UserInput]:
        """Tüm akışı çalıştır."""
        self.show_header()

        # 1. Dil seçimi (İLK SORU)
        language = self.get_language()

        # 2. Girdi klasörü
        input_path = self.get_input_path()

        # Dosyaları tara ve göster
        file_stats = self.scan_and_show_stats(input_path)
        if file_stats['total'] == 0:
            return None

        # Çıktı klasörü = Girdi klasörü (otomatik)
        output_path = input_path

        # 3. Çıktı türü
        output_type, output_type_name = self.get_output_type()

        # 4. Format
        output_format = self.get_output_format()

        # 5. Özel notlar
        special_notes = self.get_special_notes()

        # Kullanıcı girdisini oluştur
        user_input = UserInput(
            input_path=input_path,
            output_path=output_path,
            output_type=output_type,
            output_type_name=output_type_name,
            language=language,
            output_format=output_format,
            special_notes=special_notes,
            file_stats=file_stats
        )

        # Özet göster
        self.show_summary(user_input)

        # Onay al
        if self.confirm_start():
            return user_input
        else:
            self.console.print("[yellow]İşlem iptal edildi.[/yellow]")
            return None


def get_user_input() -> Optional[UserInput]:
    """Ana fonksiyon - kullanıcı girdisini al."""
    cli = CLI()
    return cli.run()
