"""프로젝트 저장/로드/관리

프로젝트 디렉토리 구조:
  PROJECTS_DIR/{project_id}/
    project.json   - 업체 정보, 브랜드, 씬 설정, frame_size
    previews/      - 씬별 프리뷰 이미지
    photos/        - 원본 사진 복사본
    output/        - 최종 영상
"""
from __future__ import annotations
import json
import shutil
from datetime import datetime
from pathlib import Path

from app.core.config import PROJECTS_DIR


def _project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def save_project(
    project_id: str,
    business: dict,
    brand: dict,
    scenes: list[dict],
    frame_size: str = "1080x1650",
    bgm_genre: str = "",
    logo_path: str = "",
    output_filename: str = "",
) -> dict:
    """프로젝트 저장 (생성 또는 덮어쓰기)"""
    pdir = _project_dir(project_id)
    pdir.mkdir(exist_ok=True, parents=True)
    (pdir / "previews").mkdir(exist_ok=True)
    (pdir / "photos").mkdir(exist_ok=True)

    data = {
        "project_id": project_id,
        "business": business,
        "brand": brand,
        "scenes": scenes,
        "frame_size": frame_size,
        "bgm_genre": bgm_genre,
        "logo_path": logo_path,
        "output_filename": output_filename,
        "updated_at": datetime.now().isoformat(),
    }

    # created_at 보존
    existing = load_project(project_id)
    if existing:
        data["created_at"] = existing.get("created_at", data["updated_at"])
    else:
        data["created_at"] = data["updated_at"]

    with open(pdir / "project.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data


def load_project(project_id: str) -> dict | None:
    """프로젝트 로드. 없으면 None."""
    json_path = _project_dir(project_id) / "project.json"
    if not json_path.exists():
        return None
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def list_projects() -> list[dict]:
    """전체 프로젝트 목록 (최신순)"""
    projects = []
    if not PROJECTS_DIR.exists():
        return projects

    for pdir in PROJECTS_DIR.iterdir():
        if not pdir.is_dir():
            continue
        data = load_project(pdir.name)
        if data:
            # 프리뷰 존재 여부
            previews = sorted((pdir / "previews").glob("*.jpg"))
            data["preview_count"] = len(previews)
            projects.append(data)

    projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return projects


def delete_project(project_id: str) -> bool:
    """프로젝트 삭제"""
    pdir = _project_dir(project_id)
    if pdir.exists():
        shutil.rmtree(pdir)
        return True
    return False


def copy_photos_to_project(project_id: str, upload_dir: Path) -> list[str]:
    """업로드 사진을 프로젝트 디렉토리로 복사"""
    pdir = _project_dir(project_id) / "photos"
    pdir.mkdir(exist_ok=True, parents=True)

    copied = []
    if not upload_dir or not upload_dir.exists():
        return copied

    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp",
                "*.JPG", "*.JPEG", "*.PNG"):
        for f in sorted(upload_dir.glob(ext)):
            dst = pdir / f.name
            if not dst.exists():
                shutil.copy2(f, dst)
            copied.append(f.name)
    return copied


def get_project_previews(project_id: str) -> list[str]:
    """프로젝트 프리뷰 이미지 경로 목록"""
    pdir = _project_dir(project_id) / "previews"
    if not pdir.exists():
        return []
    return [str(f) for f in sorted(pdir.glob("*.jpg"))]
