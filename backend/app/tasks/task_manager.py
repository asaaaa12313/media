"""In-process 태스크 매니저 (Celery/Redis 대체)

threading 기반 백그라운드 실행 + dict 기반 상태 저장.
로컬 단일 사용자 환경에 최적화.
"""
import uuid
import threading
from datetime import datetime
from typing import Callable


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable, *args, **kwargs) -> str:
        task_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._tasks[task_id] = {
                "status": "pending",
                "progress": 0,
                "step": "",
                "result": None,
                "error": None,
            }

        def _run():
            try:
                with self._lock:
                    self._tasks[task_id]["status"] = "processing"
                result = fn(task_id, self._make_updater(task_id), *args, **kwargs)
                with self._lock:
                    self._tasks[task_id].update({
                        "status": "completed",
                        "progress": 100,
                        "result": result,
                    })
            except Exception as e:
                with self._lock:
                    self._tasks[task_id].update({
                        "status": "failed",
                        "error": str(e),
                    })

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return task_id

    def _make_updater(self, task_id: str):
        def update(step: str, progress: int):
            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]["step"] = step
                    self._tasks[task_id]["progress"] = progress
        return update

    def get_status(self, task_id: str) -> dict:
        with self._lock:
            task = self._tasks.get(task_id)
        if not task:
            return {"status": "not_found"}
        result = task.get("result") or {}
        return {
            "status": task["status"],
            "progress": task["progress"],
            "step": task["step"],
            "filename": result.get("filename", "") if isinstance(result, dict) else "",
            "error": task.get("error", ""),
            "bgm_genre": result.get("bgm_genre", "") if isinstance(result, dict) else "",
            "project_id": result.get("project_id", "") if isinstance(result, dict) else "",
        }


task_manager = TaskManager()
