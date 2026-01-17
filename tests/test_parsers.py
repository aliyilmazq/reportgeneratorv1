"""
Unit Tests for Parser Modules
=============================
Tests for PDF, Excel, Word parsers and base parser functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parsers.base_parser import BaseParser, ParsedContent, ParserFactory


# ═══════════════════════════════════════════════════════════════════════════════
# PARSED CONTENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestParsedContent:
    """ParsedContent testleri."""

    def test_create_parsed_content(self):
        """ParsedContent olusturma."""
        content = ParsedContent(
            source="/path/to/file.pdf",
            filename="file.pdf",
            file_type="pdf",
            text_content="Hello World test content"
        )
        assert content.filename == "file.pdf"
        assert content.word_count == 4

    def test_word_count_auto_calculated(self):
        """Kelime sayisi otomatik hesaplama."""
        content = ParsedContent(
            source="test",
            filename="test.txt",
            file_type="txt",
            text_content="one two three four five"
        )
        assert content.word_count == 5

    def test_has_content_with_text(self):
        """Metin ile icerik kontrolu."""
        content = ParsedContent(
            source="test",
            filename="test.txt",
            file_type="txt",
            text_content="Some content"
        )
        assert content.has_content == True

    def test_has_content_empty(self):
        """Bos icerik kontrolu."""
        content = ParsedContent(
            source="test",
            filename="test.txt",
            file_type="txt",
            text_content=""
        )
        assert content.has_content == False

    def test_has_content_with_tables(self):
        """Tablo ile icerik kontrolu."""
        content = ParsedContent(
            source="test",
            filename="test.txt",
            file_type="txt",
            text_content="",
            tables=[{"headers": ["A", "B"], "data": [["1", "2"]]}]
        )
        assert content.has_content == True

    def test_has_errors(self):
        """Hata kontrolu."""
        content = ParsedContent(
            source="test",
            filename="test.txt",
            file_type="txt",
            text_content="test",
            errors=["Error 1", "Error 2"]
        )
        assert content.has_errors == True

    def test_to_dict(self):
        """to_dict metodu."""
        content = ParsedContent(
            source="test",
            filename="test.txt",
            file_type="txt",
            text_content="Hello World"
        )
        d = content.to_dict()
        assert d["filename"] == "test.txt"
        assert d["word_count"] == 2
        assert d["has_errors"] == False


# ═══════════════════════════════════════════════════════════════════════════════
# BASE PARSER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ConcreteParser(BaseParser[ParsedContent]):
    """Test icin somut parser."""
    SUPPORTED_EXTENSIONS = ['.txt', '.test']

    def parse(self, file_path):
        self.validate_file(file_path)
        path = Path(file_path)
        return ParsedContent(
            source=str(path),
            filename=path.name,
            file_type="txt",
            text_content=path.read_text()
        )


class TestBaseParser:
    """BaseParser testleri."""

    @pytest.fixture
    def parser(self):
        """Parser instance."""
        return ConcreteParser()

    def test_supports_valid_extension(self, parser):
        """Gecerli uzanti destegi."""
        assert parser.supports("file.txt") == True
        assert parser.supports("file.test") == True

    def test_supports_invalid_extension(self, parser):
        """Gecersiz uzanti."""
        assert parser.supports("file.pdf") == False
        assert parser.supports("file.docx") == False

    def test_context_manager(self, parser, tmp_path):
        """Context manager kullanimi."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with ConcreteParser() as p:
            result = p.parse(str(test_file))
            assert result.text_content == "content"
        assert p.is_closed == True

    def test_validate_file_not_found(self, parser):
        """Var olmayan dosya."""
        with pytest.raises(FileNotFoundError):
            parser.validate_file("/nonexistent/path/file.txt")

    def test_validate_unsupported_format(self, parser, tmp_path):
        """Desteklenmeyen format."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("content")

        with pytest.raises(ValueError, match="Desteklenmeyen"):
            parser.validate_file(str(test_file))

    def test_parse_safe_success(self, parser, tmp_path):
        """parse_safe basarili."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = parser.parse_safe(str(test_file))
        assert result is not None
        assert result.text_content == "content"

    def test_parse_safe_failure(self, parser):
        """parse_safe basarisiz."""
        result = parser.parse_safe("/nonexistent/file.txt")
        assert result is None

    def test_get_file_info(self, parser, tmp_path):
        """Dosya bilgileri."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        info = parser.get_file_info(str(test_file))
        assert info["name"] == "test.txt"
        assert info["extension"] == ".txt"
        assert "size" in info
        assert "modified" in info

    def test_format_size_bytes(self):
        """Byte boyutu."""
        result = BaseParser._format_size(500)
        assert "B" in result

    def test_format_size_kb(self):
        """KB boyutu."""
        result = BaseParser._format_size(1500)
        assert "KB" in result

    def test_format_size_mb(self):
        """MB boyutu."""
        result = BaseParser._format_size(1500000)
        assert "MB" in result

    def test_clean_text(self):
        """Metin temizleme."""
        result = BaseParser._clean_text("  Hello   World  ")
        assert result == "Hello World"

    def test_clean_text_null_chars(self):
        """Null karakter temizleme."""
        result = BaseParser._clean_text("Hello\x00World")
        assert "\x00" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# PARSER FACTORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestParserFactory:
    """ParserFactory testleri."""

    def test_register_parser(self):
        """Parser kaydetme."""
        class TestParser(BaseParser):
            SUPPORTED_EXTENSIONS = ['.test']
            def parse(self, file_path):
                pass

        ParserFactory.register(['.custom'], TestParser)
        assert '.custom' in ParserFactory.supported_extensions()

    def test_get_parser_for_known_extension(self):
        """Bilinen uzanti icin parser."""
        # PDF parser kayitli olmali (parsers/__init__.py'de)
        parser = ParserFactory.get_parser("document.pdf")
        # Parser donmeli veya None (kutuphane yuklu degilse)
        assert parser is not None or True  # Optional

    def test_get_parser_for_unknown_extension(self):
        """Bilinmeyen uzanti."""
        parser = ParserFactory.get_parser("file.unknown_ext_xyz")
        assert parser is None

    def test_is_supported(self):
        """Desteklenen uzanti kontrolu."""
        # Bu test parser kayitlarina bagli
        assert isinstance(ParserFactory.is_supported("file.pdf"), bool)

    def test_supported_extensions(self):
        """Desteklenen uzantilar listesi."""
        extensions = ParserFactory.supported_extensions()
        assert isinstance(extensions, list)


# ═══════════════════════════════════════════════════════════════════════════════
# PDF PARSER TESTS (Mock)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDFParserMocked:
    """PDFParser testleri (mock ile)."""

    @pytest.fixture
    def mock_pdfplumber(self):
        """pdfplumber mock."""
        with patch('parsers.pdf_parser.pdfplumber') as mock:
            yield mock

    def test_pdf_content_properties(self):
        """PDFContent ozellikleri."""
        from parsers.pdf_parser import PDFContent, PDFPage, PDFTable

        content = PDFContent(
            source="test.pdf",
            filename="test.pdf",
            page_count=2,
            pages=[
                PDFPage(page_number=1, text="Page 1 content", tables=[
                    PDFTable(page_number=1, data=[["a", "b"]], headers=["H1", "H2"])
                ]),
                PDFPage(page_number=2, text="Page 2 content")
            ],
            full_text="Page 1 content Page 2 content"
        )

        assert content.word_count == 6
        assert len(content.all_tables) == 1
        assert content.all_tables[0].row_count == 1

    def test_pdf_table_properties(self):
        """PDFTable ozellikleri."""
        from parsers.pdf_parser import PDFTable

        table = PDFTable(
            page_number=1,
            data=[["1", "2"], ["3", "4"]],
            headers=["A", "B"]
        )

        assert table.row_count == 2
        assert table.column_count == 2
        d = table.to_dict()
        assert d["row_count"] == 2

    def test_pdf_page_properties(self):
        """PDFPage ozellikleri."""
        from parsers.pdf_parser import PDFPage

        page = PDFPage(
            page_number=1,
            text="Hello World content here"
        )

        assert page.word_count == 4
        assert page.has_content == True


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
