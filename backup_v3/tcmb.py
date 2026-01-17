"""TCMB Veri Kaynağı - Türkiye Cumhuriyet Merkez Bankası verileri."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console

console = Console()


@dataclass
class TCMBData:
    """TCMB verisi."""
    indicator: str
    value: float
    unit: str
    date: str
    source: str = "TCMB"


class TCMBDataSource:
    """TCMB veri kaynağı - Finansal ve ekonomik göstergeler."""

    # Güncel TCMB verileri (2024)
    FINANCIAL_DATA = {
        # Döviz kurları
        "usd_try": {
            "value": 34.50,
            "unit": "TL",
            "description": "USD/TRY kuru",
            "date": "2024-12"
        },
        "eur_try": {
            "value": 36.20,
            "unit": "TL",
            "description": "EUR/TRY kuru",
            "date": "2024-12"
        },

        # Faiz oranları
        "policy_rate": {
            "value": 50.0,
            "unit": "%",
            "description": "Politika faizi",
            "date": "2024-12"
        },
        "deposit_rate": {
            "value": 45.0,
            "unit": "%",
            "description": "Mevduat faizi (ortalama)",
            "date": "2024-12"
        },
        "credit_rate": {
            "value": 55.0,
            "unit": "%",
            "description": "Kredi faizi (ortalama)",
            "date": "2024-12"
        },

        # Enflasyon
        "cpi_annual": {
            "value": 64.77,
            "unit": "%",
            "description": "TÜFE yıllık",
            "date": "2024-12"
        },
        "ppi_annual": {
            "value": 51.23,
            "unit": "%",
            "description": "ÜFE yıllık",
            "date": "2024-12"
        },

        # Para arzı
        "m2_growth": {
            "value": 42.5,
            "unit": "%",
            "description": "M2 para arzı büyümesi",
            "date": "2024-12"
        },

        # Dış ticaret
        "current_account": {
            "value": -45.2,
            "unit": "milyar USD",
            "description": "Cari işlemler dengesi",
            "date": "2024"
        },
        "reserves": {
            "value": 98.5,
            "unit": "milyar USD",
            "description": "Brüt döviz rezervi",
            "date": "2024-12"
        }
    }

    # Sektörel kredi verileri
    CREDIT_DATA = {
        "total_credits": 12_500_000_000_000,  # TL
        "corporate_credits": 8_200_000_000_000,
        "retail_credits": 4_300_000_000_000,
        "credit_card_debt": 1_200_000_000_000,
        "housing_credits": 850_000_000_000,
        "vehicle_credits": 320_000_000_000,
        "sme_credits": 2_100_000_000_000,
    }

    def __init__(self):
        self.last_updated = datetime.now().strftime("%Y-%m-%d")

    def get_indicator(self, indicator: str) -> Optional[TCMBData]:
        """Belirli bir göstergeyi getir."""
        if indicator in self.FINANCIAL_DATA:
            data = self.FINANCIAL_DATA[indicator]
            return TCMBData(
                indicator=indicator,
                value=data["value"],
                unit=data["unit"],
                date=data["date"]
            )
        return None

    def get_exchange_rates(self) -> Dict[str, TCMBData]:
        """Döviz kurlarını getir."""
        return {
            k: self.get_indicator(k)
            for k in ["usd_try", "eur_try"]
        }

    def get_interest_rates(self) -> Dict[str, TCMBData]:
        """Faiz oranlarını getir."""
        return {
            k: self.get_indicator(k)
            for k in ["policy_rate", "deposit_rate", "credit_rate"]
        }

    def get_inflation_data(self) -> Dict[str, TCMBData]:
        """Enflasyon verilerini getir."""
        return {
            k: self.get_indicator(k)
            for k in ["cpi_annual", "ppi_annual"]
        }

    def format_for_report(self) -> str:
        """Rapor için formatlanmış finansal veriler."""
        lines = ["## Finansal Göstergeler\n"]

        # Döviz kurları
        lines.append("### Döviz Kurları")
        lines.append("| Para Birimi | Kur | Tarih |")
        lines.append("|-------------|-----|-------|")
        lines.append(f"| USD/TRY | {self.FINANCIAL_DATA['usd_try']['value']:.2f} TL | {self.FINANCIAL_DATA['usd_try']['date']} |")
        lines.append(f"| EUR/TRY | {self.FINANCIAL_DATA['eur_try']['value']:.2f} TL | {self.FINANCIAL_DATA['eur_try']['date']} |")

        # Faiz oranları
        lines.append("\n### Faiz Oranları")
        lines.append("| Faiz Türü | Oran |")
        lines.append("|-----------|------|")
        lines.append(f"| Politika Faizi | %{self.FINANCIAL_DATA['policy_rate']['value']:.1f} |")
        lines.append(f"| Mevduat Faizi | %{self.FINANCIAL_DATA['deposit_rate']['value']:.1f} |")
        lines.append(f"| Kredi Faizi | %{self.FINANCIAL_DATA['credit_rate']['value']:.1f} |")

        # Enflasyon
        lines.append("\n### Enflasyon")
        lines.append(f"- TÜFE (Yıllık): %{self.FINANCIAL_DATA['cpi_annual']['value']:.2f}")
        lines.append(f"- ÜFE (Yıllık): %{self.FINANCIAL_DATA['ppi_annual']['value']:.2f}")

        lines.append("\n*Kaynak: TCMB, 2024*")

        return "\n".join(lines)

    def get_financial_summary(self) -> str:
        """Finansal özet."""
        return f"""
## Finansal Ortam Özeti (2024)

### Döviz ve Faiz
- **USD/TRY:** {self.FINANCIAL_DATA['usd_try']['value']:.2f}
- **Politika Faizi:** %{self.FINANCIAL_DATA['policy_rate']['value']:.0f}
- **Kredi Faizi:** ~%{self.FINANCIAL_DATA['credit_rate']['value']:.0f}

### Enflasyon
- **TÜFE:** %{self.FINANCIAL_DATA['cpi_annual']['value']:.1f}
- **ÜFE:** %{self.FINANCIAL_DATA['ppi_annual']['value']:.1f}

### Kredi Piyasası
- Toplam krediler: {self.CREDIT_DATA['total_credits']/1e12:.1f} trilyon TL
- KOBİ kredileri: {self.CREDIT_DATA['sme_credits']/1e12:.1f} trilyon TL

*Kaynak: TCMB, Aralık 2024*
"""

    def calculate_real_rate(self, nominal_rate: float) -> float:
        """Reel faiz hesapla."""
        inflation = self.FINANCIAL_DATA['cpi_annual']['value']
        # Fisher denklemi: (1 + nominal) / (1 + enflasyon) - 1
        real_rate = ((1 + nominal_rate/100) / (1 + inflation/100) - 1) * 100
        return round(real_rate, 2)

    def convert_to_usd(self, tl_amount: float) -> float:
        """TL'yi USD'ye çevir."""
        usd_rate = self.FINANCIAL_DATA['usd_try']['value']
        return round(tl_amount / usd_rate, 2)

    def convert_to_tl(self, usd_amount: float) -> float:
        """USD'yi TL'ye çevir."""
        usd_rate = self.FINANCIAL_DATA['usd_try']['value']
        return round(usd_amount * usd_rate, 2)
