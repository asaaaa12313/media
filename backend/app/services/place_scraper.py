"""네이버 플레이스 URL에서 업체 정보 및 사진 자동 추출

전략:
1. 단축 URL → appLink에서 place ID 추출
2. 모바일 페이지에서 __APOLLO_STATE__ 파싱 → 업체 정보
3. PC 사진 페이지에서 __APOLLO_STATE__ 파싱 → 사진 URL
4. fallback: og:title 등 meta 태그
"""
import re
import json
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

MOBILE_UA = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

PC_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 네이버 카테고리 → 우리 카테고리 매핑
CATEGORY_MAP = {
    "한식": "음식점", "중식": "음식점", "일식": "음식점", "양식": "음식점",
    "분식": "음식점", "카페": "음식점", "베이커리": "음식점", "패스트푸드": "음식점",
    "치킨": "음식점", "피자": "음식점", "족발": "음식점", "보쌈": "음식점",
    "음식점": "음식점", "맛집": "음식점", "식당": "음식점", "레스토랑": "음식점",
    "디저트": "음식점", "브런치": "음식점", "뷔페": "음식점", "술집": "음식점",
    "호프": "음식점", "바": "음식점",
    "헬스": "헬스", "피트니스": "헬스", "체육관": "헬스", "PT": "헬스",
    "크로스핏": "헬스", "요가": "헬스", "필라테스": "헬스", "스포츠": "헬스",
    "뷰티": "뷰티", "네일": "뷰티", "피부과": "뷰티", "피부관리": "뷰티",
    "에스테틱": "뷰티", "속눈썹": "뷰티", "왁싱": "뷰티",
    "학원": "학원", "교육": "학원", "입시": "학원", "영어": "학원",
    "수학": "학원", "코딩": "학원", "어학원": "학원",
    "음악": "학원", "피아노": "학원", "바이올린": "학원", "기타교실": "학원",
    "악기": "학원", "레슨": "학원", "보컬": "학원", "드럼": "학원",
    "첼로": "학원", "플루트": "학원", "미술": "학원", "댄스": "학원",
    "무용": "학원", "발레": "학원", "태권도": "학원", "합기도": "학원",
    "검도": "학원", "수영": "학원", "연기": "학원",
    "병원": "병원", "의원": "병원", "한의원": "병원", "치과": "병원",
    "안과": "병원", "이비인후과": "병원", "정형외과": "병원", "내과": "병원",
    "소아과": "병원", "산부인과": "병원", "성형외과": "병원", "약국": "병원",
    "안경": "안경", "렌즈": "안경", "안경점": "안경",
    "부동산": "부동산", "공인중개사": "부동산", "중개": "부동산",
    "골프": "골프", "골프연습장": "골프", "스크린골프": "골프",
    "핸드폰": "핸드폰", "휴대폰": "핸드폰", "스마트폰": "핸드폰", "통신": "핸드폰",
    "동물병원": "동물병원", "수의": "동물병원", "반려동물": "동물병원", "펫": "동물병원",
    "미용실": "미용실", "헤어": "미용실", "헤어샵": "미용실", "바버샵": "미용실",
}


def _extract_place_id(url: str) -> str:
    """URL에서 place ID 추출 (다양한 형식 지원)"""
    # 1. 단축 URL(naver.me) → 리다이렉트 후 appLink에서 추출
    parsed = urlparse(url)
    if parsed.hostname and "naver.me" in parsed.hostname:
        try:
            resp = requests.head(url, headers=MOBILE_UA, allow_redirects=True, timeout=10)
            url = resp.url
            parsed = urlparse(url)
        except requests.RequestException:
            return ""

    # 2. appLink URL에서 id 파라미터 추출
    if "appLink" in url or "pinId" in url:
        qs = parse_qs(parsed.query)
        for key in ("id", "pinId"):
            if key in qs:
                return qs[key][0]

    # 3. 경로에서 숫자 ID 추출 (/place/12345/home 등)
    path_match = re.search(r"/(\d{5,})", parsed.path)
    if path_match:
        return path_match.group(1)

    # 4. 쿼리 파라미터에서 id 추출
    qs = parse_qs(parsed.query)
    if "id" in qs:
        return qs["id"][0]

    return ""


def _parse_apollo_state(html: str) -> dict:
    """window.__APOLLO_STATE__ 파싱"""
    match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});\s*$', html, re.MULTILINE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}


def _extract_info_from_apollo(apollo: dict, place_id: str) -> dict:
    """Apollo State에서 PlaceDetailBase 정보 추출"""
    result = {
        "name": "", "category": "", "phone": "", "address": "",
        "website": "", "tagline": "", "services": [], "photo_urls": [],
    }

    detail = apollo.get(f"PlaceDetailBase:{place_id}", {})
    if not detail:
        # PlaceDetailBase 키를 찾지 못하면 모든 키에서 검색
        for key, val in apollo.items():
            if isinstance(val, dict) and val.get("__typename") == "PlaceDetailBase":
                detail = val
                break

    if not detail:
        return result

    result["name"] = detail.get("name", "")
    result["category"] = detail.get("category", "")
    result["phone"] = detail.get("virtualPhone") or detail.get("phone") or ""
    result["address"] = detail.get("roadAddress") or detail.get("address") or ""
    result["website"] = detail.get("homepage") or detail.get("talktalkUrl") or ""
    result["tagline"] = detail.get("description") or detail.get("microReview") or ""

    # 서비스/편의시설
    conveniences = detail.get("conveniences", [])
    if isinstance(conveniences, list):
        result["services"] = [c for c in conveniences if isinstance(c, str)]

    return result


def _extract_photos_from_apollo(apollo: dict) -> list[str]:
    """Apollo State JSON 전체에서 ldb-phinf 사진 URL 추출"""
    apollo_str = json.dumps(apollo, ensure_ascii=False)
    # ldb-phinf, naverbooking-phinf 패턴의 사진 URL
    photos = re.findall(
        r'(https://(?:ldb-phinf|naverbooking-phinf)\.pstatic\.net/[^"\\<>\s]+)',
        apollo_str,
    )
    # 중복 제거 (순서 유지)
    seen = set()
    unique = []
    for url in photos:
        # 크롭 파라미터 정리
        clean = re.sub(r'\?type=.*$', '', url)
        if clean not in seen:
            seen.add(clean)
            unique.append(url)
    return unique


def _extract_from_meta(html: str) -> dict:
    """og:title, og:description 등 메타태그에서 정보 추출"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    result = {"name": "", "tagline": "", "photo_urls": []}

    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title.get("content", "")
        # " : 네이버" 제거
        result["name"] = re.sub(r'\s*:\s*네이버\s*$', '', title).strip()

    og_desc = soup.find("meta", property="og:description")
    if og_desc:
        result["tagline"] = og_desc.get("content", "")

    og_image = soup.find("meta", property="og:image")
    if og_image:
        img_url = og_image.get("content", "")
        if img_url and "pstatic.net" in img_url:
            result["photo_urls"].append(img_url)

    return result


def _map_category(naver_category: str) -> str:
    """네이버 카테고리 → 12개 카테고리로 매핑"""
    if not naver_category:
        return "기타"
    if naver_category in CATEGORY_MAP:
        return CATEGORY_MAP[naver_category]
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in naver_category:
            return cat
    return "기타"


def extract_place_info(url: str) -> dict:
    """네이버 플레이스 URL에서 업체 정보 추출"""
    result = {
        "name": "", "category": "기타", "phone": "", "address": "",
        "website": "", "tagline": "", "services": [], "photo_urls": [],
    }

    try:
        # 1. place ID 추출
        place_id = _extract_place_id(url.strip())
        if not place_id:
            logger.warning("place ID 추출 실패: %s", url)
            return {**result, "error": "플레이스 ID를 추출할 수 없습니다"}

        logger.info("Place ID: %s", place_id)

        # 2. 모바일 페이지에서 업체 정보 (Apollo State)
        mobile_url = f"https://m.place.naver.com/place/{place_id}/home"
        resp = requests.get(mobile_url, headers=MOBILE_UA, timeout=15)
        resp.encoding = "utf-8"
        html = resp.text

        apollo = _parse_apollo_state(html)
        if apollo:
            info = _extract_info_from_apollo(apollo, place_id)
            for key in ("name", "phone", "address", "website", "tagline"):
                if info.get(key):
                    result[key] = info[key]
            if info.get("services"):
                result["services"] = info["services"]
            if info.get("category"):
                result["category"] = _map_category(info["category"])

        # 3. fallback: 메타태그
        if not result["name"]:
            meta = _extract_from_meta(html)
            if meta["name"]:
                result["name"] = meta["name"]
            if meta["tagline"]:
                result["tagline"] = meta["tagline"]

        # 4. PC 사진 페이지에서 사진 URL 수집
        pc_photo_url = f"https://pcmap.place.naver.com/place/{place_id}/photo"
        try:
            resp2 = requests.get(pc_photo_url, headers=PC_UA, timeout=15)
            resp2.encoding = "utf-8"
            apollo2 = _parse_apollo_state(resp2.text)
            if apollo2:
                photos = _extract_photos_from_apollo(apollo2)
                result["photo_urls"] = photos
        except requests.RequestException:
            pass

        # 5. 사진이 없으면 home 페이지 Apollo에서도 시도
        if not result["photo_urls"] and apollo:
            photos = _extract_photos_from_apollo(apollo)
            result["photo_urls"] = photos

        # 6. 최후 fallback: og:image
        if not result["photo_urls"]:
            meta = _extract_from_meta(html)
            result["photo_urls"] = meta["photo_urls"]

        logger.info("추출 완료: %s (%s), 사진 %d장",
                     result["name"], result["category"], len(result["photo_urls"]))

    except requests.RequestException as e:
        logger.error("네이버 플레이스 요청 실패: %s", e)
    except Exception as e:
        logger.error("플레이스 정보 추출 중 오류: %s", e)

    return result


def download_place_photos(
    place_url: str,
    save_dir: str,
    max_photos: int = 10,
) -> list[str]:
    """네이버 플레이스 사진 다운로드"""
    info = extract_place_info(place_url)
    photo_urls = info.get("photo_urls", [])[:max_photos]

    if not photo_urls:
        logger.warning("다운로드할 사진이 없습니다")
        return []

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for i, url in enumerate(photo_urls):
        try:
            resp = requests.get(url, headers=MOBILE_UA, timeout=15)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            else:
                ext = ".jpg"

            filename = f"{i:02d}_place{ext}"
            file_path = save_path / filename
            file_path.write_bytes(resp.content)
            saved_files.append(str(file_path))

        except requests.RequestException as e:
            logger.warning("사진 다운로드 실패 (%d): %s", i, e)

    return saved_files
