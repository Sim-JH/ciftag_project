import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ciftag.version import version
from ciftag.configuration import conf
from ciftag.web.api import api_router


def create_app(debug=True):
    __app = FastAPI(title="CIFTAG REST API", version=version, description="CIFTAG REST API", debug=debug)

    # CORS 설정
    __app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    __app.include_router(api_router, prefix="/api")

    return __app


if __name__ == "__main__":
    app = create_app()
    host = conf.get("web", "api_host")
    port = conf.get("web", "api_port")
    uvicorn.run(app, host=host, port=int(port))
