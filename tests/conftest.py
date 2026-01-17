"""Pytest fixtures ve konfigurasyonlari."""

import pytest
import sys
from pathlib import Path
from typing import List, Dict, Any

# Proje root'u path'e ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================
# Sample Data Fixtures
# ============================================================

@pytest.fixture
def sample_turkish_text() -> str:
    """Turkce ornek metin."""
    return """
    Şirketimiz 2024 yılında %15 büyüme hedeflemektedir. Pazar analizi sonuçlarına göre,
    e-ticaret sektörü Türkiye'de hızla büyümektedir. Toplam pazar büyüklüğü 50 milyar TL'ye
    ulaşmıştır. Rekabet analizi göstermektedir ki, sektörde 3 ana oyuncu bulunmaktadır.

    Finansal projeksiyonlarımıza göre, 2024 yılında 10 milyon TL gelir elde etmeyi
    hedefliyoruz. Maliyet yapımız optimize edilmiş olup, brüt kar marjımız %40 seviyesindedir.

    Operasyonel süreçlerimiz verimli çalışmaktadır. Tedarik zinciri yönetimi ve lojistik
    operasyonları başarıyla yürütülmektedir.
    """


@pytest.fixture
def sample_english_text() -> str:
    """Ingilizce ornek metin."""
    return """
    Our company targets 15% growth in 2024. According to market analysis results,
    the e-commerce sector is growing rapidly. The total market size has reached
    $500 million. Competition analysis shows that there are 3 main players in the sector.

    According to our financial projections, we aim to generate $10 million in revenue
    in 2024. Our cost structure is optimized with a gross profit margin of 40%.
    """


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Ornek dokuman listesi."""
    return [
        {
            "text": "E-ticaret sektörü Türkiye'de yıllık %25 büyüme göstermektedir.",
            "source": "pazar_raporu.pdf",
            "type": "text"
        },
        {
            "text": "2024 yılı bütçe projeksiyonu 15 milyon TL olarak belirlenmiştir.",
            "source": "butce_2024.xlsx",
            "type": "text"
        },
        {
            "text": "Rakip analizi sonucunda 5 ana rekabet avantajı tespit edilmiştir.",
            "source": "rekabet_analizi.docx",
            "type": "text"
        },
        {
            "text": "Operasyonel verimlilik %20 artırılmıştır.",
            "source": "operasyon_raporu.pdf",
            "type": "text"
        },
        {
            "text": "Müşteri memnuniyet oranı %92 seviyesine ulaşmıştır.",
            "source": "musteri_anketi.pdf",
            "type": "text"
        }
    ]


@pytest.fixture
def sample_chunks() -> List[Dict[str, Any]]:
    """Ornek chunk listesi."""
    return [
        {"text": "Pazar büyüklüğü 50 milyar TL.", "score": 0.85, "source": "doc1"},
        {"text": "Yıllık büyüme oranı %15.", "score": 0.78, "source": "doc2"},
        {"text": "Rakip sayısı 3.", "score": 0.65, "source": "doc3"},
        {"text": "Müşteri sayısı 100.000.", "score": 0.60, "source": "doc4"},
    ]


# ============================================================
# Mock Fixtures
# ============================================================

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    class MockMessage:
        def __init__(self, text):
            self.text = text

    class MockContent:
        def __init__(self, text):
            self.content = [MockMessage(text)]

    class MockClient:
        class Messages:
            def create(self, **kwargs):
                return MockContent("Bu bir test ozetidir.")

        def __init__(self):
            self.messages = self.Messages()

    return MockClient()


@pytest.fixture
def mock_embeddings():
    """Mock embedding vektorleri."""
    import random
    return [[random.random() for _ in range(384)] for _ in range(10)]


# ============================================================
# Configuration Fixtures
# ============================================================

@pytest.fixture
def rag_config_dict() -> Dict[str, Any]:
    """RAG konfigurasyon dict."""
    return {
        "embedding": {
            "model": "paraphrase-multilingual-MiniLM-L12-v2",
            "dimension": 384,
            "batch_size": 16
        },
        "chunking": {
            "strategy": "semantic",
            "chunk_size": 500,
            "chunk_overlap": 100
        },
        "hybrid_search": {
            "enabled": True,
            "semantic_weight": 0.6,
            "bm25_weight": 0.4
        }
    }


# ============================================================
# Temporary Directory Fixtures
# ============================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Gecici dizin."""
    return tmp_path


@pytest.fixture
def temp_config_file(tmp_path, rag_config_dict):
    """Gecici konfigurasyon dosyasi."""
    import yaml

    config_file = tmp_path / "rag_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(rag_config_dict, f)

    return config_file
