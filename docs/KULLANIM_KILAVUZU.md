# Kullanim Kilavuzu

Bu kilavuz Rapor Uretici v4.0 PRO'nun detayli kullanimini aciklar.

## Icindekiler

1. [Hizli Baslangic](#hizli-baslangic)
2. [Interaktif Mod](#interaktif-mod)
3. [Programatik Kullanim](#programatik-kullanim)
4. [Dosya Hazirlama](#dosya-hazirlama)
5. [Rapor Turleri](#rapor-turleri)
6. [Cikti Formatlari](#cikti-formatlari)
7. [Kalite Ayarlari](#kalite-ayarlari)
8. [Ileri Duzey Kullanim](#ileri-duzey-kullanim)

---

## Hizli Baslangic

### 1. Ortami Hazirla

```bash
# Bagimliliklari yukle
pip install -r requirements.txt

# API anahtarini ayarla
cp .env.example .env
# .env dosyasini duzenle
```

### 2. Kaynak Dosyalari Hazirla

Analiz edilecek dosyalari bir klasore koy:

```
belgeler/
├── finansal_tablo.xlsx
├── proje_ozeti.pdf
├── toplanti_notlari.docx
└── grafik.png
```

### 3. Raporu Uret

```bash
python main.py
```

---

## Interaktif Mod

Program calistirildiginda asagidaki sorular sorulur:

### Adim 1: Dil Secimi

```
[1/5] Cikti dilini secin:
      1. Turkce
      2. Ingilizce
      > 1
```

### Adim 2: Kaynak Dosya/Klasor

```
[2/5] Kaynak dosya veya klasor yolu:
      > ./belgeler
```

Desteklenen formatlar:
- PDF (.pdf)
- Word (.docx, .doc)
- Excel (.xlsx, .xls)
- CSV (.csv)
- Gorseller (.png, .jpg, .jpeg, .gif)

### Adim 3: Rapor Turu

```
[3/5] Rapor turunu secin:
      1. Is Plani
      2. Proje Raporu
      3. Sunum
      4. On Fizibilite
      5. Teknik Dokumantasyon
      6. Analiz Raporu
      7. Kisa Not / Ozet
      > 6
```

### Adim 4: Cikti Formati

```
[4/5] Cikti formatini secin:
      1. DOCX (Word)
      2. PDF
      3. Her ikisi
      > 3
```

### Adim 5: Ozel Notlar (Opsiyonel)

```
[5/5] Ozel notlar (bos birakilabilir):
      > Finansal verilere odaklan, 2024 projeksiyonlari ekle
```

### Rapor Uretimi

```
╔════════════════════════════════════════════╗
║ Rapor uretimi basliyor...                  ║
║                                            ║
║ ✓ Kurallar bellekte aktif                  ║
║   - Min kelime/bolum: 500                  ║
║   - Min kaynak: 15                         ║
║   - Min kalite: 70%                        ║
║                                            ║
║ Bu islem 30-60 dakika surebilir.           ║
╚════════════════════════════════════════════╝
```

---

## Programatik Kullanim

### Temel Kullanim

```python
from src.orchestrator import ReportOrchestrator, UserInput

# Kullanici girdisi
user_input = UserInput(
    input_path="./belgeler",
    output_type="analiz_raporu",
    output_format="both",
    language="tr",
    special_notes=""
)

# Orchestrator olustur
orchestrator = ReportOrchestrator(
    output_dir="./output",
    use_live_progress=True
)

# Rapor uret
report = orchestrator.generate_report(user_input)

# Sonuclari goster
print(f"Baslik: {report.title}")
print(f"Bolum sayisi: {len(report.sections)}")
print(f"Toplam kelime: {report.statistics['total_words']}")
print(f"Kaynak sayisi: {report.statistics['total_sources']}")
print(f"Cikti dosyalari: {report.output_files}")
```

### Dosya Tarama

```python
from src.scanner import FileScanner

scanner = FileScanner()
result = scanner.scan("./belgeler")

print(f"Toplam dosya: {result.total_files}")
print(f"Toplam boyut: {result.total_size} bytes")

# Kategorilere gore dosyalar
for category, files in result.files.items():
    print(f"{category}: {len(files)} dosya")
```

### Tek Dosya Parse Etme

```python
from src.parsers import ParserFactory

# PDF parse
parser = ParserFactory.create("document.pdf")
content = parser.parse("document.pdf")
print(content.text)
print(content.tables)

# Excel parse
parser = ParserFactory.create("data.xlsx")
content = parser.parse("data.xlsx")
print(content.dataframes)
```

### Web Arastirmasi

```python
from src.research.web_researcher import WebResearcher

researcher = WebResearcher()
results = researcher.research_topic(
    topic="Turkiye ekonomisi 2024",
    max_sources=10
)

for result in results:
    print(f"Baslik: {result.title}")
    print(f"URL: {result.url}")
    print(f"Ozet: {result.summary[:200]}...")
```

### Turkce Sayi Parsing

```python
from src.utils.turkish_parser import TurkishNumberParser, parse_number

# Turkce format: 1.234,56
num = TurkishNumberParser.parse("1.234,56")
print(num)  # 1234.56

# US format: 1,234.56
num = parse_number("1,234.56")
print(num)  # 1234.56

# Formatlama
from src.utils.turkish_parser import format_turkish_number
formatted = format_turkish_number(1234.56)
print(formatted)  # "1.234,56"
```

---

## Dosya Hazirlama

### PDF Dosyalari

- Metin tabanli PDF'ler en iyi sonucu verir
- Taranmis PDF'ler icin OCR kullanilir (sinirli)
- Tablolar otomatik olarak cikarilir

### Excel Dosyalari

- Her sayfa ayri ayri islenir
- Baslik satiri otomatik algilanir
- Formul sonuclari kullanilir (formul kendisi degil)

### Word Dosyalari

- Tum metin icerik cikarilir
- Tablolar korunur
- Gorseller analiz edilir

### Gorseller

- Claude Vision API ile analiz edilir
- Grafik ve tablolar yorumlanir
- Metin icerigi (OCR) cikarilir

---

## Rapor Turleri

### Is Plani (`is_plani`)

Kapsamli is plani dokumani:
- Yonetici ozeti
- Pazar analizi
- Rekabet analizi
- Pazarlama stratejisi
- Operasyon plani
- Finansal projeksiyonlar
- Risk analizi

### Proje Raporu (`proje_raporu`)

Proje durumu ve sonuc raporu:
- Proje ozeti
- Hedefler ve kapsam
- Metodoloji
- Bulgular
- Sonuclar ve oneriler

### Sunum (`sunum`)

Ozet sunum dokumani:
- Ana mesajlar
- Anahtar bulgular
- Gorsel agirlikli icerik
- Sonuc ve aksiyon ogeleri

### On Fizibilite (`on_fizibilite`)

Fizibilite degerlendirme raporu:
- Teknik fizibilite
- Ekonomik fizibilite
- Operasyonel fizibilite
- Yasal uyumluluk

### Teknik Dokumantasyon (`teknik_dok`)

Teknik detay dokumani:
- Sistem mimarisi
- Teknik spesifikasyonlar
- Uygulama detaylari
- Bakim gereksinimleri

### Analiz Raporu (`analiz_raporu`)

Veri analizi ve bulgular raporu:
- Veri kaynaklari
- Metodoloji
- Analiz sonuclari
- Yorumlar
- Oneriler

### Kisa Not (`kisa_not`)

Kisa ozet dokumani:
- Temel bulgular
- Kritik noktalar
- Hizli referans

---

## Cikti Formatlari

### DOCX (Word)

- Duzenlenebilir format
- Kurumsal sablonla uyumlu
- Tablo ve grafik destegi
- Sayfa numaralama

### PDF

- Salt okunur format
- Profesyonel gorunum
- Dijital imza uyumlu
- Baski icin optimize

---

## Kalite Ayarlari

Kurallar `rules/` klasorunde tanimlidir:

### Minimum Gereksinimler

| Parametre | Deger |
|-----------|-------|
| Kelime/Bolum | 500 |
| Paragraf/Bolum | 3 |
| Kaynak/Bolum | 2 |
| Toplam Kaynak | 15 |
| Kalite Puani | %70 |

### Kalite Puani Hesaplama

```
Puan = (
    Kelime Skoru * 0.25 +
    Kaynak Skoru * 0.25 +
    Yapı Skoru * 0.20 +
    Dogruluk Skoru * 0.30
)
```

---

## Ileri Duzey Kullanim

### Ozel Kural Dosyalari

`rules/` klasorundeki dosyalari duzenleyerek kurallari ozellestirin:

```markdown
# 01_genel_kurallar.md

## Minimum Gereksinimler
- min_words_per_section: 800  # Arttirildi
- min_sources: 20             # Arttirildi
```

### Cache Yonetimi

```python
from src.data_sources.cache import CacheManager

cache = CacheManager()

# Cache temizle
cache.clear()

# Belirli bir anahtari sil
cache.delete("economic_data_2024")

# Cache istatistikleri
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
```

### Loglama Seviyesi

`.env` dosyasinda:

```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### Zaman Asimi Ayarlari

```env
API_TIMEOUT=60        # API istekleri icin (saniye)
RETRY_MAX_ATTEMPTS=5  # Maksimum yeniden deneme
RETRY_MIN_WAIT=2      # Minimum bekleme (saniye)
RETRY_MAX_WAIT=30     # Maksimum bekleme (saniye)
```

---

## Sik Sorulan Sorular

### S: Rapor ne kadar surede olusur?

Kaynak dosya sayisi ve buyuklugune bagli olarak 30-60 dakika arasinda degisir.

### S: API maliyeti ne kadar?

Claude API kullanim miktarina bagli. Ortalama bir rapor 50-100K token kullanir.

### S: Hangi dilleri destekliyor?

Turkce ve Ingilizce tam desteklenir. Diger diller sinirli destek sunar.

### S: Maksimum dosya boyutu nedir?

Varsayilan 100MB. `.env` dosyasinda `MAX_FILE_SIZE_MB` ile degistirilebilir.

### S: Cevrimdisi calisir mi?

Hayir, Claude API erisimi gerektirir. Ancak cache sayesinde tekrarlayan istekler hizlanir.
