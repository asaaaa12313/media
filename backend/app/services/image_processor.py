"""사진 크롭/리사이즈/오버레이 처리"""
from PIL import Image, ImageDraw
from app.core.config import WIDTH, CONTENT_HEIGHT


def center_crop_resize(img: Image.Image,
                       target_w: int = WIDTH,
                       target_h: int = CONTENT_HEIGHT) -> Image.Image:
    """이미지를 target 크기에 맞춰 center-crop + resize"""
    img = img.convert("RGB")
    src_ratio = img.width / img.height
    tgt_ratio = target_w / target_h

    if src_ratio > tgt_ratio:
        new_w = int(img.height * tgt_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = int(img.width / tgt_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def _gradient_mask(w: int, h: int, start_pct: float, end_pct: float,
                   max_alpha: int = 220, direction: str = "top_to_bottom") -> Image.Image:
    """1D 그라데이션 마스크 생성 헬퍼"""
    grad = Image.new("L", (1, h), 0)
    start_y = int(h * start_pct)
    end_y = int(h * end_pct)
    span = max(end_y - start_y, 1)
    for y in range(h):
        if direction == "top_to_bottom":
            if start_y <= y <= end_y:
                alpha = int(max_alpha * (y - start_y) / span)
                grad.putpixel((0, y), min(alpha, max_alpha))
            elif y > end_y:
                grad.putpixel((0, y), max_alpha)
        elif direction == "bottom_to_top":
            ry = h - 1 - y
            if start_y <= ry <= end_y:
                alpha = int(max_alpha * (ry - start_y) / span)
                grad.putpixel((0, y), min(alpha, max_alpha))
            elif ry > end_y:
                grad.putpixel((0, y), max_alpha)
    return grad.resize((w, h), Image.BILINEAR)


def apply_overlay_fast(img: Image.Image, overlay_type: str,
                       overlay_color: tuple = (0, 0, 0)) -> Image.Image:
    """최적화된 오버레이 적용. overlay_color로 브랜드 컬러 지원."""
    w, h = img.size
    color = overlay_color[:3]

    if overlay_type == "none":
        return img.convert("RGB")

    elif overlay_type == "gradient_bottom":
        grad = _gradient_mask(w, h, 0.3, 1.0, 220)
        dark = Image.new("RGB", (w, h), (0, 0, 0))
        result = img.convert("RGB")
        result.paste(dark, mask=grad)
        return result

    elif overlay_type == "gradient_top_bottom":
        grad = Image.new("L", (1, h), 0)
        for y in range(h):
            if y < h * 2 // 10:
                alpha = int(180 * (1 - y / (h * 2 // 10)))
            elif y > h * 7 // 10:
                alpha = int(220 * (y - h * 7 // 10) / (h * 3 // 10))
            else:
                alpha = 0
            grad.putpixel((0, y), min(alpha, 220))
        grad = grad.resize((w, h), Image.BILINEAR)
        dark = Image.new("RGB", (w, h), (0, 0, 0))
        result = img.convert("RGB")
        result.paste(dark, mask=grad)
        return result

    elif overlay_type == "gradient_bottom_heavy":
        grad = _gradient_mask(w, h, 0.4, 1.0, 240)
        dark = Image.new("RGB", (w, h), (0, 0, 0))
        result = img.convert("RGB")
        result.paste(dark, mask=grad)
        return result

    elif overlay_type == "dark_overlay":
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 120))
        result = img.convert("RGBA")
        return Image.alpha_composite(result, dark).convert("RGB")

    elif overlay_type == "dark_heavy":
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 180))
        result = img.convert("RGBA")
        return Image.alpha_composite(result, dark).convert("RGB")

    elif overlay_type == "soft_vignette":
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 50))
        result = img.convert("RGBA")
        return Image.alpha_composite(result, dark).convert("RGB")

    elif overlay_type == "light_overlay":
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 60))
        result = img.convert("RGBA")
        return Image.alpha_composite(result, dark).convert("RGB")

    # ── 새 오버레이 타입들 ──

    elif overlay_type == "color_gradient_bottom":
        grad = _gradient_mask(w, h, 0.3, 1.0, 200)
        dark = Image.new("RGB", (w, h), color)
        result = img.convert("RGB")
        result.paste(dark, mask=grad)
        return result

    elif overlay_type == "color_gradient_top":
        grad = _gradient_mask(w, h, 0.0, 0.5, 180, direction="bottom_to_top")
        dark = Image.new("RGB", (w, h), color)
        result = img.convert("RGB")
        result.paste(dark, mask=grad)
        return result

    elif overlay_type == "color_overlay_light":
        overlay = Image.new("RGBA", (w, h), (*color, 60))
        result = img.convert("RGBA")
        return Image.alpha_composite(result, overlay).convert("RGB")

    elif overlay_type == "color_overlay_heavy":
        overlay = Image.new("RGBA", (w, h), (*color, 150))
        result = img.convert("RGBA")
        return Image.alpha_composite(result, overlay).convert("RGB")

    elif overlay_type == "diagonal_gradient":
        # 좌하→우상 대각선 그라데이션
        result = img.convert("RGBA")
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(h):
            for x_step in range(0, w, 4):
                progress = (x_step / w * 0.4 + y / h * 0.6)
                alpha = int(200 * min(1.0, progress))
                draw.rectangle([x_step, y, x_step + 3, y], fill=(0, 0, 0, alpha))
        return Image.alpha_composite(result, overlay).convert("RGB")

    elif overlay_type == "vignette":
        # 방사형 비네팅: 가장자리 어둡게
        result = img.convert("RGBA")
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cx, cy = w // 2, h // 2
        # 빠른 근사: 동심 타원 레이어
        steps = 30
        for i in range(steps):
            ratio = 1.0 - i / steps
            alpha = int(160 * (1.0 - ratio) ** 2)
            rx = int(cx * (0.5 + ratio * 0.7))
            ry = int(cy * (0.5 + ratio * 0.7))
            mask = Image.new("L", (w, h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
            ring = Image.new("RGBA", (w, h), (0, 0, 0, alpha))
            ring.putalpha(mask)
            # 반전: 타원 바깥을 어둡게
        # 단순 방식으로 대체
        for ring_i in range(8):
            shrink = 0.15 + ring_i * 0.1
            alpha = int(25 * (ring_i + 1))
            rx = int(cx * (1.0 - shrink))
            ry = int(cy * (1.0 - shrink))
            ring_mask = Image.new("L", (w, h), alpha)
            ring_draw = ImageDraw.Draw(ring_mask)
            ring_draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=0)
            dark_layer = Image.new("RGB", (w, h), (0, 0, 0))
            result_rgb = result.convert("RGB")
            result_rgb.paste(dark_layer, mask=ring_mask)
            result = result_rgb.convert("RGBA")
        return result.convert("RGB")

    elif overlay_type == "duotone":
        # 듀오톤: 이미지를 그레이스케일로 변환 후 2색 매핑
        gray = img.convert("L")
        result = Image.new("RGB", (w, h))
        color2 = (255, 255, 255)  # 밝은 톤은 흰색
        pixels_gray = gray.load()
        pixels_out = result.load()
        for y in range(h):
            for x in range(w):
                v = pixels_gray[x, y] / 255.0
                r = int(color[0] * (1 - v) + color2[0] * v)
                g = int(color[1] * (1 - v) + color2[1] * v)
                b = int(color[2] * (1 - v) + color2[2] * v)
                pixels_out[x, y] = (r, g, b)
        # 원본과 블렌딩 (50%)
        original = img.convert("RGB")
        return Image.blend(original, result, 0.5)

    return img.convert("RGB")
