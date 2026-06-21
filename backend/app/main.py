from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    accounts,
    audit_log,
    backups,
    budgets,
    categories,
    coinbase,
    data_quality,
    goals,
    health,
    holdings,
    imports,
    instruments,
    liabilities,
    monthly_review,
    prices,
    reconciliation,
    recurring,
    reports,
    rules,
    settings,
    snapshots,
    transactions,
)
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging import configure_logging
from app.core.paths import ensure_data_dirs
from app.models import domain  # noqa: F401
from app.services.daily_refresh_service import run_daily_refresh
from app.services.seed_service import ensure_seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    ensure_data_dirs()
    Base.metadata.create_all(bind=engine)
    settings_obj = get_settings()
    with SessionLocal() as db:
        if settings_obj.demo_seed_enabled:
            ensure_seed_data(db)
        run_daily_refresh(db)
        db.commit()
    yield


def create_app() -> FastAPI:
    settings_obj = get_settings()
    app = FastAPI(title=settings_obj.app_name, version=settings_obj.app_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings_obj.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def standard_exception_handler(_request: Request, exc: Exception):
        if hasattr(exc, "status_code"):
            raise exc
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected local app error occurred.",
                "details": {"error": str(exc)},
                "recommended_action": "Check data/logs/backend.log and retry the operation.",
            },
        )

    api_prefix = "/api"
    for router in [
        health.router,
        accounts.router,
        transactions.router,
        categories.router,
        rules.router,
        imports.router,
        reconciliation.router,
        instruments.router,
        holdings.router,
        prices.router,
        budgets.router,
        recurring.router,
        goals.router,
        liabilities.router,
        snapshots.router,
        reports.router,
        monthly_review.router,
        data_quality.router,
        backups.router,
        audit_log.router,
        settings.router,
        coinbase.router,
    ]:
        app.include_router(router, prefix=api_prefix)
    return app


app = create_app()
