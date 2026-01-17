"""
Progress Reporter Module - Rich terminal progress display

Bu modül terminal'de güzel bir ilerleme gösterimi sağlar.
Rich kütüphanesini kullanır.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TaskID
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

from .phase_tracker import PhaseTracker, GenerationPhase


class ProgressReporter:
    """
    Terminal'de zengin ilerleme gösterimi.

    Gösterir:
    - Mevcut faz ve ilerleme
    - Genel ilerleme çubuğu
    - Faz listesi (tamamlanan, devam eden, bekleyen)
    - Tahmini kalan süre
    """

    # Faz ikonları
    PHASE_ICONS = {
        "pending": "○",
        "in_progress": "◉",
        "completed": "✓",
        "failed": "✗",
        "skipped": "⊘"
    }

    # Faz renkleri
    PHASE_COLORS = {
        "pending": "dim",
        "in_progress": "yellow",
        "completed": "green",
        "failed": "red",
        "skipped": "dim cyan"
    }

    def __init__(self, tracker: PhaseTracker, console: Optional[Console] = None):
        self.tracker = tracker
        self.console = console or Console()
        self.live: Optional[Live] = None
        self.progress: Optional[Progress] = None
        self.main_task: Optional[TaskID] = None
        self.phase_tasks: Dict[GenerationPhase, TaskID] = {}

        # Tracker callback'i kaydet
        self.tracker.add_callback(self._on_progress_update)

    def start(self):
        """İlerleme gösterimini başlat."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
            transient=False
        )

        # Ana görev
        self.main_task = self.progress.add_task(
            "[bold blue]Rapor Üretimi",
            total=100
        )

        self.live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=2,
            transient=False
        )
        self.live.start()

    def _on_progress_update(self, summary: Dict[str, Any]):
        """İlerleme güncellemelerini işle."""
        if self.live:
            self.live.update(self._build_display())

    def _build_display(self) -> Panel:
        """İlerleme panelini oluştur."""
        summary = self.tracker.get_summary()

        # Ana layout
        layout = Layout()

        # Başlık
        current_phase = summary.get("current_phase_description", "Başlatılıyor")
        current_detail = summary.get("current_phase_details", "")
        overall_progress = summary.get("overall_progress", 0)
        remaining = summary.get("remaining_formatted", "hesaplanıyor...")
        elapsed = summary.get("elapsed_formatted", "0:00")

        # Progress bar oluştur
        bar_width = 40
        filled = int(bar_width * overall_progress / 100)
        empty = bar_width - filled
        progress_bar = f"[green]{'█' * filled}[/green][dim]{'░' * empty}[/dim]"

        # Header text
        header = Text()
        header.append("RAPOR ÜRETİMİ\n", style="bold blue")
        header.append(f"\nFaz: ", style="dim")
        header.append(f"{current_phase}\n", style="bold yellow")

        if current_detail:
            header.append(f"     {current_detail}\n", style="dim italic")

        header.append(f"\n{progress_bar} ", style="")
        header.append(f"{overall_progress:.1f}%\n", style="bold")
        header.append(f"\nGeçen: {elapsed} | Kalan: ~{remaining}", style="dim")

        # Faz listesi tablosu
        phase_table = Table(show_header=False, box=None, padding=(0, 1))
        phase_table.add_column("Icon", width=3)
        phase_table.add_column("Phase", width=30)
        phase_table.add_column("Status", width=15)

        phases_data = summary.get("phases", {})
        for phase in GenerationPhase:
            phase_info = phases_data.get(phase.value, {})
            status = phase_info.get("status", "pending")

            icon = self.PHASE_ICONS.get(status, "○")
            color = self.PHASE_COLORS.get(status, "dim")
            description = self.tracker.PHASE_DESCRIPTIONS.get(phase, phase.value)

            # İlerleme göster (devam ediyorsa)
            status_text = ""
            if status == "in_progress":
                progress_pct = phase_info.get("progress_percent", 0)
                status_text = f"{progress_pct:.0f}%"
            elif status == "completed":
                duration = phase_info.get("duration_seconds")
                if duration:
                    if duration < 60:
                        status_text = f"{duration:.0f}s"
                    else:
                        status_text = f"{duration/60:.1f}m"
            elif status == "failed":
                status_text = "HATA"

            phase_table.add_row(
                f"[{color}]{icon}[/{color}]",
                f"[{color}]{description}[/{color}]",
                f"[{color}]{status_text}[/{color}]"
            )

        # Panel oluştur
        content = Table.grid(padding=1)
        content.add_column()
        content.add_row(header)
        content.add_row("")
        content.add_row(phase_table)

        return Panel(
            content,
            title="[bold]Rapor Üretici v4.0[/bold]",
            border_style="blue",
            padding=(1, 2)
        )

    def update(self):
        """Gösterimi güncelle."""
        if self.live:
            self.live.update(self._build_display())

    def stop(self):
        """İlerleme gösterimini durdur."""
        if self.live:
            self.live.stop()
            self.live = None

    def print_summary(self):
        """Son özeti yazdır."""
        summary = self.tracker.get_summary()

        # Sonuç tablosu
        table = Table(title="Rapor Üretimi Tamamlandı", box=None)
        table.add_column("Metrik", style="cyan")
        table.add_column("Değer", style="green")

        table.add_row("Toplam Süre", summary.get("elapsed_formatted", "N/A"))
        table.add_row("Tamamlanan Fazlar", f"{summary.get('completed_phases', 0)}/{summary.get('total_phases', 0)}")

        # Faz süreleri
        phases_data = summary.get("phases", {})
        for phase in GenerationPhase:
            phase_info = phases_data.get(phase.value, {})
            if phase_info.get("status") == "completed":
                duration = phase_info.get("duration_seconds", 0)
                if duration > 5:  # Sadece anlamlı süreleri göster
                    desc = self.tracker.PHASE_DESCRIPTIONS.get(phase, phase.value)
                    if duration < 60:
                        table.add_row(f"  {desc}", f"{duration:.1f}s")
                    else:
                        table.add_row(f"  {desc}", f"{duration/60:.1f}m")

        self.console.print(table)

    def print_error(self, phase: GenerationPhase, error: str):
        """Hata mesajı yazdır."""
        desc = self.tracker.PHASE_DESCRIPTIONS.get(phase, phase.value)
        self.console.print(f"\n[red]✗ HATA ({desc}):[/red] {error}")

    def print_phase_start(self, phase: GenerationPhase):
        """Faz başlangıcını yazdır (live mode dışında)."""
        if not self.live:
            desc = self.tracker.PHASE_DESCRIPTIONS.get(phase, phase.value)
            self.console.print(f"[yellow]◉[/yellow] {desc}...")

    def print_phase_complete(self, phase: GenerationPhase, duration: float = None):
        """Faz tamamlanmasını yazdır (live mode dışında)."""
        if not self.live:
            desc = self.tracker.PHASE_DESCRIPTIONS.get(phase, phase.value)
            duration_str = f" ({duration:.1f}s)" if duration else ""
            self.console.print(f"[green]✓[/green] {desc}{duration_str}")


class SimpleProgressReporter:
    """
    Basit ilerleme raporcusu (Live mode olmadan).

    Daha hafif, ama yine de bilgilendirici.
    """

    def __init__(self, tracker: PhaseTracker, console: Optional[Console] = None):
        self.tracker = tracker
        self.console = console or Console()
        self.tracker.add_callback(self._on_update)
        self.last_phase = None

    def _on_update(self, summary: Dict[str, Any]):
        """İlerleme güncellemesi."""
        current = summary.get("current_phase")

        if current != self.last_phase:
            if self.last_phase:
                # Önceki fazı tamamlandı olarak göster
                self.console.print(f"  [green]✓[/green]")

            # Yeni fazı başlat
            desc = summary.get("current_phase_description", "")
            self.console.print(f"[yellow]◉[/yellow] {desc}...", end="")
            self.last_phase = current

    def start(self):
        """Başlat."""
        self.console.print("\n[bold blue]═══ RAPOR ÜRETİMİ ═══[/bold blue]\n")

    def stop(self):
        """Durdur."""
        if self.last_phase:
            self.console.print(f"  [green]✓[/green]")

        summary = self.tracker.get_summary()
        elapsed = summary.get("elapsed_formatted", "N/A")
        self.console.print(f"\n[green]✓[/green] [bold]Tamamlandı![/bold] (Süre: {elapsed})")
