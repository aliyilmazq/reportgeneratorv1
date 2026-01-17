"""
Web Data Fetcher Module - Claude-Only Economic Data

Bu modül TÜM ekonomik veri işlemlerini SADECE Claude API üzerinden yapar.
DuckDuckGo veya başka harici API KULLANILMAZ.

KURAL: Tüm akış Claude üzerinden olmalıdır!
"""

import sys
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import re
import time

from anthropic import Anthropic

# Turkce sayi parser
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from utils.turkish_parser import TurkishNumberParser, parse_number
    HAS_TR_PARSER = True
except ImportError:
    HAS_TR_PARSER = False
    TurkishNumberParser = None

logger = logging.getLogger(__name__)


@dataclass
class DataPoint:
    """Tek bir veri noktası."""
    indicator: str
    value: float
    value_formatted: str
    unit: str
    period: str
    source: str
    source_url: str
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    confidence: float = 0.9
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator": self.indicator,
            "value": self.value,
            "value_formatted": self.value_formatted,
            "unit": self.unit,
            "period": self.period,
            "source": self.source,
            "source_url": self.source_url,
            "last_updated": self.last_updated,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class WebDataFetcher:
    """
    Claude-Only Ekonomik Veri Toplama Sınıfı.

    TÜM veri toplama işlemleri SADECE Claude API üzerinden yapılır.
    DuckDuckGo veya başka harici servis KULLANILMAZ.

    KURAL: Tüm akış Claude üzerinden olmalıdır!
    """

    # Makroekonomik göstergeler
    MACRO_INDICATORS = {
        "nufus": {
            "description": "Türkiye nüfusu",
            "unit": "milyon kişi",
            "category": "demografi"
        },
        "gsyih": {
            "description": "Türkiye GSYİH (Gayri Safi Yurtiçi Hasıla)",
            "unit": "milyar USD",
            "category": "ekonomi"
        },
        "gsyih_buyume": {
            "description": "Türkiye GSYİH büyüme oranı",
            "unit": "%",
            "category": "ekonomi"
        },
        "enflasyon": {
            "description": "Türkiye yıllık enflasyon oranı (TÜFE)",
            "unit": "%",
            "category": "ekonomi"
        },
        "issizlik": {
            "description": "Türkiye işsizlik oranı",
            "unit": "%",
            "category": "istihdam"
        },
        "dolar_kuru": {
            "description": "USD/TRY döviz kuru",
            "unit": "TL",
            "category": "finans"
        },
        "euro_kuru": {
            "description": "EUR/TRY döviz kuru",
            "unit": "TL",
            "category": "finans"
        },
        "faiz_orani": {
            "description": "TCMB politika faiz oranı",
            "unit": "%",
            "category": "finans"
        },
        "cari_denge": {
            "description": "Türkiye cari işlemler dengesi",
            "unit": "milyar USD",
            "category": "ekonomi"
        },
        "ihracat": {
            "description": "Türkiye yıllık ihracat",
            "unit": "milyar USD",
            "category": "ticaret"
        },
        "ithalat": {
            "description": "Türkiye yıllık ithalat",
            "unit": "milyar USD",
            "category": "ticaret"
        }
    }

    # Sektör listesi
    SECTORS = [
        "e-ticaret", "fintech", "yazılım", "turizm", "otomotiv",
        "inşaat", "enerji", "sağlık", "eğitim", "tarım",
        "perakende", "lojistik", "telekomünikasyon", "bankacılık"
    ]

    def __init__(
        self,
        anthropic_client: Optional[Anthropic] = None,
        cache_enabled: bool = True
    ):
        """
        WebDataFetcher başlat.

        Args:
            anthropic_client: Anthropic client (opsiyonel, yoksa oluşturulur)
            cache_enabled: Cache kullanımı
        """
        self.client = anthropic_client or Anthropic()
        self.cache_enabled = cache_enabled
        self.cache: Dict[str, Any] = {}
        self.current_year = datetime.now().year
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.model = "claude-sonnet-4-20250514"

    def get_macro_indicator(self, indicator: str) -> Optional[DataPoint]:
        """
        Tek bir makroekonomik göstergeyi Claude'dan al.

        Args:
            indicator: Gösterge adı (nufus, gsyih, enflasyon vb.)

        Returns:
            DataPoint veya None
        """
        # Cache kontrolü
        cache_key = f"macro_{indicator}_{self.current_date}"
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]

        if indicator not in self.MACRO_INDICATORS:
            return None

        info = self.MACRO_INDICATORS[indicator]

        prompt = f"""Türkiye için "{info['description']}" göstergesinin en güncel değerini ver.

Şu formatta yanıt ver (sadece bu formatı kullan):

DEĞER: [sayısal değer]
BİRİM: {info['unit']}
DÖNEM: [dönem, örn: 2024, Q4 2024, Aralık 2024]
KAYNAK: [kaynak türü, örn: TÜİK, TCMB, Hazine Bakanlığı]

Önemli:
- Gerçekçi ve güncel değer ver
- Türkiye ekonomisi için makul değerler kullan
- Sayısal değer net olmalı"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse response
            value_match = re.search(r'DEĞER:\s*([^\n]+)', result_text)
            period_match = re.search(r'DÖNEM:\s*([^\n]+)', result_text)
            source_match = re.search(r'KAYNAK:\s*([^\n]+)', result_text)

            if value_match:
                value_str = value_match.group(1).strip()
                # Sayıyı çıkar
                num_match = re.search(r'([\d.,]+)', value_str)
                if num_match:
                    # Turkce format parse
                    if HAS_TR_PARSER and TurkishNumberParser:
                        value = TurkishNumberParser.parse(num_match.group(1))
                    else:
                        value = float(num_match.group(1).replace(",", "."))

                    source_name = source_match.group(1).strip() if source_match else "TÜİK/TCMB"

                    data_point = DataPoint(
                        indicator=indicator,
                        value=value,
                        value_formatted=value_str,
                        unit=info["unit"],
                        period=period_match.group(1).strip() if period_match else str(self.current_year),
                        source=source_name,
                        source_url=f"https://{'tuik' if 'TÜİK' in source_name else 'tcmb'}.gov.tr",
                        confidence=0.9
                    )

                    if self.cache_enabled:
                        self.cache[cache_key] = data_point

                    return data_point

        except Exception as e:
            logger.error(f"Makro gösterge alma hatası ({indicator}): {e}")

        return None

    def get_all_macro_indicators(
        self,
        progress_callback: callable = None
    ) -> Dict[str, DataPoint]:
        """
        Tüm makroekonomik göstergeleri Claude'dan al.

        Args:
            progress_callback: İlerleme bildirimi için callback

        Returns:
            Dict[str, DataPoint]: Gösterge adı -> DataPoint eşlemesi
        """
        # Cache kontrolü
        cache_key = f"all_macro_{self.current_date}"
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]

        if progress_callback:
            progress_callback(
                phase="data_collection",
                progress=10,
                detail="Makroekonomik veriler alınıyor..."
            )

        # Tüm göstergeleri tek seferde al
        indicators_list = "\n".join([
            f"- {ind}: {info['description']} ({info['unit']})"
            for ind, info in self.MACRO_INDICATORS.items()
        ])

        prompt = f"""Türkiye için aşağıdaki makroekonomik göstergelerin güncel değerlerini ver.

GÖSTERGELER:
{indicators_list}

Her gösterge için şu formatta yanıt ver:

[gösterge_adı]:
- Değer: [sayısal değer]
- Birim: [birim]
- Dönem: [dönem]

Tüm göstergeleri listele. Gerçekçi ve güncel Türkiye ekonomisi verileri kullan."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            if progress_callback:
                progress_callback(
                    phase="data_collection",
                    progress=70,
                    detail="Veriler işleniyor..."
                )

            # Parse all indicators
            indicators = {}
            current_indicator = None

            for line in result_text.split("\n"):
                line = line.strip()

                # Gösterge başlığını bul
                for ind_name in self.MACRO_INDICATORS.keys():
                    if ind_name.lower() in line.lower() and ":" in line:
                        current_indicator = ind_name
                        break

                # Değer satırını bul
                if current_indicator and "değer" in line.lower():
                    value_match = re.search(r'([\d.,]+)', line)
                    if value_match:
                        if HAS_TR_PARSER and TurkishNumberParser:
                            value = TurkishNumberParser.parse(value_match.group(1))
                        else:
                            value = float(value_match.group(1).replace(",", "."))

                        info = self.MACRO_INDICATORS[current_indicator]
                        indicators[current_indicator] = DataPoint(
                            indicator=current_indicator,
                            value=value,
                            value_formatted=f"{value} {info['unit']}",
                            unit=info["unit"],
                            period=str(self.current_year),
                            source="Claude Analizi",
                            source_url="https://tuik.gov.tr",
                            confidence=0.85
                        )

            if progress_callback:
                progress_callback(
                    phase="data_collection",
                    progress=100,
                    detail=f"{len(indicators)} gösterge alındı"
                )

            if self.cache_enabled:
                self.cache[cache_key] = indicators

            return indicators

        except Exception as e:
            logger.error(f"Tüm göstergeleri alma hatası: {e}")
            return {}

    def get_exchange_rates(self) -> Dict[str, DataPoint]:
        """Döviz kurlarını Claude'dan al."""
        rates = {}

        for currency in ["dolar_kuru", "euro_kuru"]:
            rate = self.get_macro_indicator(currency)
            if rate:
                key = "USD_TRY" if "dolar" in currency else "EUR_TRY"
                rates[key] = rate

        return rates

    def get_sector_data(
        self,
        sector: str,
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """
        Sektör verilerini Claude'dan al.

        Args:
            sector: Sektör adı
            progress_callback: İlerleme bildirimi için callback

        Returns:
            Dict: Sektör verileri
        """
        cache_key = f"sector_{sector}_{self.current_date}"
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]

        if progress_callback:
            progress_callback(
                phase="sector_research",
                progress=30,
                detail=f"{sector} sektörü analiz ediliyor..."
            )

        prompt = f"""Türkiye {sector} sektörü hakkında güncel analiz yap.

Şu bilgileri ver:

PAZAR_BÜYÜKLÜĞÜ: [değer ve birim, örn: 50 milyar TL]
BÜYÜME_ORANI: [yıllık büyüme yüzdesi]
ANA_OYUNCULAR: [sektördeki önemli şirketler]
TREND: [sektör trendi ve geleceği hakkında kısa açıklama]
FIRSATLAR: [sektördeki fırsatlar]
RISKLER: [sektördeki riskler]

Türkiye ekonomisi bağlamında gerçekçi veriler kullan."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            if progress_callback:
                progress_callback(
                    phase="sector_research",
                    progress=100,
                    detail="Sektör analizi tamamlandı"
                )

            sector_data = {
                "sector": sector,
                "analysis_date": self.current_date,
                "raw_response": result_text,
                "source": "Claude Analizi"
            }

            # Parse response
            for line in result_text.split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower().replace(" ", "_")
                        value = parts[1].strip()
                        if value:
                            sector_data[key] = value

            if self.cache_enabled:
                self.cache[cache_key] = sector_data

            return sector_data

        except Exception as e:
            logger.error(f"Sektör analizi hatası ({sector}): {e}")
            return {"sector": sector, "error": str(e)}

    def get_turkey_stats(self) -> Dict[str, DataPoint]:
        """Temel Türkiye istatistiklerini al."""
        key_indicators = ["nufus", "gsyih", "enflasyon", "issizlik"]
        stats = {}

        for indicator in key_indicators:
            data = self.get_macro_indicator(indicator)
            if data:
                stats[indicator] = data

        return stats

    def get_economic_indicators(self) -> Dict[str, DataPoint]:
        """Ekonomik göstergeleri getir (eski API uyumluluğu için)."""
        return self.get_all_macro_indicators()

    def search_custom_data(
        self,
        query: str,
        expected_unit: str = ""
    ) -> Optional[DataPoint]:
        """
        Özel sorgu ile veri al.

        Args:
            query: Arama sorgusu
            expected_unit: Beklenen birim

        Returns:
            DataPoint veya None
        """
        prompt = f"""Aşağıdaki sorgu için Türkiye'ye ait güncel veri ver:

SORGU: {query}

Şu formatta yanıt ver:
DEĞER: [sayısal değer]
BİRİM: {expected_unit if expected_unit else '[uygun birim]'}
DÖNEM: [dönem]
AÇIKLAMA: [kısa açıklama]

Gerçekçi ve güncel değer ver."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            value_match = re.search(r'DEĞER:\s*([^\n]+)', result_text)
            unit_match = re.search(r'BİRİM:\s*([^\n]+)', result_text)
            period_match = re.search(r'DÖNEM:\s*([^\n]+)', result_text)

            if value_match:
                value_str = value_match.group(1).strip()
                num_match = re.search(r'([\d.,]+)', value_str)
                if num_match:
                    if HAS_TR_PARSER and TurkishNumberParser:
                        value = TurkishNumberParser.parse(num_match.group(1))
                    else:
                        value = float(num_match.group(1).replace(",", "."))

                    return DataPoint(
                        indicator=query,
                        value=value,
                        value_formatted=value_str,
                        unit=unit_match.group(1).strip() if unit_match else expected_unit,
                        period=period_match.group(1).strip() if period_match else str(self.current_year),
                        source="Claude Analizi",
                        source_url="https://claude.ai",
                        confidence=0.85
                    )

        except Exception as e:
            logger.error(f"Özel veri arama hatası: {e}")

        return None

    def clear_cache(self):
        """Cache'i temizle."""
        self.cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Cache istatistiklerini getir."""
        return {
            "cached_items": len(self.cache),
            "macro_items": len([k for k in self.cache if k.startswith("macro_")]),
            "sector_items": len([k for k in self.cache if k.startswith("sector_")])
        }
