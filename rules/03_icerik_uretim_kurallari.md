# İÇERİK ÜRETİM KURALLARI

Rapor içeriği oluştururken uyulması gereken kurallar.

---

## 1. İÇERİK YAPISI

### 1.1 Paragraf Kuralları
- Her paragraf: **minimum 100 kelime**
- Her paragraf: **tek bir ana fikir**
- Paragraflar arası: **mantıksal geçiş cümleleri**
- Madde işaretleri: **sadece destekleyici** (ana içerik değil)

### 1.2 Bölüm Yapısı
```
## Bölüm Başlığı

[Giriş paragrafı - konuyu tanıt, 100-150 kelime]

[Gelişme paragrafı 1 - ana nokta 1, 150-200 kelime]

[Gelişme paragrafı 2 - ana nokta 2, 150-200 kelime]

[Gelişme paragrafı 3 - destekleyici bilgi, 100-150 kelime]

[Sonuç paragrafı - özet ve çıkarım, 100-150 kelime]
```

---

## 2. DİL VE ÜSLUP

### 2.1 Genel Kurallar
- Resmi ve profesyonel dil
- Türkçe dil bilgisi kurallarına tam uyum
- Kısa ve net cümleler (ortalama 15-20 kelime)
- Aktif cümle yapısı tercih edilmeli

### 2.2 Kaçınılacaklar
- ❌ "Oldukça", "çok", "son derece" gibi belirsiz ifadeler
- ❌ "Bilindiği üzere", "Malumunuz" gibi klişeler
- ❌ Argo veya günlük konuşma dili
- ❌ Gereksiz tekrarlar
- ❌ Uzun ve karmaşık cümleler

### 2.3 Tercih Edilecekler
- ✅ Somut rakamlar: "büyük artış" yerine "%15 artış"
- ✅ Spesifik ifadeler: "yakın zamanda" yerine "2024 Q3'te"
- ✅ Aktif fiiller: "yapılmaktadır" yerine "yapıyoruz"

---

## 3. VERİ SUNUMU

### 3.1 Rakam Formatları
```
Para birimi: 1.5 milyar TL, 500 milyon USD
Yüzde: %15.5 (% işareti önde)
Büyük sayılar: 1.250.000 (nokta ile ayır)
Ondalık: 3,75 (virgül ile)
```

### 3.2 Tablo Kullanımı
- 3+ veri noktası varsa tablo kullan
- Tabloda başlık satırı zorunlu
- Sayısal veriler sağa hizalı
- Birim bilgisi başlıkta belirt

```markdown
| Gösterge | 2023 | 2024 | Değişim |
|----------|------|------|---------|
| GSYİH (milyar $) | 1.100 | 1.150 | +4.5% |
```

### 3.3 Referans Kullanımı
- Her istatistik sonrası: `[1]`, `[2]`
- Her tablo altında: "Kaynak: ..."
- Her iddia için: kaynak belirt

---

## 4. BÖLÜM BAZLI KURALLAR

### 4.1 Yönetici Özeti
- Maksimum 2 sayfa
- Anahtar bulgular vurgulu
- Rakamlar ve sonuçlar öne çıkarılmalı
- Detaylara girmeden özet sun

### 4.2 Pazar Analizi
- Pazar büyüklüğü (TL ve USD)
- Büyüme oranları (yıllık, CAGR)
- Pazar segmentleri
- En az 5 güncel kaynak kullan

### 4.3 Rekabet Analizi
- En az 3-5 rakip analiz et
- Karşılaştırmalı tablo kullan
- SWOT analizi dahil et
- Pazar payı verileri sun

### 4.4 Finansal Projeksiyonlar
- 3-5 yıllık projeksiyon
- Varsayımları açıkça belirt
- Senaryo analizi (iyimser/kötümser)
- Başabaş analizi

### 4.5 Risk Analizi
- Risk kategorileri (operasyonel, finansal, pazar)
- Olasılık ve etki değerlendirmesi
- Risk azaltma stratejileri
- Acil durum planları

---

## 5. YASAKLAR

### 5.1 ASLA Yapılmayacaklar
- ❌ Kaynak göstermeden istatistik kullanmak
- ❌ "Araştırmalar gösteriyor ki..." gibi belirsiz atıflar
- ❌ Kopyala-yapıştır içerik
- ❌ Tek cümlelik paragraflar
- ❌ Sadece madde işaretlerinden oluşan bölümler
- ❌ Boş veya anlamsız dolgu cümleleri

### 5.2 Şablon Kullanımı YASAK
- ❌ Önceden hazırlanmış şablon metinler
- ❌ "Lorem ipsum" benzeri dolgu
- ❌ Genel geçer ifadeler
- ❌ Kopyala-yapıştır bölümler

---

## 6. KALİTE KONTROL

### 6.1 Her Bölüm Sonrası Kontrol
- [ ] Minimum kelime sayısı sağlandı mı?
- [ ] En az 3 paragraf var mı?
- [ ] Kaynak referansları eklendi mi?
- [ ] Rakamlar doğru formatlandı mı?
- [ ] Mantıksal akış var mı?

### 6.2 Otomatik Kontroller
```python
assert word_count >= 500, "Yetersiz kelime sayısı"
assert paragraph_count >= 3, "Yetersiz paragraf"
assert len(citations) >= 2, "Yetersiz kaynak"
```

---

## İÇERİK ÜRETİM SIRASI

```
1. Araştırma verilerini incele
2. Anahtar noktaları belirle
3. Bölüm taslağı oluştur
4. Giriş paragrafını yaz
5. Gelişme paragraflarını yaz
6. Verileri ve tabloları yerleştir
7. Referansları ekle
8. Sonuç paragrafını yaz
9. Kalite kontrolü yap
10. Gerekirse revize et
```

**Her adım ZORUNLUDUR ve atlanamaz.**
