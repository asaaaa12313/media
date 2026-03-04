"""고정 하단 정보 바 렌더링 (200px)

레퍼런스 스타일: 주소 + 전화번호 + QR코드를 한 줄로 컴팩트하게 배치
전 씬에서 동일하게 표시됨
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from app.core.config import WIDTH, BOTTOM_BAR_HEIGHT
from app.services.text_layout import (
    _get_font,
    MARGIN,
)


def _draw_gradient_divider(draw: ImageDraw.Draw, y: int, color: tuple,
                           width: int, bar_width: int = WIDTH):
    """그라데이션 구분선 (좌우 페이드)"""
    for x_pos in range(bar_width):
        dist = abs(x_pos - bar_width // 2) / (bar_width // 2)
        alpha = int(255 * (1 - dist * 0.6))
        draw.line([(x_pos, y), (x_pos, y + width - 1)],
                  fill=(*color[:3], alpha))


def render_bottom_bar(template: dict, _business_name: str,
                      phone: str, address: str,
                      logo: Image.Image | None = None,
                      qr: Image.Image | None = None,
                      bar_style: str = "classic") -> Image.Image:
    """고정 하단 정보 바 (1080 x 200) 렌더링. 전 씬 동일."""
    style = bar_style or "classic"
    if style == "centered":
        return _render_centered_bar(template, phone, address, logo, qr)
    elif style == "brand_bar":
        return _render_brand_bar(template, _business_name, phone, address, logo, qr)
    elif style == "minimal":
        return _render_minimal_bar(template, phone, qr)
    elif style == "card_style":
        return _render_card_bar(template, phone, address, logo, qr)
    return _render_classic_bar(template, phone, address, logo, qr)


def _render_classic_bar(template: dict, phone: str, address: str,
                        logo: Image.Image | None, qr: Image.Image | None) -> Image.Image:
    """기존 스타일: 좌측 정보 + 우측 QR"""
    bar = Image.new("RGBA", (WIDTH, BOTTOM_BAR_HEIGHT), (*template["panel_bg"], 255))
    draw = ImageDraw.Draw(bar)
    text_color = template["panel_text"]
    fonts = template["fonts"]

    _draw_gradient_divider(draw, 0, template["primary"], 3)

    qr_size = 130
    qr_margin = 30
    qr_x = WIDTH - qr_margin - qr_size if qr else WIDTH
    content_right = qr_x - 20 if qr else WIDTH - MARGIN

    x = MARGIN
    y_top = 25

    if logo:
        logo_h = min(logo.height, 50)
        logo_w = int(logo.width * (logo_h / logo.height))
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        bar.paste(logo_resized, (x, y_top),
                  logo_resized if logo_resized.mode == "RGBA" else None)
        x += logo_w + 12

    if address:
        addr_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 22)
        max_addr_w = content_right - x
        bbox = draw.textbbox((0, 0), address, font=addr_font)
        addr_text = address
        while bbox[2] - bbox[0] > max_addr_w and len(addr_text) > 10:
            addr_text = addr_text[:-2] + "…"
            bbox = draw.textbbox((0, 0), addr_text, font=addr_font)
        dim_color = tuple(min(255, c + 60) for c in text_color[:3])
        draw.text((x, y_top + 8), addr_text, font=addr_font, fill=dim_color)

    if phone:
        phone_y = y_top + 55
        phone_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), 46)
        icon_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 28)
        draw.text((x, phone_y + 8), "☎", font=icon_font, fill=template["primary"])
        draw.text((x + 40, phone_y), phone, font=phone_font, fill=text_color)

    if qr:
        qr_resized = qr.resize((qr_size, qr_size), Image.LANCZOS).convert("RGBA")
        qr_y = (BOTTOM_BAR_HEIGHT - qr_size) // 2 + 5
        bar.paste(qr_resized, (qr_x, qr_y), qr_resized)

    return bar


def _render_centered_bar(template: dict, phone: str, address: str,
                         logo: Image.Image | None, qr: Image.Image | None) -> Image.Image:
    """중앙 정렬: 전화번호 크게 + 주소 작게"""
    bar = Image.new("RGBA", (WIDTH, BOTTOM_BAR_HEIGHT), (*template["panel_bg"], 255))
    draw = ImageDraw.Draw(bar)
    text_color = template["panel_text"]
    fonts = template["fonts"]

    _draw_gradient_divider(draw, 0, template["primary"], 3)

    # 로고 중앙 상단
    if logo:
        logo_h = min(logo.height, 40)
        logo_w = int(logo.width * (logo_h / logo.height))
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        lx = (WIDTH - logo_w) // 2
        bar.paste(logo_resized, (lx, 12),
                  logo_resized if logo_resized.mode == "RGBA" else None)

    # 전화번호 중앙 크게
    if phone:
        phone_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), 52)
        bbox = draw.textbbox((0, 0), phone, font=phone_font)
        pw = bbox[2] - bbox[0]
        px = (WIDTH - pw) // 2
        py = 55 if logo else 40
        draw.text((px, py), phone, font=phone_font, fill=template["primary"])

    # 주소 하단 작게
    if address:
        addr_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 20)
        bbox = draw.textbbox((0, 0), address, font=addr_font)
        aw = bbox[2] - bbox[0]
        ax = (WIDTH - aw) // 2
        dim_color = tuple(min(255, c + 60) for c in text_color[:3])
        draw.text((ax, BOTTOM_BAR_HEIGHT - 40), address, font=addr_font, fill=dim_color)

    # QR 우측
    if qr:
        qr_size = 110
        qr_resized = qr.resize((qr_size, qr_size), Image.LANCZOS).convert("RGBA")
        bar.paste(qr_resized, (WIDTH - 30 - qr_size, (BOTTOM_BAR_HEIGHT - qr_size) // 2), qr_resized)

    return bar


def _render_brand_bar(template: dict, business_name: str,
                      phone: str, address: str,
                      logo: Image.Image | None, qr: Image.Image | None) -> Image.Image:
    """브랜드 컬러 배경 + 로고 중앙"""
    primary = template.get("primary", (50, 50, 50))
    bar = Image.new("RGBA", (WIDTH, BOTTOM_BAR_HEIGHT), (*primary, 255))
    draw = ImageDraw.Draw(bar)
    fonts = template["fonts"]
    text_color = template.get("text_on_primary", (255, 255, 255))

    # 로고 좌측
    x = MARGIN
    if logo:
        logo_h = min(logo.height, 60)
        logo_w = int(logo.width * (logo_h / logo.height))
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        ly = (BOTTOM_BAR_HEIGHT - logo_h) // 2
        bar.paste(logo_resized, (x, ly),
                  logo_resized if logo_resized.mode == "RGBA" else None)
        x += logo_w + 20
    elif business_name:
        name_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), 36)
        draw.text((x, 30), business_name, font=name_font, fill=text_color)
        bbox = draw.textbbox((0, 0), business_name, font=name_font)
        x += bbox[2] - bbox[0] + 20

    # 세로 구분선
    draw.line([(x, 30), (x, BOTTOM_BAR_HEIGHT - 30)],
              fill=(*text_color[:3], 100), width=2)
    x += 20

    # 전화 + 주소
    if phone:
        phone_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), 42)
        draw.text((x, 35), phone, font=phone_font, fill=text_color)
    if address:
        addr_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 20)
        addr_text = address if len(address) < 30 else address[:28] + "…"
        draw.text((x, 95), addr_text, font=addr_font, fill=(*text_color[:3], 180))

    # QR 우측
    if qr:
        qr_size = 120
        qr_resized = qr.resize((qr_size, qr_size), Image.LANCZOS).convert("RGBA")
        bar.paste(qr_resized, (WIDTH - 30 - qr_size, (BOTTOM_BAR_HEIGHT - qr_size) // 2), qr_resized)

    return bar


def _render_minimal_bar(template: dict, phone: str,
                        qr: Image.Image | None) -> Image.Image:
    """미니멀: 전화번호만 크게"""
    bar = Image.new("RGBA", (WIDTH, BOTTOM_BAR_HEIGHT), (*template["panel_bg"], 255))
    draw = ImageDraw.Draw(bar)
    fonts = template["fonts"]

    _draw_gradient_divider(draw, 0, template["primary"], 3)

    if phone:
        phone_font = _get_font(fonts.get("headline", "GmarketSansBold.otf"), 60)
        bbox = draw.textbbox((0, 0), phone, font=phone_font)
        pw = bbox[2] - bbox[0]
        px = (WIDTH - pw) // 2
        py = (BOTTOM_BAR_HEIGHT - (bbox[3] - bbox[1])) // 2
        draw.text((px, py), phone, font=phone_font, fill=template["primary"])

    if qr:
        qr_size = 120
        qr_resized = qr.resize((qr_size, qr_size), Image.LANCZOS).convert("RGBA")
        bar.paste(qr_resized, (WIDTH - 30 - qr_size, (BOTTOM_BAR_HEIGHT - qr_size) // 2), qr_resized)

    return bar


def _render_card_bar(template: dict, phone: str, address: str,
                     logo: Image.Image | None, qr: Image.Image | None) -> Image.Image:
    """명함 스타일: 아이콘 + 2열 배치"""
    bar = Image.new("RGBA", (WIDTH, BOTTOM_BAR_HEIGHT), (*template["panel_bg"], 255))
    draw = ImageDraw.Draw(bar)
    text_color = template["panel_text"]
    fonts = template["fonts"]

    _draw_gradient_divider(draw, 0, template["primary"], 3)

    # 좌측 로고
    x = MARGIN
    if logo:
        logo_h = min(logo.height, 80)
        logo_w = int(logo.width * (logo_h / logo.height))
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        ly = (BOTTOM_BAR_HEIGHT - logo_h) // 2
        bar.paste(logo_resized, (x, ly),
                  logo_resized if logo_resized.mode == "RGBA" else None)
        x += logo_w + 24

    # 세로 구분선
    draw.line([(x, 25), (x, BOTTOM_BAR_HEIGHT - 25)],
              fill=(*text_color[:3], 60), width=1)
    x += 20

    # 우측 정보 2행
    icon_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 22)
    info_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 24)

    if phone:
        draw.text((x, 40), "📞", font=icon_font, fill=template["primary"])
        draw.text((x + 35, 38), phone, font=info_font, fill=text_color)

    if address:
        addr_text = address if len(address) < 25 else address[:23] + "…"
        draw.text((x, 90), "📍", font=icon_font, fill=template["primary"])
        dim = tuple(min(255, c + 40) for c in text_color[:3])
        draw.text((x + 35, 88), addr_text, font=info_font, fill=dim)

    # QR 우측
    if qr:
        qr_size = 120
        qr_resized = qr.resize((qr_size, qr_size), Image.LANCZOS).convert("RGBA")
        bar.paste(qr_resized, (WIDTH - 30 - qr_size, (BOTTOM_BAR_HEIGHT - qr_size) // 2), qr_resized)

    return bar


# 하위 호환: 기존 render_info_panel 호출 지원
def render_info_panel(template: dict, business_name: str,
                      _tagline: str, _services: list[str],
                      phone: str, address: str,
                      logo: Image.Image | None = None,
                      qr: Image.Image | None = None) -> Image.Image:
    """하위 호환 래퍼. 새 render_bottom_bar로 위임."""
    return render_bottom_bar(template, business_name, phone, address, logo, qr)
