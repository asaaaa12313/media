"""구조화된 텍스트/뱃지 렌더링 유틸 (Pillow) + 텍스트 효과 시스템"""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from app.core.config import FONTS_DIR, WIDTH

MARGIN = 60


def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    # 폴백: 아무 폰트나 찾기
    for f in FONTS_DIR.iterdir():
        if f.suffix in (".otf", ".ttf"):
            return ImageFont.truetype(str(f), size)
    return ImageFont.load_default()


# ─────────────────────────────────────────────
# TextEffects: 6가지 텍스트 렌더링 효과
# ─────────────────────────────────────────────

class TextEffects:
    """텍스트 효과 렌더러 (12종)"""

    @staticmethod
    def apply(draw: ImageDraw.Draw, text: str, x: int, y: int,
              font: ImageFont.FreeTypeFont, color: tuple,
              effect: str = "none", params: dict | None = None,
              layer: Image.Image | None = None):
        """효과를 적용하여 텍스트 렌더링. layer는 이미지 레벨 합성 효과용."""
        params = params or {}
        method = getattr(TextEffects, f"_effect_{effect}", TextEffects._effect_none)
        # gradient_text는 layer 필요
        if effect == "gradient_text" and layer is not None:
            method(draw, text, x, y, font, color, params, layer)
        else:
            method(draw, text, x, y, font, color, params)

    @staticmethod
    def _effect_none(draw, text, x, y, font, color, _params):
        draw.text((x, y), text, font=font, fill=color)

    @staticmethod
    def _effect_shadow(draw, text, x, y, font, color, params):
        ox = params.get("offset_x", 3)
        oy = params.get("offset_y", 3)
        sa = params.get("shadow_alpha", 140)
        sc = params.get("shadow_color", (0, 0, 0))
        draw.text((x + ox, y + oy), text, font=font, fill=(*sc[:3], sa))
        draw.text((x, y), text, font=font, fill=color)

    @staticmethod
    def _effect_outline(draw, text, x, y, font, color, params):
        sw = params.get("stroke_width", 3)
        sc = params.get("stroke_color", (0, 0, 0))
        draw.text((x, y), text, font=font, fill=color,
                  stroke_width=sw, stroke_fill=sc)

    @staticmethod
    def _effect_bg_box(draw, text, x, y, font, color, params):
        bbox = draw.textbbox((x, y), text, font=font)
        pad = params.get("padding", 16)
        bg = params.get("bg_color", (0, 0, 0))
        ba = params.get("bg_alpha", 160)
        radius = params.get("radius", 10)
        draw.rounded_rectangle(
            [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
            radius=radius, fill=(*bg[:3], ba)
        )
        draw.text((x, y), text, font=font, fill=color)

    @staticmethod
    def _effect_highlight(draw, text, x, y, font, color, params):
        bbox = draw.textbbox((x, y), text, font=font)
        hc = params.get("highlight_color", (255, 255, 0))
        ha = params.get("highlight_alpha", 180)
        pad_x = params.get("padding_x", 10)
        pad_y = params.get("padding_y", 4)
        text_h = bbox[3] - bbox[1]
        draw.rectangle(
            [bbox[0] - pad_x, bbox[1] + int(text_h * 0.55),
             bbox[2] + pad_x, bbox[3] + pad_y],
            fill=(*hc[:3], ha)
        )
        draw.text((x, y), text, font=font, fill=color)

    @staticmethod
    def _effect_glow(draw, text, x, y, font, color, params):
        gc = params.get("glow_color", color[:3])
        radius = params.get("glow_radius", 4)
        for offset in range(radius, 0, -1):
            alpha = int(80 / offset)
            for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset),
                           (-offset, -offset), (offset, offset),
                           (-offset, offset), (offset, -offset)]:
                draw.text((x + dx, y + dy), text, font=font,
                          fill=(*gc[:3], alpha))
        draw.text((x, y), text, font=font, fill=color)

    # ── 새 효과 6종 ──

    @staticmethod
    def _effect_shadow_3d(draw, text, x, y, font, color, params):
        """3D 깊이감 그림자: 여러 레이어로 입체 효과"""
        depth = params.get("depth", 6)
        sc = params.get("shadow_color", (0, 0, 0))
        for d in range(depth, 0, -1):
            alpha = int(40 + 25 * (depth - d) / depth)
            draw.text((x + d, y + d), text, font=font, fill=(*sc[:3], alpha))
        draw.text((x, y), text, font=font, fill=color)

    @staticmethod
    def _effect_neon(draw, text, x, y, font, color, params):
        """네온사인: 넓은 glow + 밝은 내부"""
        nc = params.get("neon_color", color[:3])
        for r in range(8, 0, -1):
            alpha = int(100 / r)
            for dx in range(-r, r + 1, max(1, r // 2)):
                for dy in range(-r, r + 1, max(1, r // 2)):
                    if dx * dx + dy * dy <= r * r:
                        draw.text((x + dx, y + dy), text, font=font,
                                  fill=(*nc[:3], alpha))
        # 외곽선
        draw.text((x, y), text, font=font, fill=(*nc[:3], 255),
                  stroke_width=2, stroke_fill=(*nc[:3], 180))
        # 밝은 내부
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 240))

    @staticmethod
    def _effect_double_outline(draw, text, x, y, font, color, params):
        """이중 외곽선: 안쪽/바깥쪽 다른 색"""
        outer_width = params.get("outer_width", 6)
        inner_width = params.get("inner_width", 3)
        outer_color = params.get("outer_color", (0, 0, 0))
        inner_color = params.get("inner_color", (255, 255, 255))
        # 바깥 외곽선
        draw.text((x, y), text, font=font, fill=color,
                  stroke_width=outer_width, stroke_fill=outer_color)
        # 안쪽 외곽선
        draw.text((x, y), text, font=font, fill=color,
                  stroke_width=inner_width, stroke_fill=inner_color)

    @staticmethod
    def _effect_underline_accent(draw, text, x, y, font, color, params):
        """밑줄 강조: 텍스트 아래 두꺼운 컬러 바"""
        bbox = draw.textbbox((x, y), text, font=font)
        bar_color = params.get("bar_color", (255, 200, 50))
        bar_alpha = params.get("bar_alpha", 220)
        bar_height = params.get("bar_height", 8)
        pad_x = params.get("padding_x", 6)
        draw.rectangle(
            [bbox[0] - pad_x, bbox[3] - bar_height // 2,
             bbox[2] + pad_x, bbox[3] + bar_height // 2],
            fill=(*bar_color[:3], bar_alpha)
        )
        draw.text((x, y), text, font=font, fill=color)

    @staticmethod
    def _effect_bg_pill(draw, text, x, y, font, color, params):
        """둥근 필 형태 배경 (완전 둥근 모서리)"""
        bbox = draw.textbbox((x, y), text, font=font)
        pad_x = params.get("padding_x", 24)
        pad_y = params.get("padding_y", 12)
        bg = params.get("bg_color", (0, 0, 0))
        ba = params.get("bg_alpha", 180)
        pill_h = bbox[3] - bbox[1] + pad_y * 2
        radius = pill_h // 2
        draw.rounded_rectangle(
            [bbox[0] - pad_x, bbox[1] - pad_y,
             bbox[2] + pad_x, bbox[3] + pad_y],
            radius=radius, fill=(*bg[:3], ba)
        )
        draw.text((x, y), text, font=font, fill=color)

    @staticmethod
    def _effect_gradient_text(draw, text, x, y, font, color, params, layer=None):
        """그라데이션 텍스트: 상하 2색"""
        color_top = params.get("color_top", color[:3])
        color_bottom = params.get("color_bottom", (255, 200, 50))
        if layer is None:
            # layer 없으면 일반 렌더링으로 폴백
            draw.text((x, y), text, font=font, fill=color)
            return
        bbox = draw.textbbox((x, y), text, font=font)
        tw = bbox[2] - bbox[0] + 4
        th = bbox[3] - bbox[1] + 4
        if tw <= 0 or th <= 0:
            return
        # 텍스트 마스크 생성
        mask_img = Image.new("L", (tw, th), 0)
        mask_draw = ImageDraw.Draw(mask_img)
        mask_draw.text((0, 0), text, font=font, fill=255)
        # 그라데이션 이미지 생성
        grad_img = Image.new("RGBA", (tw, th))
        for row in range(th):
            ratio = row / max(th - 1, 1)
            r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
            g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
            b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
            for col in range(tw):
                if mask_img.getpixel((col, row)) > 0:
                    grad_img.putpixel((col, row), (r, g, b, mask_img.getpixel((col, row))))
        layer.paste(grad_img, (bbox[0], bbox[1]), grad_img)


# ─────────────────────────────────────────────
# 기본 텍스트 렌더링 (하위 호환 유지)
# ─────────────────────────────────────────────

def draw_text_centered(draw: ImageDraw.Draw, text: str, y: int,
                       font_name: str, size: int, color: tuple,
                       shadow: bool = True, max_width: int = 0) -> int:
    """중앙 정렬 텍스트. 그림자 포함. 실제 차지한 높이 반환."""
    if not text:
        return 0
    max_w = max_width or (WIDTH - MARGIN * 2)
    font = _get_font(font_name, size)

    # 텍스트가 너무 길면 폰트 크기 축소
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    while text_w > max_w and size > 20:
        size -= 2
        font = _get_font(font_name, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]

    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) // 2

    if shadow:
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 120))
    draw.text((x, y), text, font=font, fill=color)
    return text_h


def draw_text_left(draw: ImageDraw.Draw, text: str, x: int, y: int,
                   font_name: str, size: int, color: tuple) -> int:
    """좌측 정렬 텍스트. 높이 반환."""
    if not text:
        return 0
    font = _get_font(font_name, size)
    draw.text((x, y), text, font=font, fill=color)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def draw_multiline_centered(draw: ImageDraw.Draw, text: str, y: int,
                            font_name: str, size: int, color: tuple,
                            line_spacing: int = 10,
                            shadow: bool = True) -> int:
    """여러 줄 중앙 정렬. 줄바꿈 문자 지원. 총 높이 반환."""
    lines = text.split("\n")
    total_h = 0
    for line in lines:
        h = draw_text_centered(draw, line.strip(), y + total_h,
                               font_name, size, color, shadow)
        total_h += h + line_spacing
    return total_h


def measure_text(text: str, font_name: str, size: int) -> tuple[int, int]:
    """텍스트의 (너비, 높이) 측정"""
    font = _get_font(font_name, size)
    img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# ─────────────────────────────────────────────
# 영역 기반 텍스트 렌더링 (새 레이아웃 시스템)
# ─────────────────────────────────────────────

def draw_text_in_region(draw: ImageDraw.Draw, text: str,
                        region: dict, font_name: str, size: int,
                        color: tuple, effect: str = "none",
                        effect_params: dict | None = None,
                        max_lines: int = 3,
                        layer: Image.Image | None = None) -> int:
    """영역 내에 텍스트 렌더링 (자동 크기 조정 + 줄바꿈 + 효과 적용).

    Returns: 실제 사용한 높이
    """
    if not text:
        return 0
    effect_params = effect_params or {}
    font = _get_font(font_name, size)
    align = region.get("align", "center")
    rx, ry, rw, rh = region["x"], region["y"], region["w"], region["h"]

    # 줄바꿈 처리 (\n 포함된 경우)
    lines = text.split("\n")
    if len(lines) == 1:
        # 단일 줄: 너비 초과 시 크기 축소
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        while text_w > rw and size > 20:
            size -= 2
            font = _get_font(font_name, size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
        lines = [text]
    else:
        # 각 줄의 크기도 조정
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            while text_w > rw and size > 20:
                size -= 2
                font = _get_font(font_name, size)
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]

    total_h = 0
    line_spacing = max(8, size // 4)

    for line in lines[:max_lines]:
        if not line.strip():
            total_h += line_spacing
            continue
        bbox = draw.textbbox((0, 0), line.strip(), font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 정렬에 따른 x 좌표
        if align == "center":
            x = rx + (rw - text_w) // 2
        elif align == "right":
            x = rx + rw - text_w
        else:
            x = rx

        y = ry + total_h
        TextEffects.apply(draw, line.strip(), x, y, font, color, effect, effect_params, layer=layer)
        total_h += text_h + line_spacing

    return total_h


def draw_number_list(draw: ImageDraw.Draw, items: list[str],
                     region: dict, font_name: str, size: int,
                     color: tuple, number_color: tuple,
                     number_bg: tuple) -> int:
    """원형 번호 + 텍스트 리스트 렌더링 (레퍼런스: 학원 KT 스타일).

    Returns: 실제 사용한 높이
    """
    if not items:
        return 0
    font = _get_font(font_name, size)
    num_font = _get_font(font_name, size + 4)
    rx, ry = region["x"], region["y"]
    rw = region["w"]
    total_h = 0
    circle_r = size + 6

    for i, item in enumerate(items[:5]):  # 최대 5개
        # 원형 번호 배경
        cx = rx + circle_r
        cy = ry + total_h + circle_r
        draw.ellipse(
            [cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r],
            fill=number_bg
        )
        # 번호 텍스트
        num_text = str(i + 1)
        num_bbox = draw.textbbox((0, 0), num_text, font=num_font)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]
        draw.text((cx - num_w // 2, cy - num_h // 2 - 2),
                  num_text, font=num_font, fill=number_color)

        # 항목 텍스트
        text_x = rx + circle_r * 2 + 16
        # 크기 조정
        item_font = font
        item_size = size
        bbox = draw.textbbox((0, 0), item, font=item_font)
        while bbox[2] - bbox[0] > rw - circle_r * 2 - 20 and item_size > 16:
            item_size -= 2
            item_font = _get_font(font_name, item_size)
            bbox = draw.textbbox((0, 0), item, font=item_font)

        draw.text((text_x, ry + total_h + circle_r - item_size // 2),
                  item, font=item_font, fill=color)
        total_h += circle_r * 2 + 12

    return total_h


# ─────────────────────────────────────────────
# 뱃지/태그 렌더링
# ─────────────────────────────────────────────

def draw_badge(draw: ImageDraw.Draw, text: str, x: int, y: int,
               bg_color: tuple, text_color: tuple,
               font_name: str = "NanumSquareRoundEB.ttf",
               font_size: int = 22, style: str = "rounded") -> int:
    """뱃지 그리기. 뱃지의 너비 반환."""
    font = _get_font(font_name, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x, pad_y = 18, 10
    badge_w = text_w + pad_x * 2
    badge_h = text_h + pad_y * 2

    if style == "rounded":
        radius = 10
    elif style == "pill":
        radius = badge_h // 2
    else:
        radius = 4

    draw.rounded_rectangle(
        [x, y, x + badge_w, y + badge_h],
        radius=radius, fill=bg_color
    )
    # 테두리
    draw.rounded_rectangle(
        [x, y, x + badge_w, y + badge_h],
        radius=radius, outline=(*bg_color[:3], 180), width=1
    )
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=text_color)
    return badge_w


def draw_badges_row(draw: ImageDraw.Draw, tags: list[str], y: int,
                    bg_color: tuple, text_color: tuple,
                    font_name: str = "NanumSquareRoundEB.ttf",
                    font_size: int = 22, style: str = "rounded",
                    center: bool = True) -> int:
    """태그들을 가로로 배열 (자동 줄바꿈). 사용한 총 높이 반환."""
    if not tags:
        return 0

    gap = 10
    badge_h = font_size + 20
    row_height = badge_h + 8

    # 먼저 각 뱃지의 너비 측정
    widths = []
    for tag in tags:
        tw, _ = measure_text(tag, font_name, font_size)
        widths.append(tw + 36)

    # 줄 나누기
    rows = []
    current_row = []
    current_w = 0
    max_w = WIDTH - MARGIN * 2
    for i, (tag, w) in enumerate(zip(tags, widths)):
        if current_w + w + gap > max_w and current_row:
            rows.append(current_row)
            current_row = []
            current_w = 0
        current_row.append((tag, w))
        current_w += w + gap
    if current_row:
        rows.append(current_row)

    # 그리기
    cur_y = y
    for row in rows:
        total_row_w = sum(w for _, w in row) + gap * (len(row) - 1)
        if center:
            x = (WIDTH - total_row_w) // 2
        else:
            x = MARGIN
        for tag, w in row:
            draw_badge(draw, tag, x, cur_y, bg_color, text_color,
                       font_name, font_size, style)
            x += w + gap
        cur_y += row_height

    return cur_y - y


def draw_badge_grid(draw: ImageDraw.Draw, tags: list[str],
                    region: dict, bg_color: tuple, text_color: tuple,
                    font_name: str = "NanumSquareRoundEB.ttf",
                    font_size: int = 22, style: str = "rounded",
                    cols: int = 3) -> int:
    """뱃지를 그리드 형태로 배열 (레퍼런스: 헬스 KT 서비스 그리드).

    Returns: 실제 사용한 높이
    """
    if not tags:
        return 0

    rx, ry, rw = region["x"], region["y"], region["w"]
    gap = 10
    col_w = (rw - gap * (cols - 1)) // cols
    badge_h = font_size + 20
    row_h = badge_h + gap
    total_h = 0

    for i, tag in enumerate(tags[:cols * 3]):  # 최대 3행
        col = i % cols
        row = i // cols
        bx = rx + col * (col_w + gap)
        by = ry + row * row_h

        font = _get_font(font_name, font_size)
        bbox = draw.textbbox((0, 0), tag, font=font)
        text_w = bbox[2] - bbox[0]

        # 뱃지 크기를 열 너비에 맞춤
        actual_w = min(col_w, text_w + 36)

        if style == "rounded":
            radius = 10
        elif style == "pill":
            radius = badge_h // 2
        else:
            radius = 4

        # 중앙 정렬
        offset_x = (col_w - actual_w) // 2

        draw.rounded_rectangle(
            [bx + offset_x, by, bx + offset_x + actual_w, by + badge_h],
            radius=radius, fill=bg_color,
            outline=(*bg_color[:3], 200), width=2
        )
        draw.text(
            (bx + offset_x + (actual_w - text_w) // 2, by + (badge_h - (bbox[3] - bbox[1])) // 2),
            tag, font=font, fill=text_color
        )

        total_h = max(total_h, (row + 1) * row_h)

    return total_h


def draw_divider(draw: ImageDraw.Draw, y: int, color: tuple,
                 margin: int = MARGIN, width: int = 1) -> None:
    """수평 구분선"""
    draw.line([(margin, y), (WIDTH - margin, y)],
              fill=(*color[:3], 80), width=width)
