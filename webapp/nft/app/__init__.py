import asyncio
from logging import Logger
from pathlib import Path

from dependency_injector.wiring import inject, Provide
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from nft.app.config import settings
from nft.app.containers import Container
from nft.app.internal import run_scanner
from nft.app.routers import healthcheck, nft, call_center


@inject
async def catch_exceptions_middleware(
        request: Request, call_next,
        logger: Logger = Provide[Container.logger]):
    try:
        return await call_next(request)
    except Exception as e:
        print(e)
        return JSONResponse(content={'detail': 'Internal server error'},
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


app = FastAPI(title=settings.APP_NAME, redoc_url=None, docs_url=None)
app.container = Container()
app.include_router(nft.router)
app.include_router(healthcheck.router)
app.include_router(call_center.router)

app.middleware('http')(catch_exceptions_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['POST', 'GET'],
    allow_headers=['*'],
)


@app.get('/user-cats')
async def redirect_static():
    return RedirectResponse(url='/')


app.mount('/', StaticFiles(
    directory=Path(__file__).cwd() / settings.STATIC_DIR,
    html=True),
          name="static")


@app.on_event('startup')
def init_resources():
    app.container.init_resources()


@app.on_event('startup')
def scan_blocks():
    asyncio.create_task(run_scanner())
