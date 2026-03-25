"""
RoboBuddy - Main FastAPI Application

Your Smart Assistant That Actually Remembers You
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api.routes import router
from .core.scheduler import ProactiveScheduler


# Initialize scheduler
scheduler = ProactiveScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print(f"Starting {settings.companion_name} - RoboBuddy...")
    scheduler.start()
    yield
    # Shutdown
    print("Shutting down...")
    scheduler.stop()


app = FastAPI(
    title="RoboBuddy",
    description="Your Smart Assistant That Actually Remembers You",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "RoboBuddy",
        "status": "online",
        "message": f"Hey! I'm {settings.companion_name} - what's on your mind?",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
