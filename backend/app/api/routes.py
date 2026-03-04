"""포커스미디어 REST API 엔드포인트"""
from __future__ import annotations
import uuid
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from PIL import Image

from app.core.config import UPLOAD_DIR, OUTPUT_DIR, PROJECTS_DIR
from app.tasks.task_manager import task_manager
from app.tasks.video_tasks import process_focus_media
from app.services.bgm_selector import list_genres
from app.services.scene_text_gen import generate_scene_texts
from app.services.place_scraper import extract_place_info, download_place_photos
from app.services.project import (
    save_project, load_project, list_projects, delete_project,
    get_project_previews,
)
from app.services.template_engine import get_template
from app.services.layout_renderer import (
    LayoutRenderer, build_scene_layout, FRAME_SIZES, DEFAULT_FRAME_SIZE,
)
from app.services.info_panel import render_bottom_bar
from app.services.brand_system import load_logo, load_logo_small
from app.services.qr_generator import generate_qr
from app.models.schemas import BusinessInfo, SceneUpdateRequest

router = APIRouter()


@router.post("/api/generate-full")
async def generate_full(
    business_name: str = Form(...),
    category: str = Form("기타"),
    tagline: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    website: str = Form(""),
    services: str = Form(""),
    primary_color: str = Form(""),
    secondary_color: str = Form(""),
    bgm_genre: str = Form(""),
    text_mode: str = Form("ai"),
    frame_size: str = Form("1080x1650"),
    num_scenes: int = Form(4),
    scene_headlines: str = Form(""),
    scene_subtexts: str = Form(""),
    scene_types: str = Form(""),
    scene_font_colors: str = Form(""),
    scene_emphasis_colors: str = Form(""),
    scene_text_positions: str = Form(""),
    upload_dir_override: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    logo: Optional[UploadFile] = File(None),
):
    """원스텝 업로드 + 생성"""
    # 자동 사진 모드: 이미 다운로드된 디렉토리 사용
    if upload_dir_override and Path(upload_dir_override).exists():
        job_upload_dir = Path(upload_dir_override)
        job_id = job_upload_dir.name
    else:
        job_id = uuid.uuid4().hex[:8]
        job_upload_dir = UPLOAD_DIR / job_id
        job_upload_dir.mkdir(exist_ok=True, parents=True)

    logo_path = ""
    if logo and logo.filename:
        logo_path = str(job_upload_dir / f"logo_{logo.filename}")
        with open(logo_path, "wb") as f:
            f.write(await logo.read())

    for i, file in enumerate(files):
        if file.filename:
            file_path = job_upload_dir / f"{i:02d}_{file.filename}"
            with open(file_path, "wb") as f:
                f.write(await file.read())

    # 씬 텍스트 파싱
    scenes = []
    font_colors = scene_font_colors.split("|") if scene_font_colors else []
    emphasis_colors = scene_emphasis_colors.split("|") if scene_emphasis_colors else []
    text_positions = scene_text_positions.split("|") if scene_text_positions else []

    if scene_headlines:
        headlines = scene_headlines.split("|")
        subtexts = scene_subtexts.split("|") if scene_subtexts else [""] * len(headlines)
        types = scene_types.split("|") if scene_types else [""] * len(headlines)
        for i, (h, s) in enumerate(zip(headlines, subtexts)):
            scenes.append({
                "headline": h.strip(),
                "subtext": s.strip(),
                "media_index": i,
                "media_type": "photo",
                "scene_type": types[i].strip() if i < len(types) else "",
                "font_color": font_colors[i].strip() if i < len(font_colors) else "",
                "emphasis_color": emphasis_colors[i].strip() if i < len(emphasis_colors) else "",
                "text_position": text_positions[i].strip() if i < len(text_positions) else "",
            })

    services_list = [s.strip() for s in services.split(",") if s.strip()]

    options = {
        "business": {
            "name": business_name,
            "category": category,
            "tagline": tagline,
            "phone": phone,
            "address": address,
            "website": website,
            "services": services_list,
        },
        "brand": {
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "text_color": "#FFFFFF",
        },
        "scenes": scenes,
        "num_scenes": num_scenes,
        "frame_size": frame_size,
        "bgm_genre": bgm_genre,
        "text_mode": text_mode,
        "upload_dir": str(job_upload_dir),
        "logo_path": logo_path,
    }

    task_id = task_manager.submit(process_focus_media, options)
    return {"task_id": task_id, "job_id": job_id}


@router.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """작업 진행 상태 조회"""
    return task_manager.get_status(task_id)


@router.get("/api/download/{filename}")
async def download(filename: str):
    """완성된 영상 다운로드"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return {"error": "파일을 찾을 수 없습니다"}
    return FileResponse(str(file_path), filename=filename,
                        media_type="video/mp4")


@router.get("/api/output/list")
async def list_outputs():
    """완성된 영상 목록"""
    items = []
    for f in sorted(OUTPUT_DIR.glob("*.mp4"), reverse=True):
        items.append({
            "filename": f.name,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
        })
    return {"files": items}


@router.get("/api/bgm/genres")
async def bgm_genres(bgm_dir: str = ""):
    """BGM 장르 목록"""
    return {"genres": list_genres(bgm_dir)}


@router.post("/api/generate-texts")
async def generate_texts(business: BusinessInfo, num_scenes: int = 4):
    """AI로 씬 텍스트 자동 생성"""
    scenes = generate_scene_texts(business, num_scenes=num_scenes)
    return {"scenes": [s.model_dump() for s in scenes]}


@router.post("/api/place-info")
async def get_place_info(url: str = Form(...)):
    """네이버 플레이스 URL에서 업체 정보 추출"""
    try:
        info = extract_place_info(url)
        if not info.get("name"):
            return {"error": info.get("error", "업체 정보를 추출할 수 없습니다")}
        return info
    except Exception as e:
        return {"error": f"정보 추출 실패: {str(e)}"}


@router.post("/api/place-photos")
async def get_place_photos(url: str = Form(...), job_id: str = Form("")):
    """네이버 플레이스 사진 다운로드"""
    if not job_id:
        job_id = uuid.uuid4().hex[:8]

    job_upload_dir = UPLOAD_DIR / job_id
    job_upload_dir.mkdir(exist_ok=True, parents=True)

    try:
        saved_files = download_place_photos(url, str(job_upload_dir), max_photos=10)
        filenames = [Path(f).name for f in saved_files]
        return {
            "job_id": job_id,
            "upload_dir": str(job_upload_dir),
            "files": filenames,
            "count": len(filenames),
        }
    except Exception as e:
        return {"error": f"사진 다운로드 실패: {str(e)}", "upload_dir": "", "count": 0}


# ─────────────────────────────────────────────
# 프로젝트 관리
# ─────────────────────────────────────────────

@router.get("/api/projects")
async def api_list_projects():
    """프로젝트 목록 (최신순)"""
    return {"projects": list_projects()}


@router.get("/api/projects/{project_id}")
async def api_get_project(project_id: str):
    """프로젝트 상세 조회"""
    data = load_project(project_id)
    if not data:
        return {"error": "프로젝트를 찾을 수 없습니다"}
    data["previews"] = get_project_previews(project_id)
    return data


@router.delete("/api/projects/{project_id}")
async def api_delete_project(project_id: str):
    """프로젝트 삭제"""
    if delete_project(project_id):
        return {"ok": True}
    return {"error": "프로젝트를 찾을 수 없습니다"}


@router.get("/api/projects/{project_id}/preview/{scene_index}")
async def api_scene_preview(project_id: str, scene_index: int):
    """씬 프리뷰 이미지 반환"""
    previews = get_project_previews(project_id)
    if scene_index < 0 or scene_index >= len(previews):
        return {"error": "프리뷰를 찾을 수 없습니다"}
    return FileResponse(previews[scene_index], media_type="image/jpeg")


# ─────────────────────────────────────────────
# 씬 수정 + 프리뷰 재생성
# ─────────────────────────────────────────────

@router.put("/api/projects/{project_id}/scenes/{scene_index}")
async def api_update_scene(project_id: str, scene_index: int,
                           update: SceneUpdateRequest):
    """씬 수정 후 프리뷰 재생성"""
    data = load_project(project_id)
    if not data:
        return {"error": "프로젝트를 찾을 수 없습니다"}

    scenes = data.get("scenes", [])
    if scene_index < 0 or scene_index >= len(scenes):
        return {"error": "씬 인덱스 범위 초과"}

    scene = scenes[scene_index]

    # 변경 사항 적용
    if update.headline is not None:
        scene["headline"] = update.headline
    if update.subtext is not None:
        scene["subtext"] = update.subtext
    if update.text_blocks is not None:
        scene["text_blocks"] = [tb.model_dump() for tb in update.text_blocks]
    if update.photo_index is not None:
        scene["media_index"] = update.photo_index
    if update.scene_type is not None:
        scene["scene_type"] = update.scene_type
    if update.text_position is not None:
        scene["text_position"] = update.text_position
    if update.font_color is not None:
        scene["font_color"] = update.font_color
    if update.emphasis_color is not None:
        scene["emphasis_color"] = update.emphasis_color

    # 프리뷰 재생성
    frame_size = data.get("frame_size", DEFAULT_FRAME_SIZE)
    template = get_template(
        data["business"].get("category", "기타"),
        data["brand"].get("primary_color", ""),
        data["brand"].get("secondary_color", ""),
    )

    # 사진 로드
    photos_dir = PROJECTS_DIR / project_id / "photos"
    photos = _load_project_photos(photos_dir)

    if photos:
        from app.core.config import get_scene_sequence
        num_scenes = len(data.get("scenes", []))
        default_seq = get_scene_sequence(
            data["business"].get("category", "기타"),
            num_scenes,
        )
        scene_type = scene.get("scene_type") or (
            default_seq[scene_index] if scene_index < len(default_seq) else "cta"
        )

        custom_blocks = scene.get("text_blocks") or None
        layout = build_scene_layout(
            scene_type=scene_type,
            template=template,
            headline=scene.get("headline", ""),
            subtext=scene.get("subtext", ""),
            business_name=data["business"].get("name", ""),
            services=data["business"].get("services", []),
            custom_blocks=custom_blocks,
            font_color_override=scene.get("font_color", ""),
            emphasis_color=scene.get("emphasis_color", ""),
            emphasis_words=scene.get("emphasis_words", []),
        )

        logo_path = data.get("logo_path", "")
        logo = load_logo(logo_path) if logo_path else None
        renderer = LayoutRenderer(template, logo,
                                  data["business"].get("name", ""),
                                  frame_size=frame_size)

        logo_small = load_logo_small(logo_path) if logo_path else None
        qr = generate_qr(data["business"].get("website", ""))
        bottom_bar = render_bottom_bar(
            template, data["business"].get("name", ""),
            data["business"].get("phone", ""),
            data["business"].get("address", ""),
            logo_small, qr,
        )
        renderer.set_bottom_bar(bottom_bar)

        photo_idx = min(scene.get("media_index", 0), max(0, len(photos) - 1))
        frame = renderer.render_scene(layout, photos, photo_idx)

        preview_path = PROJECTS_DIR / project_id / "previews" / f"scene_{scene_index}.jpg"
        preview_path.parent.mkdir(exist_ok=True)
        frame.save(str(preview_path), quality=85)

    # 프로젝트 저장
    save_project(
        project_id=project_id,
        business=data["business"],
        brand=data["brand"],
        scenes=scenes,
        frame_size=frame_size,
        bgm_genre=data.get("bgm_genre", ""),
        logo_path=data.get("logo_path", ""),
        output_filename=data.get("output_filename", ""),
    )

    return {"ok": True, "scene_index": scene_index}


@router.post("/api/projects/{project_id}/regenerate")
async def api_regenerate_project(project_id: str):
    """수정된 설정으로 영상 전체 재생성"""
    data = load_project(project_id)
    if not data:
        return {"error": "프로젝트를 찾을 수 없습니다"}

    photos_dir = PROJECTS_DIR / project_id / "photos"
    if not photos_dir.exists():
        return {"error": "프로젝트 사진을 찾을 수 없습니다"}

    options = {
        "business": data["business"],
        "brand": data.get("brand", {}),
        "scenes": data.get("scenes", []),
        "num_scenes": len(data.get("scenes", [])),
        "frame_size": data.get("frame_size", "1080x1650"),
        "bgm_genre": data.get("bgm_genre", ""),
        "text_mode": "manual",
        "upload_dir": str(photos_dir),
        "logo_path": data.get("logo_path", ""),
    }

    task_id = task_manager.submit(process_focus_media, options)
    return {"task_id": task_id, "project_id": project_id}


def _load_project_photos(photos_dir: Path) -> list[Image.Image]:
    """프로젝트 사진 디렉토리에서 이미지 로드"""
    photos = []
    if not photos_dir.exists():
        return photos
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        for f in sorted(photos_dir.glob(ext)):
            try:
                photos.append(Image.open(f).convert("RGB"))
            except Exception:
                continue
    return photos
