"""AI 씬 텍스트 자동생성 (Claude + Gemini 이중 지원)

우선순위: Claude API → Gemini API → 폴백 텍스트
"""
from __future__ import annotations
import json
from app.core.config import GEMINI_API_KEY, CLAUDE_API_KEY
from app.models.schemas import BusinessInfo, SceneConfig


# 업종별 카피라이팅 톤
CATEGORY_TONE = {
    "음식점": "맛있는 음식의 감동을 전달하는 따뜻하고 감성적인 톤. 식욕을 자극하는 표현 사용.",
    "헬스": "강렬하고 동기부여가 되는 파워풀한 톤. 변화와 성장을 강조.",
    "뷰티": "우아하고 세련된 톤. 아름다움과 자기관리의 가치를 전달.",
    "학원": "신뢰감 있고 전문적인 톤. 성장과 성취를 강조.",
    "병원": "따뜻하고 신뢰감 있는 전문적 톤. 건강과 안심을 강조.",
    "안경": "트렌디하고 스타일리시한 톤. 패션과 기능성을 모두 강조.",
    "부동산": "고급스럽고 안정감 있는 톤. 가치와 투자를 강조.",
    "골프": "프리미엄하고 여유로운 톤. 품격과 즐거움을 강조.",
    "핸드폰": "테크놀로지 감성의 현대적 톤. 혁신과 편의성을 강조.",
    "동물병원": "따뜻하고 사랑스러운 톤. 반려동물에 대한 애정과 전문성을 강조.",
    "미용실": "세련되고 트렌디한 톤. 변신과 스타일의 즐거움을 전달.",
    "기타": "전문적이고 신뢰감 있는 톤. 업체의 핵심 가치를 명확히 전달.",
}

# 씬 역할 매핑 (씬 개수에 따라 동적으로 선택)
SCENE_ROLES = [
    {"role": "인트로", "desc": "브랜드명과 핵심 가치를 강렬하게 소개. 첫인상을 결정짓는 임팩트 있는 문구."},
    {"role": "메인 특징", "desc": "주요 서비스나 핵심 강점을 구체적으로 소개. 차별화 포인트를 명확히."},
    {"role": "정보 카드", "desc": "핵심 서비스 상세 설명. 고객이 알아야 할 구체적 정보 전달."},
    {"role": "프로모션", "desc": "현재 이벤트, 할인, 특별 혜택 소개. 행동을 유도하는 긴급성 부여."},
    {"role": "하이라이트", "desc": "가장 자랑하고 싶은 포인트를 강조. 감성적인 어필."},
    {"role": "기능 리스트", "desc": "제공 서비스를 목록 형태로 정리. 한눈에 파악 가능하게."},
    {"role": "후기/신뢰", "desc": "고객 후기, 수상 경력, 인증 등 신뢰 요소 전달."},
    {"role": "갤러리", "desc": "시각적 매력을 강조하는 짧고 강렬한 문구."},
    {"role": "상세 정보", "desc": "위치, 영업시간, 특이사항 등 실용적 정보 전달."},
    {"role": "CTA", "desc": "방문/문의/예약을 유도하는 강력한 마무리. 행동을 촉구하는 문구."},
]


def _build_prompt(business: BusinessInfo, num_scenes: int) -> str:
    """동적 씬 수에 맞는 프롬프트 생성"""
    tone = CATEGORY_TONE.get(business.category, CATEGORY_TONE["기타"])
    roles = SCENE_ROLES[:num_scenes]
    # 마지막 씬은 항상 CTA
    if roles[-1]["role"] != "CTA":
        roles[-1] = SCENE_ROLES[-1]

    roles_text = "\n".join(
        f"- 씬{i+1}: {r['role']} - {r['desc']}"
        for i, r in enumerate(roles)
    )

    services_text = ", ".join(business.services) if business.services else "없음"

    return f"""당신은 포커스미디어(엘리베이터/빌딩 스크린) 광고 영상의 전문 카피라이터입니다.

다음 업체 정보를 바탕으로 15초 광고 영상의 {num_scenes}개 씬 텍스트를 작성하세요.

업체명: {business.name}
업종: {business.category}
태그라인: {business.tagline or "없음"}
서비스: {services_text}

카피라이팅 톤: {tone}

각 씬의 역할:
{roles_text}

작성 규칙:
- headline: 15자 이내, 임팩트 있는 핵심 문구 (1줄). 업체의 핵심 가치를 한 문장으로.
- subtext: 40자 이내, 감성적이고 구체적인 보조 설명 (2-3줄, 줄바꿈 \\n 사용)
- emphasis_words: headline에서 가장 강조할 단어 1-2개 (다른 색상으로 표시될 단어)
- suggested_position: 텍스트 위치 추천 (top_left, top_center, top_right, mid_left, mid_center, mid_right, bottom_wide 중 택1)
- suggested_photo_index: 이 씬에 가장 적합한 사진 번호 (0부터 시작, 다양하게 배치)
- 한국어로 작성
- 광고 문구답게 간결하면서도 감성적으로
- 반복되는 표현 피하기, 각 씬마다 다른 관점에서 어필
- 인트로는 강렬하게, CTA는 행동을 유도하게

반드시 아래 JSON 형식으로만 응답하세요 (JSON 외 다른 텍스트 없이):
[
  {{"headline": "...", "subtext": "...", "emphasis_words": ["..."], "suggested_position": "...", "suggested_photo_index": 0}},
  ...총 {num_scenes}개
]"""


def generate_scene_texts(business: BusinessInfo, num_scenes: int = 4) -> list[SceneConfig]:
    """AI로 씬 텍스트 자동 생성 (Claude → Gemini → 폴백)"""
    num_scenes = max(4, min(10, num_scenes))

    # 1. Gemini API 시도 (Claude는 비활성화)
    if GEMINI_API_KEY:
        result = _generate_with_gemini(business, num_scenes)
        if result:
            return result

    # 3. 폴백
    return _fallback_texts(business, num_scenes)


def _generate_with_claude(business: BusinessInfo, num_scenes: int) -> list[SceneConfig] | None:
    """Claude API로 텍스트 생성"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        prompt = _build_prompt(business, num_scenes)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = message.content[0].text.strip()
        return _parse_ai_response(text, num_scenes)
    except Exception:
        return None


def _generate_with_gemini(business: BusinessInfo, num_scenes: int) -> list[SceneConfig] | None:
    """Gemini API로 텍스트 생성"""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = _build_prompt(business, num_scenes)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        text = response.text.strip()
        return _parse_ai_response(text, num_scenes)
    except Exception:
        return None


def _parse_ai_response(text: str, num_scenes: int) -> list[SceneConfig] | None:
    """AI 응답 JSON 파싱"""
    try:
        # JSON 코드블록 제거
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        scenes_data = json.loads(text)
        scenes = []
        for i, s in enumerate(scenes_data[:num_scenes]):
            scenes.append(SceneConfig(
                headline=s.get("headline", ""),
                subtext=s.get("subtext", ""),
                media_index=s.get("suggested_photo_index", i),
                media_type="photo",
                text_position=s.get("suggested_position", ""),
                emphasis_words=s.get("emphasis_words", []),
            ))
        return scenes if scenes else None
    except Exception:
        return None


def _fallback_texts(business: BusinessInfo, num_scenes: int = 4) -> list[SceneConfig]:
    """AI 실패 시 기본 텍스트"""
    name = business.name
    services_str = " | ".join(business.services[:3]) if business.services else ""

    base_scenes = [
        SceneConfig(headline=name, subtext=business.tagline or "최고의 선택",
                    media_index=0, media_type="photo", emphasis_words=[name]),
        SceneConfig(headline="전문 서비스", subtext=services_str or "최상의 서비스를\n제공합니다",
                    media_index=1, media_type="photo", emphasis_words=["전문"]),
        SceneConfig(headline="특별한 경험", subtext="차별화된 퀄리티로\n만족을 드립니다",
                    media_index=2, media_type="photo", emphasis_words=["특별한"]),
        SceneConfig(headline="특별한 혜택", subtext="지금 방문하시면\n특별 혜택을 드립니다",
                    media_index=3, media_type="photo", emphasis_words=["특별한"]),
        SceneConfig(headline="프리미엄 공간", subtext="당신만을 위한\n특별한 공간",
                    media_index=4, media_type="photo", emphasis_words=["프리미엄"]),
        SceneConfig(headline="고객 만족", subtext="수많은 고객이\n인정한 서비스",
                    media_index=5, media_type="photo", emphasis_words=["만족"]),
        SceneConfig(headline="최고의 품질", subtext="타협 없는\n퀄리티를 약속합니다",
                    media_index=6, media_type="photo", emphasis_words=["최고의"]),
        SceneConfig(headline="편리한 접근", subtext="가까운 곳에서\n만나보세요",
                    media_index=7, media_type="photo", emphasis_words=["편리한"]),
        SceneConfig(headline="새로운 시작", subtext="지금이 바로\n시작할 때입니다",
                    media_index=8, media_type="photo", emphasis_words=["새로운"]),
        SceneConfig(headline="지금 방문하세요!", subtext=f"{name}에서\n만나뵙겠습니다",
                    media_index=0, media_type="photo", emphasis_words=["지금"]),
    ]

    result = base_scenes[:num_scenes]
    # 마지막 씬은 항상 CTA
    if num_scenes > 1:
        result[-1] = base_scenes[-1]
    return result
