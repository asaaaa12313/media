"""3-Zone 프레임 렌더러 (핵심 모듈)

1080x1650 프레임을 3개 Zone으로 나눠 렌더링:
- Zone 1 (0-140px): 상단 헤더
- Zone 2 (140-1020px): 콘텐츠 영역
- Zone 3 (1020-1650px): 하단 정보 패널
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from app.core.config import WIDTH, HEIGHT, ZONE1_HEIGHT, ZONE2_HEIGHT, ZONE3_HEIGHT
from app.services.text_layout import (
    draw_text_centered, draw_text_left, draw_multiline_centered,
)
from app.services.image_processor import center_crop_resize, apply_overlay_fast


class ZoneRenderer:
    def __init__(self, template: dict, logo: Image.Image | None = None,
                 business_name: str = ""):
        self.template = template
        self.logo = logo
        self.business_name = business_name
        self.fonts = template["fonts"]

        # Zone 1, Zone 3은 전 프레임에서 동일 → 캐싱
        self._header_cache: Image.Image | None = None
        self._panel_cache: Image.Image | None = None

    def set_panel_cache(self, panel: Image.Image):
        """외부에서 생성한 패널 이미지를 캐싱"""
        self._panel_cache = panel

    def render_header(self) -> Image.Image:
        """Zone 1: 상단 헤더 (1080 x 140) 렌더링"""
        if self._header_cache:
            return self._header_cache

        header = Image.new("RGBA", (WIDTH, ZONE1_HEIGHT),
                           (*self.template["primary"], 255))
        draw = ImageDraw.Draw(header)
        text_color = self.template["text_on_primary"]

        x = 40
        if self.logo:
            y_offset = (ZONE1_HEIGHT - self.logo.height) // 2
            header.paste(self.logo, (x, y_offset),
                         self.logo if self.logo.mode == "RGBA" else None)
            x += self.logo.width + 15

        # 업체명 표시
        if self.business_name:
            from app.services.text_layout import _get_font
            font = _get_font(self.fonts["headline"], 40)
            y_text = (ZONE1_HEIGHT - 40) // 2
            draw.text((x, y_text), self.business_name, font=font, fill=text_color)

        self._header_cache = header
        return header

    def render_content(self, photo: Image.Image, headline: str,
                       subtext: str) -> Image.Image:
        """Zone 2: 콘텐츠 영역 (1080 x 880) 렌더링"""
        # 사진 크롭/리사이즈
        content = center_crop_resize(photo, WIDTH, ZONE2_HEIGHT)

        # 오버레이 적용
        content = apply_overlay_fast(content, self.template["overlay"])

        # RGBA로 변환하여 텍스트 렌더링
        content = content.convert("RGBA")
        txt_layer = Image.new("RGBA", content.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)

        text_color = self.template["text_on_content"]

        # 헤드라인 위치: 중앙~하단 영역 (레퍼런스 매칭)
        y_start = int(ZONE2_HEIGHT * 0.42)

        if headline:
            h = draw_text_centered(draw, headline, y_start,
                                   self.fonts["headline"], 64,
                                   text_color, shadow=True)
            y_start += h + 15

        if subtext:
            draw_multiline_centered(draw, subtext, y_start,
                                    self.fonts["body"], 36,
                                    text_color, shadow=True)

        content = Image.alpha_composite(content, txt_layer)
        return content

    def render_frame(self, photo: Image.Image, headline: str,
                     subtext: str) -> Image.Image:
        """전체 프레임 (1080 x 1650) 조합"""
        frame = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))

        # Zone 1: 헤더
        header = self.render_header()
        frame.paste(header, (0, 0), header)

        # Zone 2: 콘텐츠
        content = self.render_content(photo, headline, subtext)
        frame.paste(content, (0, ZONE1_HEIGHT), content)

        # Zone 3: 정보 패널
        if self._panel_cache:
            frame.paste(self._panel_cache, (0, ZONE1_HEIGHT + ZONE2_HEIGHT),
                        self._panel_cache if self._panel_cache.mode == "RGBA" else None)

        return frame.convert("RGB")


def render_text_overlay_png(headline: str, subtext: str,
                            template: dict) -> Image.Image:
    """텍스트만 있는 투명 PNG 생성 (영상 씬 오버레이용)"""
    overlay = Image.new("RGBA", (WIDTH, ZONE2_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    text_color = template["text_on_content"]
    fonts = template["fonts"]

    y_start = int(ZONE2_HEIGHT * 0.42)

    if headline:
        h = draw_text_centered(draw, headline, y_start,
                               fonts["headline"], 64,
                               text_color, shadow=True)
        y_start += h + 15

    if subtext:
        draw_multiline_centered(draw, subtext, y_start,
                                fonts["body"], 36,
                                text_color, shadow=True)

    return overlay
