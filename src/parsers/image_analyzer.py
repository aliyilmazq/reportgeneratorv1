"""Görsel analiz modülü - Claude Vision API ile görsel içerik analizi."""

import base64
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import anthropic
except ImportError:
    anthropic = None


@dataclass
class ImageContent:
    """Görsel dosyası içeriği."""
    source: str
    filename: str
    width: int
    height: int
    format: str
    size_bytes: int
    analysis: str = ""
    extracted_text: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ImageAnalyzer:
    """Görsel analiz sınıfı - Claude Vision API kullanır."""

    SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_DIMENSION = 8192

    def __init__(self, api_key: Optional[str] = None):
        if Image is None:
            raise ImportError("Pillow kütüphanesi yüklü değil. 'pip install Pillow' komutunu çalıştırın.")

        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.client = None

        if anthropic is not None and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def parse(self, file_path: str, analyze: bool = True, language: str = "tr") -> ImageContent:
        """Görsel dosyasını oku ve analiz et."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

        content = ImageContent(
            source=str(file_path),
            filename=file_path.name,
            width=0,
            height=0,
            format="",
            size_bytes=file_path.stat().st_size
        )

        try:
            with Image.open(file_path) as img:
                content.width = img.width
                content.height = img.height
                content.format = img.format or file_path.suffix[1:].upper()

                # EXIF metadata
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    content.metadata['exif'] = {str(k): str(v)[:100] for k, v in exif.items() if isinstance(v, (str, int, float))}

        except Exception as e:
            content.metadata['error'] = str(e)

        # Claude Vision ile analiz
        if analyze and self.client:
            try:
                content = self._analyze_with_claude(file_path, content, language)
            except Exception as e:
                content.metadata['analysis_error'] = str(e)

        return content

    def _analyze_with_claude(self, file_path: Path, content: ImageContent, language: str = "tr") -> ImageContent:
        """Claude Vision API ile görsel analizi."""
        if not self.client:
            return content

        # Görseli base64'e çevir
        image_data = self._prepare_image(file_path)
        if not image_data:
            return content

        media_type = f"image/{content.format.lower()}"
        if media_type == "image/jpg":
            media_type = "image/jpeg"

        # Dil ayarı
        if language == "tr":
            prompt = """Bu görseli analiz et ve şu bilgileri Türkçe olarak ver:

1. **Açıklama**: Görselde ne var? Detaylı açıkla.
2. **Metin**: Görselde metin varsa, aynen yaz.
3. **Veri**: Grafik, tablo veya şema varsa, içerdiği verileri listele.
4. **Önemli Noktalar**: Bir raporda kullanılacaksa öne çıkarılması gereken noktalar.

Yanıtını düzenli ve yapılandırılmış şekilde ver."""
        else:
            prompt = """Analyze this image and provide the following information:

1. **Description**: What is in the image? Describe in detail.
2. **Text**: If there is text in the image, transcribe it.
3. **Data**: If there are charts, tables, or diagrams, list the data.
4. **Key Points**: Important points to highlight if used in a report.

Provide a structured response."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            content.analysis = response.content[0].text

            # Analizi parçala
            self._parse_analysis(content)

        except Exception as e:
            content.metadata['api_error'] = str(e)

        return content

    def _prepare_image(self, file_path: Path) -> Optional[str]:
        """Görseli API için hazırla (boyut kontrolü ve base64)."""
        try:
            file_size = file_path.stat().st_size

            # Boyut kontrolü
            if file_size > self.MAX_IMAGE_SIZE:
                # Görseli küçült
                with Image.open(file_path) as img:
                    # Oranı koru
                    ratio = min(self.MAX_DIMENSION / img.width, self.MAX_DIMENSION / img.height)
                    if ratio < 1:
                        new_size = (int(img.width * ratio), int(img.height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)

                    # Geçici buffer'a kaydet
                    import io
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG', optimize=True)
                    buffer.seek(0)
                    return base64.standard_b64encode(buffer.read()).decode('utf-8')

            # Normal boyutlu görsel
            with open(file_path, 'rb') as f:
                return base64.standard_b64encode(f.read()).decode('utf-8')

        except Exception:
            return None

    def _parse_analysis(self, content: ImageContent):
        """Analiz metnini parçala."""
        analysis = content.analysis

        # Metin bölümünü bul
        if "**Metin**" in analysis or "**Text**" in analysis:
            try:
                start = analysis.find("**Metin**") if "**Metin**" in analysis else analysis.find("**Text**")
                end = analysis.find("**", start + 10)
                if end == -1:
                    end = len(analysis)
                text_section = analysis[start:end]
                # Başlığı kaldır
                text_section = text_section.replace("**Metin**:", "").replace("**Text**:", "").strip()
                content.extracted_text = text_section
            except Exception:
                pass

        # Açıklama bölümünü bul
        if "**Açıklama**" in analysis or "**Description**" in analysis:
            try:
                start = analysis.find("**Açıklama**") if "**Açıklama**" in analysis else analysis.find("**Description**")
                end = analysis.find("**", start + 15)
                if end == -1:
                    end = len(analysis)
                desc_section = analysis[start:end]
                desc_section = desc_section.replace("**Açıklama**:", "").replace("**Description**:", "").strip()
                content.description = desc_section
            except Exception:
                pass

    def get_basic_info(self, file_path: str) -> Dict[str, Any]:
        """Sadece temel bilgileri al (API çağrısı yapmadan)."""
        file_path = Path(file_path)

        info = {
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "format": file_path.suffix[1:].upper()
        }

        try:
            with Image.open(file_path) as img:
                info["width"] = img.width
                info["height"] = img.height
                info["mode"] = img.mode
        except Exception:
            pass

        return info

    def to_dict(self, content: ImageContent) -> Dict[str, Any]:
        """ImageContent'i sözlüğe çevir."""
        return {
            "type": "image",
            "source": content.source,
            "filename": content.filename,
            "width": content.width,
            "height": content.height,
            "format": content.format,
            "size_bytes": content.size_bytes,
            "analysis": content.analysis,
            "extracted_text": content.extracted_text,
            "description": content.description,
            "metadata": content.metadata
        }
