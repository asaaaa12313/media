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
    """업종에 맞는 기본 추천 색상 팔레트 (5색)"""
    CATEGORY_PALETTES = {
        "음식점": ["#DC3232", "#FF8C00", "#8B4513", "#FFD700", "#2C1810"],
        "헬스": ["#1E1E1E", "#DC3232", "#FFD700", "#333333", "#FF4444"],
        "뷰티": ["#C8AA8C", "#D4618C", "#8B6B8B", "#F5E6DA", "#A0526B"],
        "학원": ["#329650", "#2C5F8A", "#FF8C00", "#1A3D5C", "#FFB347"],
        "병원": ["#4A90D9", "#2C5F8A", "#5CB8E6", "#1A3A5C", "#87CEEB"],
        "안경": ["#E68220", "#2C3E6B", "#333333", "#F5A623", "#1A2744"],
        "부동산": ["#2C3E6B", "#1A3A5C", "#C9A96E", "#4A6B8A", "#8B7D4A"],
        "골프": ["#1A5C2A", "#2E7D32", "#4CAF50", "#0D3318", "#81C784"],
        "핸드폰": ["#0066CC", "#333333", "#FF3B30", "#004499", "#FF6B60"],
        "동물병원": ["#4AADE8", "#FF8C5A", "#2E7D32", "#2888C4", "#FFB088"],
        "미용실": ["#D4618C", "#8B6B8B", "#333333", "#F08CB4", "#5C4A5C"],
        "기타": ["#4A4A4A", "#2C5F8A", "#FF8C00", "#666666", "#1A3D5C"],
    }
    return CATEGORY_PALETTES.get(category, CATEGORY_PALETTES["기타"])


# --- 색상 팔레트 생성 (coolors.co 스타일) ---

def _hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    """Hex → HSL (h: 0-360, s: 0-1, l: 0-1)"""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16) / 255, int(hex_color[2:4], 16) / 255, int(hex_color[4:6], 16) / 255
    max_c, min_c = max(r, g, b), min(r, g, b)
    l = (max_c + min_c) / 2

    if max_c == min_c:
        h = s = 0.0
    else:
        d = max_c - min_c
        s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
        if max_c == r:
            h = ((g - b) / d + (6 if g < b else 0)) / 6
        elif max_c == g:
            h = ((b - r) / d + 2) / 6
        else:
            h = ((r - g) / d + 4) / 6

    return h * 360, s, l


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """HSL → Hex"""
    h = h % 360
    s = max(0, min(1, s))
    l = max(0, min(1, l))

    if s == 0:
        v = int(l * 255)
        return f"#{v:02x}{v:02x}{v:02x}"

    def hue_to_rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    h_norm = h / 360

    r = int(hue_to_rgb(p, q, h_norm + 1/3) * 255)
    g = int(hue_to_rgb(p, q, h_norm) * 255)
    b = int(hue_to_rgb(p, q, h_norm - 1/3) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def generate_palette(base_hex: str, mode: str = "analogous") -> list[str]:
    """베이스 컬러에서 5색 조화 팔레트 생성

    mode: analogous | complementary | triadic | split | monochrome
    """
    h, s, l = _hex_to_hsl(base_hex)

    if mode == "complementary":
        return [
            base_hex,
            _hsl_to_hex(h, s * 0.6, min(l + 0.2, 0.85)),
            _hsl_to_hex((h + 180) % 360, s, l),
            _hsl_to_hex((h + 180) % 360, s * 0.6, min(l + 0.15, 0.8)),
            _hsl_to_hex(h, s * 0.8, max(l - 0.2, 0.15)),
        ]
    elif mode == "triadic":
        return [
            base_hex,
            _hsl_to_hex((h + 120) % 360, s * 0.85, l),
            _hsl_to_hex((h + 240) % 360, s * 0.85, l),
            _hsl_to_hex(h, s * 0.5, min(l + 0.2, 0.85)),
            _hsl_to_hex((h + 120) % 360, s * 0.5, max(l - 0.15, 0.2)),
        ]
    elif mode == "split":
        return [
            base_hex,
            _hsl_to_hex((h + 150) % 360, s * 0.85, l),
            _hsl_to_hex((h + 210) % 360, s * 0.85, l),
            _hsl_to_hex(h, s * 0.6, min(l + 0.2, 0.85)),
            _hsl_to_hex(h, s * 0.8, max(l - 0.2, 0.15)),
        ]
    elif mode == "monochrome":
        return [
            base_hex,
            _hsl_to_hex(h, s * 0.7, min(l + 0.25, 0.9)),
            _hsl_to_hex(h, s * 0.85, min(l + 0.12, 0.8)),
            _hsl_to_hex(h, min(s * 1.2, 1.0), max(l - 0.15, 0.15)),
            _hsl_to_hex(h, min(s * 1.1, 1.0), max(l - 0.3, 0.1)),
        ]
    else:  # analogous (기본)
        return [
            base_hex,
            _hsl_to_hex((h + 30) % 360, s * 0.9, l),
            _hsl_to_hex((h - 30) % 360, s * 0.9, l),
            _hsl_to_hex((h + 15) % 360, s * 0.6, min(l + 0.2, 0.85)),
            _hsl_to_hex(h, min(s * 1.2, 1.0), max(l - 0.2, 0.15)),
        ]
