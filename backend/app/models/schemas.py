from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class BusinessInfo(BaseModel):
    name: str
    category: str = "기타"
    tagline: str = ""
    phone: str = ""
    address: str = ""
    website: str = ""
    services: list[str] = []
    operating_hours: str = ""
    concept_note: str = ""


class BrandConfig(BaseModel):
    primary_color: str = ""
    secondary_color: str = ""
    text_color: str = "#FFFFFF"


class TextBlockConfig(BaseModel):
    """개별 텍스트 블록 설정"""
    content: str = ""
    region: str = "mid_center"
    role: str = "headline"
    font_role: str = "headline"
    font_size: int = 64
    effect: str = "shadow"
    effect_params: dict = {}


class SceneConfig(BaseModel):
    headline: str = ""
    subtext: str = ""
    media_index: int = 0
    media_type: str = "photo"  # "photo" | "video"
    scene_type: str = ""       # 비어있으면 업종별 기본 시퀀스 사용
    text_blocks: list[TextBlockConfig] = []  # 비어있으면 자동 생성
    text_position: str = ""    # TEXT_REGIONS 키 (비어있으면 씬 타입 기본값)
    font_color: str = ""       # #RRGGBB (비어있으면 템플릿 기본값)
    emphasis_color: str = ""   # 강조 단어 색상 #RRGGBB
    emphasis_words: list[str] = []  # 강조할 단어 리스트
    # 확장 필드
    layout_variant: int = 0          # 레이아웃 변형 (0=기본)
    photo_mode: str = ""             # 사진 배치 모드 오버라이드
    photo_overlay: str = ""          # 오버레이 타입 오버라이드
    text_effect: str = ""            # 텍스트 효과 오버라이드
    font_name: str = ""              # 폰트 직접 선택
    font_size_scale: float = 1.0     # 폰트 크기 배율


class SceneUpdateRequest(BaseModel):
    """씬 수정 요청"""
    headline: Optional[str] = None
    subtext: Optional[str] = None
    text_blocks: Optional[List[TextBlockConfig]] = None
    photo_index: Optional[int] = None
    scene_type: Optional[str] = None
    photo_mode: Optional[str] = None
    text_position: Optional[str] = None
    font_color: Optional[str] = None
    emphasis_color: Optional[str] = None
    # 확장 필드
    layout_variant: Optional[int] = None
    photo_overlay: Optional[str] = None
    text_effect: Optional[str] = None
    font_name: Optional[str] = None
    font_size_scale: Optional[float] = None


class GenerateRequest(BaseModel):
    business: BusinessInfo
    brand: BrandConfig = BrandConfig()
    scenes: list[SceneConfig] = []
    bgm_genre: str = ""
    bgm_dir: str = ""
    text_mode: str = "manual"  # "manual" | "ai"
