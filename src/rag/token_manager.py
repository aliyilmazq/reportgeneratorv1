"""Token Yonetim Modulu - tiktoken ile token sayimi ve context yonetimi."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from rich.console import Console

console = Console()

# tiktoken import
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False


@dataclass
class TokenBudget:
    """Token butcesi."""
    total_available: int
    reserved_for_system: int
    reserved_for_response: int
    available_for_context: int

    def __str__(self) -> str:
        return (
            f"Total: {self.total_available}, "
            f"System: {self.reserved_for_system}, "
            f"Response: {self.reserved_for_response}, "
            f"Available: {self.available_for_context}"
        )


@dataclass
class ContextWindow:
    """Context window bilgisi."""
    documents: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    total_chars: int = 0
    document_count: int = 0
    utilization_ratio: float = 0.0
    truncated: bool = False


# Model context limitleri
MODEL_LIMITS = {
    # Claude 3.x
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    # Claude 4.x
    "claude-opus-4-5-20250514": 200000,
    "claude-sonnet-4-20250514": 200000,
    # Varsayilan
    "default": 100000
}


class TokenManager:
    """Token sayimi ve yonetimi."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.max_tokens = MODEL_LIMITS.get(model, MODEL_LIMITS["default"])
        self.encoding = None

        self._initialize_encoding()

    def _initialize_encoding(self):
        """tiktoken encoding'i baslat."""
        if TIKTOKEN_AVAILABLE:
            try:
                # cl100k_base Claude-benzeri modeller icin uygun
                self.encoding = tiktoken.get_encoding("cl100k_base")
                console.print("[dim]tiktoken aktif (cl100k_base)[/dim]")
            except Exception as e:
                console.print(f"[yellow]tiktoken yuklenemedi: {e}[/yellow]")
                self.encoding = None
        else:
            console.print("[yellow]tiktoken yuklenmemis, tahmin kullanilacak[/yellow]")

    def count_tokens(self, text: str) -> int:
        """Metindeki token sayisini hesapla."""
        if not text:
            return 0

        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception:
                pass

        # Fallback: kelime bazli tahmin
        # Ortalama 1 kelime = 1.3 token (Ingilizce)
        # Turkce icin biraz daha yuksek (1.5)
        words = len(text.split())
        chars = len(text)

        # Hibrit tahmin
        word_estimate = int(words * 1.5)
        char_estimate = int(chars / 3.5)  # Ortalama 3.5 karakter/token

        return max(word_estimate, char_estimate)

    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """Batch halinde token sayimi."""
        return [self.count_tokens(text) for text in texts]

    def calculate_budget(
        self,
        system_prompt: str = "",
        expected_response_tokens: int = 4000,
        safety_margin: float = 0.1
    ) -> TokenBudget:
        """Context icin kullanilabilir token butcesini hesapla."""
        system_tokens = self.count_tokens(system_prompt)

        # Guvenlik marji
        usable_tokens = int(self.max_tokens * (1 - safety_margin))

        available = usable_tokens - system_tokens - expected_response_tokens

        return TokenBudget(
            total_available=self.max_tokens,
            reserved_for_system=system_tokens,
            reserved_for_response=expected_response_tokens,
            available_for_context=max(0, available)
        )

    def estimate_tokens_for_docs(
        self,
        documents: List[Dict[str, Any]],
        text_key: str = "text"
    ) -> int:
        """Dokuman listesi icin toplam token tahmini."""
        total = 0
        for doc in documents:
            text = doc.get(text_key, "")
            total += self.count_tokens(text)
            # Metadata icin ek token
            total += 20  # Ortalama metadata overhead
        return total

    def truncate_to_tokens(
        self,
        text: str,
        max_tokens: int,
        suffix: str = "..."
    ) -> str:
        """Metni belirli token sayisina kisalt."""
        current_tokens = self.count_tokens(text)

        if current_tokens <= max_tokens:
            return text

        # Binary search ile kesme noktasi bul
        left, right = 0, len(text)

        while left < right:
            mid = (left + right) // 2
            truncated = text[:mid] + suffix

            if self.count_tokens(truncated) <= max_tokens:
                left = mid + 1
            else:
                right = mid

        return text[:left - 1] + suffix if left > 0 else suffix


class DynamicContextManager:
    """Dinamik context yonetimi."""

    def __init__(self, token_manager: TokenManager = None):
        self.token_manager = token_manager or TokenManager()

    def build_context(
        self,
        documents: List[Dict[str, Any]],
        system_prompt: str = "",
        max_tokens: int = None,
        text_key: str = "text",
        score_key: str = "score",
        priority_strategy: str = "score"  # score, position, balanced
    ) -> ContextWindow:
        """
        Dinamik olarak context olustur.

        Args:
            documents: Dokuman listesi
            system_prompt: System prompt (token hesabi icin)
            max_tokens: Maksimum token (None = otomatik)
            text_key: Text alani adi
            score_key: Skor alani adi
            priority_strategy: Onceliklendirme stratejisi
        """
        if not documents:
            return ContextWindow()

        # Token butcesi hesapla
        budget = self.token_manager.calculate_budget(system_prompt)
        available_tokens = max_tokens or budget.available_for_context

        # Strateiye gore sirala
        sorted_docs = self._sort_by_priority(documents, score_key, priority_strategy)

        # Context olustur
        selected_docs = []
        used_tokens = 0
        truncated = False

        for doc in sorted_docs:
            text = doc.get(text_key, "")
            doc_tokens = self.token_manager.count_tokens(text)

            if used_tokens + doc_tokens <= available_tokens:
                selected_docs.append(doc)
                used_tokens += doc_tokens
            elif used_tokens + 100 <= available_tokens:
                # Kalan alana sigacak kadar ekle
                remaining_tokens = available_tokens - used_tokens - 50  # Buffer
                truncated_text = self.token_manager.truncate_to_tokens(
                    text, remaining_tokens
                )
                truncated_doc = {**doc, text_key: truncated_text}
                selected_docs.append(truncated_doc)
                used_tokens += self.token_manager.count_tokens(truncated_text)
                truncated = True
                break
            else:
                break

        # Toplam karakter sayisi
        total_chars = sum(len(doc.get(text_key, "")) for doc in selected_docs)

        return ContextWindow(
            documents=selected_docs,
            total_tokens=used_tokens,
            total_chars=total_chars,
            document_count=len(selected_docs),
            utilization_ratio=used_tokens / available_tokens if available_tokens > 0 else 0,
            truncated=truncated
        )

    def _sort_by_priority(
        self,
        documents: List[Dict[str, Any]],
        score_key: str,
        strategy: str
    ) -> List[Dict[str, Any]]:
        """Oncelik stratejisine gore sirala."""
        if strategy == "score":
            # Yuksek skorlu once
            return sorted(
                documents,
                key=lambda x: x.get(score_key, 0),
                reverse=True
            )
        elif strategy == "position":
            # Pozisyona gore (orijinal sira)
            return documents
        elif strategy == "balanced":
            # Skor ve pozisyon dengesi
            return sorted(
                documents,
                key=lambda x: (x.get(score_key, 0) * 0.7) + (1 / (x.get("position", 1) + 1) * 0.3),
                reverse=True
            )
        else:
            return documents

    def format_context(
        self,
        context_window: ContextWindow,
        text_key: str = "text",
        source_key: str = "source",
        score_key: str = "score",
        include_metadata: bool = True,
        format_style: str = "numbered"  # numbered, markdown, simple
    ) -> str:
        """Context'i formatlayarak string'e donustur."""
        if not context_window.documents:
            return ""

        parts = []

        if format_style == "markdown":
            parts.append("## Ilgili Dokumanlar\n")

        for i, doc in enumerate(context_window.documents, 1):
            text = doc.get(text_key, "")
            source = doc.get(source_key, "Bilinmeyen")
            score = doc.get(score_key, 0)

            if format_style == "numbered":
                header = f"[{i}] "
                if include_metadata:
                    header += f"(Kaynak: {source}, Skor: {score:.2f})"
                parts.append(f"{header}\n{text}\n")

            elif format_style == "markdown":
                parts.append(f"### Kaynak {i}")
                if include_metadata:
                    parts.append(f"*Kaynak: {source} | Skor: {score:.2f}*\n")
                parts.append(f"{text}\n")

            else:  # simple
                parts.append(f"{text}\n")

        # Footer
        if include_metadata:
            parts.append(f"\n---\nToplam: {context_window.document_count} dokuman, "
                        f"{context_window.total_tokens} token")

        return "\n".join(parts)

    def sliding_window_context(
        self,
        long_document: str,
        window_size: int = 4000,
        overlap: int = 500
    ) -> List[str]:
        """Sliding window ile uzun dokumani parcala."""
        if not long_document:
            return []

        doc_tokens = self.token_manager.count_tokens(long_document)

        if doc_tokens <= window_size:
            return [long_document]

        windows = []
        step = window_size - overlap

        # Karakter bazli sliding window
        char_window = int(window_size * 4)  # Tahmini karakter/token orani
        char_step = int(step * 4)

        for i in range(0, len(long_document), char_step):
            window = long_document[i:i + char_window]
            if window.strip():
                windows.append(window)

            # Son window'a ulastik mi kontrol et
            if i + char_window >= len(long_document):
                break

        return windows


class ContextOptimizer:
    """Context optimizasyonu icin yardimci sinif."""

    def __init__(self, token_manager: TokenManager = None):
        self.token_manager = token_manager or TokenManager()

    def deduplicate_context(
        self,
        documents: List[Dict[str, Any]],
        text_key: str = "text",
        similarity_threshold: float = 0.9
    ) -> List[Dict[str, Any]]:
        """Benzer dokumanlari cikar."""
        if not documents:
            return []

        unique_docs = []
        seen_texts = set()

        for doc in documents:
            text = doc.get(text_key, "")
            # Basit hash-bazli deduplication
            text_hash = hash(text.lower().strip()[:200])

            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_docs.append(doc)

        return unique_docs

    def merge_overlapping_chunks(
        self,
        chunks: List[Dict[str, Any]],
        text_key: str = "text"
    ) -> List[Dict[str, Any]]:
        """Overlapping chunk'lari birlestir."""
        if len(chunks) <= 1:
            return chunks

        merged = []
        current = chunks[0]

        for next_chunk in chunks[1:]:
            current_text = current.get(text_key, "")
            next_text = next_chunk.get(text_key, "")

            # Overlap kontrolu (son 100 karakter)
            overlap_len = min(100, len(current_text), len(next_text))
            if current_text[-overlap_len:] in next_text[:overlap_len * 2]:
                # Birlestir
                merged_text = current_text + next_text[overlap_len:]
                current = {**current, text_key: merged_text}
            else:
                merged.append(current)
                current = next_chunk

        merged.append(current)
        return merged

    def prioritize_by_section(
        self,
        documents: List[Dict[str, Any]],
        section_id: str,
        category_key: str = "estimated_category"
    ) -> List[Dict[str, Any]]:
        """Bolume gore onceliklendirme."""
        section_categories = {
            "yonetici_ozeti": ["finansal", "pazar"],
            "pazar_analizi": ["pazar"],
            "finansal_projeksiyonlar": ["finansal"],
            "risk_analizi": ["risk"],
            "operasyon_plani": ["operasyon"],
        }

        preferred = section_categories.get(section_id, [])

        if not preferred:
            return documents

        # Oncelikli kategorileri one al
        prioritized = []
        others = []

        for doc in documents:
            category = doc.get(category_key)
            if category in preferred:
                prioritized.append(doc)
            else:
                others.append(doc)

        return prioritized + others
