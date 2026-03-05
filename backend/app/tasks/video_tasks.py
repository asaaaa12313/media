"""포커스미디어 영상 생성 파이프라인"""
from __future__ import annotations
import logging
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

from app.core.config import TEMP_DIR, OUTPUT_DIR, TARGET_DURATION
from app.models.schemas import BusinessInfo, BrandConfig, SceneConfig
from app.services.template_engine import get_template
from app.services.scene_text_gen import generate_scene_texts
from app.services.bgm_selector import select_bgm, auto_select_bgm
from app.services import scene_compositor, ffmpeg_composer
from app.services.project import save_project, copy_photos_to_project


def process_focus_media(job_id: str, update_fn, options: dict) -> dict:
    """포커스미디어 영상 생성 메인 파이프라인"""
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(exist_ok=True, parents=True)

    try:
        # 1. 입력 데이터 로드
        update_fn("loading", 5)
        business = BusinessInfo(**options["business"])
        brand = BrandConfig(**options.get("brand", {}))
        scenes_data = options.get("scenes", [])

        # 2. 템플릿 결정
        update_fn("template", 10)
        template = get_template(
            business.category,
            brand.primary_color,
            brand.secondary_color,
        )

        # 팔레트 색상이 있으면 template에 오버라이드
        palette = brand.color_palette if hasattr(brand, 'color_palette') and brand.color_palette else []
        if not palette:
            palette = options.get("brand", {}).get("color_palette", [])
        if palette and len(palette) >= 2:
            def _hex_to_rgb(h: str) -> tuple:
                h = h.lstrip("#")
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            template["primary"] = _hex_to_rgb(palette[0])
            template["accent"] = _hex_to_rgb(palette[1])
            if len(palette) >= 3:
                template["secondary"] = _hex_to_rgb(palette[2])

        # 3. 사진 로드
        update_fn("photos", 15)
        upload_dir = Path(options.get("upload_dir", ""))
        photos = _load_photos(upload_dir)
        video_paths = _find_videos(upload_dir)

        if not photos and not video_paths:
            raise RuntimeError("사진이나 영상이 없습니다")

        logo_path = options.get("logo_path", "")

        # 4. 씬 텍스트: 사용자 입력 우선, 없으면 AI 생성
        update_fn("text_gen", 20)
        num_scenes = options.get("num_scenes", 4)
        if scenes_data and any(s.get("headline") for s in scenes_data):
            scenes = [SceneConfig(**s) for s in scenes_data]
        else:
            scenes = generate_scene_texts(business, num_scenes=num_scenes)

        # 씬 개수 보정 (최소 4개)
        while len(scenes) < max(4, num_scenes):
            scenes.append(SceneConfig(
                headline="", subtext="",
                media_index=len(scenes) % max(1, len(photos)),
                media_type="photo",
            ))

        # media_index 범위 보정
        for s in scenes:
            if photos:
                s.media_index = min(s.media_index, len(photos) - 1)

        # 5. 영상 생성
        update_fn("rendering", 30)
        frame_size = options.get("frame_size", "1080x1650")
        use_clip_pipeline = True  # 새 파이프라인 (CSS 애니메이션 영상 녹화)

        combined_path = None
        if use_clip_pipeline and not video_paths:
            # 새 파이프라인: HTML + CSS animation → Playwright 영상 녹화 → xfade
            try:
                combined_path = scene_compositor.generate_video_clips(
                    job_dir, business, brand, scenes, photos,
                    template, logo_path,
                    frame_size=frame_size,
                    progress_cb=lambda p: update_fn("rendering", 30 + int(p * 50)),
                )
                logger.info("[pipeline] 클립 기반 파이프라인 성공")
            except Exception as e:
                logger.warning(f"[pipeline] 클립 기반 파이프라인 실패, 레거시로 폴백: {e}")
                # 사진 재로드 (generate_video_clips에서 close됨)
                photos = _load_photos(upload_dir)
                combined_path = None

        if combined_path is None:
            # 레거시 파이프라인: HTML → PNG 스크린샷 → 프레임 시퀀스
            combined_path = scene_compositor.generate_mixed_video(
                job_dir, business, brand, scenes, photos,
                video_paths, template, logo_path,
                frame_size=frame_size,
                progress_cb=lambda p: update_fn("rendering", 30 + int(p * 50)),
            )

        # 6. BGM: genre 지정 없으면 업종 기반 자동
        update_fn("bgm", 82)
        bgm_genre = options.get("bgm_genre", "")
        if bgm_genre:
            bgm_info = select_bgm(genre=bgm_genre,
                                   bgm_dir=options.get("bgm_dir", ""))
        else:
            bgm_info = auto_select_bgm(business.category,
                                        bgm_dir=options.get("bgm_dir", ""))

        bgm_path = bgm_info.get("path", "")
        if not bgm_path:
            logger.warning("[BGM] BGM 파일을 찾을 수 없습니다. 무음 영상으로 생성합니다. "
                           f"BGM 디렉토리를 확인하세요: bgm_genre={bgm_genre}, category={business.category}")

        # 7. 최종 합성 (BGM 추가)
        update_fn("composing", 85)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = business.name.replace(" ", "_")[:20]
        filename = f"focus_{timestamp}_{safe_name}.mp4"
        output_path = str(OUTPUT_DIR / filename)

        logger.info(f"[composing] bgm_path='{bgm_info.get('path', '')}', output={output_path}")

        ffmpeg_composer.compose_from_video(
            combined_path, bgm_info.get("path", ""),
            output_path, TARGET_DURATION,
        )

        # 8. 프로젝트 저장
        update_fn("saving", 93)
        save_project(
            project_id=job_id,
            business=options["business"],
            brand=options.get("brand", {}),
            scenes=[s.model_dump() for s in scenes],
            frame_size=frame_size,
            bgm_genre=bgm_info.get("genre", ""),
            logo_path=logo_path,
            output_filename=filename,
        )
        copy_photos_to_project(job_id, upload_dir)

        # 9. 임시 파일 정리
        update_fn("cleanup", 97)
        shutil.rmtree(job_dir, ignore_errors=True)

        return {
            "status": "completed",
            "progress": 100,
            "filename": filename,
            "project_id": job_id,
            "bgm_genre": bgm_info.get("genre", ""),
        }

    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise


def _load_photos(upload_dir: Path, max_pixels: int = 1200 * 1800) -> list[Image.Image]:
    """업로드 디렉토리에서 사진 로드 (메모리 절약을 위해 즉시 리사이즈)"""
    photos = []
    if not upload_dir or not upload_dir.exists():
        return photos

    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp",
                "*.JPG", "*.JPEG", "*.PNG"):
        for f in sorted(upload_dir.glob(ext)):
            try:
                img = Image.open(f).convert("RGB")
                # 메모리 절약: 필요 이상 큰 이미지는 즉시 축소
                total = img.width * img.height
                if total > max_pixels:
                    ratio = (max_pixels / total) ** 0.5
                    new_w = int(img.width * ratio)
                    new_h = int(img.height * ratio)
                    img = img.resize((new_w, new_h), Image.LANCZOS)
                photos.append(img)
            except Exception:
                continue
    return photos


def _find_videos(upload_dir: Path) -> dict[int, str]:
    """업로드 디렉토리에서 영상 파일 인덱스 맵핑"""
    videos = {}
    if not upload_dir or not upload_dir.exists():
        return videos

    idx = 0
    for ext in ("*.mp4", "*.mov", "*.avi", "*.MP4", "*.MOV"):
        for f in sorted(upload_dir.glob(ext)):
            videos[idx] = str(f)
            idx += 1
    return videos
