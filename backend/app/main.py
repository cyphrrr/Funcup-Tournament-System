import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import router
from .db import engine
from . import models

# DB-Tabellen erstellen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BIW Pokal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Static Files für Uploads (Wappen, etc.)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
if os.path.exists(UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/health")
def health():
    return {"status": "ok"}
