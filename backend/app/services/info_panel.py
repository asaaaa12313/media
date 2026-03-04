"""정보 패널 렌더링 (550px 3-섹션 디자인 패널)

레퍼런스 기반 3영역 구성:
- 섹션 1 (~33%): 홍보 영역 (업종별 3패턴)
- 섹션 2 (~36%): 브랜드 정보 + QR코드
- 섹션 3 (~31%): 연락처 푸터 (브랜드 컬러 배경)
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from app.core.config import WIDTH
from app.services.text_layout import (
    _get_font, draw_badge_grid, TextEffects, MARGIN,
)
from app.services.decorations import Decorations


# 업종별 정보 패널 스타일 매핑
INFO_PANEL_STYLE = {
    "음식점": "promo",
    "헬스": "promo",
    "뷰티": "promo",
    "골프": "promo",
    "학원": "info_card",
    "병원": "info_card",
    "동물병원": "info_card",
    "부동산": "info_card",
    "안경": "brand_focus",
    "핸드폰": "brand_focus",
    "미용실": "brand_focus",
    "기타": "brand_focus",
}


def _draw_gradient_divider(draw: ImageDraw.Draw, y: int, color: tuple,
                           width: int, bar_width: int = WIDTH):
    """그라데이션 구분선 (좌우 페이드)"""
    for x_pos in range(bar_width):
        dist = abs(x_pos - bar_width // 2) / (bar_width // 2)
        alpha = int(255 * (1 - dist * 0.6))
        draw.line([(x_pos, y), (x_pos, y + width - 1)],
                  fill=(*color[:3], alpha))


def render_info_panel(
    template: dict,
    business_name: str,
    tagline: str = "",
    services: list[str] | None = None,
    phone: str = "",
    address: str = "",
    category: str = "기타",
    logo: Image.Image | None = None,
    qr: Image.Image | None = None,
    panel_height: int = 550,
) -> Image.Image:
    """550px 3-섹션 디자인 패널 렌더링"""
    services = services or []
    panel = Image.new("RGBA", (WIDTH, panel_height),
                      (*template.get("panel_bg", (255, 255, 255)), 255))
    draw = ImageDraw.Draw(panel)
    primary = template.get("primary", (50, 50, 50))

    # 상단 그라데이션 구분선
    _draw_gradient_divider(draw, 0, primary, 3)

    # 섹션 높이 분배
    sec1_h = int(panel_height * 0.33)
    sec2_h = int(panel_height * 0.36)
    sec3_h = panel_height - sec1_h - sec2_h

    sec1_y = 10
    sec2_y = sec1_h
    sec3_y = sec1_h + sec2_h

    # ─── 섹션 1: 홍보 영역 ───
    style = INFO_PANEL_STYLE.get(category, "brand_focus")
    if style == "promo":
        _render_promo_section(draw, panel, sec1_y, sec1_h - 10,
                              template, tagline, business_name)
    elif style == "info_card":
        _render_info_card_section(draw, panel, sec1_y, sec1_h - 10,
                                  template, services, tagline)
    else:
        _render_brand_focus_section(draw, panel, sec1_y, sec1_h - 10,
                                    template, business_name, tagline)

    # ─── 섹션 2: 브랜드 정보 + QR ───
    _render_brand_section(draw, panel, sec2_y, sec2_h,
                          template, business_name, tagline, logo, qr, style)

    # ─── 섹션 3: 연락처 푸터 ───
    _render_contact_footer(draw, panel, sec3_y, sec3_h,
                           template, phone, address)

    return panel


# ─────────────────────────────────────────────
# 섹션 1: 홍보 영역 (업종별 3패턴)
# ─────────────────────────────────────────────

def _render_promo_section(draw, panel, y, h, template, tagline, business_name):
    """패턴 A - 프로모션 강조 (음식점, 뷰티, 헬스, 골프)"""
    accent = template.get("accent", (255, 200, 50))
    text_color = template.get("panel_text", (50, 50, 50))
    primary = template.get("primary", (50, 50, 50))
    fonts = template.get("fonts", {})

    promo_text = tagline or f"{business_name} 방문을 환영합니다!"

    # 장식 라인 (좌측 상단)
    Decorations.draw_accent_line(panel, 80, y + 8, 200, accent, thickness=3)

    # 스파클 장식 + 홍보 문구
    font_name = fonts.get("accent", fonts.get("headline", "GmarketSansBold.otf"))
    font_size = 36
    font = _get_font(font_name, font_size)

    text = f"✨  {promo_text}  ✨"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    # 크기 조정
    while tw > WIDTH - 100 and font_size > 22:
        font_size -= 2
        font = _get_font(font_name, font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]

    tx = (WIDTH - tw) // 2
    ty = y + 30
    TextEffects.apply(draw, text, tx, ty, font, text_color, "highlight",
                      {"highlight_color": accent, "highlight_alpha": 120,
                       "padding_x": 15, "padding_y": 6})

    # 서브 카피 (박스 배경)
    sub_text = "자세한 내용은 QR코드를 확인하세요!"
    sub_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 22)
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_tw = sub_bbox[2] - sub_bbox[0]
    sub_tx = (WIDTH - sub_tw) // 2
    sub_ty = ty + 60
    TextEffects.apply(draw, sub_text, sub_tx, sub_ty, sub_font,
                      (*text_color[:3], 200), "bg_box",
                      {"bg_color": primary, "bg_alpha": 30,
                       "radius": 8, "padding": 10})

    # 장식 라인 (우측 하단)
    Decorations.draw_accent_line(panel, WIDTH - 280, y + h - 5, 200, accent, thickness=3)


def _render_info_card_section(draw, panel, y, h, template, services, tagline):
    """패턴 B - 정보 카드 (학원, 병원, 동물병원, 부동산)"""
    primary = template.get("primary", (50, 50, 50))
    text_color = template.get("panel_text", (50, 50, 50))
    fonts = template.get("fonts", {})

    items = services[:4] if services else []
    if not items and tagline:
        for sep in [",", "/", "|"]:
            if sep in tagline:
                items = [s.strip() for s in tagline.split(sep) if s.strip()][:4]
                break

    if items:
        badge_region = {"x": 60, "y": y + 20, "w": WIDTH - 120, "h": h - 25}
        badge_bg = (*primary[:3], 200)
        badge_text = template.get("text_on_primary", (255, 255, 255))
        draw_badge_grid(draw, items, badge_region,
                        bg_color=badge_bg, text_color=badge_text,
                        font_name=fonts.get("badge", "NanumSquareRoundEB.ttf"),
                        font_size=26, style="pill", cols=2)
    elif tagline:
        font_size = 34
        font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), font_size)
        bbox = draw.textbbox((0, 0), tagline, font=font)
        tw = bbox[2] - bbox[0]
        while tw > WIDTH - 120 and font_size > 22:
            font_size -= 2
            font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), font_size)
            bbox = draw.textbbox((0, 0), tagline, font=font)
            tw = bbox[2] - bbox[0]
        tx = (WIDTH - tw) // 2
        ty = y + (h - (bbox[3] - bbox[1])) // 2
        TextEffects.apply(draw, tagline, tx, ty, font, text_color, "outline",
                          {"stroke_width": 1, "stroke_color": (*primary[:3], 80)})
    else:
        # 빈 홍보 영역에 장식만
        accent = template.get("accent", (255, 200, 50))
        line_w = 120
        line_x = (WIDTH - line_w) // 2
        Decorations.draw_accent_line(panel, line_x, y + h // 2, line_w, accent, 2)


def _render_brand_focus_section(draw, panel, y, h, template, business_name, tagline):
    """패턴 C - 브랜드 중심 (안경, 핸드폰, 미용실, 기타)"""
    accent = template.get("accent", (255, 200, 50))
    text_color = template.get("panel_text", (50, 50, 50))
    fonts = template.get("fonts", {})

    # 상단 장식 라인
    line_w = 120
    line_x = (WIDTH - line_w) // 2
    Decorations.draw_accent_line(panel, line_x, y + 12, line_w, accent, thickness=2)

    # 브랜드명 (대형 display 폰트)
    font_name = fonts.get("display", fonts.get("headline", "GmarketSansBold.otf"))
    font_size = 52
    display_font = _get_font(font_name, font_size)
    bbox = draw.textbbox((0, 0), business_name, font=display_font)
    tw = bbox[2] - bbox[0]
    while tw > WIDTH - 120 and font_size > 28:
        font_size -= 2
        display_font = _get_font(font_name, font_size)
        bbox = draw.textbbox((0, 0), business_name, font=display_font)
        tw = bbox[2] - bbox[0]

    tx = (WIDTH - tw) // 2
    ty = y + 30
    draw.text((tx, ty), business_name, font=display_font, fill=text_color)

    # 서브타이틀 (tagline)
    if tagline:
        sub_size = 26
        sub_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), sub_size)
        sub_bbox = draw.textbbox((0, 0), tagline, font=sub_font)
        sub_tw = sub_bbox[2] - sub_bbox[0]
        while sub_tw > WIDTH - 120 and sub_size > 18:
            sub_size -= 2
            sub_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), sub_size)
            sub_bbox = draw.textbbox((0, 0), tagline, font=sub_font)
            sub_tw = sub_bbox[2] - sub_bbox[0]
        sub_tx = (WIDTH - sub_tw) // 2
        sub_ty = ty + bbox[3] - bbox[1] + 12
        dim_color = tuple(min(255, c + 60) for c in text_color[:3])
        draw.text((sub_tx, sub_ty), tagline, font=sub_font, fill=dim_color)

    # 하단 장식 라인
    Decorations.draw_accent_line(panel, line_x, y + h - 5, line_w, accent, thickness=2)


# ─────────────────────────────────────────────
# 섹션 2: 브랜드 정보 + QR
# ─────────────────────────────────────────────

def _render_brand_section(draw, panel, y, h, template,
                          business_name, tagline, logo, qr, style):
    """브랜드명 + 로고 (좌측) + QR코드 (우측)"""
    text_color = template.get("panel_text", (50, 50, 50))
    primary = template.get("primary", (50, 50, 50))
    fonts = template.get("fonts", {})

    # 상단 구분선
    draw.line([(MARGIN, y + 5), (WIDTH - MARGIN, y + 5)],
              fill=(*text_color[:3], 40), width=1)

    qr_size = 150
    qr_margin = 40
    qr_x = WIDTH - qr_margin - qr_size if qr else WIDTH
    content_right = qr_x - 30 if qr else WIDTH - MARGIN

    # 좌측: 로고 + 브랜드명
    x = MARGIN + 10
    cur_y = y + 25

    if logo:
        logo_h = min(logo.height, 60)
        logo_w = int(logo.width * (logo_h / logo.height))
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        panel.paste(logo_resized, (x, cur_y),
                    logo_resized if logo_resized.mode == "RGBA" else None)
        x += logo_w + 15

    # brand_focus 패턴은 섹션1에서 브랜드명 이미 표시
    if style != "brand_focus":
        name_size = 48
        name_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), name_size)
        bbox = draw.textbbox((0, 0), business_name, font=name_font)
        name_w = bbox[2] - bbox[0]
        while name_w > content_right - x and name_size > 28:
            name_size -= 2
            name_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), name_size)
            bbox = draw.textbbox((0, 0), business_name, font=name_font)
            name_w = bbox[2] - bbox[0]
        draw.text((x, cur_y), business_name, font=name_font, fill=text_color)
        cur_y += bbox[3] - bbox[1] + 12

        # tagline 서브텍스트
        if tagline:
            tag_size = 26
            tag_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), tag_size)
            tag_text = tagline if len(tagline) < 35 else tagline[:33] + "…"
            dim = tuple(min(255, c + 40) for c in text_color[:3])
            draw.text((MARGIN + 10, cur_y), tag_text, font=tag_font, fill=dim)
    else:
        # brand_focus: 간단한 서브텍스트만
        if tagline:
            sub_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 28)
            dim = tuple(min(255, c + 40) for c in text_color[:3])
            tag_text = tagline if len(tagline) < 30 else tagline[:28] + "…"
            draw.text((x, cur_y + 10), tag_text, font=sub_font, fill=dim)

    # QR코드 (우측, 둥근 테두리)
    if qr:
        qr_resized = qr.resize((qr_size, qr_size), Image.LANCZOS).convert("RGBA")
        qr_y = y + (h - qr_size) // 2
        border_pad = 8
        draw.rounded_rectangle(
            [qr_x - border_pad, qr_y - border_pad,
             qr_x + qr_size + border_pad, qr_y + qr_size + border_pad],
            radius=12, outline=(*primary[:3], 100), width=2,
        )
        panel.paste(qr_resized, (qr_x, qr_y), qr_resized)


# ─────────────────────────────────────────────
# 섹션 3: 연락처 푸터
# ─────────────────────────────────────────────

def _render_contact_footer(draw, panel, y, h, template, phone, address):
    """브랜드 컬러 배경 + 주소/전화번호"""
    primary = template.get("primary", (50, 50, 50))
    text_on_primary = template.get("text_on_primary", (255, 255, 255))
    fonts = template.get("fonts", {})

    # 브랜드 컬러 배경 (상단 둥근 모서리)
    draw.rounded_rectangle(
        [0, y, WIDTH, y + h],
        radius=20, fill=(*primary[:3], 240)
    )
    # 하단 직각 마감
    draw.rectangle([0, y + 20, WIDTH, y + h], fill=(*primary[:3], 240))

    content_y = y + 15

    if address:
        addr_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 24)
        icon_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 22)
        addr_text = address if len(address) < 40 else address[:38] + "…"
        draw.text((MARGIN, content_y + 5), "📍", font=icon_font,
                  fill=text_on_primary)
        draw.text((MARGIN + 35, content_y + 3), addr_text, font=addr_font,
                  fill=(*text_on_primary[:3], 200))
        content_y += 40

    if phone:
        # "예약·상담문의" 라벨
        label_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 20)
        draw.text((MARGIN, content_y), "예약·상담문의", font=label_font,
                  fill=(*text_on_primary[:3], 160))
        content_y += 28

        # 전화번호 (대형)
        phone_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), 44)
        icon_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 28)
        draw.text((MARGIN, content_y), "☎", font=icon_font,
                  fill=text_on_primary)
        draw.text((MARGIN + 42, content_y - 3), phone, font=phone_font,
                  fill=text_on_primary)


# ─────────────────────────────────────────────
# 하위 호환
# ─────────────────────────────────────────────

def render_bottom_bar(template: dict, business_name: str,
                      phone: str, address: str,
                      logo: Image.Image | None = None,
                      qr: Image.Image | None = None,
                      bar_style: str = "classic") -> Image.Image:
    """하위 호환 래퍼."""
    return render_info_panel(
        template=template,
        business_name=business_name,
        phone=phone,
        address=address,
        logo=logo,
        qr=qr,
    )
