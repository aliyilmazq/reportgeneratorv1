"""Yardımcı fonksiyonlar."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict


def load_yaml(file_path: str) -> Dict[str, Any]:
    """YAML dosyasını yükle."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ensure_dir(path: str) -> Path:
    """Klasörün var olduğundan emin ol, yoksa oluştur."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def format_size(size_bytes: int) -> str:
    """Dosya boyutunu okunabilir formata çevir."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_file_extension(file_path: str) -> str:
    """Dosya uzantısını al (küçük harf)."""
    return Path(file_path).suffix.lower()


def sanitize_filename(filename: str) -> str:
    """Dosya adını güvenli hale getir."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def truncate_text(text: str, max_length: int = 100) -> str:
    """Metni belirli uzunlukta kes."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
