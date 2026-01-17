# Rapor Uretici v4.0 PRO

Yapay zeka destekli kurumsal rapor uretim sistemi. Claude API kullanarak PDF, Excel, Word ve gorsel dosyalarindan profesyonel raporlar olusturur.

## Ozellikler

- **Claude-Only Mimari**: TUM islemler SADECE Claude API uzerinden yapilir
- **Coklu Dosya Destegi**: PDF, DOCX, XLSX, CSV, PNG, JPG
- **Turkce Optimizasyon**: Turkce sayi formati, karakter ve icerik destegi
- **Akilli Icerik Uretimi**: Claude ile zengin paragraf icerigi
- **Arastirma ve Analiz**: Claude tabanli arastirma ve veri analizi
- **Kalite Kontrolu**: Minimum 500 kelime/bolum, %70 kalite puani
- **Coklu Format**: DOCX ve PDF cikti destegi

> **KURAL**: Tum akis sadece Claude API uzerinden olur. Harici API kullanilmaz!

## Kurulum

### Gereksinimler

- Python 3.9+
- Anthropic API anahtari

### Adimlar

```bash
# Repoyu klonla
git clone https://github.com/kullanici/reportgeneratorv1.git
cd reportgeneratorv1

# Bagimliliklari yukle
pip install -r requirements.txt

# Ortam degiskenlerini ayarla
cp .env.example .env
# .env dosyasini duzenle ve API anahtarini ekle
```

### .env Dosyasi

```env
# Zorunlu
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Opsiyonel
LOG_LEVEL=INFO
CACHE_DIR=.cache
OUTPUT_DIR=./output
MAX_FILE_SIZE_MB=100
API_TIMEOUT=30
```

## Kullanim

### Interaktif Mod

```bash
python main.py
```

Program sizden asagidaki bilgileri isteyecektir:
1. Cikti dili (Turkce/Ingilizce)
2. Kaynak dosya/klasor yolu
3. Rapor turu (Is Plani, Proje Raporu, Sunum, vb.)
4. Cikti formati (DOCX, PDF veya her ikisi)
5. Ozel notlar (opsiyonel)

### Programatik Kullanim

```python
from src.orchestrator import ReportOrchestrator, UserInput

# Kullanici girdisi olustur
user_input = UserInput(
    input_path="./belgeler",
    output_type="analiz_raporu",
    output_format="both",
    language="tr",
    special_notes="Finansal verilere odaklan"
)

# Rapor uret
orchestrator = ReportOrchestrator(output_dir="./output")
report = orchestrator.generate_report(user_input)

print(f"Rapor olusturuldu: {report.output_files}")
```

## Proje Yapisi

```
reportgeneratorv1/
├── main.py                 # Ana giris noktasi
├── src/
│   ├── orchestrator.py     # Is akisi koordinatoru
│   ├── scanner.py          # Dosya tarayici
│   ├── cli.py              # Komut satiri arayuzu
│   ├── types.py            # Tip tanimlari
│   │
│   ├── config/
│   │   └── constants.py    # Yapilandirma sabitleri
│   │
│   ├── parsers/            # Dosya ayristiricilari
│   │   ├── base_parser.py  # Temel parser sinifi
│   │   ├── pdf_parser.py   # PDF isleme
│   │   ├── excel_parser.py # Excel/CSV isleme
│   │   ├── word_parser.py  # Word isleme
│   │   └── image_analyzer.py # Gorsel analizi
│   │
│   ├── research/           # Web arastirma
│   │   ├── web_researcher.py    # DuckDuckGo arama
│   │   ├── source_collector.py  # Kaynak toplama
│   │   └── citation_manager.py  # Alinti yonetimi
│   │
│   ├── data_sources/       # Veri kaynaklari
│   │   ├── web_data_fetcher.py  # Ekonomik veri
│   │   └── cache.py             # Onbellekleme
│   │
│   ├── content/            # Icerik uretimi
│   │   ├── content_planner.py   # Icerik planlama
│   │   └── section_generator.py # Bolum uretimi
│   │
│   ├── validation/         # Dogrulama
│   │   ├── financial_validator.py # Finansal dogrulama
│   │   └── logic_checker.py       # Mantik kontrolu
│   │
│   ├── generator/          # Belge uretimi
│   │   ├── docx_generator.py # Word ciktisi
│   │   └── pdf_generator.py  # PDF ciktisi
│   │
│   ├── rag/                # RAG sistemi
│   │   ├── vector_store.py      # Vektor deposu
│   │   ├── hybrid_retriever.py  # Hibrit arama
│   │   └── cache_manager.py     # Onbellek yonetimi
│   │
│   ├── utils/              # Yardimci moduller
│   │   ├── validators.py       # Girdi dogrulama
│   │   ├── turkish_parser.py   # Turkce sayi parsing
│   │   ├── retry_helper.py     # Yeniden deneme
│   │   ├── exceptions.py       # Ozel hatalar
│   │   ├── common.py           # Ortak fonksiyonlar
│   │   └── logger.py           # Loglama
│   │
│   ├── rules/              # Kural sistemi
│   │   └── rules_loader.py # Kural yukleyici
│   │
│   └── progress/           # Ilerleme takibi
│       ├── phase_tracker.py     # Faz takibi
│       └── progress_reporter.py # Ilerleme raporlama
│
├── rules/                  # Kural dosyalari
│   ├── 01_genel_kurallar.md
│   ├── 02_arastirma_kurallari.md
│   ├── 03_icerik_uretim_kurallari.md
│   ├── 04_kaynak_kullanim_kurallari.md
│   ├── 05_dogrulama_kurallari.md
│   └── 06_kalite_standartlari.md
│
├── tests/                  # Test dosyalari
│   ├── test_parsers.py
│   ├── test_validators.py
│   ├── test_utils.py
│   ├── test_rag_components.py
│   └── test_rag_integration.py
│
├── .env.example            # Ortam degiskenleri sablonu
├── requirements.txt        # Python bagimliliklari
└── pytest.ini              # Pytest yapilandirmasi
```

## Rapor Turleri

| Tur | Aciklama |
|-----|----------|
| `is_plani` | Kapsamli is plani dokumani |
| `proje_raporu` | Proje durumu ve sonuc raporu |
| `sunum` | Ozet sunum dokumani |
| `on_fizibilite` | Fizibilite degerlendirme raporu |
| `teknik_dok` | Teknik detay dokumani |
| `analiz_raporu` | Veri analizi ve bulgular raporu |
| `kisa_not` | Kisa ozet dokumani |

## Kalite Standartlari

Sistem asagidaki minimum gereksinimleri zorlar:

- **Kelime/Bolum**: Minimum 500 kelime
- **Paragraf/Bolum**: Minimum 3 paragraf
- **Kaynak/Bolum**: Minimum 2 kaynak
- **Toplam Kaynak**: Minimum 15 kaynak
- **Kalite Puani**: Minimum %70

## Guvenlik

- **Path Traversal Korumasi**: Dosya yolu dogrulamasi
- **Prompt Injection Onleme**: Girdi sanitizasyonu
- **URL Dogrulama**: Guvenli URL kontrolu
- **API Anahtar Korumasi**: .env ile gizli tutulan anahtarlar

## Test

```bash
# Tum testleri calistir
pytest tests/ -v

# Belirli bir test dosyasini calistir
pytest tests/test_validators.py -v

# Coverage raporu
pytest tests/ --cov=src --cov-report=html
```

### Test Sonuclari

- **155 test** - Tumu basarili
- Kapsam: Parsers, Validators, RAG, Utils

## API Referansi

### ReportOrchestrator

```python
class ReportOrchestrator:
    def __init__(
        self,
        output_dir: str = "./output",
        use_live_progress: bool = True
    ):
        """
        Rapor uretim koordinatoru.

        Args:
            output_dir: Cikti dizini
            use_live_progress: Canli ilerleme gosterimi
        """

    def generate_report(self, user_input: UserInput) -> GeneratedReport:
        """
        Rapor uret.

        Args:
            user_input: Kullanici girdileri

        Returns:
            GeneratedReport: Uretilen rapor
        """
```

### FileScanner

```python
class FileScanner:
    def scan(self, path: str) -> ScanResult:
        """
        Dizini tara ve dosyalari listele.

        Args:
            path: Taranacak dizin yolu

        Returns:
            ScanResult: Tarama sonuclari
        """
```

### TurkishNumberParser

```python
class TurkishNumberParser:
    @staticmethod
    def parse(text: str, default: float = 0.0) -> float:
        """
        Turkce sayi formatini parse et.

        Desteklenen formatlar:
        - Turkce: 1.234,56 -> 1234.56
        - US: 1,234.56 -> 1234.56

        Args:
            text: Sayi metni
            default: Hata durumunda varsayilan deger

        Returns:
            float: Parse edilen sayi
        """
```

## Sorun Giderme

### API Baglanti Hatasi

```
ANTHROPIC_API_KEY ortam degiskeni ayarlanmamis!
```

**Cozum**: `.env` dosyasina gecerli API anahtari ekleyin.

### Modul Import Hatasi

```
ModuleNotFoundError: No module named 'xxx'
```

**Cozum**: `pip install -r requirements.txt` komutunu calistirin.

### Bellek Hatasi

Buyuk dosyalarla calisirken bellek sorunu yasiyorsaniz:

```env
MAX_FILE_SIZE_MB=50  # Daha kucuk limit
```

## Degerler

- Python 3.9+
- anthropic
- pdfplumber
- python-docx
- openpyxl
- pandas
- rich
- PyYAML
- reportlab
- Pillow
- duckduckgo-search
- httpx
- beautifulsoup4
- python-dotenv

## Lisans

MIT License

## Katkida Bulunma

1. Fork yapin
2. Feature branch olusturun (`git checkout -b feature/yeni-ozellik`)
3. Degisikliklerinizi commit edin (`git commit -m 'Yeni ozellik eklendi'`)
4. Branch'i push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request olusturun

## Versiyon Gecmisi

Detayli degisiklik gecmisi icin [CHANGELOG.md](CHANGELOG.md) dosyasina bakin.
