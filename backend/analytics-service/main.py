import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

import redis
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8011"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/11")

logger = structlog.get_logger()
app = FastAPI(title="AetherAI Analytics Service", version="2026.7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class AnalyticsEvent(BaseModel):
    event_type: str
    user_id: str = None
    session_id: str = None
    properties: Dict[str, Any] = {}
    timestamp: str = None

events_db: List[Dict] = []

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "analytics-service", "version": "2026.7.0", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/analytics/events")
async def track_event(data: AnalyticsEvent):
    event = {"id": str(uuid.uuid4()), "event_type": data.event_type, "user_id": data.user_id, "session_id": data.session_id, "properties": data.properties, "timestamp": data.timestamp or datetime.now(timezone.utc).isoformat()}
    events_db.append(event)
    redis_client.lpush("analytics:events", str(event))
    redis_client.ltrim("analytics:events", 0, 9999)
    return {"status": "tracked"}

@app.get("/api/v1/analytics/dashboard")
async def get_dashboard(request: Request, days: int = 30):
    total_events = len(events_db)
    unique_users = len(set(e["user_id"] for e in events_db if e["user_id"]))
    model_usage = {}
    for e in events_db:
        if e["event_type"] == "model_request":
            model = e["properties"].get("model_id", "unknown")
            model_usage[model] = model_usage.get(model, 0) + 1
    return {"total_events": total_events, "unique_users": unique_users, "model_usage": model_usage, "period_days": days}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
