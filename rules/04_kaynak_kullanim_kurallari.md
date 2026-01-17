# KAYNAK KULLANIM KURALLARI

Kaynakların nasıl kullanılacağı, referans gösterileceği ve doğrulanacağına dair kurallar.

---

## 1. REFERANS SİSTEMİ

### 1.1 Inline Referans Formatı
```
Türkiye e-ticaret pazarı 2024 yılında 1.8 trilyon TL'ye ulaştı [1].
```

### 1.2 Çoklu Referans
```
Sektör büyüme oranı %35 olarak gerçekleşti [1][2].
```

### 1.3 Dolaylı Referans
```
TÜİK verilerine göre [3], işsizlik oranı %9.8 seviyesinde.
```

---

## 2. KAYNAKÇA FORMATI

### 2.1 Web Kaynağı
```
[1] Türkiye E-Ticaret Raporu 2024. (Erişim: 17.01.2024).
    TÜBİSAD. https://www.tubisad.org.tr/rapor2024
```

### 2.2 Resmi Kurum
```
[2] Dış Ticaret İstatistikleri, Aralık 2024.
    TÜİK. https://data.tuik.gov.tr/
```

### 2.3 Haber Kaynağı
```
[3] "Merkez Bankası faiz kararını açıkladı". (15.01.2024).
    Reuters. https://www.reuters.com/...
```

---

## 3. KAYNAK SINIFLANDIRMASI

### 3.1 Birincil Kaynaklar (Öncelikli)
| Tip | Örnekler | Kullanım |
|-----|----------|----------|
| Resmi istatistik | TÜİK, TCMB | Tüm sayısal veriler |
| Düzenleyici kurumlar | BDDK, SPK | Sektör verileri |
| Uluslararası kuruluşlar | IMF, WB, OECD | Karşılaştırmalı veriler |

### 3.2 İkincil Kaynaklar (Destekleyici)
| Tip | Örnekler | Kullanım |
|-----|----------|----------|
| Sektör raporları | Deloitte, PwC | Trend analizleri |
| Haber ajansları | Reuters, AA | Güncel gelişmeler |
| Araştırma şirketleri | Statista | Pazar verileri |

### 3.3 Üçüncül Kaynaklar (Sınırlı Kullanım)
| Tip | Örnekler | Kullanım |
|-----|----------|----------|
| Haber siteleri | Ekonomi haberleri | Sadece doğrulanmış bilgi |
| Kurumsal bloglar | Şirket blogları | Sektör görüşleri |

---

## 4. KAYNAK DOĞRULAMA

### 4.1 Zorunlu Kontroller
```python
def verify_source(source):
    assert source.url is not None, "URL zorunlu"
    assert source.access_date is not None, "Erişim tarihi zorunlu"
    assert source.credibility >= 0.5, "Düşük güvenilirlik"
    assert is_accessible(source.url), "URL erişilebilir olmalı"
```

### 4.2 Çapraz Doğrulama Kuralları
- Kritik veriler: **en az 2 kaynak**
- Finansal veriler: **resmi kaynak zorunlu**
- Tartışmalı konular: **en az 3 kaynak**

### 4.3 Tutarsızlık Durumunda
1. Resmi kaynağı tercih et
2. Daha güncel olanı seç
3. Tutarsızlığı raporda belirt:
   ```
   Not: Bu konuda kaynaklar arasında farklılık bulunmaktadır.
   TÜİK verisi (%15) ve sektör raporu (%17) arasında fark mevcuttur.
   ```

---

## 5. ALINTILAR

### 5.1 Doğrudan Alıntı
```
TCMB Başkanı'nın açıklamasına göre: "Enflasyonla mücadelede
kararlılığımız sürecektir." [4]
```

### 5.2 Dolaylı Alıntı
```
Merkez Bankası, enflasyonla mücadelede kararlı olduğunu
vurguladı [4].
```

### 5.3 Alıntı Kuralları
- Doğrudan alıntı: tırnak içinde
- 40 kelimeden uzun alıntı: blok olarak
- Her alıntı için kaynak zorunlu
- Alıntı değiştirilemez (kesme [...] ile belirtilmeli)

---

## 6. KAYNAK LİMİTLERİ

### 6.1 Minimum Kaynak Sayıları
| Bölüm | Minimum Kaynak |
|-------|----------------|
| Yönetici Özeti | 3 |
| Pazar Analizi | 5 |
| Rekabet Analizi | 4 |
| Finansal Projeksiyonlar | 4 |
| Risk Analizi | 3 |
| **TOPLAM RAPOR** | **15** |

### 6.2 Kaynak Çeşitliliği
- Aynı kaynaktan: maksimum %30
- Resmi kaynak oranı: minimum %40
- Güncel kaynak (son 1 yıl): minimum %60

---

## 7. YASAK KULLANIM

### 7.1 Kabul Edilmeyenler
- ❌ Kaynaksız istatistik
- ❌ "Araştırmalar gösteriyor" (hangi araştırma?)
- ❌ "Uzmanlar belirtiyor" (hangi uzman?)
- ❌ "Bilindiği üzere" (nereden biliniyor?)
- ❌ Sosyal medya kaynakları
- ❌ Wikipedia (doğrudan kaynak olarak)

### 7.2 Hatalı Referans Örnekleri
```
❌ YANLIŞ: Pazar büyüklüğü 50 milyar TL'dir.
✅ DOĞRU: Pazar büyüklüğü 50 milyar TL'dir [1].

❌ YANLIŞ: Araştırmalar gösteriyor ki...
✅ DOĞRU: TÜBİSAD 2024 raporuna göre [2]...

❌ YANLIŞ: Sektör hızla büyüyor.
✅ DOĞRU: Sektör yıllık %25 oranında büyüyor [3].
```

---

## 8. KAYNAK YÖNETİMİ

### 8.1 Kaynak Saklama
Her kaynak için saklanacaklar:
```json
{
  "id": 1,
  "url": "https://...",
  "title": "...",
  "source_name": "TÜİK",
  "access_date": "2024-01-17",
  "credibility_score": 1.0,
  "data_extracted": [...],
  "used_in_sections": ["pazar_analizi", "finansal"]
}
```

### 8.2 Kaynakça Oluşturma
- Rapor sonunda ayrı bölüm
- Numara sırasına göre liste
- Tüm URL'ler tıklanabilir
- Erişim tarihleri belirtilmiş

---

## KAYNAK KULLANMADAN:

- ❌ Rakam yazılamaz
- ❌ Trend belirtilemez
- ❌ Karşılaştırma yapılamaz
- ❌ Projeksiyon oluşturulamaz

**Her bilginin kaynağı BELİRTİLMELİDİR.**
