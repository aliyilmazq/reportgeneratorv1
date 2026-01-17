"""Gelismis Chunking Modulu - Semantic ve Hiyerarsik Parcalama."""

import re
import uuid
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class ChunkConfig:
    """Chunking konfigurasyonu."""
    chunk_size: int = 1200  # Karakter
    chunk_overlap: int = 240  # %20 overlap
    min_chunk_size: int = 200
    max_chunk_size: int = 2000
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True

    # Parent-child chunking
    use_hierarchical: bool = True
    parent_chunk_size: int = 2000
    child_chunk_size: int = 500


@dataclass
class DocumentChunk:
    """Zenginlestirilmis chunk yapisi."""
    id: str
    text: str
    position: int

    # Hiyerarsi bilgisi
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    level: int = 0  # 0=root, 1=section, 2=subsection, 3=paragraph

    # Yapisal metadata
    section_title: Optional[str] = None
    heading_path: List[str] = field(default_factory=list)

    # Icerik metadata
    word_count: int = 0
    char_count: int = 0
    language: str = "tr"
    content_type: str = "text"  # text, table, list, code

    # Kaynak metadata
    source_file: str = ""
    page_number: Optional[int] = None
    start_char: int = 0
    end_char: int = 0

    # Ek metadata
    has_numbers: bool = False
    has_dates: bool = False
    has_currency: bool = False
    estimated_category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Dict'e donustur."""
        return {
            "id": self.id,
            "text": self.text,
            "position": self.position,
            "parent_id": self.parent_id,
            "level": self.level,
            "section_title": self.section_title,
            "heading_path": self.heading_path,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "content_type": self.content_type,
            "source_file": self.source_file,
            "page_number": self.page_number,
            "has_numbers": self.has_numbers,
            "has_dates": self.has_dates,
            "has_currency": self.has_currency,
            "estimated_category": self.estimated_category
        }


class SemanticChunker:
    """Anlamsal chunking - cumle ve paragraf sinirlarini korur."""

    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()

    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[DocumentChunk]:
        """Metni anlamsal olarak parcala."""
        if not text or not text.strip():
            return []

        metadata = metadata or {}
        chunks = []
        position = 0

        # Paragraflara bol
        paragraphs = self._split_paragraphs(text)

        current_chunk_text = ""
        current_start = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Paragraf cok uzunsa cumlelere bol
            if len(para) > self.config.chunk_size:
                # Onceki chunk'i kaydet
                if current_chunk_text.strip():
                    chunk = self._create_chunk(
                        text=current_chunk_text.strip(),
                        position=position,
                        start_char=current_start,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    position += 1
                    current_chunk_text = ""

                # Uzun paragrafi cumlelere bolup isle
                sentence_chunks = self._chunk_by_sentences(para, metadata, position)
                chunks.extend(sentence_chunks)
                position += len(sentence_chunks)
                current_start = text.find(para) + len(para) if para in text else 0

            elif len(current_chunk_text) + len(para) <= self.config.chunk_size:
                # Mevcut chunk'a ekle
                if current_chunk_text:
                    current_chunk_text += "\n\n"
                current_chunk_text += para

            else:
                # Yeni chunk baslat
                if current_chunk_text.strip():
                    chunk = self._create_chunk(
                        text=current_chunk_text.strip(),
                        position=position,
                        start_char=current_start,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    position += 1

                # Overlap ekle
                overlap_text = self._get_overlap_text(current_chunk_text)
                current_chunk_text = overlap_text + para
                current_start = text.find(para) if para in text else 0

        # Son chunk
        if current_chunk_text.strip():
            chunk = self._create_chunk(
                text=current_chunk_text.strip(),
                position=position,
                start_char=current_start,
                metadata=metadata
            )
            chunks.append(chunk)

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Paragraflara bol."""
        # Cift satir atlama veya bosluk satirlari
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """Cumlelere bol (Turkce ve Ingilizce)."""
        # Cumle sonu isaretleri
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜa-zçğıöşü])'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _chunk_by_sentences(
        self,
        text: str,
        metadata: Dict[str, Any],
        start_position: int
    ) -> List[DocumentChunk]:
        """Uzun metni cumle bazinda parcala."""
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = ""
        position = start_position

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.config.chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        text=current_chunk.strip(),
                        position=position,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    position += 1

                # Overlap
                overlap = self._get_overlap_text(current_chunk)
                current_chunk = overlap + sentence + " "

        if current_chunk.strip():
            chunk = self._create_chunk(
                text=current_chunk.strip(),
                position=position,
                metadata=metadata
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """Overlap metnini al."""
        if len(text) <= self.config.chunk_overlap:
            return text

        # Son cumleyi bul ve onu overlap olarak kullan
        overlap_text = text[-self.config.chunk_overlap:]

        # Cumle basindan basla
        sentence_start = overlap_text.find(". ")
        if sentence_start != -1:
            overlap_text = overlap_text[sentence_start + 2:]

        return overlap_text

    def _create_chunk(
        self,
        text: str,
        position: int,
        start_char: int = 0,
        metadata: Dict[str, Any] = None
    ) -> DocumentChunk:
        """Chunk olustur ve zenginlestir."""
        metadata = metadata or {}

        chunk = DocumentChunk(
            id=str(uuid.uuid4())[:8],
            text=text,
            position=position,
            word_count=len(text.split()),
            char_count=len(text),
            start_char=start_char,
            end_char=start_char + len(text),
            source_file=metadata.get("source", metadata.get("filename", "")),
            page_number=metadata.get("page_number"),
            content_type=self._detect_content_type(text)
        )

        # Metadata zenginlestir
        self._enrich_metadata(chunk, text)

        return chunk

    def _detect_content_type(self, text: str) -> str:
        """Icerik tipini tespit et."""
        # Tablo kontrolu
        if "|" in text and text.count("|") >= 3:
            return "table"

        # Liste kontrolu
        if re.search(r'^[\s]*[-*•]\s', text, re.MULTILINE):
            return "list"

        # Kod blogu kontrolu
        if "```" in text or text.count("    ") >= 3:
            return "code"

        return "text"

    def _enrich_metadata(self, chunk: DocumentChunk, text: str):
        """Chunk metadata'sini zenginlestir."""
        text_lower = text.lower()

        # Sayi kontrolu
        chunk.has_numbers = bool(re.search(r'\d+', text))

        # Tarih kontrolu
        chunk.has_dates = bool(re.search(
            r'\d{4}|\d{1,2}/\d{1,2}|\d{1,2}\.\d{1,2}\.\d{4}',
            text
        ))

        # Para birimi kontrolu
        chunk.has_currency = bool(re.search(
            r'[$€₺]\s*\d+|\d+\s*(TL|USD|EUR|tl|usd|eur)',
            text
        ))

        # Kategori tahmini
        chunk.estimated_category = self._estimate_category(text_lower)

    def _estimate_category(self, text_lower: str) -> Optional[str]:
        """Icerik kategorisini tahmin et."""
        category_keywords = {
            "finansal": ["gelir", "maliyet", "kar", "zarar", "butce", "fiyat", "oran", "yuzde"],
            "pazar": ["pazar", "sektor", "rekabet", "musteri", "segment", "trend", "talep"],
            "operasyon": ["surec", "uretim", "tedarik", "lojistik", "operasyon", "is akisi"],
            "risk": ["risk", "tehdit", "firsat", "swot", "belirsizlik", "etki"],
            "teknik": ["sistem", "yazilim", "teknoloji", "altyapi", "entegrasyon"]
        }

        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=scores.get)
        return None


class RecursiveTextSplitter:
    """Hiyerarsik metin bolme - baslik yapisini korur."""

    MARKDOWN_SEPARATORS = [
        "\n# ",      # H1
        "\n## ",     # H2
        "\n### ",    # H3
        "\n#### ",   # H4
        "\n\n",      # Paragraf
        "\n",        # Satir
        ". ",        # Cumle
        " "          # Kelime
    ]

    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()

    def split_text(
        self,
        text: str,
        separators: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> List[DocumentChunk]:
        """Recursive bolme - buyukten kucuge."""
        separators = separators or self.MARKDOWN_SEPARATORS
        metadata = metadata or {}

        return self._recursive_split(text, separators, metadata, 0)

    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        metadata: Dict[str, Any],
        level: int
    ) -> List[DocumentChunk]:
        """Recursive bolme mantigi."""
        if not text.strip():
            return []

        # Hedef boyuta ulastiysa dondur
        if len(text) <= self.config.chunk_size:
            return [self._create_chunk(text, 0, level, metadata)]

        # Ayirici bul
        separator = None
        for sep in separators:
            if sep in text:
                separator = sep
                break

        if separator is None:
            # Ayirici bulunamadi, zorla bol
            return self._force_split(text, metadata, level)

        # Ayiriciya gore bol
        parts = text.split(separator)
        chunks = []
        current_chunk = ""
        position = 0

        for part in parts:
            if not part.strip():
                continue

            test_chunk = current_chunk + separator + part if current_chunk else part

            if len(test_chunk) <= self.config.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    # Hala buyukse recursive devam et
                    if len(current_chunk) > self.config.chunk_size:
                        remaining_seps = separators[separators.index(separator) + 1:]
                        if remaining_seps:
                            sub_chunks = self._recursive_split(
                                current_chunk, remaining_seps, metadata, level + 1
                            )
                            for sc in sub_chunks:
                                sc.position = position
                                position += 1
                            chunks.extend(sub_chunks)
                        else:
                            chunks.append(self._create_chunk(current_chunk, position, level, metadata))
                            position += 1
                    else:
                        chunks.append(self._create_chunk(current_chunk, position, level, metadata))
                        position += 1

                current_chunk = part

        # Son parca
        if current_chunk.strip():
            if len(current_chunk) > self.config.chunk_size:
                remaining_seps = separators[separators.index(separator) + 1:] if separator else []
                if remaining_seps:
                    sub_chunks = self._recursive_split(
                        current_chunk, remaining_seps, metadata, level + 1
                    )
                    for sc in sub_chunks:
                        sc.position = position
                        position += 1
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(self._create_chunk(current_chunk, position, level, metadata))
            else:
                chunks.append(self._create_chunk(current_chunk, position, level, metadata))

        return chunks

    def _force_split(
        self,
        text: str,
        metadata: Dict[str, Any],
        level: int
    ) -> List[DocumentChunk]:
        """Zorla bol (karakter bazli)."""
        chunks = []
        position = 0

        for i in range(0, len(text), self.config.chunk_size - self.config.chunk_overlap):
            chunk_text = text[i:i + self.config.chunk_size]
            if chunk_text.strip():
                chunks.append(self._create_chunk(chunk_text, position, level, metadata))
                position += 1

        return chunks

    def _create_chunk(
        self,
        text: str,
        position: int,
        level: int,
        metadata: Dict[str, Any]
    ) -> DocumentChunk:
        """Chunk olustur."""
        return DocumentChunk(
            id=str(uuid.uuid4())[:8],
            text=text.strip(),
            position=position,
            level=level,
            word_count=len(text.split()),
            char_count=len(text),
            source_file=metadata.get("source", ""),
            heading_path=metadata.get("heading_path", [])
        )

    def split_markdown(
        self,
        markdown_text: str,
        metadata: Dict[str, Any] = None
    ) -> List[DocumentChunk]:
        """Markdown yapisini koruyarak bol."""
        metadata = metadata or {}
        chunks = []

        # Basliklari bul ve hiyerarsi olustur
        heading_pattern = r'^(#{1,4})\s+(.+)$'
        current_heading_path = []

        lines = markdown_text.split('\n')
        current_section = ""
        position = 0

        for line in lines:
            heading_match = re.match(heading_pattern, line)

            if heading_match:
                # Onceki bolumu kaydet
                if current_section.strip():
                    chunk = self._create_chunk(
                        current_section.strip(),
                        position,
                        len(current_heading_path),
                        {**metadata, "heading_path": current_heading_path.copy()}
                    )
                    chunk.section_title = current_heading_path[-1] if current_heading_path else None
                    chunks.append(chunk)
                    position += 1
                    current_section = ""

                # Heading path guncelle
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_heading_path = current_heading_path[:level - 1]
                current_heading_path.append(title)

                current_section = line + "\n"
            else:
                current_section += line + "\n"

        # Son bolum
        if current_section.strip():
            chunk = self._create_chunk(
                current_section.strip(),
                position,
                len(current_heading_path),
                {**metadata, "heading_path": current_heading_path.copy()}
            )
            chunk.section_title = current_heading_path[-1] if current_heading_path else None
            chunks.append(chunk)

        return chunks


class ParentDocumentChunker:
    """Parent-child chunk iliskisi - buyuk baglam icin."""

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        child_overlap: int = 100
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.child_overlap = child_overlap

        self.semantic_chunker = SemanticChunker(ChunkConfig(
            chunk_size=child_chunk_size,
            chunk_overlap=child_overlap
        ))

    def create_hierarchical_chunks(
        self,
        document: str,
        metadata: Dict[str, Any] = None
    ) -> Tuple[List[DocumentChunk], List[DocumentChunk]]:
        """
        Parent ve child chunk'lari olustur.
        Arama child'da yapilir, context parent'tan alinir.

        Returns:
            (parent_chunks, child_chunks)
        """
        metadata = metadata or {}
        parent_chunks = []
        child_chunks = []

        # Buyuk parcalara bol (parent)
        parent_config = ChunkConfig(
            chunk_size=self.parent_chunk_size,
            chunk_overlap=200
        )
        parent_chunker = SemanticChunker(parent_config)
        parents = parent_chunker.chunk(document, metadata)

        for parent in parents:
            parent.level = 0
            parent_chunks.append(parent)

            # Her parent icin child'lar olustur
            children = self.semantic_chunker.chunk(parent.text, metadata)

            for child in children:
                child.parent_id = parent.id
                child.level = 1
                parent.children_ids.append(child.id)
                child_chunks.append(child)

        return parent_chunks, child_chunks

    def get_parent_context(
        self,
        child_chunk: DocumentChunk,
        parent_chunks: List[DocumentChunk]
    ) -> Optional[str]:
        """Child icin parent context'i getir."""
        if not child_chunk.parent_id:
            return None

        for parent in parent_chunks:
            if parent.id == child_chunk.parent_id:
                return parent.text

        return None


def create_chunker(
    strategy: str = "semantic",
    config: ChunkConfig = None
) -> SemanticChunker:
    """Kolayca chunker olustur."""
    config = config or ChunkConfig()

    if strategy == "semantic":
        return SemanticChunker(config)
    elif strategy == "recursive":
        return RecursiveTextSplitter(config)
    else:
        return SemanticChunker(config)
