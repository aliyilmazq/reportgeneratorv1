# ARAŞTIRMA KURALLARI

Web araştırması ve veri toplama sürecinde uyulması gereken kurallar.

---

## 1. ARAŞTIRMA SÜRECİ

### 1.1 Zorunlu Adımlar
```
1. Konu belirleme
2. Arama sorgularını oluşturma
3. Web araması yapma (DuckDuckGo)
4. Sonuçları filtreleme
5. İçerikleri okuma
6. Bilgileri çıkarma
7. Kaynakları doğrulama
```

### 1.2 Minimum Araştırma Gereksinimleri
- Her konu için: **minimum 5 farklı kaynak**
- Her bölüm için: **minimum 3 ilgili kaynak**
- Toplam rapor için: **minimum 15 benzersiz kaynak**

---

## 2. KAYNAK SEÇİMİ

### 2.1 Güvenilir Kaynaklar (Öncelikli)
| Domain | Güvenilirlik | Açıklama |
|--------|--------------|----------|
| *.gov.tr | %100 | Resmi devlet kaynakları |
| tuik.gov.tr | %100 | TÜİK resmi verileri |
| tcmb.gov.tr | %100 | Merkez Bankası verileri |
| bddk.org.tr | %95 | Bankacılık düzenleme |
| spk.gov.tr | %95 | Sermaye piyasası |
| worldbank.org | %95 | Dünya Bankası |
| imf.org | %95 | IMF verileri |
| oecd.org | %95 | OECD istatistikleri |

### 2.2 Kabul Edilebilir Kaynaklar
| Domain | Güvenilirlik | Açıklama |
|--------|--------------|----------|
| reuters.com | %90 | Haber ajansı |
| bloomberg.com | %90 | Finans haberleri |
| borsaistanbul.com | %90 | Borsa verileri |
| aa.com.tr | %85 | Anadolu Ajansı |
| *.edu.tr | %85 | Üniversiteler |

### 2.3 Dikkatli Kullanılacak Kaynaklar
- Haber siteleri: Doğrulama gerektirir
- Blog yazıları: Sadece referans olarak
- Forum/sosyal medya: KULLANILMAYACAK

### 2.4 YASAKLI Kaynaklar
- Wikipedia (doğrudan kaynak olarak)
- Anonim bloglar
- Sosyal medya paylaşımları
- Doğrulanamayan siteler

---

## 3. ARAMA STRATEJİSİ

### 3.1 Sorgu Formatları
```
# Temel sorgu
"{konu} {yıl}"

# İstatistik sorgusu
"{konu} istatistik {yıl} TÜİK"

# Pazar sorgusu
"{sektör} pazar büyüklüğü Türkiye {yıl}"

# Trend sorgusu
"{konu} büyüme oranı {yıl}"

# Resmi kaynak sorgusu
"{konu} site:gov.tr"
```

### 3.2 Sorgu Çeşitliliği
Her konu için en az 3 farklı sorgu türü kullan:
1. Genel bilgi sorgusu
2. İstatistik sorgusu
3. Trend/analiz sorgusu

---

## 4. VERİ ÇIKARMA

### 4.1 Çıkarılacak Bilgiler
- Sayısal veriler (rakamlar, yüzdeler)
- Tarihler ve dönemler
- Kaynak kurum/kuruluş
- Trend bilgileri
- Karşılaştırmalı veriler

### 4.2 Veri Formatı
```json
{
  "değer": "1.5",
  "birim": "milyar TL",
  "dönem": "2024",
  "kaynak": "TÜİK",
  "url": "https://...",
  "erişim_tarihi": "2024-01-17"
}
```

---

## 5. DOĞRULAMA

### 5.1 Çapraz Doğrulama
- Her kritik veri için **en az 2 kaynak** bul
- Kaynaklar arası tutarsızlık varsa, resmi kaynağı tercih et
- Tutarsızlıkları raporda belirt

### 5.2 Güncellik Doğrulama
- Verinin yayınlanma tarihini kontrol et
- 1 yıldan eski veriler için "Kaynak: {yıl} verileri" notu ekle
- Mümkünse daha güncel veri ara

---

## 6. RATE LIMITING

### 6.1 API Kullanımı
- Ardışık istekler arasında: **minimum 0.5 saniye**
- Aynı domain'e: **minimum 2 saniye**
- Toplam istek: **dakikada maksimum 30**

### 6.2 Hata Durumunda
- 3 deneme yap
- Her denemede bekleme süresini 2x artır
- 3 başarısız denemeden sonra alternatif kaynağa geç

---

## 7. KAYNAK SAKLAMA

### 7.1 Her Kaynak İçin Saklanacaklar
- URL (tam adres)
- Başlık
- Snippet/özet
- Erişim tarihi
- Güvenilirlik puanı
- Çıkarılan veriler

### 7.2 Kaynakça Formatı
```
[1] Başlık. (Erişim: Tarih). Kaynak. URL
```

---

## ARAŞTIRMA YAPILMADAN ASLA:

- ❌ İstatistik kullanılamaz
- ❌ Pazar verisi yazılamaz
- ❌ Trend analizi yapılamaz
- ❌ Rakip bilgisi verilemez
- ❌ Finansal projeksiyon oluşturulamaz

**Araştırma, rapor üretiminin TEMELİDİR.**
