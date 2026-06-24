import logging

from fastapi import FastAPI
from app.routes.upload import router as upload_router
from app.routes.classify import router as classify_router
from app.routes.jobs import router as jobs_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Intellicheck Document Intelligence",
    description="OCR + Document Classification + Stamp Detection API",
    version="0.3.0",
)

app.include_router(upload_router)
app.include_router(classify_router)
app.include_router(jobs_router)


@app.on_event("startup")
def on_startup():
    """Create database tables on first run (if they don't exist)."""
    try:
        from app.database.base import create_tables
        from app.database.session import engine

        create_tables(engine)
        logger.info("Database tables verified / created")
    except Exception as e:
        logger.warning(
            f"Database setup skipped (PostgreSQL may not be running): {e}"
        )


@app.get("/")
def root():
    return {"message": "Backend running"}