"""Dosya tarayıcı modülü - Klasördeki tüm desteklenen dosyaları bulur."""

import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class FileInfo:
    """Dosya bilgisi."""
    path: str
    name: str
    extension: str
    size: int
    category: str  # 'pdf', 'excel', 'word', 'image'
    modified_time: datetime


@dataclass
class ScanResult:
    """Tarama sonucu."""
    files: List[FileInfo] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    total_size: int = 0
    scan_time: float = 0


class FileScanner:
    """Dosya tarayıcı sınıfı."""

    EXTENSIONS = {
        'pdf': ['.pdf'],
        'excel': ['.xlsx', '.xls', '.csv'],
        'word': ['.docx', '.doc'],
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
    }

    def __init__(self):
        self.console = console
        # Uzantıdan kategoriye map
        self._ext_to_category = {}
        for category, extensions in self.EXTENSIONS.items():
            for ext in extensions:
                self._ext_to_category[ext] = category

    def get_supported_extensions(self) -> List[str]:
        """Desteklenen tüm uzantıları döndür."""
        extensions = []
        for ext_list in self.EXTENSIONS.values():
            extensions.extend(ext_list)
        return extensions

    def get_category(self, extension: str) -> str:
        """Uzantıdan kategori al."""
        return self._ext_to_category.get(extension.lower(), 'unknown')

    def scan(self, input_path: str, show_progress: bool = True) -> ScanResult:
        """Klasörü tara ve desteklenen dosyaları bul."""
        import time
        start_time = time.time()

        result = ScanResult(
            stats={'pdf': 0, 'excel': 0, 'word': 0, 'image': 0, 'total': 0}
        )

        supported = self.get_supported_extensions()
        input_path = Path(input_path)

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Dosyalar taranıyor...", total=None)

                for root, dirs, files in os.walk(input_path):
                    # Gizli klasörleri atla
                    dirs[:] = [d for d in dirs if not d.startswith('.')]

                    for filename in files:
                        # Gizli dosyaları atla
                        if filename.startswith('.'):
                            continue

                        file_path = Path(root) / filename
                        extension = file_path.suffix.lower()

                        if extension in supported:
                            try:
                                stat = file_path.stat()
                                category = self.get_category(extension)

                                file_info = FileInfo(
                                    path=str(file_path),
                                    name=filename,
                                    extension=extension,
                                    size=stat.st_size,
                                    category=category,
                                    modified_time=datetime.fromtimestamp(stat.st_mtime)
                                )

                                result.files.append(file_info)
                                result.stats[category] += 1
                                result.stats['total'] += 1
                                result.total_size += stat.st_size

                                progress.update(task, description=f"Taranıyor: {filename[:40]}...")
                            except (OSError, PermissionError):
                                # Erişilemeyen dosyaları atla
                                continue
        else:
            # Progress bar olmadan tara
            for root, dirs, files in os.walk(input_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for filename in files:
                    if filename.startswith('.'):
                        continue

                    file_path = Path(root) / filename
                    extension = file_path.suffix.lower()

                    if extension in supported:
                        try:
                            stat = file_path.stat()
                            category = self.get_category(extension)

                            file_info = FileInfo(
                                path=str(file_path),
                                name=filename,
                                extension=extension,
                                size=stat.st_size,
                                category=category,
                                modified_time=datetime.fromtimestamp(stat.st_mtime)
                            )

                            result.files.append(file_info)
                            result.stats[category] += 1
                            result.stats['total'] += 1
                            result.total_size += stat.st_size
                        except (OSError, PermissionError):
                            continue

        # Dosyaları kategoriye göre sırala
        result.files.sort(key=lambda f: (f.category, f.name))

        result.scan_time = time.time() - start_time

        return result

    def get_files_by_category(self, result: ScanResult, category: str) -> List[FileInfo]:
        """Belirli kategorideki dosyaları al."""
        return [f for f in result.files if f.category == category]

    def format_size(self, size_bytes: int) -> str:
        """Boyutu okunabilir formata çevir."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def print_summary(self, result: ScanResult):
        """Tarama özetini yazdır."""
        from rich.table import Table
        from rich import box

        table = Table(
            title="Tarama Özeti",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Kategori", style="cyan")
        table.add_column("Dosya Sayısı", justify="right")
        table.add_column("Boyut", justify="right")

        category_names = {
            'pdf': 'PDF',
            'excel': 'Excel',
            'word': 'Word',
            'image': 'Görsel'
        }

        for category, name in category_names.items():
            count = result.stats.get(category, 0)
            if count > 0:
                files = self.get_files_by_category(result, category)
                size = sum(f.size for f in files)
                table.add_row(name, str(count), self.format_size(size))

        table.add_section()
        table.add_row(
            "[bold]Toplam[/bold]",
            f"[bold]{result.stats['total']}[/bold]",
            f"[bold]{self.format_size(result.total_size)}[/bold]"
        )

        self.console.print(table)
        self.console.print(f"[dim]Tarama süresi: {result.scan_time:.2f} saniye[/dim]")


def scan_directory(input_path: str, show_progress: bool = True) -> ScanResult:
    """Ana fonksiyon - klasörü tara."""
    scanner = FileScanner()
    return scanner.scan(input_path, show_progress)
