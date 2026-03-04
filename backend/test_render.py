"""포커스미디어 렌더링 엔진 테스트 스크립트

레퍼런스 영상의 프레임과 비교할 수 있도록 테스트 이미지를 생성합니다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from PIL import Image

from app.services.template_engine import get_template
from app.services.zone_renderer import ZoneRenderer
from app.services.info_panel import render_info_panel
from app.services.brand_system import load_logo, load_logo_small
from app.services.qr_generator import generate_qr
from app.services.image_processor import center_crop_resize
from app.core.config import WIDTH, HEIGHT, ZONE1_HEIGHT, ZONE2_HEIGHT, ZONE3_HEIGHT


def test_render(category: str = "헬스"):
    """단일 카테고리의 테스트 프레임 생성"""
    output_dir = Path(__file__).parent / "test_output"
    output_dir.mkdir(exist_ok=True)

    # 템플릿
    template = get_template(category)
    print(f"카테고리: {category}")
    print(f"메인 컬러: {template['primary']}")

    # 테스트용 더미 사진 (그라데이션)
    photo = Image.new("RGB", (1080, 880), (100, 120, 140))
    for y in range(880):
        for x in range(0, 1080, 4):
            r = int(80 + 100 * (x / 1080))
            g = int(100 + 80 * (y / 880))
            b = int(140 + 60 * ((x + y) / (1080 + 880)))
            for dx in range(4):
                if x + dx < 1080:
                    photo.putpixel((x + dx, y), (r, g, b))

    # QR 코드
    qr = generate_qr("https://example.com")

    # Zone 3 패널
    panel = render_info_panel(
        template,
        business_name="테스트 업체",
        tagline="프리미엄 서비스를 제공합니다",
        services=["PT", "그룹수업", "사우나", "GX", "요가", "필라테스"],
        phone="02-1234-5678",
        address="서울시 강남구 역삼동 123-45 1층",
        logo=None,
        qr=qr,
    )
    panel.save(output_dir / f"zone3_{category}.png")
    print(f"Zone 3 패널: {panel.size}")

    # ZoneRenderer
    renderer = ZoneRenderer(template, logo=None, business_name="테스트 업체")
    renderer.set_panel_cache(panel)

    # 전체 프레임
    frame = renderer.render_frame(
        photo,
        headline="최고의 선택",
        subtext="전문 트레이너와 함께\n건강한 라이프를 시작하세요",
    )
    frame.save(output_dir / f"frame_{category}.png")
    print(f"전체 프레임: {frame.size}")
    assert frame.size == (WIDTH, HEIGHT), f"프레임 크기 오류: {frame.size}"

    print(f"✅ {category} 테스트 완료 → {output_dir}/frame_{category}.png")
    return frame


def test_all_categories():
    """모든 카테고리 테스트"""
    categories = ["음식점", "헬스", "뷰티", "학원", "병원", "안경",
                   "부동산", "골프", "핸드폰", "동물병원", "미용실", "기타"]
    for cat in categories:
        test_render(cat)
    print(f"\n✅ 전체 {len(categories)}개 카테고리 테스트 완료")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_render(sys.argv[1])
    else:
        test_all_categories()
