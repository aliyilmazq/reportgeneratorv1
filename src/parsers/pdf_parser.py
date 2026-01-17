"""PDF dosya okuyucu modülü."""

import io
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Iterator
from dataclasses import dataclass, field

try:
    import pdfplumber
    from pdfplumber.pdf import PDF as PdfPlumberPDF
except ImportError:
    pdfplumber = None
    PdfPlumberPDF = None

try:
    import fitz  # PyMuPDF
    from fitz import Document as FitzDocument
except ImportError:
    fitz = None
    FitzDocument = None

# Type alias
PathLike = Union[str, Path]

logger = logging.getLogger(__name__)


@dataclass
class PDFTable:
    """PDF'den çıkarılan tablo."""
    page_number: int
    data: List[List[str]]
    headers: List[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        """Satir sayisi."""
        return len(self.data)

    @property
    def column_count(self) -> int:
        """Sutun sayisi."""
        return len(self.headers) if self.headers else (len(self.data[0]) if self.data else 0)

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e cevir."""
        return {
            "page_number": self.page_number,
            "headers": self.headers,
            "data": self.data,
            "row_count": self.row_count,
            "column_count": self.column_count
        }


@dataclass
class PDFImage:
    """PDF'den çıkarılan görsel."""
    page_number: int
    image_data: bytes
    width: int
    height: int
    format: str

    @property
    def size_bytes(self) -> int:
        """Gorsel boyutu (byte)."""
        return len(self.image_data)


@dataclass
class PDFPage:
    """PDF sayfası içeriği."""
    page_number: int
    text: str
    tables: List[PDFTable] = field(default_factory=list)
    images: List[PDFImage] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        """Kelime sayisi."""
        return len(self.text.split())

    @property
    def has_content(self) -> bool:
        """Icerik var mi."""
        return bool(self.text.strip() or self.tables or self.images)


@dataclass
class PDFContent:
    """PDF dosyası içeriği."""
    source: str
    filename: str
    page_count: int
    pages: List[PDFPage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    full_text: str = ""

    @property
    def word_count(self) -> int:
        """Toplam kelime sayisi."""
        return len(self.full_text.split())

    @property
    def all_tables(self) -> List[PDFTable]:
        """Tum tablolar."""
        tables: List[PDFTable] = []
        for page in self.pages:
            tables.extend(page.tables)
        return tables

    @property
    def all_images(self) -> List[PDFImage]:
        """Tum gorseller."""
        images: List[PDFImage] = []
        for page in self.pages:
            images.extend(page.images)
        return images

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e cevir."""
        return {
            "source": self.source,
            "filename": self.filename,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "table_count": len(self.all_tables),
            "image_count": len(self.all_images),
            "metadata": self.metadata
        }


class PDFParser:
    """PDF dosya okuyucu sınıfı."""

    def __init__(
        self,
        extract_images: bool = True,
        extract_tables: bool = True
    ) -> None:
        self.extract_images: bool = extract_images
        self.extract_tables: bool = extract_tables
        self._current_doc: Optional[Any] = None
        self._closed: bool = False

        if pdfplumber is None:
            raise ImportError("pdfplumber kütüphanesi yüklü değil. 'pip install pdfplumber' komutunu çalıştırın.")

    def __enter__(self) -> 'PDFParser':
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> bool:
        """Context manager exit - acik dosyalari kapat."""
        self.close()
        return False

    def close(self) -> None:
        """Acik kaynaklari temizle."""
        self._current_doc = None
        self._closed = True

    def parse(self, file_path: PathLike) -> PDFContent:
        """PDF dosyasını oku ve içeriği çıkar."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

        content = PDFContent(
            source=str(file_path),
            filename=file_path.name,
            page_count=0
        )

        # pdfplumber ile metin ve tablo çıkar
        with pdfplumber.open(file_path) as pdf:
            content.page_count = len(pdf.pages)
            content.metadata = pdf.metadata or {}

            all_text = []

            for page_num, page in enumerate(pdf.pages, 1):
                page_content = PDFPage(page_number=page_num, text="")

                # Metin çıkar
                text = page.extract_text() or ""
                page_content.text = text
                all_text.append(text)

                # Tablo çıkar
                if self.extract_tables:
                    tables = page.extract_tables() or []
                    for table_data in tables:
                        if table_data and len(table_data) > 0:
                            # İlk satırı başlık olarak al
                            headers = [str(cell) if cell else "" for cell in table_data[0]]
                            data = []
                            for row in table_data[1:]:
                                data.append([str(cell) if cell else "" for cell in row])

                            pdf_table = PDFTable(
                                page_number=page_num,
                                data=data,
                                headers=headers
                            )
                            page_content.tables.append(pdf_table)

                content.pages.append(page_content)

            content.full_text = "\n\n".join(all_text)

        # PyMuPDF ile görsel çıkar
        if self.extract_images and fitz is not None:
            self._extract_images_with_fitz(file_path, content)

        return content

    def _extract_images_with_fitz(self, file_path: Path, content: PDFContent):
        """PyMuPDF ile görselleri çıkar."""
        try:
            doc = fitz.open(str(file_path))

            for page_num, page in enumerate(doc, 1):
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)

                        if base_image:
                            pdf_image = PDFImage(
                                page_number=page_num,
                                image_data=base_image["image"],
                                width=base_image.get("width", 0),
                                height=base_image.get("height", 0),
                                format=base_image.get("ext", "png")
                            )

                            # İlgili sayfaya ekle
                            if page_num <= len(content.pages):
                                content.pages[page_num - 1].images.append(pdf_image)
                    except (KeyError, IndexError, TypeError) as e:
                        # Gorsel cikarma hatasi, devam et
                        continue

            doc.close()
        except (IOError, OSError, RuntimeError) as e:
            # PyMuPDF acma/okuma hatasi, gorselleri atla
            pass

    def get_text_only(self, file_path: str) -> str:
        """Sadece metni çıkar (hızlı mod)."""
        with pdfplumber.open(file_path) as pdf:
            texts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
            return "\n\n".join(texts)

    def get_tables_only(self, file_path: str) -> List[PDFTable]:
        """Sadece tabloları çıkar."""
        tables = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_tables = page.extract_tables() or []
                for table_data in page_tables:
                    if table_data and len(table_data) > 0:
                        headers = [str(cell) if cell else "" for cell in table_data[0]]
                        data = [[str(cell) if cell else "" for cell in row] for row in table_data[1:]]
                        tables.append(PDFTable(
                            page_number=page_num,
                            data=data,
                            headers=headers
                        ))
        return tables

    def to_dict(self, content: PDFContent) -> Dict[str, Any]:
        """PDFContent'i sözlüğe çevir."""
        return {
            "type": "pdf",
            "source": content.source,
            "filename": content.filename,
            "page_count": content.page_count,
            "metadata": content.metadata,
            "full_text": content.full_text,
            "pages": [
                {
                    "page_number": page.page_number,
                    "text": page.text,
                    "tables": [
                        {
                            "headers": table.headers,
                            "data": table.data
                        }
                        for table in page.tables
                    ],
                    "image_count": len(page.images)
                }
                for page in content.pages
            ]
        }
