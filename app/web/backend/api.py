from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import os
import sys
import logging
from typing import Optional, List, Dict, Any, Union

from app.web.backend.memento_service import MementoService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Memento Web Interface")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
memento_service = MementoService()

# Pydantic models for request validation
class InitFromNDExRequest(BaseModel):
    uuid: str

class InitEmptyRequest(BaseModel):
    initial_action_desc: str
    clear_kg: bool = True


@app.get("/api/status")
async def get_status():
    """Get the current status of the server."""
    return {
        "status": "ok",
        "initialized": memento_service.initialized,
        "version": "1.0.0"
    }

@app.post("/api/init/ndex")
async def initialize_from_ndex(request: InitFromNDExRequest):
    """Initialize the system from an NDEx network."""
    result = await memento_service.initialize_from_ndex(request.uuid)
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.get("/api/kg/status")
async def check_kg_status():
    """Check if the knowledge graph has any data."""
    result = await memento_service.check_kg_has_data()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.post("/api/kg/clear")
async def clear_knowledge_graph():
    """Clear all data from the knowledge graph."""
    result = await memento_service.clear_knowledge_graph()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.post("/api/init/empty")
async def initialize_empty(request: InitEmptyRequest):
    """Initialize the system with an empty KG and initial action."""
    result = await memento_service.initialize_empty(request.initial_action_desc, request.clear_kg)
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.get("/api/ndex/networks")
async def get_ndex_networks():
    """Get available networks from NDEx account."""
    result = await memento_service.get_ndex_networks()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.get("/api/episode/current")
async def get_current_episode():
    """Get the current episode information."""
    result = await memento_service.get_current_episode()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.post("/api/episode/next")
async def start_next_episode():
    """Create the next episode."""
    result = await memento_service.start_next_episode()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.post("/api/episode/prompt")
async def run_prompt():
    """Run the prompt for the current episode."""
    result = await memento_service.run_prompt()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.post("/api/episode/execute")
async def execute_tasks():
    """Execute the tasks for the current episode."""
    result = await memento_service.execute_tasks()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.post("/api/snapshot/save")
async def save_snapshot():
    """Save the current KG to NDEx."""
    result = await memento_service.save_snapshot()
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the server shuts down."""
    await memento_service.cleanup()
    logger.info("Server shutting down, resources cleaned up")

# Mount static files for the frontend
app.mount("/", StaticFiles(directory="app/web/frontend", html=True), name="frontend")

# Default route to serve the index.html
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse("app/web/frontend/index.html")

def start():
    """Entry point for running the app with uvicorn."""
    import uvicorn
    uvicorn.run("app.web.backend.api:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()
