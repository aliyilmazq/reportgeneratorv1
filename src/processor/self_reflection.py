"""Self-Reflection Modülü - İçeriği eleştirip düzeltir."""

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
class ReflectionResult:
    """Eleştiri sonucu."""
    original_content: str
    issues_found: List[str]
    suggestions: List[str]
    revised_content: str
    quality_score: int  # 0-100
    improvement_made: bool


class SelfReflection:
    """Self-reflection sınıfı - İçeriği eleştirip iyileştirir."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.client = None

        if anthropic and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def reflect_and_improve(
        self,
        content: str,
        section_title: str,
        context: str = "",
        language: str = "tr"
    ) -> ReflectionResult:
        """İçeriği eleştir ve iyileştir."""

        if not self.client:
            return ReflectionResult(
                original_content=content,
                issues_found=[],
                suggestions=[],
                revised_content=content,
                quality_score=70,
                improvement_made=False
            )

        # ADIM 1: Eleştiri
        critique = self._critique_content(content, section_title, context, language)

        # ADIM 2: Kalite skoru ve iyileştirme gereksinimi
        needs_improvement = critique['score'] < 85 or len(critique['issues']) > 0

        if not needs_improvement:
            return ReflectionResult(
                original_content=content,
                issues_found=[],
                suggestions=[],
                revised_content=content,
                quality_score=critique['score'],
                improvement_made=False
            )

        # ADIM 3: İyileştirme
        revised = self._improve_content(
            content=content,
            section_title=section_title,
            issues=critique['issues'],
            suggestions=critique['suggestions'],
            language=language
        )

        return ReflectionResult(
            original_content=content,
            issues_found=critique['issues'],
            suggestions=critique['suggestions'],
            revised_content=revised,
            quality_score=critique['score'],
            improvement_made=True
        )

    def _critique_content(
        self,
        content: str,
        section_title: str,
        context: str,
        language: str
    ) -> Dict[str, Any]:
        """İçeriği eleştir."""

        prompt = f"""Sen deneyimli bir editör ve kalite kontrol uzmanısın. Aşağıdaki "{section_title}" bölümünü değerlendir.

## İÇERİK
{content}

## DEĞERLENDİRME KRİTERLERİ

1. **Doğruluk ve Tutarlılık (0-25 puan)**
   - Sayısal veriler tutarlı mı?
   - Mantık hataları var mı?
   - Çelişkili ifadeler var mı?

2. **Derinlik ve Özgünlük (0-25 puan)**
   - Yüzeysel mi yoksa derinlemesine mi?
   - Sektör bilgisi yeterli mi?
   - Farklılaştırıcı içgörüler var mı?

3. **Profesyonellik (0-25 puan)**
   - Dil ve üslup uygun mu?
   - Kurumsal ton korunmuş mu?
   - Yazım/imla hataları var mı?

4. **Yapı ve Akış (0-25 puan)**
   - Mantıksal sıralama var mı?
   - Geçişler akıcı mı?
   - Paragraflar dengeli mi?

## ÇIKTI FORMATI
Yanıtını tam olarak şu formatta ver:

SKOR: [0-100 arası sayı]

SORUNLAR:
- [sorun 1]
- [sorun 2]
...

ÖNERİLER:
- [öneri 1]
- [öneri 2]
...

ÖZET: [1-2 cümle genel değerlendirme]"""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._parse_critique(response.content[0].text)

        except Exception as e:
            console.print(f"[yellow]Eleştiri hatası: {e}[/yellow]")
            return {
                'score': 75,
                'issues': [],
                'suggestions': [],
                'summary': 'Değerlendirme yapılamadı'
            }

    def _parse_critique(self, response: str) -> Dict[str, Any]:
        """Eleştiri yanıtını parse et."""
        result = {
            'score': 75,
            'issues': [],
            'suggestions': [],
            'summary': ''
        }

        lines = response.strip().split('\n')
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith('SKOR:'):
                try:
                    score_text = line.replace('SKOR:', '').strip()
                    # Sayıyı çıkar
                    import re
                    match = re.search(r'\d+', score_text)
                    if match:
                        result['score'] = min(100, max(0, int(match.group())))
                except (ValueError, AttributeError):
                    # Skor parse edilemedi, varsayilan kullanilacak
                    pass

            elif line.startswith('SORUNLAR:'):
                current_section = 'issues'

            elif line.startswith('ÖNERİLER:'):
                current_section = 'suggestions'

            elif line.startswith('ÖZET:'):
                current_section = 'summary'
                result['summary'] = line.replace('ÖZET:', '').strip()

            elif line.startswith('- ') and current_section:
                item = line[2:].strip()
                if current_section == 'issues':
                    result['issues'].append(item)
                elif current_section == 'suggestions':
                    result['suggestions'].append(item)

        return result

    def _improve_content(
        self,
        content: str,
        section_title: str,
        issues: List[str],
        suggestions: List[str],
        language: str
    ) -> str:
        """İçeriği iyileştir."""

        issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "Belirgin sorun yok"
        suggestions_text = "\n".join(f"- {s}" for s in suggestions) if suggestions else "Özel öneri yok"

        prompt = f"""Sen profesyonel bir rapor editörüsün. Aşağıdaki "{section_title}" bölümünü iyileştir.

## MEVCUT İÇERİK
{content}

## TESPİT EDİLEN SORUNLAR
{issues_text}

## İYİLEŞTİRME ÖNERİLERİ
{suggestions_text}

## TALİMATLAR
1. Tespit edilen sorunları düzelt
2. Önerileri uygula
3. İçeriğin özünü ve uzunluğunu koru
4. Profesyonel ve kurumsal tonu koru
5. Sayısal verileri değiştirme, sadece tutarlılığı sağla
6. Sadece düzeltilmiş içeriği yaz, açıklama ekleme

İYİLEŞTİRİLMİŞ İÇERİK:"""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            revised = response.content[0].text.strip()

            # "İYİLEŞTİRİLMİŞ İÇERİK:" başlığını kaldır
            if revised.startswith("İYİLEŞTİRİLMİŞ İÇERİK:"):
                revised = revised.replace("İYİLEŞTİRİLMİŞ İÇERİK:", "").strip()

            return revised

        except Exception as e:
            console.print(f"[yellow]İyileştirme hatası: {e}[/yellow]")
            return content

    def batch_reflect(
        self,
        sections: Dict[str, str],
        show_progress: bool = True
    ) -> Dict[str, ReflectionResult]:
        """Birden fazla bölümü eleştir ve iyileştir."""
        results = {}

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Self-reflection...", total=len(sections))

                for section_id, content in sections.items():
                    progress.update(task, description=f"Değerlendiriliyor: {section_id}")

                    result = self.reflect_and_improve(
                        content=content,
                        section_title=section_id
                    )
                    results[section_id] = result

                    progress.advance(task)
        else:
            for section_id, content in sections.items():
                results[section_id] = self.reflect_and_improve(
                    content=content,
                    section_title=section_id
                )

        return results

    def get_improvement_summary(
        self,
        results: Dict[str, ReflectionResult]
    ) -> str:
        """İyileştirme özeti oluştur."""
        improved_count = sum(1 for r in results.values() if r.improvement_made)
        avg_score = sum(r.quality_score for r in results.values()) / len(results) if results else 0

        summary = f"""
SELF-REFLECTION ÖZET
====================
Toplam Bölüm: {len(results)}
İyileştirilen: {improved_count}
Ortalama Kalite Skoru: {avg_score:.0f}/100

BÖLÜM DETAYLARI:
"""
        for section_id, result in results.items():
            status = "✓ İyileştirildi" if result.improvement_made else "○ Değişiklik yok"
            summary += f"  - {section_id}: {result.quality_score}/100 {status}\n"

            if result.issues_found:
                summary += f"    Sorunlar: {', '.join(result.issues_found[:2])}...\n"

        return summary
