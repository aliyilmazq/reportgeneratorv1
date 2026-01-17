"""PDF rapor üretici modülü."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
    from reportlab.platypus.frames import Frame
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    SimpleDocTemplate = None

import yaml
from rich.console import Console

from ..processor.structurer import StructuredReport, ReportSection

console = Console()


class HeadingParagraph(Paragraph):
    """TOC için bookmark oluşturan özel Paragraph sınıfı."""

    def __init__(self, text, style, level=0, bookmarkName=None):
        Paragraph.__init__(self, text, style)
        self.toc_level = level
        self.bookmark_name = bookmarkName or text

    def draw(self):
        # Bookmark ekle
        key = self.bookmark_name
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(self.getPlainText(), key, self.toc_level, 0)
        Paragraph.draw(self)


class MyDocTemplate(BaseDocTemplate):
    """TOC destekli özel DocTemplate."""

    def __init__(self, filename, **kw):
        self.allowSplitting = 0
        BaseDocTemplate.__init__(self, filename, **kw)

        # Sayfa şablonu
        frame = Frame(
            self.leftMargin, self.bottomMargin,
            self.width, self.height,
            id='normal'
        )
        template = PageTemplate(id='normal', frames=frame, onPage=self._add_page_number)
        self.addPageTemplates([template])

    def _add_page_number(self, canvas, doc):
        """Sayfa numarası ekle."""
        page_num = canvas.getPageNumber()
        text = f"{page_num}"
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawCentredString(A4[0] / 2, 1.5 * cm, text)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        """Flowable eklendikten sonra TOC'a kaydet."""
        if isinstance(flowable, HeadingParagraph):
            text = flowable.getPlainText()
            level = flowable.toc_level
            page_num = self.page

            # TOC entry ekle
            self.notify('TOCEntry', (level, text, page_num))


class PdfGenerator:
    """PDF dokümanı üretici sınıfı."""

    def __init__(self, config_dir: str = None):
        if SimpleDocTemplate is None:
            raise ImportError("reportlab kütüphanesi yüklü değil. 'pip install reportlab' komutunu çalıştırın.")

        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self.templates_dir = Path(__file__).parent.parent.parent / "templates"

        # Kuralları yükle
        self.rules = self._load_rules()
        self.styles = self._setup_styles()

    def _load_rules(self) -> Dict[str, Any]:
        """Kuralları yükle."""
        rules_path = Path(self.config_dir) / "rules.yaml"
        if rules_path.exists():
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        """PDF stillerini ayarla."""
        fmt_rules = self.rules.get('format_rules', {})
        colors = fmt_rules.get('colors', {})
        fonts = fmt_rules.get('fonts', {})

        base_styles = getSampleStyleSheet()

        custom_styles = {}

        # Başlık 1
        custom_styles['Heading1'] = ParagraphStyle(
            'Heading1',
            parent=base_styles['Heading1'],
            fontSize=fonts.get('heading', {}).get('size_h1', 18),
            textColor=HexColor(colors.get('primary', '#1a365d')),
            spaceAfter=12,
            spaceBefore=24
        )

        # Başlık 2
        custom_styles['Heading2'] = ParagraphStyle(
            'Heading2',
            parent=base_styles['Heading2'],
            fontSize=fonts.get('heading', {}).get('size_h2', 14),
            textColor=HexColor(colors.get('secondary', '#2c5282')),
            spaceAfter=10,
            spaceBefore=18
        )

        # Başlık 3
        custom_styles['Heading3'] = ParagraphStyle(
            'Heading3',
            parent=base_styles['Heading3'],
            fontSize=fonts.get('heading', {}).get('size_h3', 12),
            textColor=HexColor(colors.get('accent', '#3182ce')),
            spaceAfter=8,
            spaceBefore=12
        )

        # Normal metin
        custom_styles['Normal'] = ParagraphStyle(
            'Normal',
            parent=base_styles['Normal'],
            fontSize=fonts.get('body', {}).get('size', 11),
            textColor=HexColor(colors.get('text', '#1a202c')),
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14
        )

        # Kapak başlığı
        custom_styles['CoverTitle'] = ParagraphStyle(
            'CoverTitle',
            parent=base_styles['Title'],
            fontSize=28,
            textColor=HexColor(colors.get('primary', '#1a365d')),
            alignment=TA_CENTER,
            spaceAfter=20
        )

        # Kapak alt başlık
        custom_styles['CoverSubtitle'] = ParagraphStyle(
            'CoverSubtitle',
            parent=base_styles['Normal'],
            fontSize=16,
            textColor=HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=10
        )

        # Liste öğesi
        custom_styles['ListItem'] = ParagraphStyle(
            'ListItem',
            parent=base_styles['Normal'],
            fontSize=11,
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=4
        )

        return custom_styles

    def _add_page_number(self, canvas, doc):
        """Sayfa numarası ekle."""
        page_num = canvas.getPageNumber()
        text = f"{page_num}"

        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawCentredString(A4[0] / 2, 1.5 * cm, text)
        canvas.restoreState()

    def _create_cover_page(self, report: StructuredReport) -> list:
        """Kapak sayfası oluştur."""
        elements = []

        # Üst boşluk
        elements.append(Spacer(1, 6 * cm))

        # Başlık
        elements.append(Paragraph(report.title.upper(), self.styles['CoverTitle']))

        # Alt başlık
        elements.append(Spacer(1, 1 * cm))
        type_text = report.report_type.replace('_', ' ').title()
        elements.append(Paragraph(type_text, self.styles['CoverSubtitle']))

        # Alt boşluk ve tarih
        elements.append(Spacer(1, 10 * cm))

        if report.language == "tr":
            date_str = datetime.now().strftime("%d.%m.%Y")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        date_style = ParagraphStyle(
            'Date',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12
        )
        elements.append(Paragraph(date_str, date_style))

        elements.append(PageBreak())

        return elements

    def _create_toc_styles(self):
        """TOC için özel stiller."""
        toc_styles = []

        # TOC Level 0 (Heading 1)
        toc_styles.append(ParagraphStyle(
            'TOCHeading1',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            leftIndent=0,
            spaceBefore=6,
            spaceAfter=3,
        ))

        # TOC Level 1 (Heading 2)
        toc_styles.append(ParagraphStyle(
            'TOCHeading2',
            parent=self.styles['Normal'],
            fontSize=11,
            leftIndent=20,
            spaceBefore=2,
            spaceAfter=2,
        ))

        # TOC Level 2 (Heading 3)
        toc_styles.append(ParagraphStyle(
            'TOCHeading3',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=40,
            spaceBefore=2,
            spaceAfter=2,
        ))

        return toc_styles

    def _create_table_of_contents(self, report: StructuredReport) -> list:
        """İçindekiler oluştur - sayfa numaralı."""
        elements = []

        toc_title = "İÇİNDEKİLER" if report.language == "tr" else "TABLE OF CONTENTS"
        title_style = ParagraphStyle(
            'TOCTitle',
            parent=self.styles['Heading1'],
            alignment=TA_CENTER
        )
        elements.append(Paragraph(toc_title, title_style))
        elements.append(Spacer(1, 1 * cm))

        # TableOfContents nesnesi oluştur
        toc = TableOfContents()
        toc.levelStyles = self._create_toc_styles()

        # TOC'u listeye ekle
        elements.append(toc)
        elements.append(PageBreak())

        # TOC'u sakla (generate'de kullanılacak)
        self._toc = toc

        return elements

    def _create_section(self, section: ReportSection, number: str) -> list:
        """Bölüm oluştur."""
        elements = []

        # Başlık - HeadingParagraph kullan (TOC için)
        heading_text = f"{number} {section.title}"
        heading_style = self.styles.get(f'Heading{section.level}', self.styles['Heading1'])
        level = section.level - 1  # TOC level 0-indexed
        bookmark = f"section_{number.replace('.', '_')}"
        elements.append(HeadingParagraph(heading_text, heading_style, level=level, bookmarkName=bookmark))

        # İçerik
        if section.content:
            paragraphs = section.content.split('\n\n')

            for para_text in paragraphs:
                para_text = para_text.strip()
                if not para_text:
                    continue

                # Alt başlık kontrolü
                if para_text.startswith('## '):
                    elements.append(Paragraph(para_text[3:], self.styles['Heading2']))
                elif para_text.startswith('### '):
                    elements.append(Paragraph(para_text[4:], self.styles['Heading3']))
                elif para_text.startswith('- ') or para_text.startswith('* '):
                    # Madde işaretli liste
                    for line in para_text.split('\n'):
                        line = line.strip()
                        if line.startswith('- ') or line.startswith('* '):
                            bullet_text = f"• {line[2:]}"
                            elements.append(Paragraph(bullet_text, self.styles['ListItem']))
                        elif line:
                            elements.append(Paragraph(line, self.styles['Normal']))
                elif para_text.startswith('1. ') or para_text.startswith('1) '):
                    # Numaralı liste
                    num = 1
                    for line in para_text.split('\n'):
                        line = line.strip()
                        if line and line[0].isdigit():
                            text = line.lstrip('0123456789.)').strip()
                            numbered_text = f"{num}. {text}"
                            elements.append(Paragraph(numbered_text, self.styles['ListItem']))
                            num += 1
                        elif line:
                            elements.append(Paragraph(line, self.styles['Normal']))
                else:
                    # Normal paragraf - XML karakterlerini escape et
                    safe_text = para_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    elements.append(Paragraph(safe_text, self.styles['Normal']))

        # Alt bölümler
        for i, subsection in enumerate(section.subsections, 1):
            sub_number = f"{number}.{i}"
            elements.extend(self._create_section(subsection, sub_number))

        return elements

    def generate(self, report: StructuredReport, output_path: str) -> str:
        """Raporu PDF dosyası olarak oluştur."""

        # Dosya adı oluştur
        output_path = Path(output_path)
        if output_path.is_dir():
            filename = f"{report.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = output_path / filename

        # PDF oluştur - TOC destekli özel template
        doc = MyDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2.5 * cm,
            leftMargin=2.5 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm
        )

        elements = []

        # Kapak sayfası
        elements.extend(self._create_cover_page(report))

        # İçindekiler
        elements.extend(self._create_table_of_contents(report))

        # Bölümler
        section_num = 1
        for section in report.sections:
            if section.id in ['kapak', 'kapak_sayfasi', 'icindekiler', 'table_of_contents']:
                continue

            elements.extend(self._create_section(section, str(section_num)))
            section_num += 1

        # PDF'i oluştur - multiBuild ile TOC otomatik güncellenir
        doc.multiBuild(elements)

        return str(output_path)
