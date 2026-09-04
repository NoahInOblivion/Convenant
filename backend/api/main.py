"""
RazorGrowth Agent v2 — FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.propose import router as propose_router
from backend.api.routes.audit import router as audit_router
from backend.api.routes.catalog import router as catalog_router
from backend.api.routes.feeds import router as feeds_router

app = FastAPI(
    title="RazorGrowth Agent v2",
    description="Agentic commerce with cryptographic mandate chain and Razorpay integration",
    version="2.0.0",
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
