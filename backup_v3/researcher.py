"""Web ve Akademik Kaynak Araştırma Modülü."""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

try:
    import anthropic
except ImportError:
    anthropic = None

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class ResearchResult:
    """Araştırma sonucu."""
    topic: str
    web_findings: List[Dict[str, str]] = field(default_factory=list)
    academic_sources: List[Dict[str, str]] = field(default_factory=list)
    market_data: List[Dict[str, str]] = field(default_factory=list)
    statistics: List[Dict[str, str]] = field(default_factory=list)
    summary: str = ""


class WebResearcher:
    """Web ve akademik kaynak araştırıcı."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.client = None

        if anthropic is not None and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def research(
        self,
        topic: str,
        context: str = "",
        language: str = "tr",
        include_academic: bool = True,
        include_market_data: bool = True,
        show_progress: bool = True
    ) -> ResearchResult:
        """Konu hakkında kapsamlı araştırma yap."""

        if not self.client:
            console.print("[yellow]Uyarı: API anahtarı yok, araştırma yapılamıyor[/yellow]")
            return ResearchResult(topic=topic)

        result = ResearchResult(topic=topic)

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                # Web araştırması
                task = progress.add_task("Web araştırması yapılıyor...", total=None)
                result.web_findings = self._research_web(topic, context, language)
                progress.update(task, description="Web araştırması tamamlandı")

                # Pazar verileri
                if include_market_data:
                    progress.update(task, description="Pazar verileri araştırılıyor...")
                    result.market_data = self._research_market(topic, language)

                # Akademik kaynaklar
                if include_academic:
                    progress.update(task, description="Akademik kaynaklar araştırılıyor...")
                    result.academic_sources = self._research_academic(topic, language)

                # İstatistikler
                progress.update(task, description="İstatistikler derleniyor...")
                result.statistics = self._research_statistics(topic, language)

                # Özet
                progress.update(task, description="Araştırma özetleniyor...")
                result.summary = self._create_summary(result, language)
        else:
            result.web_findings = self._research_web(topic, context, language)
            if include_market_data:
                result.market_data = self._research_market(topic, language)
            if include_academic:
                result.academic_sources = self._research_academic(topic, language)
            result.statistics = self._research_statistics(topic, language)
            result.summary = self._create_summary(result, language)

        return result

    def _research_web(self, topic: str, context: str, language: str) -> List[Dict[str, str]]:
        """Web araştırması yap - Uzman seviyesi içerik."""
        prompt = f"""Sen, 20 yıllık deneyime sahip bir sektör analisti ve stratejik danışmansın. "{topic}" konusunda derinlemesine bir sektör analizi hazırlayacaksın.

BAĞLAM: {context if context else 'Kapsamlı iş planı ve stratejik analiz'}

ÖNEMLİ: Bu rapor, yatırımcılara ve üst düzey karar vericilere sunulacak. Dolayısıyla:
- Sadece herkesin bildiği genel bilgiler DEĞİL
- Sektör içinden birinin bileceği "insider" bilgiler
- Rakiplerin göremediği fırsatlar ve gizli tehditler
- Sayısal veriler ve spesifik örnekler

DETAYLI ANALİZ BAŞLIKLARI:

## 1. Sektör Derinlemesine Analiz
- Sektörün Türkiye'deki gelişim hikayesi (önemli dönüm noktaları)
- Mevcut pazar büyüklüğü (TL ve USD, kaynaklı)
- Yıllık büyüme oranları ve 5 yıllık projeksiyon
- Sektörü etkileyen makroekonomik faktörler

## 2. Rekabet Haritası ve Kritik Oyuncular
- Türkiye'deki ilk 10 oyuncu ve tahmini pazar payları
- Her oyuncunun güçlü/zayıf yönleri
- Uluslararası oyuncuların Türkiye stratejileri
- Pazar konsolidasyonu ve M&A trendleri

## 3. Teknoloji ve İnovasyon Haritası
- Sektörü dönüştürecek 5 teknoloji trendi
- Yapay zeka ve otomasyon etkileri
- Dijital dönüşüm başarı/başarısızlık örnekleri
- Patent ve AR-GE yatırım trendleri

## 4. Düzenleyici Ortam ve Politika Değişiklikleri
- Güncel ve yaklaşan mevzuat değişiklikleri
- Sektöre özgü teşvik ve destekler (KOSGEB, TÜBİTAK, vb.)
- Uluslararası ticaret ve gümrük düzenlemeleri
- Vergi avantajları ve yatırım teşvikleri

## 5. Müşteri Davranışları ve Trendler
- Değişen tüketici beklentileri
- Demografik segmentasyon analizi
- Dijital satın alma davranışları
- Müşteri sadakati ve retention oranları

## 6. Fırsat Haritası (Herkesin Göremediği)
- Henüz doyurulmamış pazar segmentleri
- Coğrafi genişleme fırsatları
- Yan sektör sinerjileri
- "Blue ocean" stratejisi fırsatları

## 7. Risk ve Tehdit Analizi
- Kısa vadeli (0-12 ay) kritik riskler
- Orta vadeli (1-3 yıl) stratejik tehditler
- Sektöre özgü "black swan" senaryoları
- Rekabetçi tehditler ve koruma stratejileri

Her bölümde somut veriler, spesifik şirket/marka örnekleri ve kaynak belirt.
Türkiye pazarına ve yerel dinamiklere odaklan.
Yanıtını Türkçe ver."""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return [{"type": "web", "content": response.content[0].text}]
        except Exception as e:
            return [{"type": "error", "content": str(e)}]

    def _research_market(self, topic: str, language: str) -> List[Dict[str, str]]:
        """Pazar araştırması yap - Yatırımcı seviyesi detay."""
        prompt = f"""Sen, uluslararası bir yatırım bankasında çalışan kıdemli sektör analistisin. "{topic}" için Wall Street kalitesinde bir pazar analizi hazırlayacaksın.

AMAÇ: Bu analiz, yatırım kararları için kullanılacak. Dolayısıyla:
- Doğrulanabilir rakamlar ve kaynaklar kullan
- Trend analizlerinde veri odaklı ol
- Rekabet analizinde spesifik ol
- Fiyatlandırma dinamiklerini derinlemesine incele

## 1. PAZAR BÜYÜKLÜĞÜ ANALİZİ

### 1.1 Türkiye Pazarı
| Metrik | 2023 | 2024 | 2025P |
|--------|------|------|-------|
| Pazar Büyüklüğü (Milyar TL) | ? | ? | ? |
| Pazar Büyüklüğü (Milyar USD) | ? | ? | ? |
| YoY Büyüme (%) | ? | ? | ? |
| İşlem Hacmi | ? | ? | ? |

### 1.2 Alt Segment Analizi
Her alt segment için pazar payı ve büyüme potansiyeli

### 1.3 Coğrafi Dağılım
İl bazında veya bölge bazında pazar dağılımı

## 2. REKABETÇİ KONUMLANDIRMA

### 2.1 Pazar Payı Tablosu
| Şirket | Pazar Payı (%) | Güçlü Yönleri | Zayıf Yönleri |
|--------|----------------|---------------|---------------|
(İlk 10 oyuncu)

### 2.2 Rekabet Yoğunluğu Analizi
- Herfindahl-Hirschman Index (HHI) tahmini
- Giriş bariyerleri analizi
- İkame ürün/hizmet tehdidi

## 3. FİYATLANDIRMA DİNAMİKLERİ

### 3.1 Fiyat Bantları
| Segment | Min | Ortalama | Max | Trend |
|---------|-----|----------|-----|-------|

### 3.2 Marjin Analizi
- Sektör ortalama brüt marjı
- Operasyonel marjlar
- Net kar marjı benchmarkları

### 3.3 Fiyat Elastikiyeti
Talebin fiyat duyarlılığı ve segmentlere göre farklılıklar

## 4. TÜKETİCİ DAVRANIŞI ANALİZİ

### 4.1 Demografik Profil
| Yaş Grubu | Penetrasyon (%) | Ortalama Harcama |
|-----------|-----------------|------------------|

### 4.2 Satın Alma Davranışları
- Karar verme süreci
- Kanal tercihleri (online/offline)
- Marka sadakati oranları
- Churn/retention metrikleri

## 5. 5 YILLIK PROJEKSIYON (2025-2030)

### 5.1 Senaryo Analizi
| Senaryo | CAGR | 2030 Pazar Büyüklüğü | Olasılık |
|---------|------|---------------------|----------|
| Baz Senaryo | ? | ? | ? |
| İyimser | ? | ? | ? |
| Kötümser | ? | ? | ? |

### 5.2 Büyüme Sürücüleri ve Riskler
Her senaryo için kritik varsayımlar

Tüm verilerde mümkün olduğunca güncel kaynak belirt (TÜİK, BDDK, TCMB, BTK, sektör dernekleri, uluslararası araştırma şirketleri vb.).
Yanıtını Türkçe ver."""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return [{"type": "market", "content": response.content[0].text}]
        except Exception as e:
            return [{"type": "error", "content": str(e)}]

    def _research_academic(self, topic: str, language: str) -> List[Dict[str, str]]:
        """Akademik kaynak araştırması yap - Doktora seviyesi literatür taraması."""
        prompt = f"""Sen, uluslararası alanda tanınmış bir akademisyensin. "{topic}" konusunda doktora tezi kalitesinde bir sistematik literatür taraması hazırlayacaksın.

AMAÇ: Bu literatür taraması, hem akademik hem de uygulamalı değer taşımalı. İş dünyası karar vericilerin akademik temelli kararlar almasını sağlamalı.

## 1. TEORİK ÇERÇEVE VE KAVRAMSAL TEMELİNTERDİSİPLİNER YAKLAŞIM

### 1.1 Temel Teoriler
- Ana teorik yaklaşımlar ve kurucuları
- Teori evrimi ve güncel yorumlar
- Türkiye bağlamına uyarlanmış teorik çerçeveler

### 1.2 Kavramsal Model
Bu alandaki başarıyı açıklayan değişkenler arası ilişkiler

## 2. SİSTEMATİK LİTERATÜR TARAMASI

### 2.1 Uluslararası Seminal Çalışmalar (Temel Taşlar)
| Yazar(lar) | Yıl | Çalışma | Ana Bulgu | Atıf Sayısı |
|------------|-----|---------|-----------|-------------|
(Alanın en önemli 10 uluslararası çalışması)

APA Format Örneği:
- Porter, M. E. (1979). How competitive forces shape strategy. Harvard Business Review, 57(2), 137-145.

### 2.2 Türkiye Odaklı Akademik Çalışmalar
| Yazar(lar) | Yıl | Çalışma | Yayın | Ana Bulgu |
|------------|-----|---------|-------|-----------|
(Türkiye'deki en önemli 10 akademik çalışma)

Özellikle şu üniversitelerin çalışmalarına odaklan:
- Boğaziçi, ODTÜ, Koç, Sabancı, İTÜ, Bilkent
- İlgili TÜBİTAK projeleri
- Sektör dernekleri akademik raporları

### 2.3 Metodolojik Yaklaşımlar
| Metodoloji | Kullanım Alanı | Avantaj | Dezavantaj |
|------------|----------------|---------|------------|

## 3. KRİTİK ANALİZ VE SENTEZ

### 3.1 Literatürdeki Fikir Birliği
Araştırmacıların üzerinde uzlaştığı noktalar

### 3.2 Tartışmalı Konular
Farklı görüşlerin olduğu alanlar ve argümanlar

### 3.3 Araştırma Boşlukları
Henüz yeterince çalışılmamış konular (Türkiye bağlamında)

## 4. PRATİK İMPLİKASYONLAR

### 4.1 Akademiden İş Dünyasına
Akademik bulguların pratik uygulamaları

### 4.2 Kanıta Dayalı Öneriler
Araştırma bulgularından çıkarılan somut stratejik öneriler

### 4.3 Başarı Faktörleri
Akademik çalışmaların ortaya koyduğu kritik başarı faktörleri

## 5. GELECEK ARAŞTIRMA VE TREND ANALİZİ

### 5.1 Yükselen Araştırma Alanları
Önümüzdeki 5 yılda öne çıkacak konular

### 5.2 Metodolojik Yenilikler
Araştırma yöntemlerindeki gelişmeler (AI, big data, vb.)

Tüm kaynakları APA 7 formatında ver. Mümkün olduğunca gerçek ve doğrulanabilir kaynaklar kullan.
Yanıtını Türkçe ver."""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return [{"type": "academic", "content": response.content[0].text}]
        except Exception as e:
            return [{"type": "error", "content": str(e)}]

    def _research_statistics(self, topic: str, language: str) -> List[Dict[str, str]]:
        """İstatistik ve veri araştırması yap - Veri bilimi perspektifi."""
        prompt = f"""Sen, TÜİK ve McKinsey Global Institute'da çalışmış kıdemli bir veri analistisin. "{topic}" için kapsamlı bir veri ve istatistik raporu hazırlayacaksın.

AMAÇ: Bu veriler, iş planında kullanılacak ve yatırımcılara sunulacak. Dolayısıyla:
- Güvenilir kaynaklardan doğrulanabilir veriler
- Zaman serisi analizleri
- Benchmark karşılaştırmaları
- Görselleştirmeye uygun tablo formatları

## 1. TÜRKİYE MAKRO GÖSTERGELERİ

### 1.1 Sektörel Ekonomik Göstergeler
| Gösterge | 2022 | 2023 | 2024 | Kaynak |
|----------|------|------|------|--------|
| Sektör GSYH Katkısı (%) | | | | |
| İstihdam (bin kişi) | | | | |
| Yabancı Yatırım (Milyon USD) | | | | |
| İhracat (Milyon USD) | | | | |
| İthalat (Milyon USD) | | | | |

### 1.2 Büyüme ve Verimlilik
| Metrik | Değer | Trend | Kaynak |
|--------|-------|-------|--------|
| Sektör Büyüme Oranı | | | |
| İşgücü Verimliliği | | | |
| Kapasite Kullanımı | | | |

## 2. PAZAR VERİLERİ DETAYLI ANALİZ

### 2.1 Pazar Penetrasyonu
| Segment | Penetrasyon (%) | Potansiyel | Boşluk |
|---------|-----------------|------------|--------|

### 2.2 Müşteri/Kullanıcı Metrikleri
| Metrik | Değer | YoY Değişim |
|--------|-------|-------------|
| Toplam Kullanıcı Sayısı | | |
| Aktif Kullanıcı Oranı | | |
| Ortalama Kullanım Sıklığı | | |
| Müşteri Edinme Maliyeti (CAC) | | |
| Müşteri Yaşam Boyu Değeri (CLV) | | |
| Churn Rate | | |

### 2.3 Finansal Performans Benchmarkları
| KPI | Sektör Ortalaması | Lider Şirketler | Alt %25 |
|-----|-------------------|-----------------|---------|
| Brüt Marjı | | | |
| EBITDA Marjı | | | |
| ROE | | | |
| ROA | | | |

## 3. DEMOGRAFİK VE SEGMENTASYON VERİLERİ

### 3.1 Yaş Dağılımı
| Yaş Grubu | Kullanıcı Oranı (%) | Harcama Payı (%) | Büyüme Trendi |
|-----------|---------------------|------------------|---------------|
| 18-24 | | | |
| 25-34 | | | |
| 35-44 | | | |
| 45-54 | | | |
| 55+ | | | |

### 3.2 Coğrafi Dağılım
| Bölge/İl | Penetrasyon | Pazar Payı | Potansiyel |
|----------|-------------|------------|------------|
| İstanbul | | | |
| Ankara | | | |
| İzmir | | | |
| Anadolu | | | |

### 3.3 Gelir Segmentasyonu
| Gelir Grubu | Oranı (%) | Ortalama Harcama |
|-------------|-----------|------------------|

## 4. GLOBAL KARŞILAŞTIRMA (BENCHMARK)

### 4.1 Ülke Karşılaştırması
| Ülke | Pazar Büyüklüğü | Penetrasyon | Büyüme | Kişi Başı Harcama |
|------|-----------------|-------------|--------|-------------------|
| Türkiye | | | | |
| ABD | | | | |
| İngiltere | | | | |
| Almanya | | | | |
| Polonya | | | | |
| Brezilya | | | | |

### 4.2 Türkiye'nin Konumu
- Global sıralama
- Bölgesel liderlik potansiyeli
- Benchmark ulaşılabilirlik analizi

## 5. ZAMAN SERİSİ ANALİZİ (5 YILLIK TREND)

### 5.1 Yıllık Trend Tablosu
| Yıl | Pazar Büyüklüğü | Kullanıcı Sayısı | Büyüme (%) |
|-----|-----------------|------------------|------------|
| 2020 | | | |
| 2021 | | | |
| 2022 | | | |
| 2023 | | | |
| 2024 | | | |

### 5.2 Mevsimsellik ve Döngüsellik
Sektöre özgü mevsimsel paternler

## 6. KRİTİK ORANLAR VE İNDEKSLER

| Oran/İndeks | Değer | Yorumu |
|-------------|-------|--------|
| Pazar Konsantrasyon (CR4) | | |
| Büyüme Momentum İndeksi | | |
| Dijitalleşme Skoru | | |
| Müşteri Memnuniyeti Endeksi | | |

VERİ KAYNAKLARI:
- TÜİK (Türkiye İstatistik Kurumu)
- TCMB (Türkiye Cumhuriyet Merkez Bankası)
- İlgili düzenleyici kurumlar (BDDK, BTK, EPDK vb.)
- Sektör dernekleri ve federasyonlar
- Uluslararası kuruluşlar (Dünya Bankası, IMF, OECD)
- Araştırma şirketleri (Euromonitor, Statista, vb.)

Tüm verilerde kaynak belirtilmeli.
Yanıtını Türkçe ver."""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return [{"type": "statistics", "content": response.content[0].text}]
        except Exception as e:
            return [{"type": "error", "content": str(e)}]

    def _create_summary(self, result: ResearchResult, language: str) -> str:
        """Araştırma özetini oluştur."""
        all_content = []

        for item in result.web_findings:
            if item.get('content'):
                all_content.append(f"WEB ARAŞTIRMASI:\n{item['content']}")

        for item in result.market_data:
            if item.get('content'):
                all_content.append(f"PAZAR VERİLERİ:\n{item['content']}")

        for item in result.academic_sources:
            if item.get('content'):
                all_content.append(f"AKADEMİK KAYNAKLAR:\n{item['content']}")

        for item in result.statistics:
            if item.get('content'):
                all_content.append(f"İSTATİSTİKLER:\n{item['content']}")

        return "\n\n---\n\n".join(all_content)

    def to_dict(self, result: ResearchResult) -> Dict[str, Any]:
        """ResearchResult'u sözlüğe çevir."""
        return {
            "topic": result.topic,
            "web_findings": result.web_findings,
            "market_data": result.market_data,
            "academic_sources": result.academic_sources,
            "statistics": result.statistics,
            "summary": result.summary
        }
