from fastapi import APIRouter

from .cred import router as cred_router
from .crawl import router as crawl_router
from .pinterest import router as pinterest_router

api_router = APIRouter()
api_router.include_router(cred_router, prefix='/cred', tags=['Cred'])
api_router.include_router(crawl_router, prefix='/crawl', tags=['Crawl'])
api_router.include_router(pinterest_router, prefix='/pinterest', tags=['Pinterest'])
