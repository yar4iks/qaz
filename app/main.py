import logging

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routes_admin import router as admin_router
from app.routes_tracking import router as tracking_router


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(title="Security Training Tracker")

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(admin_router)
    app.include_router(tracking_router)

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    return app


app = create_app()
