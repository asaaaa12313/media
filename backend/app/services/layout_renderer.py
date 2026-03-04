"""자유 배치 레이아웃 렌더러 (멀티 해상도 지원)

지원 사이즈:
- 1080x1650 (기본, 숏폼 표준)
- 1080x1920 (9:16 풀)
- 1080x2560 (롱폼)

2-Layer 구성:
- 콘텐츠 영역 (height - 200px): 사진 + 자유 배치 텍스트
- 하단 바 (200px): 고정 정보 (주소/전화/QR)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from PIL import Image, ImageDraw

from app.core.config import TEXT_REGIONS, SCENE_LAYOUTS
from app.services.text_layout import (
    draw_text_in_region, draw_number_list, draw_badge_grid,
)
from app.services.image_processor import center_crop_resize, apply_overlay_fast


# ─────────────────────────────────────────────
# 프레임 사이즈 정의
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class FrameSpec:
    """프레임 해상도 스펙"""
    width: int
    height: int
    bottom_bar_height: int = 200

    @property
    def content_height(self) -> int:
        return self.height - self.bottom_bar_height


FRAME_SIZES: dict[str, FrameSpec] = {
    "1080x1650": FrameSpec(1080, 1650),
    "1080x1920": FrameSpec(1080, 1920),
    "1080x2560": FrameSpec(1080, 2560),
}

DEFAULT_FRAME_SIZE = "1080x1650"

# TEXT_REGIONS 기준 콘텐츠 높이 (config.py에 정의된 값 기준)
_BASE_CONTENT_HEIGHT = 1720


def _scale_regions(spec: FrameSpec) -> dict[str, dict]:
    """TEXT_REGIONS를 프레임 사이즈에 맞게 스케일링.

    x, w는 동일 (가로 1080 고정), y, h만 비율 조정.
    """
    if spec.content_height == _BASE_CONTENT_HEIGHT:
        return TEXT_REGIONS

    ratio = spec.content_height / _BASE_CONTENT_HEIGHT
    scaled = {}
    for key, r in TEXT_REGIONS.items():
        scaled[key] = {
            "x": r["x"],
            "y": int(r["y"] * ratio),
            "w": r["w"],
            "h": int(r["h"] * ratio),
            "align": r.get("align", "center"),
        }
    return scaled


# ─────────────────────────────────────────────
# 데이터 구조
# ─────────────────────────────────────────────

@dataclass
class TextBlock:
    """화면에 배치되는 개별 텍스트 요소"""
    content: str = ""
    region: str = "mid_center"       # TEXT_REGIONS 키
    role: str = "headline"           # headline, subtext, brand_name, accent, feature_list, badge_grid, cta_text
    font_role: str = "headline"      # display, headline, body, accent, handwriting, badge
    font_size: int = 64
    color: tuple = (255, 255, 255)
    effect: str = "shadow"           # none, shadow, outline, bg_box, highlight, glow
    effect_params: dict = field(default_factory=dict)


@dataclass
class SceneLayout:
    """한 씬의 전체 레이아웃 정의"""
    scene_type: str = "intro"
    photo_mode: str = "fullscreen"   # fullscreen, top_half, bottom_half, grid_2x2, none
    photo_overlay: str = "gradient_bottom"
    text_blocks: list[TextBlock] = field(default_factory=list)
    background_color: tuple = (0, 0, 0)
    bottom_template: bool = False    # 하단을 브랜드 컬러 템플릿으로 채울지


# ─────────────────────────────────────────────
# 레이아웃 렌더러
# ─────────────────────────────────────────────

class LayoutRenderer:
    """멀티 해상도 자유 배치 레이아웃 렌더러"""

    def __init__(self, template: dict, logo: Image.Image | None = None,
                 business_name: str = "",
                 frame_size: str = DEFAULT_FRAME_SIZE):
        self.template = template
        self.logo = logo
        self.business_name = business_name
        self.fonts = template["fonts"]
        self.spec = FRAME_SIZES.get(frame_size, FRAME_SIZES[DEFAULT_FRAME_SIZE])
        self.regions = _scale_regions(self.spec)
        self._font_scale = self.spec.content_height / _BASE_CONTENT_HEIGHT
        self._bottom_bar_cache: Image.Image | None = None

    def set_bottom_bar(self, bar: Image.Image):
        """외부에서 생성한 하단 바 캐싱"""
        self._bottom_bar_cache = bar

    def render_scene(self, layout: SceneLayout,
                     photos: list[Image.Image],
                     photo_index: int = 0) -> Image.Image:
        """1개 씬의 전체 프레임 렌더링"""
        W, H = self.spec.width, self.spec.height
        CH = self.spec.content_height

        frame = Image.new("RGBA", (W, H), (*layout.background_color, 255))

        # 1) 사진 배치
        bottom_tpl = getattr(layout, 'bottom_template', False)
        if photos and photo_index < len(photos):
            self._place_photo(frame, photos[photo_index],
                              layout.photo_mode, layout.photo_overlay,
                              bottom_template=bottom_tpl)
        elif photos:
            self._place_photo(frame, photos[0],
                              layout.photo_mode, layout.photo_overlay,
                              bottom_template=bottom_tpl)

        # 2) 텍스트 블록 배치
        txt_layer = Image.new("RGBA", (W, CH), (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)
        for block in layout.text_blocks:
            self._render_text_block(draw, txt_layer, block)
        frame = Image.alpha_composite(frame, self._pad_to_full(txt_layer))

        # 3) 하단 바
        if self._bottom_bar_cache:
            bar_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            bar = self._bottom_bar_cache
            if bar.mode != "RGBA":
                bar = bar.convert("RGBA")
            bar_layer.paste(bar, (0, CH), bar)
            frame = Image.alpha_composite(frame, bar_layer)

        return frame.convert("RGB")

    def _place_photo(self, frame: Image.Image, photo: Image.Image,
                     mode: str, overlay: str, bottom_template: bool = False):
        """photo_mode에 따른 사진 배치"""
        W = self.spec.width
        CH = self.spec.content_height

        if mode == "fullscreen":
            img = center_crop_resize(photo, W, CH)
            img = apply_overlay_fast(img, overlay)
            frame.paste(img.convert("RGBA"), (0, 0))

        elif mode == "top_half":
            half_h = CH // 2
            img = center_crop_resize(photo, W, half_h)
            img = apply_overlay_fast(img, overlay)
            frame.paste(img.convert("RGBA"), (0, 0))

            # 하단 템플릿 영역: 브랜드 컬러로 채움
            if bottom_template:
                self._fill_bottom_template(frame, half_h, CH)

        elif mode == "bottom_half":
            half_h = CH // 2
            img = center_crop_resize(photo, W, half_h)
            img = apply_overlay_fast(img, overlay)
            frame.paste(img.convert("RGBA"), (0, half_h))

        elif mode == "grid_2x2":
            self._place_grid_2x2(frame, photo, overlay)

    def _fill_bottom_template(self, frame: Image.Image, top: int, bottom: int):
        """하단 영역을 브랜드 컬러로 채우고 자연스러운 그라데이션 전환"""
        W = self.spec.width
        primary = self.template.get("primary", (50, 50, 50))

        # 브랜드 컬러 배경
        bg_layer = Image.new("RGBA", (W, bottom - top), (*primary, 255))
        frame.paste(bg_layer, (0, top))

        # 사진-템플릿 경계 그라데이션 블렌딩 (40px)
        blend_h = 40
        for y in range(blend_h):
            alpha = int(255 * y / blend_h)
            line = Image.new("RGBA", (W, 1), (*primary, alpha))
            frame.paste(line, (0, top - blend_h + y), line)

    def _place_grid_2x2(self, frame: Image.Image, photo: Image.Image,
                        overlay: str):
        """2x2 사진 그리드"""
        W = self.spec.width
        CH = self.spec.content_height
        gap = 8
        cell_w = (W - gap) // 2
        cell_h = (CH // 2 - gap) // 2
        img = center_crop_resize(photo, cell_w, cell_h)
        img = apply_overlay_fast(img, overlay)

        positions = [
            (0, 0), (cell_w + gap, 0),
            (0, cell_h + gap), (cell_w + gap, cell_h + gap),
        ]
        for px, py in positions:
            frame.paste(img.convert("RGBA"), (px, py))

    def _render_text_block(self, draw: ImageDraw.Draw,
                           _layer: Image.Image, block: TextBlock):
        """개별 텍스트 블록 렌더링 (해상도별 자동 스케일링)"""
        if not block.content:
            return

        region = self.regions.get(block.region)
        if not region:
            return

        font_name = self.fonts.get(
            block.font_role,
            self.fonts.get("headline", "Pretendard-Bold.otf"),
        )

        # 폰트 사이즈 스케일링
        scaled_size = max(16, int(block.font_size * self._font_scale))

        # 특수 역할 처리
        if block.role == "feature_list":
            items = [line.strip() for line in block.content.split("\n") if line.strip()]
            draw_number_list(
                draw, items, region, font_name, scaled_size,
                block.color,
                number_color=self.template.get("text_on_primary", (255, 255, 255)),
                number_bg=self.template.get("primary", (100, 100, 100)),
            )
            return

        if block.role == "badge_grid":
            tags = [t.strip() for t in block.content.split(",") if t.strip()]
            draw_badge_grid(
                draw, tags, region,
                bg_color=self.template.get("badge_bg", (100, 100, 100)),
                text_color=self.template.get("badge_text", (255, 255, 255)),
                font_name=self.fonts.get("badge", font_name),
                font_size=scaled_size,
                style=self.template.get("badge_style", "rounded"),
            )
            return

        # 일반 텍스트 렌더링
        draw_text_in_region(
            draw, block.content, region,
            font_name, scaled_size,
            block.color, block.effect, block.effect_params,
        )

    def _pad_to_full(self, content_layer: Image.Image) -> Image.Image:
        """콘텐츠 레이어를 전체 프레임 크기로 패딩"""
        W, H = self.spec.width, self.spec.height
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        full.paste(content_layer, (0, 0))
        return full


# ─────────────────────────────────────────────
# 씬 레이아웃 빌더
# ─────────────────────────────────────────────

def build_scene_layout(scene_type: str, template: dict,
                       headline: str = "", subtext: str = "",
                       business_name: str = "", services: list[str] | None = None,
                       custom_blocks: list[dict] | None = None,
                       font_color_override: str = "",
                       emphasis_color: str = "",
                       emphasis_words: list[str] | None = None) -> SceneLayout:
    """씬 타입 + 텍스트 → SceneLayout 자동 구성

    custom_blocks가 주어지면 그대로 사용 (수정 기능용).
    없으면 SCENE_LAYOUTS 기본값 + headline/subtext로 자동 매핑.
    """
    layout_def = SCENE_LAYOUTS.get(scene_type, SCENE_LAYOUTS["intro"])
    text_color = template.get("text_on_content", (255, 255, 255))
    # 폰트 색상 오버라이드
    if font_color_override:
        from app.services.template_engine import hex_to_rgb
        text_color = hex_to_rgb(font_color_override)
    emphasis_rgb = None
    if emphasis_color:
        from app.services.template_engine import hex_to_rgb
        emphasis_rgb = hex_to_rgb(emphasis_color)
    emphasis_words = emphasis_words or []
    effects = template.get("text_effects", {})

    has_bottom_tpl = layout_def.get("bottom_template", False)

    # 사용자 커스텀 블록이 있으면 우선 사용
    if custom_blocks:
        blocks = [TextBlock(**b) for b in custom_blocks]
        return SceneLayout(
            scene_type=scene_type,
            photo_mode=layout_def["photo_mode"],
            photo_overlay=layout_def["photo_overlay"],
            text_blocks=blocks,
            background_color=template.get("panel_bg", (0, 0, 0)),
            bottom_template=has_bottom_tpl,
        )

    # 자동 매핑: 씬 타입의 text_slots를 기반으로 TextBlock 생성
    blocks = []
    for slot in layout_def["text_slots"]:
        role = slot["role"]

        # 역할에 따라 content 결정
        if role == "brand_name":
            content = business_name
        elif role == "headline":
            content = headline
        elif role in ("subtext", "cta_text"):
            content = subtext
        elif role == "accent":
            content = subtext or headline
        elif role == "feature_list":
            content = subtext  # 줄바꿈 구분된 항목
        elif role == "badge_grid":
            content = ", ".join(services) if services else ""
        else:
            content = headline

        if not content:
            continue

        # 효과 결정: 역할 기반 or 템플릿 기본값
        effect_key = "headline" if role in ("headline", "brand_name", "accent") else "subtext"
        eff = effects.get(effect_key, {"effect": slot.get("effect", "shadow"), "params": {}})

        # 강조 단어가 headline에 포함되면 강조 색상 적용
        block_color = text_color
        if emphasis_rgb and role in ("headline", "brand_name") and emphasis_words:
            if any(w in content for w in emphasis_words):
                block_color = emphasis_rgb

        blocks.append(TextBlock(
            content=content,
            region=slot["region"],
            role=role,
            font_role=slot["font_role"],
            font_size=slot["size"],
            color=block_color,
            effect=eff.get("effect", "shadow"),
            effect_params=eff.get("params", {}),
        ))

    return SceneLayout(
        scene_type=scene_type,
        photo_mode=layout_def["photo_mode"],
        photo_overlay=layout_def["photo_overlay"],
        text_blocks=blocks,
        background_color=template.get("panel_bg", (0, 0, 0)),
        bottom_template=has_bottom_tpl,
    )


# ─────────────────────────────────────────────
# 하위 호환: render_text_overlay_png
# ─────────────────────────────────────────────

def render_text_overlay_png(headline: str, subtext: str,
                            template: dict,
                            frame_size: str = DEFAULT_FRAME_SIZE) -> Image.Image:
    """텍스트만 있는 투명 PNG 생성 (영상 씬 오버레이용)"""
    spec = FRAME_SIZES.get(frame_size, FRAME_SIZES[DEFAULT_FRAME_SIZE])
    regions = _scale_regions(spec)
    font_scale = spec.content_height / _BASE_CONTENT_HEIGHT

    overlay = Image.new("RGBA", (spec.width, spec.content_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    text_color = template.get("text_on_content", (255, 255, 255))
    fonts = template["fonts"]
    effects = template.get("text_effects", {})

    if headline:
        eff = effects.get("headline", {"effect": "outline", "params": {"stroke_width": 3, "stroke_color": (0, 0, 0)}})
        region = regions["mid_center"]
        font_name = fonts.get("display", fonts.get("headline", "Pretendard-Bold.otf"))
        size = max(16, int(96 * font_scale))
        draw_text_in_region(draw, headline, region, font_name, size,
                            text_color, eff.get("effect", "outline"), eff.get("params", {}))

    if subtext:
        eff = effects.get("subtext", {"effect": "shadow", "params": {}})
        region = regions["bottom_wide"]
        font_name = fonts.get("body", "Pretendard-Bold.otf")
        size = max(16, int(36 * font_scale))
        draw_text_in_region(draw, subtext, region, font_name, size,
                            text_color, eff.get("effect", "shadow"), eff.get("params", {}))

    return overlay
