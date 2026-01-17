# Degisiklik Gecmisi

Bu dosya projedeki tum onemli degisiklikleri icerir.

Format [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) standartina uygundur.

## [4.0.0] - 2024-01-17

### Eklenenler

#### Yeni Moduller
- `src/types.py` - Merkezi tip tanimlari (Protocol, Enum, Dataclass)
- `src/utils/common.py` - 40+ ortak yardimci fonksiyon
- `src/parsers/base_parser.py` - Soyut parser sinifi ve ParserFactory
- `src/utils/validators.py` - Girdi dogrulama (Path, URL, Text)
- `src/utils/turkish_parser.py` - Turkce sayi format destegi
- `src/utils/exceptions.py` - Ozel hata siniflari
- `src/config/constants.py` - Merkezi yapilandirma

#### Yeni Testler
- `tests/test_utils.py` - 46 utility testi
- `tests/test_validators.py` - 16 validator testi
- `tests/test_parsers.py` - 28 parser testi
- Toplam: 155 test, %100 basari

#### Ozellikler
- Gercek web arastirmasi (DuckDuckGo API)
- Ekonomik veri cekme (TUIK/TCMB)
- Kaynak referanslari ve kaynakca
- Ilerleme takibi ve tahmini sure
- Minimum 500+ kelime/bolum gereksinimleri

### Degistirildi

#### Guvenlik Iyilestirmeleri
- Path traversal korumasi eklendi
- Prompt injection onleme mekanizmasi
- URL dogrulama ve sanitizasyon
- Guvenli dosya yolu islemleri

#### Hata Yonetimi
- Bare `except` -> Spesifik exception turleri
- Retry logic with exponential backoff
- Merkezi hata mesajlari
- Logging framework entegrasyonu

#### Bellek Yonetimi
- LRU cache implementasyonu
- Context manager kullanimi (parsers)
- ThreadPoolExecutor yasam dongusu yonetimi
- Kaynak temizleme iyilestirmeleri

#### Kod Kalitesi
- Type hints tum fonksiyonlara eklendi
- Dataclass kullanimi yayginlastirildi
- Kod tekrari elimine edildi
- API tutarliligi saglandi
- Docstring'ler guncellendi

#### Veri Isleme
- Turkce sayi parsing duzeltildi (1.234,56 formati)
- Markdown tablo parsing guclendirildi
- Unicode karakter destegi iyilestirildi

### Duzeltildi

- Global state thread-safety sorunlari
- Cache bellek sizintilari
- API rate limiting hatalari
- Dosya handle kapatma eksiklikleri
- Turkish karakter encoding sorunlari

### Teknik Borc Odeme

| Kategori | Once | Sonra |
|----------|------|-------|
| Kritik Sorunlar | 72 | 0 |
| Onemli Sorunlar | 102 | 0 |
| Kucuk Sorunlar | 100 | 0 |
| Test Sayisi | 67 | 155 |

## [3.0.0] - 2024-01-10

### Eklenenler
- RAG (Retrieval Augmented Generation) sistemi
- Vektor store entegrasyonu
- Hibrit arama (BM25 + semantic)
- Gelismis embedding destegi

### Degistirildi
- Icerik uretim pipeline'i yeniden yapilandirildi
- Belge uretim sureci optimize edildi

## [2.0.0] - 2024-01-05

### Eklenenler
- PDF parsing (pdfplumber)
- Excel/CSV destegi (openpyxl, pandas)
- Word dokuman destegi (python-docx)
- Gorsel analizi

### Degistirildi
- Tek dosya desteginden coklu dosya destegine gecis

## [1.0.0] - 2024-01-01

### Eklenenler
- Temel rapor uretim sistemi
- Claude API entegrasyonu
- Interaktif CLI
- DOCX ve PDF cikti

---

## Surum Numaralama

Bu proje [Semantic Versioning](https://semver.org/) kullanir:

- **MAJOR**: Geriye uyumsuz degisiklikler
- **MINOR**: Geriye uyumlu yeni ozellikler
- **PATCH**: Geriye uyumlu hata duzeltmeleri
