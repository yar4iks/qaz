import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import init_engine
from app.models import Base
from app.routes_admin import router as admin_router
from app.routes_tracking import router as tracking_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_app(database_url: str | None = None) -> FastAPI:
    init_engine(database_url)
    from app.db import ENGINE

    Base.metadata.create_all(bind=ENGINE)

    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.state.templates = Jinja2Templates(directory="templates")

    app.include_router(admin_router)
    app.include_router(tracking_router)
    return app


app = create_app()
