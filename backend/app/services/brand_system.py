"""브랜드 컬러/로고 처리 유틸"""
from __future__ import annotations
from PIL import Image
from pathlib import Path


def load_logo(logo_path: str, max_height: int = 80) -> Image.Image | None:
    """로고 이미지를 로드하고 높이에 맞춰 리사이즈"""
    if not logo_path or not Path(logo_path).exists():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    ratio = max_height / logo.height
    new_w = int(logo.width * ratio)
    return logo.resize((new_w, max_height), Image.LANCZOS)


def load_logo_small(logo_path: str, max_height: int = 50) -> Image.Image | None:
    """정보 패널용 작은 로고"""
    return load_logo(logo_path, max_height)
