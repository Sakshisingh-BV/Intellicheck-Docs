from fastapi import FastAPI
from app.routes.upload import router

app = FastAPI()

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Backend running"}