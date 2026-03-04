"""사진 크롭/리사이즈/오버레이 처리"""
from PIL import Image
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


def apply_overlay_fast(img: Image.Image, overlay_type: str) -> Image.Image:
    """최적화된 오버레이 적용"""
    w, h = img.size

    if overlay_type == "gradient_bottom":
        # 상위 30%부터 하단까지 강한 그라데이션
        grad = Image.new("L", (1, h), 0)
        for y in range(h):
            if y >= h * 3 // 10:
                alpha = int(200 * (y - h * 3 // 10) / (h * 7 // 10))
                grad.putpixel((0, y), min(alpha, 220))
        grad = grad.resize((w, h), Image.BILINEAR)
        dark = Image.new("RGB", (w, h), (0, 0, 0))
        result = img.convert("RGB")
        result.paste(dark, mask=grad)
        return result

    elif overlay_type == "gradient_top_bottom":
        # 상하 양쪽 그라데이션 (인트로 씬용) - 가운데는 밝게, 상하단은 어둡게
        grad = Image.new("L", (1, h), 0)
        for y in range(h):
            if y < h * 2 // 10:
                # 상단 20%: 위에서 아래로 밝아짐
                alpha = int(180 * (1 - y / (h * 2 // 10)))
            elif y > h * 7 // 10:
                # 하단 30%: 아래로 어두워짐
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
        # 하단 60%에 강한 그라데이션 (CTA용)
        grad = Image.new("L", (1, h), 0)
        for y in range(h):
            if y >= h * 4 // 10:
                alpha = int(240 * (y - h * 4 // 10) / (h * 6 // 10))
                grad.putpixel((0, y), min(alpha, 240))
        grad = grad.resize((w, h), Image.BILINEAR)
        dark = Image.new("RGB", (w, h), (0, 0, 0))
        result = img.convert("RGB")
        result.paste(dark, mask=grad)
        return result

    elif overlay_type == "dark_overlay":
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 120))
        result = img.convert("RGBA")
        result = Image.alpha_composite(result, dark)
        return result.convert("RGB")

    elif overlay_type == "dark_heavy":
        # 강한 어둡게 (프로모션용)
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 180))
        result = img.convert("RGBA")
        result = Image.alpha_composite(result, dark)
        return result.convert("RGB")

    elif overlay_type == "soft_vignette":
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 50))
        result = img.convert("RGBA")
        result = Image.alpha_composite(result, dark)
        return result.convert("RGB")

    elif overlay_type == "light_overlay":
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 60))
        result = img.convert("RGBA")
        result = Image.alpha_composite(result, dark)
        return result.convert("RGB")

    return img.convert("RGB")
