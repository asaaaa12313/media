"""FastAPI 메인 앱 - 포커스미디어 영상 자동 생성기"""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

logger.info("=== 서버 시작 ===")
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.api.routes import router
    logger.info("=== 모듈 임포트 성공 ===")
except Exception as e:
    logger.error(f"=== 모듈 임포트 실패: {e} ===")
    sys.exit(1)

app = FastAPI(title="포커스미디어 영상 생성기", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
