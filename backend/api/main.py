"""
RazorGrowth Agent v2 — FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: inject env vars from Pydantic settings so LangChain/OpenAI can find them."""
    from backend.config import settings
    from backend.agent.tools import set_catalog
    from backend.db.seed_catalog import SEED_CATALOG

    # Inject keys into process env — LangChain reads os.environ, not Settings directly
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.razorpay_key_id:
        os.environ["RAZORPAY_KEY_ID"] = settings.razorpay_key_id
    if settings.razorpay_key_secret:
        os.environ["RAZORPAY_KEY_SECRET"] = settings.razorpay_key_secret

    # Seed agent catalog so tools have data to work with
    set_catalog(SEED_CATALOG)

    yield  # app runs here


from backend.api.routes.propose import router as propose_router
from backend.api.routes.audit import router as audit_router
from backend.api.routes.catalog import router as catalog_router
from backend.api.routes.feeds import router as feeds_router

app = FastAPI(
    title="RazorGrowth Agent v2",
    description="Agentic commerce with cryptographic mandate chain and Razorpay integration",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(propose_router, prefix="/api", tags=["Commerce"])
app.include_router(audit_router, prefix="/api", tags=["Audit"])
app.include_router(catalog_router, prefix="/api", tags=["Catalog"])
app.include_router(feeds_router, prefix="/api", tags=["Feeds"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "razorgrowth-v2"}
