"""AI 씬 텍스트 자동생성 (Claude + Gemini 이중 지원)

우선순위: Claude API → Gemini API → 폴백 텍스트
"""
from __future__ import annotations
import json
from app.core.config import GEMINI_API_KEY
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


CATEGORY_EXAMPLES = {
    "음식점": [
        {"headline": "한 입에 반하다", "subtext": "정성 가득한 재료로\n매일 새롭게 준비합니다"},
        {"headline": "오늘의 미식", "subtext": "셰프가 직접 선별한\n제철 식재료의 향연"},
        {"headline": "맛의 정석", "subtext": "10년 한결같은 맛\n단골이 증명합니다"},
        {"headline": "지금 예약하세요", "subtext": "특별한 날을 더 특별하게\n코스 예약 문의"},
    ],
    "헬스": [
        {"headline": "오늘이 Day 1", "subtext": "전문 트레이너가\n목표까지 함께합니다"},
        {"headline": "변화의 시작", "subtext": "1:1 맞춤 프로그램으로\n확실한 결과를 만듭니다"},
        {"headline": "몸이 달라진다", "subtext": "체계적인 운동 플랜\n눈에 보이는 변화"},
        {"headline": "무료 체험 신청", "subtext": "지금 등록하면\n첫 달 PT 무료"},
    ],
    "뷰티": [
        {"headline": "당신만의 아름다움", "subtext": "트렌드를 넘어\n당신에게 맞는 스타일을"},
        {"headline": "전문가의 손길", "subtext": "15년 경력 원장이\n직접 시술합니다"},
        {"headline": "자연스러운 변화", "subtext": "과하지 않게, 확실하게\n달라진 나를 만나보세요"},
        {"headline": "지금 상담 받으세요", "subtext": "카카오톡 문의 시\n10% 할인 혜택"},
    ],
    "학원": [
        {"headline": "성적이 오른다", "subtext": "입시 전문 강사진의\n검증된 커리큘럼"},
        {"headline": "1등급의 비결", "subtext": "소수 정예 맞춤 수업\n개인별 약점 집중 공략"},
        {"headline": "합격을 만드는 곳", "subtext": "SKY 합격생 배출\n실전 모의고사 제공"},
        {"headline": "무료 레벨테스트", "subtext": "실력에 맞는 반 배정\n지금 바로 신청하세요"},
    ],
    "병원": [
        {"headline": "건강을 지키다", "subtext": "대학병원 출신 전문의가\n정확하게 진단합니다"},
        {"headline": "믿을 수 있는 진료", "subtext": "최신 의료장비 완비\n꼼꼼한 상담까지"},
        {"headline": "환자 중심 치료", "subtext": "통증 최소화 시술\n빠른 일상 복귀"},
        {"headline": "온라인 예약 가능", "subtext": "대기 없는 진료\n네이버 예약 오픈"},
    ],
    "기타": [
        {"headline": "다른 차원의 경험", "subtext": "전문성과 정성이 만든\n확실한 차이를 느껴보세요"},
        {"headline": "고객이 인정한 품질", "subtext": "리뷰 평점 4.9\n재방문율 87%"},
        {"headline": "프리미엄 서비스", "subtext": "디테일이 다른\n맞춤형 솔루션"},
        {"headline": "지금 방문하세요", "subtext": "첫 방문 고객\n특별 혜택 제공"},
    ],
}


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

    # 업종별 예시 가져오기
    examples = CATEGORY_EXAMPLES.get(business.category, CATEGORY_EXAMPLES["기타"])
    examples_text = "\n".join(
        f'  씬{i+1}: headline="{ex["headline"]}", subtext="{ex["subtext"]}"'
        for i, ex in enumerate(examples[:num_scenes])
    )

    return f"""당신은 대한민국 최고의 엘리베이터/빌딩 스크린 광고 카피라이터입니다.
15초짜리 세로형 광고 영상의 씬별 텍스트를 작성합니다.

[업체 정보]
업체명: {business.name}
업종: {business.category}
태그라인: {business.tagline or "없음"}
주요 서비스: {services_text}

[톤 & 무드]
{tone}

[씬 구성 ({num_scenes}개)]
{roles_text}

[레퍼런스 예시 - 이 수준 이상으로 작성]
{examples_text}

[필수 규칙]
1. headline: 8~15자, 리듬감 있는 짧은 문장. "~합니다"체 금지. 명사형/감탄형/질문형 활용.
   - 좋은 예: "한 입에 반하다", "오늘이 Day 1", "성적이 오른다"
   - 나쁜 예: "최고의 맛을 제공합니다", "전문적인 서비스", "특별한 경험"
2. subtext: 20~40자, 구체적 숫자/사실 포함. 추상적 미사여구 금지.
   - 좋은 예: "10년 경력 셰프의\\n제철 코스 요리", "리뷰 4.9점\\n재방문율 87%"
   - 나쁜 예: "최상의 서비스를\\n제공합니다", "특별한 경험을\\n선사합니다"
3. emphasis_words: headline에서 감정/행동을 유발하는 핵심 단어 1개
4. 각 씬은 완전히 다른 관점에서 어필 (중복 표현 절대 금지)
5. 마지막 씬(CTA)은 구체적 행동 유도: "예약", "전화", "방문" 등 명확한 동사 사용
6. "{business.name}"을 자연스럽게 1~2회 포함

반드시 아래 JSON 형식으로만 응답 (JSON 외 텍스트 없이):
[
  {{"headline": "...", "subtext": "...", "emphasis_words": ["..."], "suggested_position": "...", "suggested_photo_index": 0}},
  ...총 {num_scenes}개
]

suggested_position: top_left, top_center, top_right, mid_left, mid_center, mid_right, bottom_wide 중 택1
suggested_photo_index: 0부터 시작, 씬마다 다른 사진 사용"""


def generate_scene_texts(business: BusinessInfo, num_scenes: int = 4) -> list[SceneConfig]:
    """AI로 씬 텍스트 자동 생성 (Gemini → 폴백)"""
    num_scenes = max(4, min(10, num_scenes))

    # 1. Gemini API 시도
    if GEMINI_API_KEY:
        result = _generate_with_gemini(business, num_scenes)
        if result:
            return result

    # 2. 폴백
    return _fallback_texts(business, num_scenes)


def _generate_with_gemini(business: BusinessInfo, num_scenes: int) -> list[SceneConfig] | None:
    """Gemini API로 텍스트 생성"""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = _build_prompt(business, num_scenes)

        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
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
    """AI 실패 시 업종별 레퍼런스 기반 텍스트"""
    name = business.name
    examples = CATEGORY_EXAMPLES.get(business.category, CATEGORY_EXAMPLES["기타"])

    # 인트로는 업체명 포함
    intro = SceneConfig(
        headline=name, subtext=business.tagline or examples[0]["subtext"],
        media_index=0, media_type="photo", emphasis_words=[name],
    )
    # CTA는 업체명 포함
    cta = SceneConfig(
        headline="지금 방문하세요", subtext=f"{name}에서\n만나뵙겠습니다",
        media_index=0, media_type="photo", emphasis_words=["지금"],
    )

    # 중간 씬은 업종별 예시에서 가져옴
    mid_scenes = []
    for i, ex in enumerate(examples[1:], start=1):
        mid_scenes.append(SceneConfig(
            headline=ex["headline"], subtext=ex["subtext"],
            media_index=min(i, 9), media_type="photo",
            emphasis_words=[ex["headline"].split()[0]],
        ))

    result = [intro] + mid_scenes[:num_scenes - 2] + [cta]
    # 부족한 씬 채우기
    while len(result) < num_scenes:
        idx = len(result) - 1
        result.insert(idx, SceneConfig(
            headline=examples[min(idx, len(examples) - 1)]["headline"],
            subtext=examples[min(idx, len(examples) - 1)]["subtext"],
            media_index=idx % 10, media_type="photo",
            emphasis_words=[],
        ))
    return result[:num_scenes]
