"""포커스미디어 영상 생성 파이프라인"""
from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image

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

        # 5. 프레임 생성
        update_fn("rendering", 30)
        frame_size = options.get("frame_size", "1080x1650")
        has_video_scenes = any(
            s.media_type == "video" and i in video_paths
            for i, s in enumerate(scenes)
        )

        if has_video_scenes:
            combined_path = scene_compositor.generate_mixed_video(
                job_dir, business, brand, scenes, photos,
                video_paths, template, logo_path,
                frame_size=frame_size,
                progress_cb=lambda p: update_fn("rendering", 30 + int(p * 50)),
            )
        else:
            frames_dir = scene_compositor.generate_all_frames(
                job_dir, business, brand, scenes, photos,
                template, logo_path,
                frame_size=frame_size,
                progress_cb=lambda p: update_fn("rendering", 30 + int(p * 50)),
            )
            combined_path = None

        # 6. BGM: genre 지정 없으면 업종 기반 자동
        update_fn("bgm", 82)
        bgm_genre = options.get("bgm_genre", "")
        if bgm_genre:
            bgm_info = select_bgm(genre=bgm_genre,
                                   bgm_dir=options.get("bgm_dir", ""))
        else:
            bgm_info = auto_select_bgm(business.category,
                                        bgm_dir=options.get("bgm_dir", ""))

        # 7. 최종 합성
        update_fn("composing", 85)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = business.name.replace(" ", "_")[:20]
        filename = f"focus_{timestamp}_{safe_name}.mp4"
        output_path = str(OUTPUT_DIR / filename)

        if has_video_scenes:
            ffmpeg_composer.compose_from_video(
                combined_path, bgm_info.get("path", ""),
                output_path, TARGET_DURATION,
            )
        else:
            ffmpeg_composer.compose_from_frames(
                frames_dir, bgm_info.get("path", ""),
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


def _load_photos(upload_dir: Path) -> list[Image.Image]:
    """업로드 디렉토리에서 사진 로드"""
    photos = []
    if not upload_dir or not upload_dir.exists():
        return photos

    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp",
                "*.JPG", "*.JPEG", "*.PNG"):
        for f in sorted(upload_dir.glob(ext)):
            try:
                photos.append(Image.open(f).convert("RGB"))
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
