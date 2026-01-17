"""TÜİK Veri Kaynağı - Türkiye İstatistik Kurumu verileri."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console

console = Console()


@dataclass
class TUIKData:
    """TÜİK verisi."""
    indicator: str
    value: float
    unit: str
    period: str
    source: str = "TÜİK"
    last_updated: str = ""


class TUIKDataSource:
    """TÜİK veri kaynağı - Temel Türkiye istatistikleri."""

    # Güncel Türkiye istatistikleri (2024 verileri)
    # NOT: Gerçek API entegrasyonu yapılabilir, şimdilik sabit veriler
    TURKEY_STATS = {
        "population": {
            "value": 85_372_377,
            "unit": "kişi",
            "period": "2023",
            "description": "Türkiye nüfusu"
        },
        "gdp": {
            "value": 1_118,
            "unit": "milyar USD",
            "period": "2023",
            "description": "Gayri Safi Yurtiçi Hasıla"
        },
        "gdp_per_capita": {
            "value": 13_110,
            "unit": "USD",
            "period": "2023",
            "description": "Kişi başı GSYH"
        },
        "inflation": {
            "value": 64.77,
            "unit": "%",
            "period": "Aralık 2024",
            "description": "TÜFE yıllık değişim"
        },
        "unemployment": {
            "value": 8.8,
            "unit": "%",
            "period": "2024 Q3",
            "description": "İşsizlik oranı"
        },
        "internet_users": {
            "value": 82.0,
            "unit": "%",
            "period": "2024",
            "description": "İnternet kullanım oranı"
        },
        "smartphone_penetration": {
            "value": 77.0,
            "unit": "%",
            "period": "2024",
            "description": "Akıllı telefon penetrasyonu"
        },
        "ecommerce_volume": {
            "value": 1_850,
            "unit": "milyar TL",
            "period": "2024",
            "description": "E-ticaret hacmi"
        },
        "household_count": {
            "value": 27_500_000,
            "unit": "hane",
            "period": "2023",
            "description": "Hane sayısı"
        },
        "median_age": {
            "value": 33.5,
            "unit": "yaş",
            "period": "2023",
            "description": "Medyan yaş"
        },
        "urbanization": {
            "value": 93.4,
            "unit": "%",
            "period": "2023",
            "description": "Kentleşme oranı"
        }
    }

    # Sektör bazlı veriler
    SECTOR_DATA = {
        "e_ticaret": {
            "market_size_tl": 1_850_000_000_000,
            "market_size_usd": 54_000_000_000,
            "growth_rate": 35,
            "user_count": 58_000_000,
            "active_merchants": 600_000,
            "average_basket": 850,
        },
        "fintech": {
            "market_size_tl": 250_000_000_000,
            "transaction_volume": 2_500_000_000_000,
            "user_count": 45_000_000,
            "growth_rate": 45,
        },
        "saas": {
            "market_size_tl": 15_000_000_000,
            "growth_rate": 40,
            "company_count": 1_200,
        },
        "gaming": {
            "market_size_tl": 45_000_000_000,
            "gamer_count": 40_000_000,
            "growth_rate": 25,
        },
        "logistics": {
            "market_size_tl": 850_000_000_000,
            "growth_rate": 15,
        }
    }

    # Şehir bazlı veriler
    CITY_DATA = {
        "istanbul": {"population": 15_907_951, "gdp_share": 31.0},
        "ankara": {"population": 5_782_285, "gdp_share": 9.0},
        "izmir": {"population": 4_462_056, "gdp_share": 6.5},
        "bursa": {"population": 3_194_720, "gdp_share": 4.5},
        "antalya": {"population": 2_696_249, "gdp_share": 4.0},
    }

    def __init__(self):
        self.last_updated = datetime.now().strftime("%Y-%m-%d")

    def get_stat(self, indicator: str) -> Optional[TUIKData]:
        """Belirli bir istatistiği getir."""
        if indicator in self.TURKEY_STATS:
            data = self.TURKEY_STATS[indicator]
            return TUIKData(
                indicator=indicator,
                value=data["value"],
                unit=data["unit"],
                period=data["period"],
                last_updated=self.last_updated
            )
        return None

    def get_all_stats(self) -> Dict[str, TUIKData]:
        """Tüm istatistikleri getir."""
        return {k: self.get_stat(k) for k in self.TURKEY_STATS}

    def get_sector_data(self, sector: str) -> Optional[Dict[str, Any]]:
        """Sektör verisini getir."""
        return self.SECTOR_DATA.get(sector)

    def get_city_data(self, city: str) -> Optional[Dict[str, Any]]:
        """Şehir verisini getir."""
        return self.CITY_DATA.get(city.lower())

    def format_for_report(self, indicators: List[str] = None) -> str:
        """Rapor için formatlanmış veri."""
        if indicators is None:
            indicators = list(self.TURKEY_STATS.keys())

        lines = ["## Türkiye Temel Göstergeleri\n"]
        lines.append("| Gösterge | Değer | Dönem |")
        lines.append("|----------|-------|-------|")

        for ind in indicators:
            data = self.get_stat(ind)
            if data:
                desc = self.TURKEY_STATS[ind].get("description", ind)
                if data.value >= 1_000_000:
                    formatted_value = f"{data.value/1_000_000:,.1f}M"
                elif data.value >= 1_000:
                    formatted_value = f"{data.value/1_000:,.1f}K"
                else:
                    formatted_value = f"{data.value:,.2f}"

                lines.append(f"| {desc} | {formatted_value} {data.unit} | {data.period} |")

        lines.append("\n*Kaynak: TÜİK, 2024*")

        return "\n".join(lines)

    def get_macro_summary(self) -> str:
        """Makroekonomik özet."""
        return f"""
## Türkiye Makroekonomik Özet (2024)

- **Nüfus:** 85.4 milyon
- **GSYH:** 1.1 trilyon USD
- **Kişi Başı Gelir:** 13,110 USD
- **Enflasyon:** %64.77 (yıllık)
- **İşsizlik:** %8.8
- **İnternet Penetrasyonu:** %82
- **E-ticaret Hacmi:** 1.85 trilyon TL

*Kaynak: TÜİK, TCMB, 2024*
"""
