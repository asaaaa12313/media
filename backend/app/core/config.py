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
_local_bgm.mkdir(exist_ok=True)

TEMP_DIR.mkdir(exist_ok=True)

# AI API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

# 영상 설정
TARGET_DURATION = 15.0
WIDTH = 1080
HEIGHT = 1920  # 표준 9:16
FPS = 30

# 레이아웃: 콘텐츠(67%) + 정보 패널(33%)
CONTENT_HEIGHT = 1100   # 콘텐츠 영역 (1080x1650 기준)
INFO_SECTION_HEIGHT = 550  # 하단 정보+홍보 패널
BOTTOM_BAR_HEIGHT = INFO_SECTION_HEIGHT  # 하위 호환

# 하위 호환용 (기존 import 깨지지 않도록)
ZONE1_HEIGHT = 0
ZONE2_HEIGHT = CONTENT_HEIGHT
ZONE3_HEIGHT = BOTTOM_BAR_HEIGHT

# 텍스트 배치 7개 영역 (콘텐츠 영역 1100px 기준)
TEXT_REGIONS = {
    "top_left":     {"x": 60,  "y": 40,   "w": 500, "h": 300, "align": "left"},
    "top_center":   {"x": 80,  "y": 40,   "w": 920, "h": 300, "align": "center"},
    "top_right":    {"x": 520, "y": 40,   "w": 500, "h": 300, "align": "right"},
    "mid_left":     {"x": 60,  "y": 360,  "w": 500, "h": 420, "align": "left"},
    "mid_center":   {"x": 80,  "y": 360,  "w": 920, "h": 420, "align": "center"},
    "mid_right":    {"x": 520, "y": 360,  "w": 500, "h": 420, "align": "right"},
    "bottom_wide":  {"x": 60,  "y": 800,  "w": 960, "h": 270, "align": "center"},
}

# 씬 타입별 기본 레이아웃 (콘텐츠 1100px 기준, 모두 fullscreen)
SCENE_LAYOUTS = {
    "intro": {
        "photo_mode": "fullscreen",
        "photo_overlay": "gradient_bottom_heavy",
        "text_slots": [
            {"region": "top_left", "role": "brand_name", "font_role": "headline", "size": 48, "effect": "shadow"},
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 96, "effect": "outline"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 40, "effect": "bg_box"},
        ],
    },
    "feature_list": {
        "photo_mode": "fullscreen",
        "photo_overlay": "gradient_bottom_heavy",
        "text_slots": [
            {"region": "top_center", "role": "headline", "font_role": "display", "size": 84, "effect": "outline"},
            {"region": "mid_left", "role": "feature_list", "font_role": "body", "size": 34, "effect": "none"},
        ],
    },
    "promotion": {
        "photo_mode": "fullscreen",
        "photo_overlay": "dark_heavy",
        "text_slots": [
            {"region": "top_center", "role": "accent", "font_role": "handwriting", "size": 40, "effect": "none"},
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 100, "effect": "outline"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "accent", "size": 44, "effect": "highlight"},
        ],
    },
    "gallery": {
        "photo_mode": "fullscreen",
        "photo_overlay": "light_overlay",
        "text_slots": [
            {"region": "top_center", "role": "headline", "font_role": "headline", "size": 76, "effect": "bg_box"},
        ],
    },
    "cta": {
        "photo_mode": "fullscreen",
        "photo_overlay": "gradient_bottom_heavy",
        "text_slots": [
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 92, "effect": "outline"},
            {"region": "bottom_wide", "role": "cta_text", "font_role": "headline", "size": 48, "effect": "bg_box"},
        ],
    },
    "info_card": {
        "photo_mode": "fullscreen",
        "photo_overlay": "gradient_bottom_heavy",
        "text_slots": [
            {"region": "mid_center", "role": "headline", "font_role": "display", "size": 76, "effect": "outline"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 34, "effect": "bg_box"},
        ],
    },
    "highlight": {
        "photo_mode": "fullscreen",
        "photo_overlay": "dark_overlay",
        "text_slots": [
            {"region": "top_center", "role": "headline", "font_role": "display", "size": 84, "effect": "outline"},
            {"region": "mid_center", "role": "subtext", "font_role": "body", "size": 38, "effect": "bg_box"},
        ],
    },
    "review": {
        "photo_mode": "fullscreen",
        "photo_overlay": "dark_overlay",
        "text_slots": [
            {"region": "mid_center", "role": "headline", "font_role": "handwriting", "size": 68, "effect": "none"},
            {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 30, "effect": "bg_box"},
        ],
    },
}

# 씬 레이아웃 변형 (각 씬 타입에 대안 레이아웃, 모두 fullscreen)
SCENE_LAYOUT_VARIANTS = {
    "intro": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "color_gradient_bottom",
            "text_slots": [
                {"region": "top_left", "role": "brand_name", "font_role": "headline", "size": 44, "effect": "none"},
                {"region": "mid_left", "role": "headline", "font_role": "display", "size": 88, "effect": "shadow_3d"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 36, "effect": "underline_accent"},
            ],
        },
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "gradient_bottom_heavy",
            "text_slots": [
                {"region": "top_right", "role": "brand_name", "font_role": "accent", "size": 40, "effect": "bg_pill"},
                {"region": "bottom_wide", "role": "headline", "font_role": "display", "size": 84, "effect": "neon"},
            ],
        },
    ],
    "feature_list": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "dark_overlay",
            "text_slots": [
                {"region": "top_center", "role": "headline", "font_role": "display", "size": 76, "effect": "outline"},
                {"region": "mid_left", "role": "feature_list", "font_role": "body", "size": 32, "effect": "none"},
            ],
        },
    ],
    "promotion": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "color_overlay_heavy",
            "text_slots": [
                {"region": "top_center", "role": "accent", "font_role": "handwriting", "size": 44, "effect": "none"},
                {"region": "mid_center", "role": "headline", "font_role": "display", "size": 96, "effect": "double_outline"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 38, "effect": "bg_pill"},
            ],
        },
    ],
    "gallery": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "gradient_bottom",
            "text_slots": [
                {"region": "top_center", "role": "headline", "font_role": "headline", "size": 68, "effect": "shadow"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 30, "effect": "bg_box"},
            ],
        },
    ],
    "cta": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "color_gradient_bottom",
            "text_slots": [
                {"region": "mid_center", "role": "headline", "font_role": "display", "size": 88, "effect": "double_outline"},
                {"region": "bottom_wide", "role": "cta_text", "font_role": "headline", "size": 44, "effect": "bg_pill"},
            ],
        },
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "vignette",
            "text_slots": [
                {"region": "mid_center", "role": "headline", "font_role": "display", "size": 84, "effect": "neon"},
                {"region": "bottom_wide", "role": "cta_text", "font_role": "headline", "size": 44, "effect": "underline_accent"},
            ],
        },
    ],
    "info_card": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "dark_overlay",
            "text_slots": [
                {"region": "mid_left", "role": "headline", "font_role": "display", "size": 72, "effect": "outline"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 32, "effect": "bg_box"},
            ],
        },
    ],
    "highlight": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "diagonal_gradient",
            "text_slots": [
                {"region": "top_left", "role": "headline", "font_role": "display", "size": 80, "effect": "shadow_3d"},
                {"region": "mid_left", "role": "subtext", "font_role": "body", "size": 34, "effect": "bg_box"},
            ],
        },
    ],
    "review": [
        {
            "photo_mode": "fullscreen",
            "photo_overlay": "dark_overlay",
            "text_slots": [
                {"region": "mid_center", "role": "headline", "font_role": "handwriting", "size": 64, "effect": "none"},
                {"region": "bottom_wide", "role": "subtext", "font_role": "body", "size": 28, "effect": "bg_box"},
            ],
            "decorations": [
                {"type": "quote_marks", "x": 80, "y": 360, "color_key": "accent", "size": 70},
                {"type": "star_rating", "x": 380, "y": 800, "color_key": "accent", "rating": 5, "size": 32},
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

# 씬 전환 효과 (FFmpeg xfade)
CATEGORY_TRANSITIONS = {
    "음식점": "fade",
    "헬스": "wipeleft",
    "뷰티": "dissolve",
    "학원": "fade",
    "병원": "fade",
    "안경": "slideright",
    "부동산": "fade",
    "골프": "dissolve",
    "핸드폰": "wipeleft",
    "동물병원": "fade",
    "미용실": "dissolve",
    "기타": "fade",
}


def get_transition_type(category: str) -> str:
    return CATEGORY_TRANSITIONS.get(category, "fade")

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
