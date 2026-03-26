"""
RoboBuddy - Main FastAPI Application

Your Smart Assistant That Actually Remembers You
"""
import time
import json
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .api.routes import router
from .core.scheduler import ProactiveScheduler


# Initialize scheduler
scheduler = ProactiveScheduler()

# Rate limiting storage (in-memory, resets on restart)
rate_limit_store: dict = defaultdict(list)

# Analytics file logging (local collection)
ANALYTICS_LOG = Path.home() / ".robobuddy" / "analytics_events.jsonl"
ANALYTICS_LOG.parent.mkdir(parents=True, exist_ok=True)


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


@app.middleware("http")
async def access_control_middleware(request: Request, call_next):
    """Kill switch, paywall, and rate limiting middleware"""
    path = request.url.path

    # Always allow health checks and admin endpoints
    if path in ["/", "/health", "/admin/status", "/admin/toggle", "/admin/analytics"]:
        return await call_next(request)

    # Kill switch - service disabled
    if not settings.service_enabled:
        return JSONResponse(
            status_code=503,
            content={"error": "Service temporarily unavailable", "message": "We'll be back soon!"}
        )

    # Trial expiration check
    if settings.trial_expires:
        try:
            expires = datetime.fromisoformat(settings.trial_expires).date()
            if date.today() > expires:
                return JSONResponse(
                    status_code=402,
                    content={"error": "Trial ended", "message": "Free trial has ended. Thanks for trying RoboBuddy!"}
                )
        except ValueError:
            pass

    # Paywall check
    if settings.paywall_enabled:
        api_key = request.headers.get("X-API-Key", "")
        valid_keys = [k.strip() for k in settings.api_keys.split(",") if k.strip()]
        if api_key not in valid_keys:
            return JSONResponse(
                status_code=401,
                content={"error": "API key required", "message": "This service requires a valid API key."}
            )

    # Rate limiting (per IP)
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60  # 1 minute window

    # Clean old entries
    rate_limit_store[client_ip] = [t for t in rate_limit_store[client_ip] if now - t < window]

    if len(rate_limit_store[client_ip]) >= settings.rate_limit_per_minute:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "message": f"Max {settings.rate_limit_per_minute} requests per minute"}
        )

    rate_limit_store[client_ip].append(now)

    # Log analytics event (anonymous)
    try:
        with open(ANALYTICS_LOG, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "date": date.today().isoformat(),
                "endpoint": path,
                "method": request.method
            }) + "\n")
    except:
        pass

    return await call_next(request)


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


# ==================== ADMIN ENDPOINTS ====================

@app.get("/admin/status")
async def admin_status(admin_key: str = ""):
    """Get current service status (requires admin key from env)"""
    import os
    expected_key = os.environ.get("ROBOBUDDY_ADMIN_KEY", "robobuddy-admin-2026")
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    return {
        "service_enabled": settings.service_enabled,
        "paywall_enabled": settings.paywall_enabled,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "trial_expires": settings.trial_expires,
        "active_ips": len(rate_limit_store),
        "analytics_file": str(ANALYTICS_LOG)
    }


@app.post("/admin/toggle")
async def admin_toggle(admin_key: str = "", action: str = ""):
    """Toggle service on/off or enable paywall (requires admin key)"""
    import os
    expected_key = os.environ.get("ROBOBUDDY_ADMIN_KEY", "robobuddy-admin-2026")
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    if action == "disable":
        settings.service_enabled = False
        return {"status": "Service DISABLED", "service_enabled": False}
    elif action == "enable":
        settings.service_enabled = True
        return {"status": "Service ENABLED", "service_enabled": True}
    elif action == "paywall_on":
        settings.paywall_enabled = True
        return {"status": "Paywall ENABLED", "paywall_enabled": True}
    elif action == "paywall_off":
        settings.paywall_enabled = False
        return {"status": "Paywall DISABLED", "paywall_enabled": False}
    else:
        return {"error": "Invalid action", "valid_actions": ["disable", "enable", "paywall_on", "paywall_off"]}


@app.get("/admin/analytics")
async def admin_analytics(admin_key: str = "", days: int = 7):
    """Get analytics summary (requires admin key)"""
    import os
    from collections import Counter
    expected_key = os.environ.get("ROBOBUDDY_ADMIN_KEY", "robobuddy-admin-2026")
    if admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    if not ANALYTICS_LOG.exists():
        return {"message": "No analytics data yet", "total_requests": 0}

    # Parse analytics file
    endpoint_counts = Counter()
    daily_counts = Counter()
    total = 0

    cutoff = (datetime.now().date() - __import__('datetime').timedelta(days=days)).isoformat()

    try:
        with open(ANALYTICS_LOG) as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event.get("date", "") >= cutoff:
                        total += 1
                        endpoint_counts[event.get("endpoint", "unknown")] += 1
                        daily_counts[event.get("date", "unknown")] += 1
                except:
                    continue
    except:
        return {"error": "Could not read analytics file"}

    return {
        "period_days": days,
        "total_requests": total,
        "requests_by_endpoint": dict(endpoint_counts.most_common(20)),
        "requests_by_day": dict(sorted(daily_counts.items())),
        "top_features": [
            {"endpoint": e, "count": c}
            for e, c in endpoint_counts.most_common(10)
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
