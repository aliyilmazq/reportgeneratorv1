"""
Turkish Number Parser Module
============================
Turkce sayi formatlarini dogru sekilde parse eden modul.
1.234,56 (TR) ve 1,234.56 (US) formatlarini destekler.
"""

import re
from typing import Optional, Tuple, Union
from decimal import Decimal, InvalidOperation

from .exceptions import NumberParsingError


class TurkishNumberParser:
    """
    Turkce ve uluslararasi sayi formatlarini parse eden sinif.

    Desteklenen formatlar:
    - Turkce: 1.234,56 (nokta binlik, virgul ondalik)
    - US/UK: 1,234.56 (virgul binlik, nokta ondalik)
    - Sadece sayi: 1234, 1234.56, 1234,56
    - Carpanli: 1,5 milyon, 2.3 milyar, 500 bin
    """

    # Turkce carpanlar
    MULTIPLIERS = {
        'bin': 1_000,
        'milyon': 1_000_000,
        'milyar': 1_000_000_000,
        'trilyon': 1_000_000_000_000,
        'katrilyon': 1_000_000_000_000_000,
        # Kisaltmalar
        'mn': 1_000_000,
        'mln': 1_000_000,
        'mr': 1_000_000_000,
        'mlr': 1_000_000_000,
        # Ingilizce
        'thousand': 1_000,
        'million': 1_000_000,
        'billion': 1_000_000_000,
        'trillion': 1_000_000_000_000,
        # Kisaltmalar (ing)
        'k': 1_000,
        'm': 1_000_000,
        'b': 1_000_000_000,
        't': 1_000_000_000_000,
    }

    # Format pattern'leri
    PATTERNS = {
        # Turkce format: 1.234.567,89
        'turkish': re.compile(r'^-?\d{1,3}(?:\.\d{3})*,\d+$'),
        # US format: 1,234,567.89
        'us': re.compile(r'^-?\d{1,3}(?:,\d{3})*\.\d+$'),
        # Sadece ondalik (virgul): 1234,56
        'decimal_comma': re.compile(r'^-?\d+,\d+$'),
        # Sadece ondalik (nokta): 1234.56
        'decimal_dot': re.compile(r'^-?\d+\.\d+$'),
        # Tam sayi: 1234
        'integer': re.compile(r'^-?\d+$'),
        # Binlik ayiracli tam sayi (TR): 1.234.567
        'integer_turkish': re.compile(r'^-?\d{1,3}(?:\.\d{3})+$'),
        # Binlik ayiracli tam sayi (US): 1,234,567
        'integer_us': re.compile(r'^-?\d{1,3}(?:,\d{3})+$'),
    }

    # Carpanli sayi pattern'i
    MULTIPLIER_PATTERN = re.compile(
        r'^(-?\d+(?:[.,]\d+)?)\s*'  # Sayi kismi
        r'(bin|milyon|milyar|trilyon|katrilyon|'  # Turkce carpanlar
        r'thousand|million|billion|trillion|'  # Ingilizce carpanlar
        r'mn|mln|mr|mlr|k|m|b|t)$',  # Kisaltmalar
        re.IGNORECASE
    )

    @classmethod
    def parse(
        cls,
        text: str,
        strict: bool = False,
        default: Optional[float] = None
    ) -> Optional[float]:
        """
        Metni sayiya cevir.

        Args:
            text: Parse edilecek metin
            strict: Hata durumunda exception firlat
            default: Hata durumunda donecek varsayilan deger

        Returns:
            Parse edilmis sayi veya default

        Raises:
            NumberParsingError: strict=True ve parse basarisiz ise
        """
        if not text:
            if strict:
                raise NumberParsingError("", "Bos metin")
            return default

        # Temizle
        text = cls._clean_text(text)

        if not text:
            if strict:
                raise NumberParsingError(text, "Gecerli sayi bulunamadi")
            return default

        try:
            # Carpanli sayi kontrolu
            multiplier_match = cls.MULTIPLIER_PATTERN.match(text)
            if multiplier_match:
                number_part = multiplier_match.group(1)
                multiplier_name = multiplier_match.group(2).lower()
                base_value = cls._parse_simple_number(number_part)
                multiplier = cls.MULTIPLIERS.get(multiplier_name, 1)
                return base_value * multiplier

            # Basit sayi
            return cls._parse_simple_number(text)

        except (ValueError, InvalidOperation) as e:
            if strict:
                raise NumberParsingError(text, str(e))
            return default

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Metni temizle."""
        if not isinstance(text, str):
            text = str(text)

        # Bosluklar ve ozel karakterler
        text = text.strip()

        # Para birimi sembolleri
        text = re.sub(r'[₺$€£¥]', '', text)

        # Yuzde isareti
        text = text.replace('%', '')

        # Parantezli negatif: (123) -> -123
        if text.startswith('(') and text.endswith(')'):
            text = '-' + text[1:-1]

        # Fazla bosluklar
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    @classmethod
    def _parse_simple_number(cls, text: str) -> float:
        """Basit sayiyi parse et (carpan olmadan)."""
        text = text.strip()

        # Negatif isareti
        negative = text.startswith('-')
        if negative:
            text = text[1:]

        # Format tespiti ve donusum
        result = None

        # Turkce format: 1.234.567,89
        if cls.PATTERNS['turkish'].match(text):
            # Noktalari kaldir, virgulu noktaya cevir
            result = float(text.replace('.', '').replace(',', '.'))

        # US format: 1,234,567.89
        elif cls.PATTERNS['us'].match(text):
            # Virgulleri kaldir
            result = float(text.replace(',', ''))

        # Binlik ayiracli tam sayi (TR): 1.234.567
        elif cls.PATTERNS['integer_turkish'].match(text):
            result = float(text.replace('.', ''))

        # Binlik ayiracli tam sayi (US): 1,234,567
        elif cls.PATTERNS['integer_us'].match(text):
            result = float(text.replace(',', ''))

        # Sadece ondalik (virgul): 1234,56
        elif cls.PATTERNS['decimal_comma'].match(text):
            result = float(text.replace(',', '.'))

        # Sadece ondalik (nokta) veya tam sayi
        elif cls.PATTERNS['decimal_dot'].match(text) or cls.PATTERNS['integer'].match(text):
            result = float(text)

        else:
            # Son caba: tum ayiraclari kaldir
            cleaned = re.sub(r'[.,\s]', '', text)
            if cleaned.isdigit():
                result = float(cleaned)
            else:
                raise ValueError(f"Taninamayan format: {text}")

        return -result if negative else result

    @classmethod
    def detect_format(cls, text: str) -> str:
        """
        Sayi formatini tespit et.

        Returns:
            'turkish', 'us', 'simple', veya 'unknown'
        """
        text = cls._clean_text(text)

        # Carpanli sayi
        if cls.MULTIPLIER_PATTERN.match(text):
            return 'multiplied'

        # Negatif isareti kaldir
        if text.startswith('-'):
            text = text[1:]

        if cls.PATTERNS['turkish'].match(text) or cls.PATTERNS['integer_turkish'].match(text):
            return 'turkish'

        if cls.PATTERNS['us'].match(text) or cls.PATTERNS['integer_us'].match(text):
            return 'us'

        if cls.PATTERNS['decimal_comma'].match(text):
            return 'decimal_comma'

        if cls.PATTERNS['decimal_dot'].match(text) or cls.PATTERNS['integer'].match(text):
            return 'simple'

        return 'unknown'

    @classmethod
    def format_turkish(cls, value: float, decimal_places: int = 2) -> str:
        """
        Sayiyi Turkce formata cevir.

        Args:
            value: Formatlanacak sayi
            decimal_places: Ondalik basamak sayisi

        Returns:
            Turkce formatli string (1.234,56)
        """
        # Ondalik ayirma
        if decimal_places > 0:
            formatted = f"{value:,.{decimal_places}f}"
        else:
            formatted = f"{value:,.0f}"

        # US formatindan TR formatina cevir
        # Gecici karakter kullan
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')

        return formatted

    @classmethod
    def extract_numbers(cls, text: str) -> list:
        """
        Metinden tum sayilari cikar.

        Args:
            text: Aranacak metin

        Returns:
            Bulunan sayilarin listesi
        """
        results = []

        # Carpanli sayilari bul
        multiplier_pattern = re.compile(
            r'(-?\d+(?:[.,]\d+)?)\s*'
            r'(bin|milyon|milyar|trilyon|katrilyon|thousand|million|billion|trillion|mn|mln|mr|mlr|k|m|b|t)',
            re.IGNORECASE
        )

        for match in multiplier_pattern.finditer(text):
            try:
                value = cls.parse(match.group(0))
                if value is not None:
                    results.append(value)
            except Exception:
                pass

        # Carpansiz sayilari bul
        number_pattern = re.compile(
            r'-?\d{1,3}(?:[.,]\d{3})*[.,]\d+|'  # Binlik + ondalik
            r'-?\d{1,3}(?:[.,]\d{3})+|'  # Sadece binlik
            r'-?\d+[.,]\d+|'  # Sadece ondalik
            r'-?\d+'  # Sadece tam sayi
        )

        for match in number_pattern.finditer(text):
            # Carpanli sayilarla cakisma kontrolu
            try:
                value = cls.parse(match.group(0))
                if value is not None and value not in results:
                    results.append(value)
            except Exception:
                pass

        return results


# Convenience functions
def parse_number(text: str, default: Optional[float] = None) -> Optional[float]:
    """Sayiyi parse et (shortcut)."""
    return TurkishNumberParser.parse(text, default=default)


def parse_number_strict(text: str) -> float:
    """Sayiyi parse et, hata firlat (shortcut)."""
    result = TurkishNumberParser.parse(text, strict=True)
    if result is None:
        raise NumberParsingError(text, "Parse edilemedi")
    return result


def format_turkish_number(value: float, decimal_places: int = 2) -> str:
    """Turkce format (shortcut)."""
    return TurkishNumberParser.format_turkish(value, decimal_places)


def extract_numbers(text: str) -> list:
    """Metinden sayilari cikar (shortcut)."""
    return TurkishNumberParser.extract_numbers(text)
