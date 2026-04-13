import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import get_settings
from app.db.session import init_db
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.files import router as files_router
from app.routers.onboarding import router as onboarding_router
from app.routers.onboarding_chat import router as onboarding_chat_router
from app.routers.reminders import router as reminders_router
from app.routers.transactions import router as transactions_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(title="UK AI Accountant Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(files_router)
app.include_router(reminders_router)
app.include_router(transactions_router)
app.include_router(conversations_router)
app.include_router(onboarding_router)
app.include_router(onboarding_chat_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_web_dir = Path(__file__).resolve().parent.parent / "web"
if _web_dir.is_dir():
    app.mount("/internal", StaticFiles(directory=str(_web_dir), html=True), name="internal")
