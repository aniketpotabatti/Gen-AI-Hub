"""
API router — registers all route modules.
"""
from fastapi import APIRouter
from app.api.routes.generate import router as generate_router
from app.api.routes.export import router as export_router

api_router = APIRouter()
api_router.include_router(generate_router)
api_router.include_router(export_router)
