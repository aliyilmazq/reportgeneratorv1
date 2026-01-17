"""Dosya tarayıcı modülü - Klasördeki tüm desteklenen dosyaları bulur."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Iterator, ClassVar
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Type imports
from .types import FileCategory, PathLike, ProgressCallback

console = Console()


@dataclass
class FileInfo:
    """Dosya bilgisi."""
    path: str
    name: str
    extension: str
    size: int
    category: FileCategory
    modified_time: datetime

    @property
    def size_formatted(self) -> str:
        """Okunabilir boyut."""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e cevir."""
        return {
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "size": self.size,
            "size_formatted": self.size_formatted,
            "category": self.category.value if isinstance(self.category, FileCategory) else self.category,
            "modified_time": self.modified_time.isoformat()
        }


@dataclass
class ScanResult:
    """Tarama sonucu."""
    files: List[FileInfo] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    total_size: int = 0
    scan_time: float = 0.0

    @property
    def total_files(self) -> int:
        """Toplam dosya sayisi."""
        return len(self.files)

    def get_files_by_category(self, category: FileCategory) -> List[FileInfo]:
        """Kategoriye gore dosyalari filtrele."""
        cat_value = category.value if isinstance(category, FileCategory) else category
        return [f for f in self.files if f.category == cat_value or
                (isinstance(f.category, FileCategory) and f.category.value == cat_value)]

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e cevir."""
        return {
            "files": [f.to_dict() for f in self.files],
            "stats": self.stats,
            "total_size": self.total_size,
            "total_files": self.total_files,
            "scan_time": self.scan_time
        }


class FileScanner:
    """Dosya tarayıcı sınıfı."""

    # Class-level type annotation
    EXTENSIONS: ClassVar[Dict[str, List[str]]] = {
        'pdf': ['.pdf'],
        'excel': ['.xlsx', '.xls', '.csv'],
        'word': ['.docx', '.doc'],
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
    }

    def __init__(self, console_instance: Optional[Console] = None) -> None:
        self.console: Console = console_instance or console
        # Uzantıdan kategoriye map
        self._ext_to_category: Dict[str, str] = {}
        for category, extensions in self.EXTENSIONS.items():
            for ext in extensions:
                self._ext_to_category[ext] = category

    def get_supported_extensions(self) -> List[str]:
        """Desteklenen tüm uzantıları döndür."""
        extensions: List[str] = []
        for ext_list in self.EXTENSIONS.values():
            extensions.extend(ext_list)
        return extensions

    def get_category(self, extension: str) -> FileCategory:
        """Uzantıdan kategori al."""
        cat_str = self._ext_to_category.get(extension.lower(), 'unknown')
        try:
            return FileCategory(cat_str)
        except ValueError:
            return FileCategory.UNKNOWN

    def scan(self, input_path: PathLike, show_progress: bool = True) -> ScanResult:
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

    def get_files_by_category(
        self,
        result: ScanResult,
        category: FileCategory
    ) -> List[FileInfo]:
        """Belirli kategorideki dosyaları al."""
        return result.get_files_by_category(category)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Boyutu okunabilir formata çevir."""
        size: float = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

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
