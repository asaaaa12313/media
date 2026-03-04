"""고정 하단 정보 바 렌더링 (200px)

레퍼런스 스타일: 주소 + 전화번호 + QR코드를 한 줄로 컴팩트하게 배치
전 씬에서 동일하게 표시됨
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from app.core.config import WIDTH, BOTTOM_BAR_HEIGHT
from app.services.text_layout import (
    draw_divider, _get_font,
    MARGIN,
)


def render_bottom_bar(template: dict, _business_name: str,
                      phone: str, address: str,
                      logo: Image.Image | None = None,
                      qr: Image.Image | None = None) -> Image.Image:
    """고정 하단 정보 바 (1080 x 200) 렌더링. 전 씬 동일."""
    bar = Image.new("RGBA", (WIDTH, BOTTOM_BAR_HEIGHT), (*template["panel_bg"], 255))
    draw = ImageDraw.Draw(bar)
    text_color = template["panel_text"]
    fonts = template["fonts"]

    # 상단 구분선 (브랜드 컬러, 3px)
    draw_divider(draw, 0, template["primary"], margin=0, width=3)

    # QR 코드 영역 계산
    qr_size = 130
    qr_margin = 30
    qr_x = WIDTH - qr_margin - qr_size if qr else WIDTH
    content_right = qr_x - 20 if qr else WIDTH - MARGIN

    # 좌측: 로고 (있으면) + 주소 + 전화
    x = MARGIN
    y_top = 25

    if logo:
        logo_h = min(logo.height, 50)
        logo_w = int(logo.width * (logo_h / logo.height))
        logo_resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
        bar.paste(logo_resized, (x, y_top),
                  logo_resized if logo_resized.mode == "RGBA" else None)
        x += logo_w + 12

    # 주소 (상단)
    if address:
        addr_font_name = fonts.get("body", "Pretendard-Bold.otf")
        addr_font = _get_font(addr_font_name, 22)
        # 주소가 너무 길면 잘라내기
        max_addr_w = content_right - x
        bbox = draw.textbbox((0, 0), address, font=addr_font)
        addr_text = address
        while bbox[2] - bbox[0] > max_addr_w and len(addr_text) > 10:
            addr_text = addr_text[:-2] + "…"
            bbox = draw.textbbox((0, 0), addr_text, font=addr_font)
        dim_color = tuple(min(255, c + 60) for c in text_color[:3])
        draw.text((x, y_top + 8), addr_text, font=addr_font, fill=dim_color)

    # 전화 아이콘 + 번호 (하단, 크게)
    if phone:
        phone_y = y_top + 55
        phone_font_name = fonts.get("headline", "GmarketSansBold.otf")
        phone_font = _get_font(phone_font_name, 46)

        # 전화 아이콘 (텍스트로 대체)
        icon_font = _get_font(fonts.get("body", "Pretendard-Bold.otf"), 28)
        draw.text((x, phone_y + 8), "☎", font=icon_font, fill=template["primary"])

        # 전화번호
        draw.text((x + 40, phone_y), phone, font=phone_font, fill=text_color)

    # 우측: QR 코드
    if qr:
        qr_resized = qr.resize((qr_size, qr_size), Image.LANCZOS).convert("RGBA")
        qr_y = (BOTTOM_BAR_HEIGHT - qr_size) // 2 + 5
        bar.paste(qr_resized, (qr_x, qr_y), qr_resized)

    return bar


# 하위 호환: 기존 render_info_panel 호출 지원
def render_info_panel(template: dict, business_name: str,
                      _tagline: str, _services: list[str],
                      phone: str, address: str,
                      logo: Image.Image | None = None,
                      qr: Image.Image | None = None) -> Image.Image:
    """하위 호환 래퍼. 새 render_bottom_bar로 위임."""
    return render_bottom_bar(template, business_name, phone, address, logo, qr)
