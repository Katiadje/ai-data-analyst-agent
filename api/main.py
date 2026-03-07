"""
AI Data Analyst Agent — FastAPI Backend.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.analysis import router as analysis_router
from api.routes.upload import router as upload_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUTS_DIR = os.environ.get("OUTPUTS_DIR", "/tmp/ai_analyst_outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Data Analyst Agent starting up")
    logger.info("📁 Outputs directory: %s", OUTPUTS_DIR)
    yield
    logger.info("🛑 Shutting down")


app = FastAPI(
    title="AI Data Analyst Agent",
    description=(
        "An autonomous AI agent that analyzes any CSV/Excel dataset, "
        "generates visualizations, and writes a full narrative report."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated charts as static files
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

app.include_router(upload_router, prefix="/api/v1", tags=["Upload"])
app.include_router(analysis_router, prefix="/api/v1", tags=["Analysis"])


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "AI Data Analyst Agent API",
        "docs": "/docs",
        "health": "/health",
    }
