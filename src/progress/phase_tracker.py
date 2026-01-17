"""
Phase Tracker Module - Tracks report generation phases

Bu modül rapor üretiminin her fazını takip eder ve
tahmini süre hesaplar.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class GenerationPhase(Enum):
    """Rapor üretim fazları."""
    INITIALIZATION = "initialization"
    FILE_SCANNING = "file_scanning"
    FILE_PARSING = "file_parsing"
    RAG_INDEXING = "rag_indexing"
    WEB_RESEARCH = "web_research"
    DATA_COLLECTION = "data_collection"
    CONTENT_PLANNING = "content_planning"
    SECTION_GENERATION = "section_generation"
    VALIDATION = "validation"
    ENHANCEMENT = "enhancement"
    CHART_GENERATION = "chart_generation"
    DOCUMENT_GENERATION = "document_generation"
    COMPLETION = "completion"


@dataclass
class PhaseStatus:
    """Tek bir fazın durumu."""
    phase: GenerationPhase
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    progress_percent: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    details: str = ""
    sub_tasks: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    def duration(self) -> Optional[timedelta]:
        """Faz süresini hesapla."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return datetime.now() - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        duration = self.duration()
        return {
            "phase": self.phase.value,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration.total_seconds() if duration else None,
            "details": self.details,
            "sub_tasks": self.sub_tasks,
            "error_message": self.error_message
        }


class PhaseTracker:
    """
    Rapor üretim fazlarını takip eden sınıf.

    Her faz için:
    - Başlama/bitiş zamanı
    - İlerleme yüzdesi
    - Tahmini kalan süre
    """

    # Faz süresi tahminleri (saniye)
    PHASE_ESTIMATES = {
        GenerationPhase.INITIALIZATION: 5,
        GenerationPhase.FILE_SCANNING: 10,
        GenerationPhase.FILE_PARSING: 60,
        GenerationPhase.RAG_INDEXING: 30,
        GenerationPhase.WEB_RESEARCH: 600,  # 10 dakika
        GenerationPhase.DATA_COLLECTION: 120,  # 2 dakika
        GenerationPhase.CONTENT_PLANNING: 60,
        GenerationPhase.SECTION_GENERATION: 1200,  # 20 dakika
        GenerationPhase.VALIDATION: 120,
        GenerationPhase.ENHANCEMENT: 180,
        GenerationPhase.CHART_GENERATION: 60,
        GenerationPhase.DOCUMENT_GENERATION: 30,
        GenerationPhase.COMPLETION: 5
    }

    # Faz açıklamaları (Türkçe)
    PHASE_DESCRIPTIONS = {
        GenerationPhase.INITIALIZATION: "Başlatılıyor",
        GenerationPhase.FILE_SCANNING: "Dosyalar taranıyor",
        GenerationPhase.FILE_PARSING: "Dosyalar işleniyor",
        GenerationPhase.RAG_INDEXING: "İçerik indeksleniyor",
        GenerationPhase.WEB_RESEARCH: "Web araştırması yapılıyor",
        GenerationPhase.DATA_COLLECTION: "Veriler toplanıyor",
        GenerationPhase.CONTENT_PLANNING: "İçerik planlanıyor",
        GenerationPhase.SECTION_GENERATION: "Bölümler üretiliyor",
        GenerationPhase.VALIDATION: "Doğrulama yapılıyor",
        GenerationPhase.ENHANCEMENT: "İçerik zenginleştiriliyor",
        GenerationPhase.CHART_GENERATION: "Grafikler oluşturuluyor",
        GenerationPhase.DOCUMENT_GENERATION: "Belge oluşturuluyor",
        GenerationPhase.COMPLETION: "Tamamlandı"
    }

    def __init__(self):
        self.phases: Dict[GenerationPhase, PhaseStatus] = {}
        self.phase_order: List[GenerationPhase] = list(GenerationPhase)
        self.current_phase: Optional[GenerationPhase] = None
        self.start_time: Optional[datetime] = None
        self.callbacks: List[callable] = []

        # Tüm fazları başlat
        for phase in GenerationPhase:
            self.phases[phase] = PhaseStatus(phase=phase)

    def add_callback(self, callback: callable):
        """İlerleme callback'i ekle."""
        self.callbacks.append(callback)

    def _notify_callbacks(self):
        """Tüm callback'leri bilgilendir."""
        for callback in self.callbacks:
            try:
                callback(self.get_summary())
            except Exception as e:
                print(f"Callback hatası: {e}")

    def start_phase(self, phase: GenerationPhase, details: str = "") -> PhaseStatus:
        """Bir fazı başlat."""
        if self.start_time is None:
            self.start_time = datetime.now()

        status = self.phases[phase]
        status.status = "in_progress"
        status.start_time = datetime.now()
        status.progress_percent = 0.0
        status.details = details or self.PHASE_DESCRIPTIONS.get(phase, "")

        self.current_phase = phase

        self._notify_callbacks()
        return status

    def update_progress(
        self,
        phase: GenerationPhase,
        progress: float,
        details: str = ""
    ):
        """Faz ilerlemesini güncelle."""
        if phase not in self.phases:
            return

        status = self.phases[phase]
        status.progress_percent = min(max(progress, 0), 100)

        if details:
            status.details = details

        self._notify_callbacks()

    def add_subtask(
        self,
        phase: GenerationPhase,
        task_name: str,
        completed: bool = False
    ):
        """Faza alt görev ekle."""
        if phase not in self.phases:
            return

        status = self.phases[phase]
        status.sub_tasks.append({
            "name": task_name,
            "completed": completed,
            "timestamp": datetime.now().isoformat()
        })

    def complete_phase(
        self,
        phase: GenerationPhase,
        success: bool = True,
        message: str = ""
    ) -> PhaseStatus:
        """Fazı tamamla."""
        status = self.phases[phase]
        status.end_time = datetime.now()
        status.progress_percent = 100.0

        if success:
            status.status = "completed"
            status.details = message or "Tamamlandı"
        else:
            status.status = "failed"
            status.error_message = message

        # Sonraki faza geç
        current_idx = self.phase_order.index(phase)
        if current_idx < len(self.phase_order) - 1:
            self.current_phase = self.phase_order[current_idx + 1]
        else:
            self.current_phase = None

        self._notify_callbacks()
        return status

    def skip_phase(self, phase: GenerationPhase, reason: str = ""):
        """Fazı atla."""
        status = self.phases[phase]
        status.status = "skipped"
        status.details = reason or "Atlandı"
        status.progress_percent = 100.0

        self._notify_callbacks()

    def fail_phase(self, phase: GenerationPhase, error: str):
        """Fazı başarısız olarak işaretle."""
        status = self.phases[phase]
        status.status = "failed"
        status.error_message = error
        status.end_time = datetime.now()

        self._notify_callbacks()

    def get_current_phase(self) -> Optional[PhaseStatus]:
        """Mevcut fazı getir."""
        if self.current_phase:
            return self.phases[self.current_phase]
        return None

    def get_completed_phases(self) -> List[PhaseStatus]:
        """Tamamlanan fazları getir."""
        return [
            s for s in self.phases.values()
            if s.status == "completed"
        ]

    def get_pending_phases(self) -> List[PhaseStatus]:
        """Bekleyen fazları getir."""
        return [
            s for s in self.phases.values()
            if s.status == "pending"
        ]

    def get_overall_progress(self) -> float:
        """Genel ilerleme yüzdesini hesapla."""
        total_weight = sum(self.PHASE_ESTIMATES.values())
        completed_weight = 0

        for phase, status in self.phases.items():
            phase_weight = self.PHASE_ESTIMATES.get(phase, 60)

            if status.status == "completed":
                completed_weight += phase_weight
            elif status.status == "in_progress":
                completed_weight += phase_weight * (status.progress_percent / 100)
            elif status.status == "skipped":
                completed_weight += phase_weight

        return (completed_weight / total_weight) * 100 if total_weight > 0 else 0

    def get_elapsed_time(self) -> Optional[timedelta]:
        """Geçen süreyi hesapla."""
        if self.start_time:
            return datetime.now() - self.start_time
        return None

    def get_estimated_remaining(self) -> timedelta:
        """Tahmini kalan süreyi hesapla."""
        remaining_seconds = 0

        for phase, status in self.phases.items():
            estimate = self.PHASE_ESTIMATES.get(phase, 60)

            if status.status == "pending":
                remaining_seconds += estimate
            elif status.status == "in_progress":
                remaining_pct = 1 - (status.progress_percent / 100)
                remaining_seconds += estimate * remaining_pct

        return timedelta(seconds=remaining_seconds)

    def get_estimated_total(self) -> timedelta:
        """Tahmini toplam süreyi hesapla."""
        return timedelta(seconds=sum(self.PHASE_ESTIMATES.values()))

    def get_summary(self) -> Dict[str, Any]:
        """Durum özetini getir."""
        elapsed = self.get_elapsed_time()
        remaining = self.get_estimated_remaining()

        return {
            "current_phase": self.current_phase.value if self.current_phase else None,
            "current_phase_description": self.PHASE_DESCRIPTIONS.get(self.current_phase, "") if self.current_phase else "",
            "current_phase_progress": self.phases[self.current_phase].progress_percent if self.current_phase else 0,
            "current_phase_details": self.phases[self.current_phase].details if self.current_phase else "",
            "overall_progress": self.get_overall_progress(),
            "elapsed_seconds": elapsed.total_seconds() if elapsed else 0,
            "elapsed_formatted": self._format_duration(elapsed) if elapsed else "0:00",
            "remaining_seconds": remaining.total_seconds(),
            "remaining_formatted": self._format_duration(remaining),
            "completed_phases": len(self.get_completed_phases()),
            "total_phases": len(self.phase_order),
            "phases": {
                phase.value: status.to_dict()
                for phase, status in self.phases.items()
            }
        }

    def _format_duration(self, duration: timedelta) -> str:
        """Süreyi formatla."""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def reset(self):
        """Tracker'ı sıfırla."""
        self.start_time = None
        self.current_phase = None

        for phase in GenerationPhase:
            self.phases[phase] = PhaseStatus(phase=phase)
