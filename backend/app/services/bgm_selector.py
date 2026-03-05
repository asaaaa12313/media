"""BGM 자동 선택: 자막 내용 + 파일명 키워드 기반"""
from __future__ import annotations
import logging
import os
import random
import glob
import subprocess
from pathlib import Path
from app.core.config import BGM_DIR

logger = logging.getLogger(__name__)

GENRE_KEYWORDS = {
    "신남": ["에너지", "챌린지", "운동", "댄스", "신나", "빠른", "파이팅", "화이팅", "고고", "레츠고"],
    "강렬한": ["극적", "임팩트", "하이라이트", "대박", "최고", "역대급", "미쳤", "실화"],
    "밝음": ["따뜻", "일상", "브이로그", "카페", "산책", "출근", "아침", "커피", "맛있"],
    "잔잔": ["감성", "힐링", "풍경", "여행", "바다", "하늘", "석양", "숲", "조용", "편안"],
    "펑키": ["유쾌", "리뷰", "언박싱", "먹방", "맛집", "추천", "꿀팁", "개꿀"],
    "클래식": ["고급", "교육", "격식", "전문", "클래스", "레슨", "세미나"],
    "팝": ["트렌디", "노래", "커버", "뮤직", "음악"],
    "일본풍": ["도쿄", "오사카", "일본", "라멘", "스시", "교토", "일식"],
    "크리스마스": ["크리스마스", "연말", "겨울", "산타", "눈", "선물"],
}

DEFAULT_GENRE = "신남"


def select_bgm(srt_content: str = "", filenames: list[str] = None,
                genre: str = "", bgm_dir: str = "") -> dict:
    """
    BGM 자동 선택.
    - genre가 지정되면 해당 장르에서 랜덤 선택
    - 아니면 srt_content + filenames 기반으로 장르 추론
    """
    bgm_base = Path(bgm_dir) if bgm_dir else BGM_DIR

    if not bgm_base.exists():
        logger.warning(f"[BGM] BGM 디렉토리를 찾을 수 없습니다: {bgm_base}")
        return {"genre": genre or DEFAULT_GENRE, "path": "", "filename": "", "available": False}

    if genre:
        selected_genre = genre
    else:
        selected_genre = _infer_genre(srt_content, filenames or [])

    # 장르 폴더에서 BGM 파일 찾기
    genre_dir = bgm_base / selected_genre
    if not genre_dir.exists():
        # 폴백: 아무 장르나 찾기
        for d in bgm_base.iterdir():
            if d.is_dir():
                genre_dir = d
                selected_genre = d.name
                break
        else:
            return {"genre": selected_genre, "path": "", "filename": ""}

    bgm_files = []
    for ext in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a"):
        bgm_files.extend(glob.glob(str(genre_dir / ext)))

    if not bgm_files:
        logger.warning(f"[BGM] '{selected_genre}' 장르에 BGM 파일이 없습니다: {genre_dir}")
        return {"genre": selected_genre, "path": "", "filename": "", "available": False}

    chosen = random.choice(bgm_files)
    return {
        "genre": selected_genre,
        "path": chosen,
        "filename": os.path.basename(chosen),
    }


def _infer_genre(srt_content: str, filenames: list[str]) -> str:
    """자막 내용과 파일명에서 장르 추론"""
    text = srt_content.lower() + " " + " ".join(filenames).lower()

    scores = {}
    for genre, keywords in GENRE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[genre] = score

    if not scores:
        # 무음 영상이면 잔잔
        if not srt_content.strip():
            return "잔잔"
        return DEFAULT_GENRE

    return max(scores, key=scores.get)


# 업종 → BGM 장르 매핑
CATEGORY_BGM_MAP = {
    "음식점": "밝음", "헬스": "강렬한", "뷰티": "잔잔",
    "학원": "밝음", "병원": "클래식", "안경": "밝음",
    "부동산": "클래식", "골프": "클래식", "핸드폰": "신남",
    "동물병원": "밝음", "미용실": "팝", "기타": "밝음",
}


def auto_select_bgm(category: str, bgm_dir: str = "") -> dict:
    """업종에 맞는 BGM 자동 선택. 파일 없으면 자동 생성."""
    genre = CATEGORY_BGM_MAP.get(category, "밝음")
    result = select_bgm(genre=genre, bgm_dir=bgm_dir)
    if not result.get("path"):
        # BGM 파일이 없으면 간단한 앰비언트 트랙 생성
        generated = _generate_ambient_bgm(genre, bgm_dir=bgm_dir)
        if generated:
            return generated
    return result


def _generate_ambient_bgm(genre: str, duration: float = 18.0, bgm_dir: str = "") -> dict | None:
    """FFmpeg로 간단한 앰비언트 BGM 생성"""
    bgm_base = Path(bgm_dir) if bgm_dir else BGM_DIR
    genre_dir = bgm_base / genre
    genre_dir.mkdir(parents=True, exist_ok=True)
    output_path = genre_dir / f"ambient_{genre}.mp3"

    if output_path.exists() and output_path.stat().st_size > 1000:
        return {"genre": genre, "path": str(output_path), "filename": output_path.name}

    # 장르별 주파수 설정 (C major chord 변형)
    GENRE_FREQS = {
        "밝음":   [(523.25, 0.12), (659.25, 0.10), (783.99, 0.08)],
        "잔잔":   [(261.63, 0.10), (329.63, 0.08), (392.00, 0.07)],
        "신남":   [(523.25, 0.14), (783.99, 0.12), (1046.50, 0.08)],
        "강렬한": [(440.00, 0.14), (554.37, 0.12), (659.25, 0.10)],
        "클래식": [(261.63, 0.10), (329.63, 0.08), (392.00, 0.06), (523.25, 0.05)],
        "팝":     [(440.00, 0.12), (554.37, 0.10), (659.25, 0.08)],
    }
    freqs = GENRE_FREQS.get(genre, GENRE_FREQS["밝음"])

    try:
        # 여러 사인파를 합성하여 앰비언트 사운드 생성
        inputs = []
        for i, (freq, vol) in enumerate(freqs):
            inputs.extend(["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}"])

        amix_input = "".join(f"[{i}]volume={freqs[i][1]}[s{i}];" for i in range(len(freqs)))
        amix_input += "".join(f"[s{i}]" for i in range(len(freqs)))
        amix_input += f"amix=inputs={len(freqs)}:normalize=0,"
        amix_input += f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-2}:d=2"

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", amix_input,
            "-t", str(duration),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and output_path.exists():
            logger.info(f"[BGM] 앰비언트 BGM 자동 생성: {output_path}")
            return {"genre": genre, "path": str(output_path), "filename": output_path.name}
        else:
            logger.warning(f"[BGM] 앰비언트 BGM 생성 실패: {result.stderr[-200:]}")
    except Exception as e:
        logger.warning(f"[BGM] 앰비언트 BGM 생성 오류: {e}")
    return None


def list_genres(bgm_dir: str = "") -> list[dict]:
    """사용 가능한 BGM 장르 목록 반환"""
    bgm_base = Path(bgm_dir) if bgm_dir else BGM_DIR
    genres = []
    if bgm_base.exists():
        for d in sorted(bgm_base.iterdir()):
            if d.is_dir():
                count = len(list(d.glob("*.mp3")) + list(d.glob("*.MP3")))
                genres.append({"name": d.name, "count": count})
    return genres
