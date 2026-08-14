from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from core.config import get_settings
from core.internal_auth import enforce_backend_access

settings = get_settings()
Path("uploads").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="3D Print Manager API", version="0.1.0")
app.middleware("http")(enforce_backend_access)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.backend_cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
