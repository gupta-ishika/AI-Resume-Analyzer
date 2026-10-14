from fastapi import APIRouter

from backend.api.analyses import router as analyses_router
from backend.api.candidates import router as candidates_router
from backend.api.resumes import router as resumes_router

api_router = APIRouter(prefix="/api")
api_router.include_router(analyses_router)
api_router.include_router(resumes_router)
api_router.include_router(candidates_router)
