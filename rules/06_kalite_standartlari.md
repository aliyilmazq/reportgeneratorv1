# KALİTE STANDARTLARI

Raporun kalitesini belirleyen standartlar ve ölçütler.

---

## 1. İÇERİK KALİTESİ

### 1.1 Derinlik Seviyeleri

| Seviye | Açıklama | Kabul |
|--------|----------|-------|
| 1 - Yüzeysel | Genel bilgi, detay yok | ❌ RED |
| 2 - Temel | Bazı detaylar, sınırlı analiz | ❌ RED |
| 3 - Orta | Yeterli detay, temel analiz | ⚠️ Minimum |
| 4 - İyi | Detaylı analiz, kaynaklar | ✅ Kabul |
| 5 - Mükemmel | Kapsamlı, çok kaynaklı | ✅ Hedef |

### 1.2 Derinlik Kriterleri
```
Seviye 3 (Minimum) Gereksinimleri:
- 500+ kelime/bölüm
- 3+ paragraf/bölüm
- 2+ kaynak/bölüm
- Temel analiz ve çıkarımlar
- Mantıksal akış

Seviye 4-5 (Hedef) Gereksinimleri:
- 800+ kelime/bölüm
- 5+ paragraf/bölüm
- 4+ kaynak/bölüm
- Derinlemesine analiz
- Karşılaştırmalı değerlendirme
- Somut öneriler
```

---

## 2. YAZI KALİTESİ

### 2.1 Okunabilirlik
```
Hedef Metrikler:
- Ortalama cümle uzunluğu: 15-20 kelime
- Paragraf uzunluğu: 100-200 kelime
- Pasif cümle oranı: <%20
- Teknik terim oranı: <%15 (açıklamalı)
```

### 2.2 Profesyonellik
- [ ] Resmi dil kullanımı
- [ ] Doğru terminoloji
- [ ] Tutarlı format
- [ ] Hatasız yazım
- [ ] Doğru noktalama

### 2.3 Akıcılık
- [ ] Mantıksal paragraf sırası
- [ ] Geçiş cümleleri
- [ ] Bölümler arası bağlantı
- [ ] Sonuç-giriş tutarlılığı

---

## 3. VERİ KALİTESİ

### 3.1 Güncellik Standartları
| Veri Tipi | Maksimum Yaş | Uyarı Yaşı |
|-----------|--------------|------------|
| Pazar verileri | 2 yıl | 1 yıl |
| Finansal veriler | 1 yıl | 6 ay |
| Makro göstergeler | 1 yıl | 6 ay |
| Döviz kurları | 1 gün | - |
| Demografik | 3 yıl | 2 yıl |

### 3.2 Doğruluk Standartları
- Resmi kaynak: %100 güvenilir
- Sektör raporu: %90 güvenilir
- Haber kaynağı: %80 güvenilir (doğrulama gerekir)
- Diğer: %70 güvenilir (çapraz doğrulama zorunlu)

### 3.3 Temsiliyet
- Tek kaynaklı veri: ⚠️ Uyarı
- İki kaynaklı veri: ✅ Kabul
- Üç+ kaynaklı veri: ✅ İdeal

---

## 4. GÖRSEL KALİTE

### 4.1 Tablo Standartları
```markdown
✅ DOĞRU TABLO:
| Gösterge | 2023 | 2024 | Değişim |
|----------|------|------|---------|
| Gelir (mn TL) | 150 | 180 | +20% |
| Kar (mn TL) | 15 | 22 | +47% |

❌ YANLIŞ TABLO:
| x | y | z |
|---|---|---|
| 150 | 180 | ? |
```

### 4.2 Tablo Gereksinimleri
- Açıklayıcı başlıklar
- Tutarlı birimler
- Doğru hizalama
- Kaynak belirtilmiş
- 10'dan fazla satır için özet

### 4.3 Grafik Standartları
- Başlık zorunlu
- Eksen etiketleri
- Açıklama (legend)
- Kaynak notu
- Yüksek çözünürlük

---

## 5. TUTARLILIK

### 5.1 Terminoloji Tutarlılığı
```
Aynı kavram için tek terim kullan:
✅ "Pazar büyüklüğü" (her yerde)
❌ "Pazar büyüklüğü", "Market size", "Pazar hacmi" (karışık)
```

### 5.2 Format Tutarlılığı
```
Sayı formatı:
✅ 1.500.000 TL, 2.300.000 TL, 3.100.000 TL
❌ 1.5 milyon TL, 2,300,000 TL, 3.1M TL

Tarih formatı:
✅ 17.01.2024, 18.01.2024, 19.01.2024
❌ 17/01/2024, 18 Ocak 2024, 2024-01-19
```

### 5.3 Üslup Tutarlılığı
- Aynı zaman kipi
- Aynı şahıs (biz/şirket)
- Aynı formalite seviyesi

---

## 6. BÜTÜNLÜK

### 6.1 Zorunlu Bileşenler
Her raporda bulunması gereken:
- [ ] Yönetici özeti
- [ ] Giriş/amaç
- [ ] Metodoloji açıklaması
- [ ] Ana bölümler
- [ ] Sonuç ve öneriler
- [ ] Kaynakça

### 6.2 Eksiklik Kontrolü
```python
ZORUNLU_BILESENLER = [
    "yonetici_ozeti",
    "giris",
    "pazar_analizi",
    "finansal",
    "sonuc",
    "kaynakca"
]

for bileşen in ZORUNLU_BILESENLER:
    assert bileşen in rapor, f"Eksik: {bileşen}"
```

---

## 7. KALİTE PUANI HESAPLAMA

### 7.1 Ağırlıklı Puanlama
```
Toplam Puan = (
    İçerik Kalitesi × 0.35 +
    Yazı Kalitesi × 0.20 +
    Veri Kalitesi × 0.25 +
    Görsel Kalite × 0.10 +
    Tutarlılık × 0.10
)
```

### 7.2 Puan Aralıkları
| Puan | Değerlendirme | Aksiyon |
|------|---------------|---------|
| 90-100 | Mükemmel | Onay |
| 80-89 | İyi | Onay |
| 70-79 | Kabul edilebilir | Onay (uyarı) |
| 60-69 | Geliştirmeli | Revizyon |
| 0-59 | Yetersiz | Yeniden üret |

### 7.3 Minimum Kabul
- Toplam puan: **70+**
- Kritik bölüm puanları: **65+**
- Hiçbir bölüm: **50 altı olamaz**

---

## 8. KALİTE GÜVENCESİ

### 8.1 Üretim Öncesi
- [ ] Tüm kurallar okundu
- [ ] Kaynaklar toplandı
- [ ] Plan oluşturuldu

### 8.2 Üretim Sırasında
- [ ] Minimum standartlar kontrol
- [ ] Referanslar ekleniyor
- [ ] Tutarlılık sağlanıyor

### 8.3 Üretim Sonrası
- [ ] Otomatik doğrulama geçti
- [ ] Kalite puanı hesaplandı
- [ ] Eksikler giderildi

---

## KALİTE TAAHHÜDÜ

Bu rapor:
- ✅ Gerçek araştırmaya dayanır
- ✅ Doğrulanmış kaynaklar kullanır
- ✅ Profesyonel standartlara uyar
- ✅ Güncel verilere dayanır
- ✅ Tutarlı ve bütünsel yapıdadır

**Kalite standardını karşılamayan içerik TESLİM EDİLMEZ.**
