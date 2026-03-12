"""
Bildverarbeitungs-Utilities für Wappen-Upload
Verwendet Pillow für Resize, Format-Konvertierung und Validierung
"""

import os
import io
from typing import Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Erlaubte Dateiformate
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif"
}

# Upload-Limits aus Environment (mit Defaults)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 5242880))  # 5MB default
CREST_MAX_WIDTH = int(os.getenv("CREST_MAX_WIDTH", 512))
CREST_MAX_HEIGHT = int(os.getenv("CREST_MAX_HEIGHT", 512))


def validate_image_file(
    filename: str,
    content_type: str,
    file_size: int,
    max_file_size: int | None = None
) -> Tuple[bool, str]:
    """
    Validiert hochgeladene Bilddatei.

    Args:
        filename: Dateiname (z.B. "wappen.png")
        content_type: MIME Type (z.B. "image/png")
        file_size: Dateigröße in Bytes

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # Extension prüfen
    extension = filename.lower().split(".")[-1] if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        return False, (
            f"Ungültiges Dateiformat: .{extension}. "
            f"Erlaubt: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # MIME Type prüfen
    if content_type not in ALLOWED_MIME_TYPES:
        return False, (
            f"Ungültiger Content-Type: {content_type}. "
            f"Erlaubte Typen: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # Dateigröße prüfen
    limit = max_file_size if max_file_size is not None else MAX_FILE_SIZE
    if file_size > limit:
        max_mb = limit / (1024 * 1024)
        current_mb = file_size / (1024 * 1024)
        return False, (
            f"Datei zu groß: {current_mb:.2f}MB. "
            f"Maximal erlaubt: {max_mb:.2f}MB"
        )

    return True, ""


async def process_crest_image(
    file_content: bytes,
    max_width: int = CREST_MAX_WIDTH,
    max_height: int = CREST_MAX_HEIGHT
) -> bytes:
    """
    Verarbeitet hochgeladenes Wappen-Bild:
    - Validiert dass es ein Bild ist
    - Resized auf max Dimensionen (Aspect Ratio erhalten)
    - Konvertiert zu WebP (kleinere Dateigröße)
    - Gibt verarbeitete Bytes zurück

    Args:
        file_content: Original-Bilddaten
        max_width: Maximale Breite
        max_height: Maximale Höhe

    Returns:
        bytes: Verarbeitetes Bild als WebP

    Raises:
        ValueError: Wenn Datei kein gültiges Bild ist
    """
    try:
        # Bild aus Bytes laden
        image = Image.open(io.BytesIO(file_content))

        # Validierung: Ist es wirklich ein Bild?
        image.verify()

        # Nochmal laden (verify() schließt das Image)
        image = Image.open(io.BytesIO(file_content))

        # EXIF Orientation korrigieren (bei gedrehten Handy-Fotos)
        image = _fix_image_orientation(image)

        # RGB Mode sicherstellen (WebP braucht RGB)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        # Resize auf max Dimensionen (Aspect Ratio beibehalten)
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        logger.info(
            f"Bild verarbeitet: {image.size[0]}x{image.size[1]}px, "
            f"Format: {image.format}, Mode: {image.mode}"
        )

        # Als WebP exportieren (gute Kompression)
        output = io.BytesIO()
        image.save(
            output,
            format="WEBP",
            quality=85,  # Gute Balance zwischen Qualität und Größe
            method=6     # Beste Kompression (langsamer, aber kleiner)
        )

        output.seek(0)
        return output.read()

    except Exception as e:
        logger.error(f"Fehler bei Bildverarbeitung: {e}")
        raise ValueError(f"Ungültiges Bild oder Fehler bei Verarbeitung: {str(e)}")


def _fix_image_orientation(image: Image.Image) -> Image.Image:
    """
    Korrigiert EXIF Orientation (bei gedrehten Handy-Fotos).

    Args:
        image: PIL Image

    Returns:
        Image mit korrigierter Orientation
    """
    try:
        # EXIF Daten auslesen
        exif = image.getexif()
        if exif is None:
            return image

        # Orientation Tag (274)
        orientation = exif.get(274)

        # Rotation basierend auf EXIF
        rotation_map = {
            3: 180,
            6: 270,
            8: 90
        }

        if orientation in rotation_map:
            degrees = rotation_map[orientation]
            image = image.rotate(degrees, expand=True)
            logger.debug(f"Bild um {degrees}° gedreht (EXIF Orientation {orientation})")

    except Exception as e:
        logger.warning(f"Konnte EXIF Orientation nicht korrigieren: {e}")

    return image


async def process_background_image(
    file_content: bytes,
    max_width: int = 2560,
    max_height: int = 1440
) -> bytes:
    """
    Verarbeitet hochgeladenes Hintergrundbild:
    - Resized auf max 2560x1440 (Aspect Ratio erhalten)
    - Konvertiert zu WebP quality 85
    - EXIF Orientation korrigieren
    """
    try:
        image = Image.open(io.BytesIO(file_content))
        image.verify()
        image = Image.open(io.BytesIO(file_content))
        image = _fix_image_orientation(image)

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        elif image.mode == "RGBA":
            # Backgrounds sollten kein Alpha haben
            image = image.convert("RGB")

        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        logger.info(
            f"Background verarbeitet: {image.size[0]}x{image.size[1]}px, Mode: {image.mode}"
        )

        output = io.BytesIO()
        image.save(output, format="WEBP", quality=85, method=6)
        output.seek(0)
        return output.read()

    except Exception as e:
        logger.error(f"Fehler bei Background-Verarbeitung: {e}")
        raise ValueError(f"Ungültiges Bild oder Fehler bei Verarbeitung: {str(e)}")


def get_file_extension(filename: str) -> str:
    """
    Extrahiert Dateierweiterung aus Filename.

    Args:
        filename: Dateiname

    Returns:
        Extension ohne Punkt (lowercase)
    """
    return filename.lower().split(".")[-1] if "." in filename else ""
