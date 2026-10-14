"""Apollo FastAPI Main Application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_approvals import router as approvals_router
from app.api.routes_evidence import router as evidence_router
from app.api.routes_plugins import router as plugins_router
from app.api.routes_reports import router as reports_router
from app.api.routes_research import router as research_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("apollo")

app = FastAPI(
    title="Apollo Financial Research API",
    description="Plugin-based financial research platform with verifiable SEC EDGAR citations",
    version="0.1.0",
)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(research_router)
app.include_router(approvals_router)
app.include_router(evidence_router)
app.include_router(reports_router)
app.include_router(plugins_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "env": settings.APOLLO_ENV}
