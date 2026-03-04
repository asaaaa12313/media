"""장식 요소 렌더링: 모서리 꺾쇠, 강조 라인, 따옴표, 별점, 가격표"""
from __future__ import annotations
from PIL import Image, ImageDraw
from app.services.text_layout import _get_font


class Decorations:
    """씬 장식 요소 렌더러"""

    @staticmethod
    def draw_corner_brackets(layer: Image.Image, x: int, y: int,
                             w: int, h: int, color: tuple,
                             thickness: int = 3, length: int = 40):
        """모서리 꺾쇠 장식 (사진 프레임용)"""
        draw = ImageDraw.Draw(layer)
        c = (*color[:3], 200)
        # 좌상
        draw.line([(x, y + length), (x, y), (x + length, y)], fill=c, width=thickness)
        # 우상
        draw.line([(x + w - length, y), (x + w, y), (x + w, y + length)], fill=c, width=thickness)
        # 좌하
        draw.line([(x, y + h - length), (x, y + h), (x + length, y + h)], fill=c, width=thickness)
        # 우하
        draw.line([(x + w - length, y + h), (x + w, y + h), (x + w, y + h - length)], fill=c, width=thickness)

    @staticmethod
    def draw_accent_line(layer: Image.Image, x: int, y: int,
                         w: int, color: tuple, thickness: int = 4):
        """강조 라인 (텍스트 위/아래 장식)"""
        draw = ImageDraw.Draw(layer)
        draw.rectangle([x, y, x + w, y + thickness], fill=(*color[:3], 220))

    @staticmethod
    def draw_quote_marks(layer: Image.Image, x: int, y: int,
                         color: tuple, size: int = 60):
        """큰따옴표 장식 (후기 씬용)"""
        draw = ImageDraw.Draw(layer)
        font = _get_font("Pretendard-Bold.otf", size)
        draw.text((x, y), "\u201C", font=font, fill=(*color[:3], 160))

    @staticmethod
    def draw_star_rating(layer: Image.Image, x: int, y: int,
                         rating: float, color: tuple, size: int = 30):
        """별점 표시 (후기 씬용)"""
        draw = ImageDraw.Draw(layer)
        font = _get_font("Pretendard-Bold.otf", size)
        full = int(rating)
        stars = "\u2605" * full + "\u2606" * (5 - full)
        draw.text((x, y), stars, font=font, fill=(*color[:3], 220))

    @staticmethod
    def draw_price_tag(layer: Image.Image, x: int, y: int,
                       price_text: str, bg_color: tuple, text_color: tuple,
                       font_name: str = "GmarketSansBold.otf", font_size: int = 36):
        """가격표 장식 (프로모션 씬용)"""
        draw = ImageDraw.Draw(layer)
        font = _get_font(font_name, font_size)
        bbox = draw.textbbox((0, 0), price_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 20, 10
        # 배경
        draw.rounded_rectangle(
            [x, y, x + tw + pad_x * 2, y + th + pad_y * 2],
            radius=(th + pad_y * 2) // 2,
            fill=(*bg_color[:3], 230)
        )
        draw.text((x + pad_x, y + pad_y), price_text, font=font,
                  fill=(*text_color[:3], 255))


def render_decorations(layer: Image.Image, decorations: list[dict],
                       template: dict):
    """씬 레이아웃의 장식 목록을 렌더링"""
    for deco in decorations:
        dtype = deco.get("type", "")
        color_key = deco.get("color_key", "accent")
        color = template.get(color_key, template.get("primary", (255, 200, 50)))

        if dtype == "corner_brackets":
            Decorations.draw_corner_brackets(
                layer, deco.get("x", 40), deco.get("y", 40),
                deco.get("w", 1000), deco.get("h", 600), color,
                deco.get("thickness", 3), deco.get("length", 40))
        elif dtype == "accent_line":
            Decorations.draw_accent_line(
                layer, deco.get("x", 60), deco.get("y", 480),
                deco.get("w", 200), color, deco.get("thickness", 4))
        elif dtype == "quote_marks":
            Decorations.draw_quote_marks(
                layer, deco.get("x", 80), deco.get("y", 500),
                color, deco.get("size", 60))
        elif dtype == "star_rating":
            Decorations.draw_star_rating(
                layer, deco.get("x", 400), deco.get("y", 1100),
                deco.get("rating", 5), color, deco.get("size", 30))
        elif dtype == "price_tag":
            Decorations.draw_price_tag(
                layer, deco.get("x", 100), deco.get("y", 800),
                deco.get("text", ""), template.get("accent", color),
                template.get("text_on_primary", (255, 255, 255)),
                deco.get("font_name", "GmarketSansBold.otf"),
                deco.get("font_size", 36))
