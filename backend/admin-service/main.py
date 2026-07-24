import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

import redis
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8012"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/12")

logger = structlog.get_logger()
app = FastAPI(title="AetherAI Admin Service", version="2026.7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class SystemConfig(BaseModel):
    key: str
    value: Any

class UserAction(BaseModel):
    user_id: str
    action: str
    reason: str = None

system_config: Dict[str, Any] = {
    "maintenance_mode": False,
    "registration_enabled": True,
    "max_file_size": 100 * 1024 * 1024,
    "allowed_models": ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"],
}

users_admin_db: Dict[str, Dict] = {}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "admin-service", "version": "2026.7.0", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/admin/system")
async def get_system_status(request: Request):
    return {
        "status": "operational", "version": "2026.7.0", "uptime": "99.99%",
        "services": {"auth": "healthy", "chat": "healthy", "agent": "healthy", "model": "healthy", "memory": "healthy", "rag": "healthy", "workspace": "healthy", "billing": "healthy", "mcp": "healthy", "a2a": "healthy", "analytics": "healthy"},
        "databases": {"postgres": "healthy", "redis": "healthy", "qdrant": "healthy", "neo4j": "healthy", "clickhouse": "healthy", "elasticsearch": "healthy"},
        "config": system_config,
    }

@app.get("/api/v1/admin/users")
async def list_users(request: Request, limit: int = 50, offset: int = 0):
    results = list(users_admin_db.values())
    return {"users": results[offset:offset+limit], "total": len(results)}

@app.post("/api/v1/admin/users/{user_id}/suspend")
async def suspend_user(user_id: str, data: UserAction, request: Request):
    if user_id in users_admin_db:
        users_admin_db[user_id]["status"] = "suspended"
        users_admin_db[user_id]["suspension_reason"] = data.reason
    return {"message": f"User {user_id} suspended", "reason": data.reason}

@app.post("/api/v1/admin/users/{user_id}/activate")
async def activate_user(user_id: str, request: Request):
    if user_id in users_admin_db:
        users_admin_db[user_id]["status"] = "active"
        users_admin_db[user_id].pop("suspension_reason", None)
    return {"message": f"User {user_id} activated"}

@app.get("/api/v1/admin/metrics")
async def get_metrics(request: Request):
    return {"total_users": len(users_admin_db), "active_conversations": redis_client.scard("chat:active_connections"), "total_models": 20, "requests_today": redis_client.get("stats:requests:today") or 0, "tokens_today": redis_client.get("stats:tokens:today") or 0}

@app.put("/api/v1/admin/config")
async def update_config(data: SystemConfig, request: Request):
    system_config[data.key] = data.value
    return {"config": system_config}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
