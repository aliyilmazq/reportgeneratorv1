"""
Web Data Fetcher Module - Fetches economic data via web search

Bu modül TÜİK ve TCMB verilerini web araştırması yoluyla toplar.
API anahtarı gerektirmez, DuckDuckGo üzerinden güncel verileri arar.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import re
import time

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

from anthropic import Anthropic


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
    confidence: float = 0.8
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
    Web üzerinden ekonomik veri toplayan sınıf.

    TÜİK ve TCMB verilerini API olmadan, web araması yaparak toplar.
    """

    # Aranacak göstergeler
    MACRO_INDICATORS = {
        "nufus": {
            "queries": ["Türkiye nüfusu {year}", "Türkiye nüfus {year} TÜİK"],
            "unit": "kişi",
            "category": "demografi"
        },
        "gsyih": {
            "queries": ["Türkiye GSYİH {year}", "Türkiye GSYH milyar dolar {year}"],
            "unit": "milyar USD",
            "category": "ekonomi"
        },
        "gsyih_buyume": {
            "queries": ["Türkiye ekonomik büyüme {year}", "Türkiye GSYİH büyüme oranı {year}"],
            "unit": "%",
            "category": "ekonomi"
        },
        "enflasyon": {
            "queries": ["Türkiye enflasyon oranı {year}", "TÜFE yıllık {year}"],
            "unit": "%",
            "category": "ekonomi"
        },
        "issizlik": {
            "queries": ["Türkiye işsizlik oranı {year}", "işsizlik Türkiye {year} TÜİK"],
            "unit": "%",
            "category": "istihdam"
        },
        "dolar_kuru": {
            "queries": ["dolar kuru bugün", "USD TRY kur"],
            "unit": "TL",
            "category": "finans"
        },
        "euro_kuru": {
            "queries": ["euro kuru bugün", "EUR TRY kur"],
            "unit": "TL",
            "category": "finans"
        },
        "faiz_orani": {
            "queries": ["TCMB politika faizi {year}", "Merkez Bankası faiz oranı"],
            "unit": "%",
            "category": "finans"
        },
        "cari_denge": {
            "queries": ["Türkiye cari açık {year}", "cari denge milyar dolar {year}"],
            "unit": "milyar USD",
            "category": "ekonomi"
        },
        "ihracat": {
            "queries": ["Türkiye ihracat {year}", "ihracat milyar dolar {year}"],
            "unit": "milyar USD",
            "category": "ticaret"
        },
        "ithalat": {
            "queries": ["Türkiye ithalat {year}", "ithalat milyar dolar {year}"],
            "unit": "milyar USD",
            "category": "ticaret"
        }
    }

    # Sektör verileri
    SECTOR_QUERIES = {
        "e_ticaret": ["e-ticaret pazar büyüklüğü Türkiye {year}", "online alışveriş hacmi {year}"],
        "fintech": ["fintech pazar büyüklüğü Türkiye {year}", "finansal teknoloji sektörü {year}"],
        "yazilim": ["yazılım sektörü Türkiye {year}", "bilişim sektörü büyüklüğü {year}"],
        "turizm": ["turizm gelirleri Türkiye {year}", "turist sayısı {year}"],
        "otomotiv": ["otomotiv sektörü Türkiye {year}", "araç üretimi {year}"],
        "insaat": ["inşaat sektörü Türkiye {year}", "konut satışları {year}"],
        "enerji": ["enerji sektörü Türkiye {year}", "elektrik tüketimi {year}"],
        "saglik": ["sağlık sektörü Türkiye {year}", "sağlık harcamaları {year}"],
        "egitim": ["eğitim sektörü Türkiye {year}", "öğrenci sayısı {year}"],
        "tarim": ["tarım sektörü Türkiye {year}", "tarımsal üretim {year}"]
    }

    def __init__(
        self,
        anthropic_client: Optional[Anthropic] = None,
        cache_enabled: bool = True
    ):
        self.client = anthropic_client
        self.cache_enabled = cache_enabled
        self.cache: Dict[str, DataPoint] = {}
        self.current_year = datetime.now().year
        self.current_date = datetime.now().strftime("%Y-%m-%d")

        # DuckDuckGo search
        self.ddgs = DDGS() if HAS_DDGS else None

    def _search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """DuckDuckGo'da arama yap."""
        if not self.ddgs:
            return []

        try:
            results = list(self.ddgs.text(
                query,
                region="tr-tr",
                max_results=max_results,
                safesearch="moderate"
            ))
            return results
        except Exception as e:
            print(f"Arama hatası: {e}")
            return []

    def _extract_number(self, text: str, indicator: str) -> Optional[Dict[str, Any]]:
        """Metinden sayısal değer çıkar."""
        text = text.lower()

        # Farklı pattern'ler
        patterns = [
            # "1.5 milyar dolar" veya "1,5 milyar TL"
            r'(\d{1,3}(?:[.,]\d{1,3})*)\s*(milyar|milyon|trilyon)?\s*(dolar|tl|usd|eur|euro|₺|\$|€)?',
            # "%65.5" veya "yüzde 65"
            r'%\s*(\d+[.,]?\d*)|yüzde\s*(\d+[.,]?\d*)',
            # "65 milyon kişi"
            r'(\d{1,3}(?:[.,]\d{1,3})*)\s*(milyon|milyar)?\s*(kişi|kisi)?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                match = matches[0]
                if isinstance(match, tuple):
                    value_str = next((m for m in match if m and re.match(r'\d', m)), None)
                    if value_str:
                        # Sayıyı parse et
                        value_str = value_str.replace(".", "").replace(",", ".")
                        try:
                            value = float(value_str)

                            # Çarpan uygula
                            multiplier = 1
                            full_text = " ".join(match).lower()
                            if "trilyon" in full_text:
                                multiplier = 1_000_000_000_000
                            elif "milyar" in full_text:
                                multiplier = 1_000_000_000
                            elif "milyon" in full_text:
                                multiplier = 1_000_000

                            return {
                                "value": value,
                                "multiplier": multiplier,
                                "raw": match
                            }
                        except ValueError:
                            continue
        return None

    def _extract_value_with_claude(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        indicator_info: Dict[str, Any]
    ) -> Optional[DataPoint]:
        """Claude kullanarak arama sonuçlarından değer çıkar."""
        if not self.client or not search_results:
            return None

        # Sonuçları birleştir
        context = ""
        best_url = ""
        best_source = ""

        for result in search_results[:5]:
            title = result.get("title", "")
            body = result.get("body", "")
            url = result.get("href", "")

            context += f"Başlık: {title}\nİçerik: {body}\nURL: {url}\n\n"

            # En iyi kaynağı belirle
            if not best_url:
                if "tuik" in url.lower() or "tcmb" in url.lower() or ".gov.tr" in url.lower():
                    best_url = url
                    best_source = title
                else:
                    best_url = url
                    best_source = title

        prompt = f"""Aşağıdaki arama sonuçlarından "{query}" için en güncel değeri çıkar.

ARAMA SONUÇLARI:
{context}

Lütfen şu formatta yanıt ver (sadece bu formatı kullan, başka açıklama yapma):

DEĞER: [sayısal değer]
BİRİM: [birim - ör: %, milyar USD, milyon kişi, TL]
DÖNEM: [dönem - ör: 2024, Ocak 2024, Q3 2024]
GÜVEN: [0-1 arası güven puanı]

Eğer kesin bir değer bulamıyorsan:
DEĞER: BULUNAMADI

Önemli: Sadece kaynaklarda açıkça belirtilen değerleri kullan."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse response
            if "BULUNAMADI" in result_text:
                return None

            value_match = re.search(r'DEĞER:\s*([^\n]+)', result_text)
            unit_match = re.search(r'BİRİM:\s*([^\n]+)', result_text)
            period_match = re.search(r'DÖNEM:\s*([^\n]+)', result_text)
            confidence_match = re.search(r'GÜVEN:\s*([0-9.]+)', result_text)

            if value_match:
                value_str = value_match.group(1).strip()
                # Sayıyı çıkar
                num_match = re.search(r'([\d.,]+)', value_str)
                if num_match:
                    value = float(num_match.group(1).replace(",", "."))

                    return DataPoint(
                        indicator=query,
                        value=value,
                        value_formatted=value_str,
                        unit=unit_match.group(1).strip() if unit_match else indicator_info.get("unit", ""),
                        period=period_match.group(1).strip() if period_match else str(self.current_year),
                        source=best_source,
                        source_url=best_url,
                        confidence=float(confidence_match.group(1)) if confidence_match else 0.7
                    )

        except Exception as e:
            print(f"Claude API hatası: {e}")

        return None

    def get_macro_indicator(self, indicator: str) -> Optional[DataPoint]:
        """Tek bir makroekonomik göstergeyi getir."""
        # Cache kontrolü
        cache_key = f"macro_{indicator}_{self.current_date}"
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]

        if indicator not in self.MACRO_INDICATORS:
            return None

        info = self.MACRO_INDICATORS[indicator]
        queries = [q.format(year=self.current_year) for q in info["queries"]]

        all_results = []
        for query in queries:
            results = self._search(query, max_results=3)
            all_results.extend(results)
            time.sleep(0.3)

        if not all_results:
            return None

        # Claude ile değer çıkar
        data_point = self._extract_value_with_claude(
            query=indicator,
            search_results=all_results,
            indicator_info=info
        )

        if data_point and self.cache_enabled:
            self.cache[cache_key] = data_point

        return data_point

    def get_all_macro_indicators(
        self,
        progress_callback: callable = None
    ) -> Dict[str, DataPoint]:
        """Tüm makroekonomik göstergeleri getir."""
        indicators = {}
        total = len(self.MACRO_INDICATORS)

        for i, indicator in enumerate(self.MACRO_INDICATORS.keys()):
            if progress_callback:
                progress_callback(
                    phase="data_collection",
                    progress=(i + 1) / total * 100,
                    detail=f"Veri alınıyor: {indicator}"
                )

            data_point = self.get_macro_indicator(indicator)
            if data_point:
                indicators[indicator] = data_point

            time.sleep(0.5)  # Rate limiting

        return indicators

    def get_exchange_rates(self) -> Dict[str, DataPoint]:
        """Döviz kurlarını getir."""
        rates = {}

        # Dolar kuru
        dolar = self.get_macro_indicator("dolar_kuru")
        if dolar:
            rates["USD_TRY"] = dolar

        # Euro kuru
        euro = self.get_macro_indicator("euro_kuru")
        if euro:
            rates["EUR_TRY"] = euro

        return rates

    def get_sector_data(
        self,
        sector: str,
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """Sektör verilerini getir."""
        cache_key = f"sector_{sector}_{self.current_date}"
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]

        if sector not in self.SECTOR_QUERIES:
            # Genel arama yap
            queries = [f"{sector} pazar büyüklüğü Türkiye {self.current_year}"]
        else:
            queries = [q.format(year=self.current_year) for q in self.SECTOR_QUERIES[sector]]

        all_results = []
        for query in queries:
            if progress_callback:
                progress_callback(
                    phase="sector_research",
                    progress=50,
                    detail=f"Aranıyor: {query}"
                )

            results = self._search(query, max_results=5)
            all_results.extend(results)
            time.sleep(0.3)

        if not all_results or not self.client:
            return {"sector": sector, "data": [], "sources": []}

        # Claude ile analiz et
        context = "\n\n".join([
            f"Başlık: {r.get('title', '')}\nİçerik: {r.get('body', '')}\nURL: {r.get('href', '')}"
            for r in all_results[:10]
        ])

        prompt = f"""Aşağıdaki arama sonuçlarından "{sector}" sektörü hakkında bilgi çıkar.

ARAMA SONUÇLARI:
{context}

Lütfen şu formatta yanıt ver:

PAZAR_BÜYÜKLÜĞÜ: [değer ve birim, ör: 50 milyar TL]
BÜYÜME_ORANI: [yüzde, ör: %15]
OYUNCU_SAYISI: [varsa rakam]
TREND: [kısa açıklama]
KAYNAK: [en güvenilir kaynak URL'si]

Bulamadığın bilgiler için "BİLİNMİYOR" yaz."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            sector_data = {
                "sector": sector,
                "raw_response": result_text,
                "sources": [r.get("href", "") for r in all_results[:5] if r.get("href")]
            }

            # Parse response
            for line in result_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    value = value.strip()
                    if value and value != "BİLİNMİYOR":
                        sector_data[key] = value

            if self.cache_enabled:
                self.cache[cache_key] = sector_data

            return sector_data

        except Exception as e:
            print(f"Sektör analizi hatası: {e}")
            return {"sector": sector, "error": str(e), "sources": []}

    def get_turkey_stats(self) -> Dict[str, DataPoint]:
        """Temel Türkiye istatistiklerini getir."""
        stats = {}

        key_indicators = ["nufus", "gsyih", "enflasyon", "issizlik"]

        for indicator in key_indicators:
            data = self.get_macro_indicator(indicator)
            if data:
                stats[indicator] = data

        return stats

    def search_custom_data(
        self,
        query: str,
        expected_unit: str = ""
    ) -> Optional[DataPoint]:
        """Özel sorgu ile veri ara."""
        results = self._search(query, max_results=5)

        if not results:
            return None

        return self._extract_value_with_claude(
            query=query,
            search_results=results,
            indicator_info={"unit": expected_unit}
        )

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
