"""İçerik birleştirici modülü - Tüm parse edilmiş içerikleri birleştirir."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ..scanner import FileInfo, ScanResult
from ..parsers.pdf_parser import PDFParser, PDFContent
from ..parsers.excel_parser import ExcelParser, ExcelContent
from ..parsers.word_parser import WordParser, WordContent
from ..parsers.image_analyzer import ImageAnalyzer, ImageContent

console = Console()


@dataclass
class AggregatedContent:
    """Birleştirilmiş içerik."""
    pdf_contents: List[Dict[str, Any]] = field(default_factory=list)
    excel_contents: List[Dict[str, Any]] = field(default_factory=list)
    word_contents: List[Dict[str, Any]] = field(default_factory=list)
    image_contents: List[Dict[str, Any]] = field(default_factory=list)

    total_files: int = 0
    total_pages: int = 0
    total_tables: int = 0
    total_images: int = 0

    all_text: str = ""
    all_tables: List[Dict[str, Any]] = field(default_factory=list)

    errors: List[Dict[str, str]] = field(default_factory=list)


class ContentAggregator:
    """İçerik birleştirici sınıfı."""

    def __init__(self, analyze_images: bool = True, language: str = "tr"):
        self.analyze_images = analyze_images
        self.language = language

        # Parser'ları başlat
        self.pdf_parser = None
        self.excel_parser = None
        self.word_parser = None
        self.image_analyzer = None

        self._init_parsers()

    def _init_parsers(self):
        """Parser'ları başlat."""
        try:
            self.pdf_parser = PDFParser()
        except ImportError as e:
            console.print(f"[yellow]Uyarı: PDF parser yüklenemedi: {e}[/yellow]")

        try:
            self.excel_parser = ExcelParser()
        except ImportError as e:
            console.print(f"[yellow]Uyarı: Excel parser yüklenemedi: {e}[/yellow]")

        try:
            self.word_parser = WordParser()
        except ImportError as e:
            console.print(f"[yellow]Uyarı: Word parser yüklenemedi: {e}[/yellow]")

        try:
            self.image_analyzer = ImageAnalyzer()
        except ImportError as e:
            console.print(f"[yellow]Uyarı: Image analyzer yüklenemedi: {e}[/yellow]")

    def aggregate(self, scan_result: ScanResult, show_progress: bool = True) -> AggregatedContent:
        """Tüm dosyaları parse et ve birleştir."""
        content = AggregatedContent()
        content.total_files = scan_result.stats['total']

        all_texts = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Dosyalar işleniyor...", total=len(scan_result.files))

                for file_info in scan_result.files:
                    progress.update(task, description=f"İşleniyor: {file_info.name[:30]}...")

                    try:
                        self._process_file(file_info, content, all_texts)
                    except Exception as e:
                        content.errors.append({
                            "file": file_info.path,
                            "error": str(e)
                        })

                    progress.advance(task)
        else:
            for file_info in scan_result.files:
                try:
                    self._process_file(file_info, content, all_texts)
                except Exception as e:
                    content.errors.append({
                        "file": file_info.path,
                        "error": str(e)
                    })

        # Tüm metni birleştir
        content.all_text = "\n\n---\n\n".join(all_texts)

        return content

    def _process_file(self, file_info: FileInfo, content: AggregatedContent, all_texts: List[str]):
        """Tek bir dosyayı işle."""
        if file_info.category == 'pdf' and self.pdf_parser:
            self._process_pdf(file_info, content, all_texts)

        elif file_info.category == 'excel' and self.excel_parser:
            self._process_excel(file_info, content, all_texts)

        elif file_info.category == 'word' and self.word_parser:
            self._process_word(file_info, content, all_texts)

        elif file_info.category == 'image' and self.image_analyzer:
            self._process_image(file_info, content, all_texts)

    def _process_pdf(self, file_info: FileInfo, content: AggregatedContent, all_texts: List[str]):
        """PDF dosyasını işle."""
        pdf_content = self.pdf_parser.parse(file_info.path)
        content_dict = self.pdf_parser.to_dict(pdf_content)

        content.pdf_contents.append(content_dict)
        content.total_pages += pdf_content.page_count

        # Metni ekle
        if pdf_content.full_text:
            all_texts.append(f"[Kaynak: {file_info.name}]\n{pdf_content.full_text}")

        # Tabloları ekle
        for page in pdf_content.pages:
            for table in page.tables:
                content.total_tables += 1
                content.all_tables.append({
                    "source": file_info.name,
                    "page": page.page_number,
                    "headers": table.headers,
                    "data": table.data
                })

            content.total_images += len(page.images)

    def _process_excel(self, file_info: FileInfo, content: AggregatedContent, all_texts: List[str]):
        """Excel dosyasını işle."""
        excel_content = self.excel_parser.parse(file_info.path)
        content_dict = self.excel_parser.to_dict(excel_content)

        content.excel_contents.append(content_dict)

        # Tabloları ekle
        for sheet in excel_content.sheets:
            content.total_tables += 1
            content.all_tables.append({
                "source": file_info.name,
                "sheet": sheet.name,
                "headers": sheet.headers,
                "data": sheet.data
            })

            # Markdown formatında metne ekle
            markdown = self.excel_parser.to_markdown_tables(excel_content)
            if markdown:
                all_texts.append(f"[Kaynak: {file_info.name}]\n{markdown}")

    def _process_word(self, file_info: FileInfo, content: AggregatedContent, all_texts: List[str]):
        """Word dosyasını işle."""
        word_content = self.word_parser.parse(file_info.path)
        content_dict = self.word_parser.to_dict(word_content)

        content.word_contents.append(content_dict)
        content.total_images += word_content.image_count

        # Metni ekle
        if word_content.full_text:
            all_texts.append(f"[Kaynak: {file_info.name}]\n{word_content.full_text}")

        # Tabloları ekle
        for i, table in enumerate(word_content.tables):
            content.total_tables += 1
            content.all_tables.append({
                "source": file_info.name,
                "table_index": i + 1,
                "headers": table.headers,
                "data": table.data
            })

    def _process_image(self, file_info: FileInfo, content: AggregatedContent, all_texts: List[str]):
        """Görsel dosyasını işle."""
        image_content = self.image_analyzer.parse(
            file_info.path,
            analyze=self.analyze_images,
            language=self.language
        )
        content_dict = self.image_analyzer.to_dict(image_content)

        content.image_contents.append(content_dict)
        content.total_images += 1

        # Analizi metne ekle
        if image_content.analysis:
            all_texts.append(f"[Kaynak: {file_info.name} (Görsel)]\n{image_content.analysis}")
        elif image_content.description:
            all_texts.append(f"[Kaynak: {file_info.name} (Görsel)]\n{image_content.description}")

    def get_summary(self, content: AggregatedContent) -> Dict[str, Any]:
        """İçerik özetini al."""
        return {
            "total_files": content.total_files,
            "total_pages": content.total_pages,
            "total_tables": content.total_tables,
            "total_images": content.total_images,
            "pdf_count": len(content.pdf_contents),
            "excel_count": len(content.excel_contents),
            "word_count": len(content.word_contents),
            "image_count": len(content.image_contents),
            "error_count": len(content.errors),
            "text_length": len(content.all_text)
        }

    def print_summary(self, content: AggregatedContent):
        """Özeti yazdır."""
        from rich.table import Table
        from rich import box

        summary = self.get_summary(content)

        table = Table(title="İşleme Özeti", box=box.ROUNDED, show_header=False)
        table.add_column("Metrik", style="cyan")
        table.add_column("Değer", justify="right")

        table.add_row("Toplam Dosya", str(summary['total_files']))
        table.add_row("Toplam Sayfa", str(summary['total_pages']))
        table.add_row("Toplam Tablo", str(summary['total_tables']))
        table.add_row("Toplam Görsel", str(summary['total_images']))

        if summary['error_count'] > 0:
            table.add_row("[red]Hatalar[/red]", f"[red]{summary['error_count']}[/red]")

        console.print(table)

        # Hataları göster
        if content.errors:
            console.print("\n[yellow]Hatalar:[/yellow]")
            for error in content.errors[:5]:  # İlk 5 hatayı göster
                console.print(f"  - {Path(error['file']).name}: {error['error'][:50]}")
            if len(content.errors) > 5:
                console.print(f"  ... ve {len(content.errors) - 5} hata daha")
