import json
import logging
from contextlib import asynccontextmanager

import fastapi
import pydantic
from apps.bots.handlers import BotFunctions
from apps.bots.routes import router as bots_router
from core import exceptions
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from json_advanced import dumps

from . import config, db


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):  # type: ignore
    """Initialize application services."""
    logging.info(f"Service initialization")

    await db.init_db()
    config.Settings().config_logger()
    await BotFunctions().setup()

    logging.info("Startup complete")
    yield
    logging.info("Shutdown complete")


app = fastapi.FastAPI(
    title="FastAPI Launchpad",
    # description=DESCRIPTION,
    version="0.1.0",
    contact={
        "name": "Mahdi Kiani",
        "url": "https://github.com/mahdikiani/FastAPILaunchpad",
        "email": "mahdikiany@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/mahdikiani/FastAPILaunchpad/blob/main/LICENSE",
    },
    lifespan=lifespan,
)


@app.exception_handler(exceptions.BaseHTTPException)
async def base_http_exception_handler(
    request: fastapi.Request, exc: exceptions.BaseHTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "error": exc.error},
    )


@app.exception_handler(pydantic.ValidationError)
async def pydantic_exception_handler(
    request: fastapi.Request, exc: pydantic.ValidationError
):
    return JSONResponse(
        status_code=500,
        content={
            "message": str(exc),
            "error": "Exception",
            "erros": json.loads(dumps(exc.errors())),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: fastapi.Request, exc: Exception):
    import traceback

    traceback_str = "".join(traceback.format_tb(exc.__traceback__))
    # body = request._body

    logging.error(f"Exception: {traceback_str} {exc}")
    logging.error(f"Exception on request: {request.url}")
    # logging.error(f"Exception on request: {await request.body()}")
    return JSONResponse(
        status_code=500,
        content={"message": str(exc), "error": "Exception"},
    )


origins = [
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bots_router)


@app.get("/")
async def index():
    return {"message": "Hello World!"}
