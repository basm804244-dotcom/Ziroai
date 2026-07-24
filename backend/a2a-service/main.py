import os
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

import redis
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8010"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/10")

logger = structlog.get_logger()
app = FastAPI(title="AetherAI A2A Service", version="2026.7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str = "1.0"
    capabilities: Dict[str, Any] = {}
    skills: List[Dict] = []
    defaultInputModes: List[str] = ["text"]
    defaultOutputModes: List[str] = ["text"]

class A2ARegister(BaseModel):
    endpoint: str
    agent_card: AgentCard

class A2ATask(BaseModel):
    id: str = None
    sessionId: str = None
    status: str = "submitted"
    message: Dict[str, Any]

agents_registry: Dict[str, Dict] = {}
tasks_db: Dict[str, Dict] = {}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "a2a-service", "version": "2026.7.0", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/a2a/agents")
async def register_agent(data: A2ARegister):
    agent_id = str(uuid.uuid4())
    agent = {"id": agent_id, "endpoint": data.endpoint, "agent_card": data.agent_card.model_dump(), "status": "online", "last_seen": datetime.now(timezone.utc).isoformat(), "created_at": datetime.now(timezone.utc).isoformat()}
    agents_registry[agent_id] = agent
    redis_client.hset(f"a2a:agent:{agent_id}", mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in agent.items()})
    return agent

@app.get("/api/v1/a2a/agents")
async def list_agents():
    return {"agents": list(agents_registry.values()), "total": len(agents_registry)}

@app.get("/api/v1/a2a/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = agents_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@app.post("/api/v1/a2a/tasks")
async def create_task(data: A2ATask):
    task_id = data.id or str(uuid.uuid4())
    task = {"id": task_id, "sessionId": data.sessionId or str(uuid.uuid4()), "status": data.status, "message": data.message, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    tasks_db[task_id] = task
    return task

@app.get("/api/v1/a2a/tasks/{task_id}")
async def get_task(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
