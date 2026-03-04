"""QR 코드 생성"""
from __future__ import annotations
import qrcode
from PIL import Image


def generate_qr(url: str, size: int = 150) -> Image.Image | None:
    """URL → QR 코드 이미지 생성"""
    if not url:
        return None
    qr = qrcode.QRCode(version=1, box_size=10, border=2,
                        error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((size, size), Image.LANCZOS)
