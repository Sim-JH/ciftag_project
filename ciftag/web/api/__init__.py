from fastapi import APIRouter

from .cred import router as cred_router
from .crawl import router as crawl_router
from .result import router as pinterest_router
# from .download import router as download_router  # TODO celery -> kafka
from .provider import router as provider_router

api_router = APIRouter()
api_router.include_router(cred_router, prefix='/cred', tags=['Cred'])
api_router.include_router(crawl_router, prefix='/crawl', tags=['Crawl'])
api_router.include_router(pinterest_router, prefix='/result', tags=['Result'])
# api_router.include_router(download_router, prefix='/download', tags=['Download'])
api_router.include_router(provider_router, prefix='/provider', tags=['Provider'])
