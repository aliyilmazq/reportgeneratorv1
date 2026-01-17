# TEMEL MİMARİ KURALI

## KRİTİK KURAL: SADECE CLAUDE API

**TÜM AKIŞ SADECE CLAUDE API ÜZERİNDEN OLMALIDIR!**

Bu kural, uygulamanın temel mimari prensibidir ve ihlal edilemez.

---

## Kapsam

Bu kural aşağıdaki TÜM işlemleri kapsar:

1. **Araştırma İşlemleri**
   - Web araştırması
   - Kaynak toplama
   - Veri analizi

2. **Veri Toplama**
   - Ekonomik veriler
   - Sektör verileri
   - İstatistikler

3. **İçerik Üretimi**
   - Bölüm yazımı
   - Özet oluşturma
   - Analiz yapma

4. **Görsel Analizi**
   - Resim analizi
   - Grafik yorumlama

---

## YASAKLAR

Aşağıdaki harici servisler/API'ler **KULLANILMAZ**:

| Servis | Durum | Neden |
|--------|-------|-------|
| DuckDuckGo Search | ❌ YASAK | Harici API |
| Google Search API | ❌ YASAK | Harici API |
| Bing Search API | ❌ YASAK | Harici API |
| Web Scraping (httpx, requests) | ❌ YASAK | Harici bağlantı |
| BeautifulSoup | ❌ YASAK | Web parsing |
| TÜİK API | ❌ YASAK | Harici API |
| TCMB API | ❌ YASAK | Harici API |
| Diğer tüm harici API'ler | ❌ YASAK | Harici bağlantı |

---

## İZİN VERİLEN

| Servis | Durum | Kullanım |
|--------|-------|----------|
| Anthropic (Claude) API | ✅ İZİNLİ | Tüm AI işlemleri |
| Yerel dosya sistemi | ✅ İZİNLİ | Dosya okuma/yazma |
| Yerel veritabanı (ChromaDB) | ✅ İZİNLİ | RAG sistemi |

---

## Uygulama

### Araştırma
```python
# DOĞRU: Claude ile araştırma
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Türkiye ekonomisi hakkında araştırma yap"}]
)

# YANLIŞ: Harici API kullanımı
from duckduckgo_search import DDGS  # ❌ YASAK
ddgs = DDGS()
results = ddgs.text("query")  # ❌ YASAK
```

### Veri Toplama
```python
# DOĞRU: Claude'dan veri al
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Türkiye enflasyon oranı nedir?"}]
)

# YANLIŞ: Web'den veri çekme
import httpx  # ❌ YASAK
response = httpx.get("https://api.tcmb.gov.tr/...")  # ❌ YASAK
```

---

## Gerekçe

1. **Basitlik**: Tek API bağımlılığı ile bakım kolaylığı
2. **Güvenilirlik**: Harici servislerin kesinti riski yok
3. **Tutarlılık**: Tüm içerik tek kaynaktan
4. **Maliyet Kontrolü**: Sadece Claude API maliyeti
5. **Güvenlik**: Harici bağlantı riski yok

---

## İhlal Durumunda

Bu kural ihlal edilirse:

1. Kod review'da reddedilir
2. Merge engellenir
3. Mevcut ihlaller düzeltilir

---

**Bu kural tartışmaya açık DEĞİLDİR.**

Tarih: 2024-01-17
Versiyon: 1.0
