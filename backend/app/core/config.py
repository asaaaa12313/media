import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")
TEMP_DIR = BASE_DIR / "temp"
FONTS_DIR = BASE_DIR / "fonts"
ASSETS_DIR = BASE_DIR / "assets"
_google_drive_bgm = Path(os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-tkfkdgowldms@gmail.com/내 드라이브/3.위즈더플래닝 디자인/숏폼/BGM"
))
_local_bgm = BASE_DIR / "bgm"
BGM_DIR = _google_drive_bgm if _google_drive_bgm.exists() else _local_bgm

TEMP_DIR.mkdir(exist_ok=True)

# AI API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

# 영상 설정
TARGET_DURATION = 15.0
WIDTH = 1080
HEIGHT = 1920  # 표준 9:16
FPS = 30

# 레이아웃: 자유 콘텐츠 + 고정 하단 바
CONTENT_HEIGHT = 1720   # 자유 콘텐츠 영역
BOTTOM_BAR_HEIGHT = 200  # 고정 하단 정보 바

# 하위 호환용 (기존 import 깨지지 않도록)
ZONE1_HEIGHT = 0
ZONE2_HEIGHT = CONTENT_HEIGHT
ZONE3_HEIGHT = BOTTOM_BAR_HEIGHT

# 텍스트 배치 7개 영역 (콘텐츠 영역 내 좌표)
TEXT_REGIONS = {
    "top_left":     {"x": 60,  "y": 60,   "w": 460, "h": 280, "align": "left"},
    "top_center":   {"x": 100, "y": 60,   "w": 880, "h": 280, "align": "center"},
    "top_right":    {"x": 560, "y": 60,   "w": 460, "h": 280, "align": "right"},
    "mid_left":     {"x": 60,  "y": 500,  "w": 460, "h": 500, "align": "left"},
    "mid_center":   {"x": 100, "y": 500,  "w": 880, "h": 500, "align": "center"},
    "mid_right":    {"x": 560, "y": 500,  "w": 460, "h": 500, "align": "right"},
    "bottom_wide":  {"x": 60,  "y": 1200, "w": 960, "h": 400, "align": "center"},
}

# 씬 타입별 기본 레이아웃
SCENE_LAYOUTS = {
    "intro": {
        "photo_mode": "fullscreen",
        "photo_overlay": "gradient_top_bottom",
        "text_slots": [
            {"region": "top_left", "role": "brand_name", "font_role": "headline", "size": 44, "effect": "shadow"},
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 96, "effect": "outline"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 36, "effect": "bg_box"},
        ],
    },
    "feature_list": {
        "photo_mode": "top_half",
        "photo_overlay": "gradient_bottom",
        "text_slots": [
            {"region": "top_center", "role": "headline", "font_role": "display", "size": 80, "effect": "outline"},
            {"region": "mid_left", "role": "feature_list", "font_role": "body", "size": 32, "effect": "none"},
            {"region": "bottom_wide", "role": "badge_grid", "font_role": "badge", "size": 24, "effect": "none"},
        ],
    },
    "promotion": {
        "photo_mode": "fullscreen",
        "photo_overlay": "dark_heavy",
        "text_slots": [
            {"region": "top_center", "role": "accent", "font_role": "handwriting", "size": 44, "effect": "none"},
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 110, "effect": "outline"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "accent", "size": 40, "effect": "highlight"},
        ],
    },
    "gallery": {
        "photo_mode": "grid_2x2",
        "photo_overlay": "light_overlay",
        "text_slots": [
            {"region": "top_center", "role": "headline", "font_role": "headline", "size": 64, "effect": "bg_box"},
        ],
    },
    "cta": {
        "photo_mode": "fullscreen",
        "photo_overlay": "gradient_bottom_heavy",
        "text_slots": [
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 88, "effect": "outline"},
            {"region": "bottom_wide", "role": "cta_text", "font_role": "headline", "size": 48, "effect": "bg_box"},
        ],
    },
    "info_card": {
        "photo_mode": "top_half",
        "photo_overlay": "gradient_bottom",
        "bottom_template": True,
        "text_slots": [
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 72, "effect": "none"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 32, "effect": "none"},
        ],
    },
    "highlight": {
        "photo_mode": "fullscreen",
        "photo_overlay": "dark_overlay",
        "text_slots": [
            {"region": "top_center", "role": "headline", "font_role": "display", "size": 80, "effect": "outline"},
            {"region": "mid_center", "role": "subtext", "font_role": "body", "size": 36, "effect": "bg_box"},
        ],
    },
    "review": {
        "photo_mode": "top_half",
        "photo_overlay": "light_overlay",
        "bottom_template": True,
        "text_slots": [
            {"region": "mid_center", "role": "headline", "font_role": "handwriting", "size": 64, "effect": "none"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 28, "effect": "none"},
        ],
    },
}

# 씬 레이아웃 변형 (각 씬 타입에 2~3가지 대안 레이아웃)
SCENE_LAYOUT_VARIANTS = {
    "intro": [
        # 변형 1: 좌측 정렬 + 브랜드 컬러 그라데이션
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "color_gradient_bottom",
            "text_slots": [
                {"region": "top_left", "role": "brand_name", "font_role": "headline", "size": 40, "effect": "none"},
                {"region": "mid_left", "role": "headline", "font_role": "display", "size": 88, "effect": "shadow_3d"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 34, "effect": "underline_accent"},
            ],
        },
        # 변형 2: 하단 집중 + 네온
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "gradient_bottom_heavy",
            "text_slots": [
                {"region": "top_right", "role": "brand_name", "font_role": "accent", "size": 36, "effect": "bg_pill"},
                {"region": "bottom_wide", "role": "headline", "font_role": "display", "size": 80, "effect": "neon"},
            ],
        },
    ],
    "feature_list": [
        # 변형 1: 좌우 분할
        {
            "photo_mode": "left_half",
            "photo_overlay": "none",
            "text_slots": [
                {"region": "mid_right", "role": "headline", "font_role": "display", "size": 64, "effect": "none"},
                {"region": "bottom_wide", "role": "feature_list", "font_role": "body", "size": 28, "effect": "none"},
            ],
        },
        # 변형 2: 상단 2/3 사진
        {
            "photo_mode": "top_two_thirds",
            "photo_overlay": "gradient_bottom",
            "text_slots": [
                {"region": "top_center", "role": "headline", "font_role": "display", "size": 72, "effect": "outline"},
                {"region": "bottom_wide", "role": "badge_grid", "font_role": "badge", "size": 22, "effect": "none"},
            ],
        },
    ],
    "promotion": [
        # 변형 1: 좌우 분할
        {
            "photo_mode": "left_half",
            "photo_overlay": "none",
            "text_slots": [
                {"region": "mid_right", "role": "headline", "font_role": "display", "size": 72, "effect": "shadow_3d"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "accent", "size": 40, "effect": "highlight"},
            ],
        },
        # 변형 2: 컬러 오버레이 + 이중 외곽선
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "color_overlay_heavy",
            "text_slots": [
                {"region": "top_center", "role": "accent", "font_role": "handwriting", "size": 44, "effect": "none"},
                {"region": "mid_center", "role": "headline", "font_role": "display", "size": 100, "effect": "double_outline"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 36, "effect": "bg_pill"},
            ],
        },
    ],
    "gallery": [
        # 변형 1: 원형 마스크
        {
            "photo_mode": "center_circle",
            "photo_overlay": "none",
            "text_slots": [
                {"region": "top_center", "role": "headline", "font_role": "headline", "size": 56, "effect": "none"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 28, "effect": "none"},
            ],
        },
    ],
    "cta": [
        # 변형 1: 브랜드 컬러 그라데이션
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "color_gradient_bottom",
            "text_slots": [
                {"region": "mid_center", "role": "headline", "font_role": "display", "size": 88, "effect": "double_outline"},
                {"region": "bottom_wide", "role": "cta_text", "font_role": "headline", "size": 48, "effect": "bg_pill"},
            ],
        },
        # 변형 2: 비네팅 + 네온
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "vignette",
            "text_slots": [
                {"region": "mid_center", "role": "headline", "font_role": "display", "size": 80, "effect": "neon"},
                {"region": "bottom_wide", "role": "cta_text", "font_role": "headline", "size": 44, "effect": "underline_accent"},
            ],
        },
    ],
    "info_card": [
        # 변형 1: 우측 사진
        {
            "photo_mode": "right_half",
            "photo_overlay": "none",
            "bottom_template": False,
            "text_slots": [
                {"region": "mid_left", "role": "headline", "font_role": "display", "size": 64, "effect": "none"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 28, "effect": "none"},
            ],
        },
    ],
    "highlight": [
        # 변형 1: 대각선 그라데이션
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "diagonal_gradient",
            "text_slots": [
                {"region": "top_left", "role": "headline", "font_role": "display", "size": 76, "effect": "shadow_3d"},
                {"region": "mid_left", "role": "subtext", "font_role": "body", "size": 32, "effect": "bg_box"},
            ],
        },
    ],
    "review": [
        # 변형 1: 전체 화면 + 따옴표 장식
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "dark_overlay",
            "text_slots": [
                {"region": "mid_center", "role": "headline", "font_role": "handwriting", "size": 60, "effect": "none"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 28, "effect": "bg_box"},
            ],
            "decorations": [
                {"type": "quote_marks", "x": 80, "y": 420, "color_key": "accent", "size": 80},
                {"type": "star_rating", "x": 380, "y": 1100, "color_key": "accent", "rating": 5, "size": 36},
            ],
        },
    ],
}

# 업종별 기본 씬 시퀀스 (확장 가능 - 최대 10씬 풀까지 정의)
CATEGORY_SCENE_SEQUENCE = {
    "음식점":   ["intro", "gallery", "info_card", "promotion", "highlight", "feature_list", "review", "info_card", "promotion", "cta"],
    "헬스":     ["intro", "feature_list", "info_card", "highlight", "promotion", "feature_list", "review", "gallery", "info_card", "cta"],
    "뷰티":     ["intro", "promotion", "info_card", "gallery", "highlight", "review", "feature_list", "info_card", "promotion", "cta"],
    "학원":     ["intro", "feature_list", "info_card", "promotion", "highlight", "feature_list", "review", "gallery", "info_card", "cta"],
    "병원":     ["intro", "feature_list", "info_card", "promotion", "highlight", "review", "feature_list", "gallery", "info_card", "cta"],
    "안경":     ["intro", "promotion", "info_card", "feature_list", "highlight", "gallery", "review", "info_card", "promotion", "cta"],
    "부동산":   ["intro", "feature_list", "info_card", "promotion", "highlight", "gallery", "review", "feature_list", "info_card", "cta"],
    "골프":     ["intro", "promotion", "info_card", "gallery", "highlight", "feature_list", "review", "info_card", "promotion", "cta"],
    "핸드폰":   ["intro", "promotion", "info_card", "feature_list", "highlight", "gallery", "review", "info_card", "promotion", "cta"],
    "동물병원": ["intro", "feature_list", "info_card", "promotion", "highlight", "review", "gallery", "feature_list", "info_card", "cta"],
    "미용실":   ["intro", "promotion", "info_card", "gallery", "highlight", "review", "feature_list", "info_card", "promotion", "cta"],
    "기타":     ["intro", "feature_list", "info_card", "promotion", "highlight", "gallery", "review", "feature_list", "info_card", "cta"],
}


def get_scene_sequence(category: str, num_scenes: int) -> list[str]:
    """카테고리와 씬 개수에 맞는 시퀀스 반환"""
    full_seq = CATEGORY_SCENE_SEQUENCE.get(category, CATEGORY_SCENE_SEQUENCE["기타"])
    return full_seq[:num_scenes]

# 씬 타이밍 (하위 호환용 기본값)
SCENE_TIMINGS = [
    (0.0, 3.0),
    (3.0, 7.0),
    (7.0, 11.0),
    (11.0, 15.0),
]
TRANSITION_DURATION = 0.5  # 씬 전환 크로스페이드 (초)

# 동적 씬 설정
MIN_SCENES = 4
MAX_SCENES = 10


def generate_scene_timings(num_scenes: int, total_duration: float = 15.0) -> list[tuple[float, float]]:
    """씬 개수에 따라 균등 분배 타이밍 생성"""
    num_scenes = max(MIN_SCENES, min(MAX_SCENES, num_scenes))
    duration_per_scene = total_duration / num_scenes
    return [(round(i * duration_per_scene, 2), round((i + 1) * duration_per_scene, 2))
            for i in range(num_scenes)]

# BGM
BGM_VOLUME = 0.45
BGM_FADE_IN = 0.2
BGM_FADE_OUT = 1.0

# 저장 경로
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
PROJECTS_DIR = OUTPUT_DIR / "projects"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)
