"""사진에서 브랜드 컬러 자동 추출"""
import logging
from PIL import Image

logger = logging.getLogger(__name__)


def extract_dominant_colors(images: list, n_colors: int = 3) -> list[str]:
    """여러 이미지에서 주요 색상 추출 (hex 문자열 리스트 반환)

    Args:
        images: PIL Image 객체 리스트 또는 파일 경로 리스트
        n_colors: 추출할 색상 수
    Returns:
        ["#FF5050", "#2C3E6B", ...] 형태의 hex 색상 리스트
    """
    all_pixels = []

    for img_input in images[:5]:  # 최대 5장
        try:
            if isinstance(img_input, str):
                img = Image.open(img_input).convert("RGB")
            elif isinstance(img_input, Image.Image):
                img = img_input.convert("RGB")
            else:
                continue

            # 성능을 위해 작은 크기로 리사이즈
            img = img.resize((100, 100), Image.LANCZOS)
            pixels = list(img.getdata())
            all_pixels.extend(pixels)
        except Exception as e:
            logger.warning(f"[color_extractor] 이미지 처리 실패: {e}")
            continue

    if not all_pixels:
        return []

    # 너무 어둡거나 밝은 픽셀 제외
    filtered = [(r, g, b) for r, g, b in all_pixels
                if 30 < (r + g + b) / 3 < 230]

    if len(filtered) < 10:
        filtered = all_pixels

    # 간단한 양자화 기반 색상 추출 (K-means 대신 median cut 근사)
    colors = _median_cut(filtered, n_colors)

    # 채도와 명도 기준으로 정렬 (브랜드 컬러에 적합한 순서)
    colors.sort(key=lambda c: _color_score(c), reverse=True)

    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in colors[:n_colors]]


def _median_cut(pixels: list[tuple], n: int) -> list[tuple]:
    """Median cut 양자화로 대표 색상 추출"""
    if n <= 0 or not pixels:
        return []
    if n == 1 or len(pixels) <= 1:
        r = sum(p[0] for p in pixels) // len(pixels)
        g = sum(p[1] for p in pixels) // len(pixels)
        b = sum(p[2] for p in pixels) // len(pixels)
        return [(r, g, b)]

    # 가장 범위가 넓은 채널 찾기
    r_range = max(p[0] for p in pixels) - min(p[0] for p in pixels)
    g_range = max(p[1] for p in pixels) - min(p[1] for p in pixels)
    b_range = max(p[2] for p in pixels) - min(p[2] for p in pixels)

    if r_range >= g_range and r_range >= b_range:
        channel = 0
    elif g_range >= b_range:
        channel = 1
    else:
        channel = 2

    # 해당 채널 기준 정렬 후 중앙에서 분할
    pixels.sort(key=lambda p: p[channel])
    mid = len(pixels) // 2

    left = _median_cut(pixels[:mid], n // 2)
    right = _median_cut(pixels[mid:], n - n // 2)
    return left + right


def _color_score(rgb: tuple) -> float:
    """색상의 브랜드 적합도 점수 (채도 + 적절한 명도)"""
    r, g, b = rgb
    # HSL 변환 간소화
    max_c = max(r, g, b) / 255
    min_c = min(r, g, b) / 255
    l = (max_c + min_c) / 2

    if max_c == min_c:
        s = 0
    elif l <= 0.5:
        s = (max_c - min_c) / (max_c + min_c)
    else:
        s = (max_c - min_c) / (2 - max_c - min_c)

    # 채도 높고, 명도 중간(0.3~0.7)인 색상에 높은 점수
    lightness_score = 1 - abs(l - 0.5) * 2
    return s * 0.7 + lightness_score * 0.3


def extract_colors_from_category(category: str) -> list[str]:
    """업종에 맞는 기본 추천 색상 팔레트"""
    CATEGORY_PALETTES = {
        "음식점": ["#DC3232", "#FF8C00", "#8B4513"],
        "헬스": ["#1E1E1E", "#DC3232", "#FFD700"],
        "뷰티": ["#C8AA8C", "#D4618C", "#8B6B8B"],
        "학원": ["#329650", "#2C5F8A", "#FF8C00"],
        "병원": ["#4A90D9", "#2C5F8A", "#FFFFFF"],
        "안경": ["#E68220", "#2C3E6B", "#333333"],
        "부동산": ["#2C3E6B", "#1A3A5C", "#C9A96E"],
        "골프": ["#1A5C2A", "#2E7D32", "#FFFFFF"],
        "핸드폰": ["#0066CC", "#333333", "#FF3B30"],
        "동물병원": ["#4AADE8", "#FF8C5A", "#2E7D32"],
        "미용실": ["#D4618C", "#8B6B8B", "#333333"],
        "기타": ["#4A4A4A", "#2C5F8A", "#FF8C00"],
    }
    return CATEGORY_PALETTES.get(category, CATEGORY_PALETTES["기타"])
