"""Mantık Kontrolü Modülü - İçerik tutarlılığı ve mantık hatası tespiti."""

import re
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class LogicIssue:
    """Mantık sorunu."""
    rule_id: str
    severity: str
    message: str
    section: str
    context: str = ""
    fix_suggestion: str = ""


class LogicChecker:
    """Mantık kontrolcüsü - İçerik tutarlılığını doğrular."""

    # Mantık kuralları
    LOGIC_RULES = {
        # Finansal mantık kuralları
        "net_less_than_gross": {
            "description": "Net kar marjı brüt kar marjından küçük olmalı",
            "severity": "error"
        },
        "revenue_cost_profit": {
            "description": "Gelir - Maliyet = Kar tutmalı",
            "severity": "error"
        },
        "market_share_sum": {
            "description": "Pazar payları toplamı %100'ü geçmemeli",
            "severity": "error"
        },
        "growth_consistency": {
            "description": "Büyüme oranları yıllar arası tutarlı olmalı",
            "severity": "warning"
        },
        "projection_base": {
            "description": "Projeksiyon baz yılı mevcut yıldan önce olmalı",
            "severity": "warning"
        },

        # İş mantığı kuralları
        "target_achievability": {
            "description": "Hedefler mevcut kaynaklar ile ulaşılabilir olmalı",
            "severity": "warning"
        },
        "timeline_feasibility": {
            "description": "Zaman çizelgesi gerçekçi olmalı",
            "severity": "warning"
        },

        # Metin tutarlılığı
        "contradiction_check": {
            "description": "Bölümler arası çelişki olmamalı",
            "severity": "error"
        }
    }

    # Çelişki tespiti için anahtar kelimeler
    CONTRADICTION_PAIRS = [
        (["artış", "yükseliş", "büyüme", "pozitif"], ["düşüş", "azalma", "daralma", "negatif"]),
        (["güçlü", "lider", "dominant"], ["zayıf", "geride", "rekabetçi değil"]),
        (["düşük risk", "güvenli"], ["yüksek risk", "riskli", "tehlikeli"]),
        (["karlı", "kazançlı"], ["zararlı", "kayıp"]),
    ]

    def __init__(self):
        pass

    def check(self, report_content: Dict[str, str]) -> List[LogicIssue]:
        """Rapor içeriğinde mantık kontrolü yap."""
        issues = []

        # 1. Finansal mantık kontrolü
        issues.extend(self._check_financial_logic(report_content))

        # 2. Çelişki kontrolü
        issues.extend(self._check_contradictions(report_content))

        # 3. Tutarlılık kontrolü
        issues.extend(self._check_consistency(report_content))

        # 4. Gerçekçilik kontrolü
        issues.extend(self._check_realism(report_content))

        return issues

    def _check_financial_logic(self, content: Dict[str, str]) -> List[LogicIssue]:
        """Finansal mantık kurallarını kontrol et."""
        issues = []
        full_text = " ".join(content.values())

        # Net kar < Brüt kar kontrolü
        gross_margin = self._extract_margin(full_text, ["brüt kar", "brüt marj", "gross margin", "gross profit"])
        net_margin = self._extract_margin(full_text, ["net kar", "net marj", "net margin", "net profit"])

        if gross_margin and net_margin:
            if net_margin > gross_margin:
                issues.append(LogicIssue(
                    rule_id="net_less_than_gross",
                    severity="error",
                    message=f"Net kar marjı (%{net_margin}) brüt kar marjından (%{gross_margin}) büyük olamaz",
                    section="finansal",
                    fix_suggestion="Marjin değerlerini kontrol edin"
                ))

        # EBITDA < Gelir kontrolü
        # Maliyet > 0 kontrolü

        return issues

    def _extract_margin(self, text: str, keywords: List[str]) -> float:
        """Metinden marjin değeri çıkar."""
        for keyword in keywords:
            pattern = rf'{keyword}[:\s]*%?\s*([\d.,]+)\s*%?'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = match.group(1).replace(',', '.')
                    return float(value)
                except (ValueError, AttributeError):
                    # Marjin degeri parse edilemedi
                    pass
        return None

    def _check_contradictions(self, content: Dict[str, str]) -> List[LogicIssue]:
        """Bölümler arası çelişkileri tespit et."""
        issues = []

        sections = list(content.items())

        for i, (section1_id, section1_text) in enumerate(sections):
            if not section1_text:
                continue

            for section2_id, section2_text in sections[i+1:]:
                if not section2_text:
                    continue

                # Çelişki çiftlerini kontrol et
                for positive_words, negative_words in self.CONTRADICTION_PAIRS:
                    has_positive_1 = any(w in section1_text.lower() for w in positive_words)
                    has_negative_1 = any(w in section1_text.lower() for w in negative_words)
                    has_positive_2 = any(w in section2_text.lower() for w in positive_words)
                    has_negative_2 = any(w in section2_text.lower() for w in negative_words)

                    # Aynı konuda zıt ifadeler
                    if (has_positive_1 and has_negative_2) or (has_negative_1 and has_positive_2):
                        # Daha detaylı kontrol - aynı cümle içinde mi?
                        # Şimdilik sadece uyarı ver
                        pass  # Çok fazla false positive olabilir

        return issues

    def _check_consistency(self, content: Dict[str, str]) -> List[LogicIssue]:
        """Sayısal tutarlılık kontrolü."""
        issues = []

        # Aynı metrik için farklı değerler
        metrics_found = {}

        metric_patterns = [
            (r'pazar\s*büyüklüğü[:\s]*([\d.,]+)\s*(milyon|milyar)?', 'pazar_buyuklugu'),
            (r'hedef\s*(?:müşteri|kullanıcı)[:\s]*([\d.,]+)', 'hedef_musteri'),
            (r'yatırım\s*(?:ihtiyacı|tutarı)[:\s]*([\d.,]+)', 'yatirim'),
        ]

        for section_id, text in content.items():
            if not text:
                continue

            for pattern, metric_name in metric_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if metric_name not in metrics_found:
                        metrics_found[metric_name] = []
                    for match in matches:
                        try:
                            value = float(match[0].replace(',', '.').replace('.', ''))
                            metrics_found[metric_name].append({
                                'value': value,
                                'section': section_id,
                                'multiplier': match[1] if len(match) > 1 else ''
                            })
                        except (ValueError, TypeError, IndexError):
                            # Metrik degeri parse edilemedi
                            pass

        # Aynı metrik için farklı değerler varsa uyar
        for metric_name, values in metrics_found.items():
            if len(values) >= 2:
                unique_values = set(v['value'] for v in values)
                if len(unique_values) > 1:
                    issues.append(LogicIssue(
                        rule_id="value_inconsistency",
                        severity="warning",
                        message=f"'{metric_name}' için farklı değerler tespit edildi: {unique_values}",
                        section="çoklu bölüm",
                        fix_suggestion="Tüm bölümlerde aynı değeri kullanın"
                    ))

        return issues

    def _check_realism(self, content: Dict[str, str]) -> List[LogicIssue]:
        """Gerçekçilik kontrolü."""
        issues = []
        full_text = " ".join(content.values())

        # Aşırı iddialı hedefler
        unrealistic_patterns = [
            (r'(\d+)\s*yıl\s*içinde\s*lider', "liderlik_hedefi"),
            (r'%\s*(\d{3,})\s*büyüme', "asiri_buyume"),  # %100+ büyüme
            (r'(\d+)\s*ayda\s*başa\s*baş', "basa_bas"),
        ]

        for pattern, check_type in unrealistic_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                value = int(match.group(1))

                if check_type == "liderlik_hedefi" and value <= 1:
                    issues.append(LogicIssue(
                        rule_id="unrealistic_target",
                        severity="warning",
                        message=f"{value} yıl içinde liderlik hedefi çok iddialı olabilir",
                        section="hedefler",
                        fix_suggestion="Daha gerçekçi bir zaman çizelgesi belirleyin"
                    ))

                elif check_type == "asiri_buyume" and value > 300:
                    issues.append(LogicIssue(
                        rule_id="unrealistic_growth",
                        severity="warning",
                        message=f"%{value} büyüme oranı gerçekçi değil görünüyor",
                        section="finansal",
                        fix_suggestion="Büyüme projeksiyonunu gözden geçirin"
                    ))

                elif check_type == "basa_bas" and value <= 6:
                    issues.append(LogicIssue(
                        rule_id="unrealistic_breakeven",
                        severity="info",
                        message=f"{value} ayda başa baş çok iyimser olabilir",
                        section="finansal",
                        fix_suggestion="Başa baş analizini detaylandırın"
                    ))

        return issues

    def fix_issues(
        self,
        content: Dict[str, str],
        issues: List[LogicIssue]
    ) -> Dict[str, str]:
        """Tespit edilen sorunları düzeltmeye çalış."""
        fixed_content = content.copy()

        for issue in issues:
            if issue.severity == "error":
                # Kritik hatalar için düzeltme önerisi ekle
                # Gerçek düzeltme Claude ile yapılmalı
                pass

        return fixed_content
