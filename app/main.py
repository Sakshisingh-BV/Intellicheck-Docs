from fastapi import FastAPI
from app.routes.upload import router as upload_router
from app.routes.classify import router as classify_router

app = FastAPI(
    title="Intellicheck Document Intelligence",
    description="OCR + Document Classification API",
    version="0.2.0",
)

app.include_router(upload_router)
app.include_router(classify_router)


@app.get("/")
def root():
    return {"message": "Backend running"}