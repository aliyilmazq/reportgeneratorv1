# API Referansi

Bu dokuman Rapor Uretici v4.0 PRO'nun tum public API'lerini detayli olarak aciklar.

## Icindekiler

1. [Orchestrator](#orchestrator)
2. [Scanner](#scanner)
3. [Parsers](#parsers)
4. [Research](#research)
5. [Content Generation](#content-generation)
6. [Validation](#validation)
7. [Generators](#generators)
8. [Utilities](#utilities)
9. [Types](#types)

---

## Orchestrator

### `ReportOrchestrator`

Rapor uretim is akisini koordine eden ana sinif.

```python
from src.orchestrator import ReportOrchestrator, UserInput, GeneratedReport
```

#### Constructor

```python
ReportOrchestrator(
    output_dir: str = "./output",
    use_live_progress: bool = True
)
```

| Parametre | Tip | Varsayilan | Aciklama |
|-----------|-----|------------|----------|
| `output_dir` | str | "./output" | Cikti dosyalarinin kaydedilecegi dizin |
| `use_live_progress` | bool | True | Canli ilerleme gosterimi |

#### Metodlar

##### `generate_report()`

```python
def generate_report(self, user_input: UserInput) -> GeneratedReport
```

Tam rapor uretim pipeline'ini calistirir.

**Parametreler:**
- `user_input`: Kullanici girdilerini iceren nesne

**Donus:**
- `GeneratedReport`: Uretilen rapor ve meta bilgileri

**Ornek:**
```python
user_input = UserInput(
    input_path="./data",
    output_type="analiz_raporu",
    output_format="both",
    language="tr"
)
report = orchestrator.generate_report(user_input)
```

### `UserInput`

Kullanici girdilerini tutan dataclass.

```python
@dataclass
class UserInput:
    input_path: str        # Kaynak dosya/klasor yolu
    output_type: str       # Rapor turu
    output_format: str     # Cikti formati (docx/pdf/both)
    language: str = "tr"   # Cikti dili
    special_notes: str = "" # Ozel notlar
```

### `GeneratedReport`

Uretilen raporu temsil eden dataclass.

```python
@dataclass
class GeneratedReport:
    title: str                      # Rapor basligi
    report_type: str                # Rapor turu
    language: str                   # Dil
    sections: List[GeneratedSection] # Bolumlerin listesi
    output_files: List[str]         # Olusturulan dosya yollari
    citations: List[Dict]           # Alintilar
    sources: List[Dict]             # Kaynaklar
    statistics: Dict[str, Any]      # Istatistikler
    generation_time_seconds: float  # Uretim suresi
    metadata: Dict[str, Any]        # Ek meta bilgiler
```

---

## Scanner

### `FileScanner`

Dosya ve dizin tarama sinifi.

```python
from src.scanner import FileScanner, ScanResult
```

#### Constructor

```python
FileScanner(
    max_file_size_mb: int = 100,
    supported_extensions: Optional[List[str]] = None
)
```

#### Metodlar

##### `scan()`

```python
def scan(self, path: str) -> ScanResult
```

Belirtilen yolu tarar ve dosyalari listeler.

**Parametreler:**
- `path`: Taranacak dosya veya dizin yolu

**Donus:**
- `ScanResult`: Tarama sonuclari

##### `scan_file()`

```python
def scan_file(self, file_path: str) -> Optional[FileInfo]
```

Tek bir dosyayi tarar.

### `ScanResult`

Tarama sonuclarini tutan dataclass.

```python
@dataclass
class ScanResult:
    files: Dict[str, List[FileInfo]]  # Kategorilere gore dosyalar
    total_files: int                   # Toplam dosya sayisi
    total_size: int                    # Toplam boyut (bytes)
    scan_time: float                   # Tarama suresi
    stats: Dict[str, int]              # Istatistikler
```

---

## Parsers

### `ParserFactory`

Dosya uzantisina gore uygun parser olusturur.

```python
from src.parsers import ParserFactory, ParsedContent
```

#### Metodlar

##### `create()`

```python
@staticmethod
def create(file_path: str) -> BaseParser
```

Dosya uzantisina gore parser olusturur.

**Ornek:**
```python
parser = ParserFactory.create("document.pdf")
content = parser.parse("document.pdf")
```

### `BaseParser`

Tum parser'larin temel sinifi (abstract).

```python
from src.parsers.base_parser import BaseParser
```

#### Metodlar

##### `parse()`

```python
@abstractmethod
def parse(self, file_path: PathLike) -> ParsedContent
```

Dosyayi parse eder.

##### `parse_safe()`

```python
def parse_safe(self, file_path: PathLike) -> Optional[ParsedContent]
```

Hata durumunda None donen guvenli parse.

### `ParsedContent`

Parse edilmis icerigi tutan dataclass.

```python
@dataclass
class ParsedContent:
    text: str                        # Ana metin
    tables: List[List[List[str]]]    # Tablolar
    images: List[bytes]              # Gorseller
    metadata: Dict[str, Any]         # Meta bilgiler
    dataframes: Optional[List]       # Pandas DataFrame'ler
    word_count: int                  # Kelime sayisi
    page_count: int                  # Sayfa sayisi
```

### Parser Siniflari

| Sinif | Dosya Tipleri |
|-------|---------------|
| `PdfParser` | .pdf |
| `WordParser` | .docx, .doc |
| `ExcelParser` | .xlsx, .xls, .csv |
| `ImageAnalyzer` | .png, .jpg, .jpeg, .gif |

---

## Research

### `WebResearcher`

Web arastirmasi yapan sinif.

```python
from src.research.web_researcher import WebResearcher, ResearchResult
```

#### Constructor

```python
WebResearcher(
    max_results: int = 10,
    timeout: int = 30
)
```

#### Metodlar

##### `research_topic()`

```python
def research_topic(
    self,
    topic: str,
    max_sources: int = 10
) -> List[ResearchResult]
```

Belirtilen konu hakkinda web arastirmasi yapar.

### `SourceCollector`

Kaynak toplama ve yonetim sinifi.

```python
from src.research.source_collector import SourceCollector
```

#### Metodlar

##### `collect_sources()`

```python
def collect_sources(
    self,
    topics: List[str],
    min_sources: int = 15
) -> List[Source]
```

Birden fazla konu icin kaynak toplar.

### `CitationManager`

Alinti yonetimi sinifi.

```python
from src.research.citation_manager import CitationManager
```

#### Metodlar

##### `add_citation()`

```python
def add_citation(
    self,
    source: Source,
    quote: str,
    section: str
) -> Citation
```

Yeni alinti ekler.

##### `generate_bibliography()`

```python
def generate_bibliography(self, style: str = "apa") -> str
```

Kaynakca olusturur.

---

## Content Generation

### `ContentPlanner`

Icerik planlama sinifi.

```python
from src.content.content_planner import ContentPlanner, ContentPlan
```

#### Metodlar

##### `create_plan()`

```python
def create_plan(
    self,
    report_type: str,
    source_content: str,
    language: str = "tr"
) -> ContentPlan
```

Rapor icin icerik plani olusturur.

### `SectionGenerator`

Bolum uretim sinifi.

```python
from src.content.section_generator import SectionGenerator, GeneratedSection
```

#### Metodlar

##### `generate_section()`

```python
def generate_section(
    self,
    section_plan: SectionPlan,
    sources: List[Source],
    data: Dict[str, Any]
) -> GeneratedSection
```

Tek bir bolum uretir.

### `GeneratedSection`

Uretilmis bolumu tutan dataclass.

```python
@dataclass
class GeneratedSection:
    title: str               # Bolum basligi
    content: str             # Icerik
    word_count: int          # Kelime sayisi
    paragraph_count: int     # Paragraf sayisi
    citations: List[str]     # Alintilar
    quality_score: float     # Kalite puani
```

---

## Validation

### `FinancialValidator`

Finansal veri dogrulama sinifi.

```python
from src.validation.financial_validator import FinancialValidator
```

#### Metodlar

##### `validate()`

```python
def validate(self, content: str) -> ValidationResult
```

Icerikteki finansal verileri dogrular.

### `ValidationResult`

Dogrulama sonucunu tutan dataclass.

```python
@dataclass
class ValidationResult:
    is_valid: bool
    score: float
    issues: List[ValidationIssue]
    warnings: List[str]
    suggestions: List[str]
```

### `ValidationIssue`

Dogrulama sorununu tutan dataclass.

```python
@dataclass
class ValidationIssue:
    severity: IssueSeverity  # ERROR, WARNING, INFO
    category: IssueCategory  # ACCURACY, CONSISTENCY, COMPLETENESS
    message: str
    location: Optional[str]
    suggestion: Optional[str]
```

---

## Generators

### `DocxGenerator`

Word belgesi uretim sinifi.

```python
from src.generator.docx_generator import DocxGenerator
```

#### Metodlar

##### `generate()`

```python
def generate(
    self,
    report: GeneratedReport,
    output_path: str
) -> str
```

DOCX dosyasi olusturur.

### `PdfGenerator`

PDF belgesi uretim sinifi.

```python
from src.generator.pdf_generator import PdfGenerator
```

#### Metodlar

##### `generate()`

```python
def generate(
    self,
    report: GeneratedReport,
    output_path: str
) -> str
```

PDF dosyasi olusturur.

---

## Utilities

### Validators

```python
from src.utils.validators import PathValidator, URLValidator, TextValidator
```

#### `PathValidator`

```python
# Dosya yolu dogrulama
PathValidator.validate(path, check_traversal=True)
PathValidator.validate_file(path)
PathValidator.validate_directory(path, create_if_missing=False)
```

#### `URLValidator`

```python
# URL dogrulama
URLValidator.validate(url)
URLValidator.is_safe(url)
```

#### `TextValidator`

```python
# Metin dogrulama
TextValidator.check_prompt_injection(text)  # bool
TextValidator.sanitize(text, max_length=10000)
```

### Turkish Parser

```python
from src.utils.turkish_parser import (
    TurkishNumberParser,
    parse_number,
    format_turkish_number
)
```

#### Metodlar

```python
# Parse etme
TurkishNumberParser.parse("1.234,56")  # 1234.56
parse_number("1.234,56")               # 1234.56 (kisayol)

# Formatlama
format_turkish_number(1234.56)  # "1.234,56"
```

### Retry Helper

```python
from src.utils.retry_helper import retry_with_backoff, retry_api_call
```

#### Decorator

```python
@retry_with_backoff(
    max_attempts=3,
    min_wait=2,
    max_wait=10,
    exceptions=(APIError,)
)
def my_function():
    pass
```

#### Fonksiyon

```python
result = retry_api_call(
    func,
    *args,
    max_attempts=3,
    **kwargs
)
```

### Common Utilities

```python
from src.utils.common import (
    truncate_text, clean_text, word_count, paragraph_count,
    format_number, format_percentage, format_currency,
    safe_divide, format_file_size, generate_hash,
    chunked, unique_by, Result, BatchResult
)
```

#### Metin Islemleri

```python
truncate_text("Long text...", max_length=100)
clean_text("  messy   text  ")  # "messy text"
word_count("one two three")     # 3
paragraph_count(text)           # paragraf sayisi
```

#### Sayi Formatlama

```python
format_number(1234567.89, locale="tr")  # "1.234.567,89"
format_percentage(75.5)                  # "%75.5"
format_currency(1000, "TRY", "tr")       # "₺1.000"
safe_divide(10, 0, default=0)            # 0
```

#### Veri Yapilari

```python
# Result monad
result = Result.ok(data)
result = Result.fail("error message")

# Batch sonucu
batch = BatchResult(total=10, succeeded=8, failed=2, ...)
print(batch.success_rate)  # 0.8
```

---

## Types

### Enums

```python
from src.types import (
    ReportType, OutputFormat, FileCategory,
    SourceType, QualityLevel
)
```

#### `ReportType`

```python
class ReportType(Enum):
    IS_PLANI = "is_plani"
    PROJE_RAPORU = "proje_raporu"
    SUNUM = "sunum"
    ON_FIZIBILITE = "on_fizibilite"
    TEKNIK_DOK = "teknik_dok"
    ANALIZ_RAPORU = "analiz_raporu"
    KISA_NOT = "kisa_not"
```

#### `OutputFormat`

```python
class OutputFormat(Enum):
    DOCX = "docx"
    PDF = "pdf"
    BOTH = "both"
```

#### `FileCategory`

```python
class FileCategory(Enum):
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    IMAGE = "image"
    UNKNOWN = "unknown"
```

### Protocols

```python
from src.types import (
    Serializable, Parseable, Validatable,
    DocumentParser, Retriever
)
```

#### `DocumentParser` Protocol

```python
class DocumentParser(Protocol):
    def parse(self, file_path: PathLike) -> ParsedDocument: ...
    def supports(self, extension: str) -> bool: ...
```

#### `Retriever` Protocol

```python
class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> List[RetrievalResult]: ...
```

### Configuration Types

```python
from src.types import RetryConfig, CacheConfig, GeneratorConfig
```

#### `RetryConfig`

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    min_wait: float = 2.0
    max_wait: float = 10.0
    exponential_base: float = 2.0
```

#### `CacheConfig`

```python
@dataclass
class CacheConfig:
    max_size: int = 1000
    ttl_seconds: int = 3600
    enabled: bool = True
```

---

## Hata Siniflari

```python
from src.utils.exceptions import (
    ReportGeneratorError,
    PathTraversalError,
    URLValidationError,
    InputValidationError,
    APIError,
    ParseError,
    ValidationError
)
```

### Hiyerarsi

```
ReportGeneratorError (base)
├── PathTraversalError
├── URLValidationError
├── InputValidationError
├── APIError
├── ParseError
└── ValidationError
```

### Kullanim

```python
try:
    result = some_operation()
except PathTraversalError as e:
    logger.error(f"Guvenlik ihlali: {e}")
except APIError as e:
    logger.error(f"API hatasi: {e}")
except ReportGeneratorError as e:
    logger.error(f"Genel hata: {e}")
```
