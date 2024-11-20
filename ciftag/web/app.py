import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from version import version
from ciftag.configuration import conf
from ciftag.exceptions import CiftagAPIException
from ciftag.web.api import api_router


def create_app(debug=True):
    api_app = FastAPI(title="CIFTAG REST API", version=version, description="CIFTAG REST API", debug=debug)

    # CORS 설정
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    api_app.include_router(api_router, prefix="/api")

    # CiftagAPIException -> HTTPException 자동 변환
    @api_app.exception_handler(CiftagAPIException)
    def handle_ciftag_exception(request, exc: CiftagAPIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc)}
        )

    return api_app


if __name__ == "__main__":
    app = create_app()
    host = conf.get("web", "api_host")
    port = conf.get("web", "api_port")
    uvicorn.run(app, host=host, port=int(port))
