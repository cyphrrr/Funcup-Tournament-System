import os
import pathlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import router
from .db import engine
from . import models

# DB-Tabellen erstellen
models.Base.metadata.create_all(bind=engine)

# Version aus VERSION-Datei lesen (Single Source of Truth)
_version_file = pathlib.Path("/VERSION")
if not _version_file.exists():
    _version_file = pathlib.Path(__file__).resolve().parent.parent.parent / "VERSION"
try:
    APP_VERSION = _version_file.read_text().strip()
except FileNotFoundError:
    APP_VERSION = "0.0.0-unknown"

app = FastAPI(title="BIW Pokal API", version=APP_VERSION)

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
