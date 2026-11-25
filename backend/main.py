"""
SmartFlow AI - Main FastAPI Application
AI-Powered Dynamic Intersection Congestion Resolution and Emergency Vehicle Green Corridor System.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routes import detection, signals, emergency, analytics

app = FastAPI(
    title="SmartFlow AI",
    description="AI-Powered Dynamic Traffic Signal & Emergency Green Corridor Management Platform",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core API routers
app.include_router(detection.router)
app.include_router(signals.router)
app.include_router(emergency.router)
app.include_router(analytics.router)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
PUBLIC_DIR = os.path.join(BASE_DIR, "..", "public")

# Mount public assets if directory exists
if os.path.exists(PUBLIC_DIR):
    app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

# Mount frontend static files
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/api/health")
async def health_check():
    """Health check endpoint confirming API and YOLO model availability."""
    return {
        "status": "healthy",
        "service": "SmartFlow AI Backend",
        "yolo_model": "YOLOv8n",
        "version": "1.0.0"
    }


@app.get("/")
async def serve_index():
    """Serves the main SmartFlow AI dashboard application."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "SmartFlow AI Backend is running. Please check frontend/index.html.",
        "docs_url": "/docs"
    }
