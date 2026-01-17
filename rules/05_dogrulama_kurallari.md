# DOĞRULAMA KURALLARI

Üretilen içeriğin doğrulanması ve kalite kontrolü için kurallar.

---

## 1. OTOMATİK DOĞRULAMA

### 1.1 Kelime Sayısı Kontrolü
```python
MINIMUM_KELIME = {
    "yonetici_ozeti": 300,
    "sirket_tanimi": 400,
    "pazar_analizi": 600,
    "rekabet_analizi": 500,
    "pazarlama_stratejisi": 500,
    "operasyon_plani": 400,
    "finansal_projeksiyonlar": 500,
    "risk_analizi": 400,
    "TOPLAM": 3000
}

# Kontrol
if section.word_count < MINIMUM_KELIME[section.id]:
    raise ValidationError(f"{section.title}: Yetersiz kelime")
```

### 1.2 Paragraf Kontrolü
```python
MINIMUM_PARAGRAF = 3

paragraphs = [p for p in content.split('\n\n') if len(p) > 100]
if len(paragraphs) < MINIMUM_PARAGRAF:
    raise ValidationError("Yetersiz paragraf sayısı")
```

### 1.3 Referans Kontrolü
```python
MINIMUM_REFERANS = 2

citations = re.findall(r'\[\d+\]', content)
if len(set(citations)) < MINIMUM_REFERANS:
    raise ValidationError("Yetersiz kaynak referansı")
```

---

## 2. İÇERİK DOĞRULAMA

### 2.1 Sayısal Veri Kontrolü
Her sayısal veri için:
- [ ] Kaynak referansı var mı?
- [ ] Birim belirtilmiş mi?
- [ ] Mantıklı aralıkta mı?
- [ ] Dönem belirtilmiş mi?

### 2.2 Mantık Kontrolü
```python
MANTIK_KURALLARI = [
    # Oran kontrolleri
    ("net_kar_marji", "<", "brut_kar_marji"),
    ("faaliyet_giderleri", ">", 0),
    ("buyume_orani", "between", (-50, 200)),

    # Toplam kontrolleri
    ("pazar_paylari_toplam", "==", 100),
    ("maliyet_dagilimi_toplam", "==", 100),
]
```

### 2.3 Tutarlılık Kontrolü
- Aynı veri farklı bölümlerde tutarlı mı?
- Rakamlar çelişiyor mu?
- Tarihler tutarlı mı?

---

## 3. KAYNAK DOĞRULAMA

### 3.1 URL Kontrolü
```python
def verify_url(url):
    # URL formatı doğru mu?
    assert url.startswith(('http://', 'https://'))

    # Domain güvenilir mi?
    domain = extract_domain(url)
    assert domain in TRUSTED_DOMAINS or credibility_score(domain) >= 0.5

    # URL erişilebilir mi? (opsiyonel)
    # response = requests.head(url, timeout=5)
    # assert response.status_code == 200
```

### 3.2 Kaynak Eşleştirme
```python
# Her referans numarası kaynakçada tanımlı mı?
citations_in_text = set(re.findall(r'\[(\d+)\]', content))
citations_in_refs = set(range(1, len(references) + 1))

missing = citations_in_text - citations_in_refs
if missing:
    raise ValidationError(f"Tanımsız referanslar: {missing}")
```

---

## 4. FİNANSAL DOĞRULAMA

### 4.1 Oran Kontrolleri
| Oran | Beklenen Aralık | Uyarı |
|------|-----------------|-------|
| Brüt Kar Marjı | %10-%80 | Sektöre göre değişir |
| Net Kar Marjı | %2-%30 | Brütten düşük olmalı |
| FAVÖK Marjı | %5-%40 | Sektöre göre değişir |
| Büyüme Oranı | -%30-%150 | Aşırı değerler uyarı |

### 4.2 Projeksiyon Kontrolü
```python
def validate_projection(projections):
    for year in projections:
        # Gelir > Gider mi?
        assert year.gelir >= year.gider, "Gelir giderden az olamaz"

        # Büyüme mantıklı mı?
        if prev_year:
            growth = (year.gelir - prev_year.gelir) / prev_year.gelir
            assert -0.5 <= growth <= 2.0, "Aşırı büyüme oranı"
```

### 4.3 Başabaş Analizi
- Başabaş noktası pozitif mi?
- Makul süre içinde mi? (genelde 6-60 ay)
- Varsayımlarla tutarlı mı?

---

## 5. ÇAPRAZ REFERANS

### 5.1 Bölümler Arası Tutarlılık
```python
# Pazar büyüklüğü her yerde aynı mı?
pazar_degerleri = extract_market_size_from_all_sections()
if len(set(pazar_degerleri)) > 1:
    raise InconsistencyError("Pazar büyüklüğü tutarsız")

# Hedef müşteri profili tutarlı mı?
# Finansal varsayımlar uyumlu mu?
```

### 5.2 Tolerans Seviyeleri
| Veri Tipi | Tolerans |
|-----------|----------|
| Pazar büyüklüğü | %5 |
| Büyüme oranları | %2 |
| Finansal rakamlar | %1 |
| Tarihler | 0 (tam eşleşme) |

---

## 6. KALİTE PUANLAMASI

### 6.1 Puan Hesaplama
```python
def calculate_quality_score(section):
    score = 0

    # Kelime sayısı (30 puan)
    if word_count >= target_words:
        score += 30
    else:
        score += 30 * (word_count / target_words)

    # Paragraf sayısı (20 puan)
    if paragraph_count >= 3:
        score += 20
    else:
        score += 20 * (paragraph_count / 3)

    # Referans kullanımı (25 puan)
    if citation_count >= 3:
        score += 25
    elif citation_count >= 1:
        score += 15

    # Tablo/görsel (10 puan)
    if has_table:
        score += 10

    # Veri çeşitliliği (15 puan)
    if has_numbers and has_percentages:
        score += 15
    elif has_numbers or has_percentages:
        score += 8

    return score
```

### 6.2 Minimum Puan Gereksinimleri
| Bölüm | Minimum Puan |
|-------|--------------|
| Yönetici Özeti | 70 |
| Pazar Analizi | 75 |
| Finansal Projeksiyonlar | 75 |
| Diğer bölümler | 65 |
| **ORTALAMA** | **70** |

---

## 7. HATA TİPLERİ

### 7.1 Kritik Hatalar (İşlemi Durdurur)
- Kaynak olmadan istatistik
- Tutarsız finansal veriler
- Minimum kelime sayısının altı
- Referanssız bölüm

### 7.2 Uyarılar (Bildirim)
- Eski kaynak (2+ yıl)
- Tek kaynaklı veri
- Marjinal kalite puanı
- Eksik tablo

### 7.3 Bilgi (Log)
- Kaynak çeşitliliği düşük
- Alternatif veri bulunamadı
- Öneri: daha fazla kaynak

---

## 8. DOĞRULAMA SIRASI

```
1. Otomatik kontroller çalıştır
2. Kelime/paragraf sayısı kontrol
3. Referans kontrolü
4. Finansal doğrulama
5. Çapraz referans kontrolü
6. Kalite puanı hesapla
7. Hataları raporla
8. Gerekirse düzeltme yap
```

---

## DOĞRULAMA BAŞARISIZ İSE:

1. Hata mesajı göster
2. Problemi tanımla
3. Düzeltme öner
4. Tekrar üret veya manuel düzeltme iste

**Doğrulamadan geçmeyen içerik YAYINLANAMAZ.**
