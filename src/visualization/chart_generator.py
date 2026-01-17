"""Grafik Üretici Modülü - Otomatik grafik oluşturma."""

import os
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import tempfile

try:
    import matplotlib
    matplotlib.use('Agg')  # GUI olmadan çalış
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
except ImportError:
    plt = None

try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    go = None
    px = None

from rich.console import Console

console = Console()


@dataclass
class ChartData:
    """Grafik verisi."""
    chart_type: str  # pie, bar, line, table, waterfall
    title: str
    labels: List[str]
    values: List[float]
    secondary_values: List[float] = None
    colors: List[str] = None
    unit: str = ""
    source: str = ""


@dataclass
class GeneratedChart:
    """Oluşturulan grafik."""
    chart_type: str
    title: str
    file_path: str
    width: int
    height: int
    format: str  # png, svg


class ChartGenerator:
    """Grafik üretici sınıfı."""

    # Kurumsal renk paleti
    CORPORATE_COLORS = [
        '#1a365d',  # Koyu mavi
        '#2c5282',  # Orta mavi
        '#3182ce',  # Açık mavi
        '#4299e1',  # Parlak mavi
        '#63b3ed',  # Soft mavi
        '#90cdf4',  # Çok açık mavi
        '#2d3748',  # Koyu gri
        '#4a5568',  # Orta gri
        '#718096',  # Açık gri
        '#38a169',  # Yeşil (pozitif)
        '#e53e3e',  # Kırmızı (negatif)
    ]

    def __init__(self, output_dir: str = None, use_plotly: bool = True):
        self.output_dir = output_dir or tempfile.mkdtemp()
        self.use_plotly = use_plotly and go is not None
        self.charts_generated = []

        # Matplotlib Türkçe font ayarı
        if plt:
            try:
                plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
            except (KeyError, ValueError) as e:
                # Font ayari yapilamadi, varsayilan kullanilacak
                pass

        os.makedirs(self.output_dir, exist_ok=True)

    def extract_chart_data(self, content: str, section_id: str) -> List[ChartData]:
        """İçerikten grafik verisi çıkar."""
        charts = []

        # Markdown tablolarını bul
        table_pattern = r'\|([^\n]+)\|\n\|[-:\s|]+\|\n((?:\|[^\n]+\|\n?)+)'

        for match in re.finditer(table_pattern, content):
            header_line = match.group(1)
            data_lines = match.group(2)

            headers = [h.strip() for h in header_line.split('|') if h.strip()]
            rows = []

            for line in data_lines.strip().split('\n'):
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells:
                    rows.append(cells)

            # Tablo türünü belirle ve grafiğe dönüştür
            chart_data = self._table_to_chart(headers, rows, section_id)
            if chart_data:
                charts.append(chart_data)

        # Yüzde dağılımlarını bul
        percentage_pattern = r'(\w[\w\s]+):\s*%?\s*([\d.,]+)\s*%'
        percentage_matches = re.findall(percentage_pattern, content)

        if len(percentage_matches) >= 3:
            labels = [m[0].strip() for m in percentage_matches]
            values = [float(m[1].replace(',', '.')) for m in percentage_matches]

            charts.append(ChartData(
                chart_type='pie',
                title=f'{section_id} Dağılımı',
                labels=labels,
                values=values
            ))

        return charts

    def _table_to_chart(
        self,
        headers: List[str],
        rows: List[List[str]],
        section_id: str
    ) -> Optional[ChartData]:
        """Tabloyu grafik verisine dönüştür."""
        if len(headers) < 2 or len(rows) < 2:
            return None

        # İlk sütun label, ikinci sütun değer varsay
        labels = []
        values = []

        for row in rows:
            if len(row) >= 2:
                labels.append(row[0])
                # Sayısal değeri çıkar
                try:
                    val_str = row[1].replace('%', '').replace(',', '.').replace('.', '', row[1].count('.') - 1)
                    val_str = re.sub(r'[^\d.]', '', val_str)
                    if val_str:
                        values.append(float(val_str))
                    else:
                        values.append(0)
                except (ValueError, IndexError, AttributeError):
                    # Gecersiz sayi formati veya eksik veri
                    values.append(0)

        if not values or sum(values) == 0:
            return None

        # Grafik türünü belirle
        if '%' in str(rows) or sum(values) <= 100:
            chart_type = 'pie'
        elif len(rows) > 4:
            chart_type = 'bar'
        else:
            chart_type = 'bar'

        return ChartData(
            chart_type=chart_type,
            title=headers[0] if headers else section_id,
            labels=labels,
            values=values,
            unit='%' if '%' in str(rows) else ''
        )

    def generate(self, chart_data: ChartData, filename: str = None) -> Optional[GeneratedChart]:
        """Grafik oluştur."""
        if not filename:
            filename = f"chart_{len(self.charts_generated) + 1}"

        if self.use_plotly:
            return self._generate_plotly(chart_data, filename)
        elif plt:
            return self._generate_matplotlib(chart_data, filename)
        else:
            console.print("[yellow]Grafik kütüphanesi yüklü değil[/yellow]")
            return None

    def _generate_plotly(self, data: ChartData, filename: str) -> Optional[GeneratedChart]:
        """Plotly ile grafik oluştur."""
        try:
            fig = None

            if data.chart_type == 'pie':
                fig = go.Figure(data=[go.Pie(
                    labels=data.labels,
                    values=data.values,
                    marker=dict(colors=self.CORPORATE_COLORS[:len(data.labels)]),
                    textinfo='label+percent',
                    hole=0.3
                )])

            elif data.chart_type == 'bar':
                fig = go.Figure(data=[go.Bar(
                    x=data.labels,
                    y=data.values,
                    marker_color=self.CORPORATE_COLORS[0],
                    text=data.values,
                    textposition='outside'
                )])

            elif data.chart_type == 'line':
                fig = go.Figure(data=[go.Scatter(
                    x=data.labels,
                    y=data.values,
                    mode='lines+markers',
                    line=dict(color=self.CORPORATE_COLORS[0], width=3),
                    marker=dict(size=10)
                )])

            if fig:
                fig.update_layout(
                    title=dict(text=data.title, font=dict(size=16)),
                    font=dict(family="Arial, sans-serif"),
                    showlegend=True if data.chart_type == 'pie' else False,
                    template='plotly_white',
                    margin=dict(l=40, r=40, t=60, b=40)
                )

                # PNG olarak kaydet
                file_path = os.path.join(self.output_dir, f"{filename}.png")

                try:
                    fig.write_image(file_path, width=800, height=500, scale=2)
                except Exception as e:
                    # Kaleido yoksa HTML kaydet
                    file_path = os.path.join(self.output_dir, f"{filename}.html")
                    fig.write_html(file_path)
                    console.print(f"[yellow]PNG kaydedilemedi, HTML olarak kaydedildi: {e}[/yellow]")

                chart = GeneratedChart(
                    chart_type=data.chart_type,
                    title=data.title,
                    file_path=file_path,
                    width=800,
                    height=500,
                    format=file_path.split('.')[-1]
                )
                self.charts_generated.append(chart)
                return chart

        except Exception as e:
            console.print(f"[red]Plotly grafik hatası: {e}[/red]")
            return None

    def _generate_matplotlib(self, data: ChartData, filename: str) -> Optional[GeneratedChart]:
        """Matplotlib ile grafik oluştur."""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            if data.chart_type == 'pie':
                ax.pie(
                    data.values,
                    labels=data.labels,
                    autopct='%1.1f%%',
                    colors=self.CORPORATE_COLORS[:len(data.labels)],
                    startangle=90
                )
                ax.axis('equal')

            elif data.chart_type == 'bar':
                bars = ax.bar(
                    data.labels,
                    data.values,
                    color=self.CORPORATE_COLORS[0]
                )
                ax.bar_label(bars, fmt='%.1f')
                plt.xticks(rotation=45, ha='right')

            elif data.chart_type == 'line':
                ax.plot(
                    data.labels,
                    data.values,
                    marker='o',
                    color=self.CORPORATE_COLORS[0],
                    linewidth=2,
                    markersize=8
                )
                plt.xticks(rotation=45, ha='right')

            ax.set_title(data.title, fontsize=14, fontweight='bold')
            plt.tight_layout()

            file_path = os.path.join(self.output_dir, f"{filename}.png")
            plt.savefig(file_path, dpi=150, bbox_inches='tight')
            plt.close()

            chart = GeneratedChart(
                chart_type=data.chart_type,
                title=data.title,
                file_path=file_path,
                width=800,
                height=500,
                format='png'
            )
            self.charts_generated.append(chart)
            return chart

        except Exception as e:
            console.print(f"[red]Matplotlib grafik hatası: {e}[/red]")
            return None

    def generate_from_content(
        self,
        content: Dict[str, str],
        max_charts: int = 10
    ) -> List[GeneratedChart]:
        """İçerikten otomatik grafik oluştur."""
        all_charts = []

        for section_id, section_content in content.items():
            if not section_content:
                continue

            chart_data_list = self.extract_chart_data(section_content, section_id)

            for chart_data in chart_data_list[:2]:  # Bölüm başına max 2 grafik
                chart = self.generate(chart_data, f"{section_id}_{len(all_charts)}")
                if chart:
                    all_charts.append(chart)

                if len(all_charts) >= max_charts:
                    break

            if len(all_charts) >= max_charts:
                break

        console.print(f"[green]✓ {len(all_charts)} grafik oluşturuldu[/green]")
        return all_charts

    def get_chart_paths(self) -> List[str]:
        """Oluşturulan grafik yollarını döndür."""
        return [c.file_path for c in self.charts_generated]

    def cleanup(self):
        """Geçici dosyaları temizle."""
        import shutil
        try:
            shutil.rmtree(self.output_dir)
        except (OSError, PermissionError) as e:
            # Dizin silinemedi (kullanımda veya izin yok)
            pass
