import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import User, UserRole
from app.realtime.ws_manager import manager
from app.routers import alerts, audit, auth, cameras, events, stats, streams, trace, watchlist, ws
from app.security import hash_password
from app.services.analytics_simulator import simulator
from app.services.heartbeat import heartbeat_service

logging.basicConfig(level=logging.INFO)
settings = get_settings()


def _ensure_default_users() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == settings.default_admin_username).first():
            db.add(
                User(
                    username=settings.default_admin_username,
                    email="admin@okdriver.local",
                    full_name="Platform Administrator",
                    hashed_password=hash_password(settings.default_admin_password),
                    role=UserRole.admin,
                )
            )
        if not db.query(User).filter(User.username == settings.default_operator_username).first():
            db.add(
                User(
                    username=settings.default_operator_username,
                    email="operator@okdriver.local",
                    full_name="Duty Operator",
                    hashed_password=hash_password(settings.default_operator_password),
                    role=UserRole.operator,
                )
            )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    _ensure_default_users()
    await manager.startup()
    await simulator.start()
    await heartbeat_service.start()
    yield
    await simulator.stop()
    await heartbeat_service.stop()
    await manager.shutdown()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend for a centralized CCTV monitoring, video analytics and "
        "real-time alerting platform: camera registry, live/simulated "
        "video, ANPR-style event ingest, watchlist correlation and "
        "vehicle trace."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(streams.router)
app.include_router(events.router)
app.include_router(watchlist.router)
app.include_router(alerts.router)
app.include_router(trace.router)
app.include_router(stats.router)
app.include_router(audit.router)
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
