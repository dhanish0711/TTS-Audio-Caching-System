"""
TTS Audio Caching System — Entry Point
========================================
Launches the FastAPI server with the cache API and serves
the static dashboard.
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import router
from config import SERVER_HOST, SERVER_PORT

app = FastAPI(
    title="TTS Audio Caching System",
    description="Cache layer for Text-to-Speech audio to reduce repeated generation latency.",
    version="1.0.0",
)

# Register API routes
app.include_router(router)

# Serve dashboard static files
dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
app.mount("/static", StaticFiles(directory=dashboard_dir), name="static")


@app.get("/")
async def serve_dashboard():
    """Serve the web dashboard."""
    return FileResponse(os.path.join(dashboard_dir, "index.html"))


if __name__ == "__main__":
    print(f"\n[TTS Audio Cache] Server starting on http://localhost:{SERVER_PORT}")
    print(f"[Dashboard] http://localhost:{SERVER_PORT}/\n")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
