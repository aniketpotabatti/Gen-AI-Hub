"""Image loading, resizing, and base64 encoding for VLM requests."""

import base64
import binascii
import io
from pathlib import Path

from PIL import Image

from src.schemas.product import ProductInput

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def guess_mime_type(image_path: str | Path | None) -> str:
    """Guess the MIME type from a file suffix; defaults to JPEG."""
    if image_path is None:
        return "image/jpeg"
    return _MIME_BY_SUFFIX.get(Path(image_path).suffix.lower(), "image/jpeg")


def load_image_bytes(product: ProductInput) -> tuple[bytes, str]:
    """Return raw image bytes + MIME type for a product.

    Raises:
        FileNotFoundError: if `image_path` does not exist.
        ValueError: for corrupt images, unsupported formats, or bad base64.
    """
    if product.image_base64:
        try:
            raw = base64.b64decode(product.image_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"Invalid base64 image data: {exc}") from exc
        return raw, guess_mime_type(product.image_path)

    path = Path(product.image_path) if product.image_path else None
    if path is None or not path.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported image format '{path.suffix}'. "
            f"Supported: {sorted(SUPPORTED_SUFFIXES)}"
        )
    data = path.read_bytes()
    _verify_image(data, path)
    return data, guess_mime_type(path)


def _verify_image(data: bytes, path: Path) -> None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise ValueError(f"Corrupt or unreadable image '{path}': {exc}") from exc


def resize_image(data: bytes, max_dim: int = 1024) -> bytes:
    """Downscale an image so its longest side is `max_dim` px (controls cost).

    Returns the original bytes when already small enough. Output is re-encoded
    with the source format when possible, else JPEG.
    """
    with Image.open(io.BytesIO(data)) as image:
        fmt = (image.format or "JPEG").upper()
        if max(image.size) <= max_dim:
            return data
        image = image.convert("RGB")
        image.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buffer = io.BytesIO()
        save_format = fmt if fmt in ("JPEG", "PNG", "WEBP") else "JPEG"
        image.save(buffer, format=save_format)
        return buffer.getvalue()


def encode_base64(data: bytes) -> str:
    """Encode raw image bytes as a base64 string."""
    return base64.b64encode(data).decode("ascii")


def resolve_image(product: ProductInput, max_dim: int = 1024) -> tuple[str, str]:
    """Load + resize a product image; return `(base64_string, mime_type)`."""
    data, mime = load_image_bytes(product)
    return encode_base64(resize_image(data, max_dim=max_dim)), mime


def resolve_image_bytes(product: ProductInput, max_dim: int = 1024) -> tuple[bytes, str]:
    """Load + resize a product image; return `(raw_bytes, mime_type)`."""
    data, mime = load_image_bytes(product)
    return resize_image(data, max_dim=max_dim), mime
