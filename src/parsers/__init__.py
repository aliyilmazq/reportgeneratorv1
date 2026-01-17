# Parser Modulleri
"""
Dosya parser modulleri.
PDF, Excel, Word ve gorsel analiz.
"""

from .base_parser import BaseParser, ParsedContent, ParserFactory
from .pdf_parser import PDFParser, PDFContent, PDFTable, PDFPage, PDFImage
from .excel_parser import ExcelParser
from .word_parser import WordParser
from .image_analyzer import ImageAnalyzer

# Parser'lari factory'ye kaydet
ParserFactory.register(['.pdf'], PDFParser)
ParserFactory.register(['.xlsx', '.xls', '.csv'], ExcelParser)
ParserFactory.register(['.docx', '.doc'], WordParser)
ParserFactory.register(['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'], ImageAnalyzer)

__all__ = [
    # Base
    'BaseParser', 'ParsedContent', 'ParserFactory',
    # PDF
    'PDFParser', 'PDFContent', 'PDFTable', 'PDFPage', 'PDFImage',
    # Excel
    'ExcelParser',
    # Word
    'WordParser',
    # Image
    'ImageAnalyzer'
]
