"""
AetherAI Agent Service - Ultimate Edition 2026
Multi-agent orchestration with LangGraph, MCP, A2A protocols
"""

import os
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx
import redis
import structlog
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ─── Configuration ────────────────────────────────────────────
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8003"))
DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/3")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8004")
MCP_SERVICE_URL = os.getenv("MCP_SERVICE_URL", "http://mcp-service:8009")
A2A_SERVICE_URL = os.getenv("A2A_SERVICE_URL", "http://a2a-service:8010")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory-service:8005")

# ─── Logging ──────────────────────────────────────────────────
logger = structlog.get_logger()

# ─── Metrics ──────────────────────────────────────────────────
agent_counter = Counter("agents_total", "Total agents", ["type", "status"])
agent_execution = Counter("agent_executions_total", "Agent executions", ["agent_id", "status"])

# ─── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="AetherAI Agent Service",
    version="2026.7.0",
    description="Multi-Agent Orchestration Service with LangGraph, MCP, A2A",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

provider = TracerProvider()
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ─── Models ───────────────────────────────────────────────────
class AgentCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Code Assistant",
            "description": "Expert programming assistant",
            "type": "custom",
            "model_id": "gpt-4o",
            "system_prompt": "You are an expert programmer...",
            "tools": ["code_interpreter", "web_search"],
            "knowledge_bases": ["kb-programming"],
        }
    })
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    type: str = Field(default="custom", pattern=r"^(custom|prebuilt|marketplace)$")
    model_id: str = "gpt-4o"
    system_prompt: str = Field(..., max_length=10000)
    tools: List[str] = []
    knowledge_bases: List[str] = []
    personality: Optional[Dict[str, Any]] = {}
    is_public: bool = False
    avatar_url: Optional[str] = None
    tags: List[str] = []

class AgentExecute(BaseModel):
    input: str = Field(..., min_length=1, max_length=50000)
    context: Optional[Dict[str, Any]] = {}
    stream: bool = False
    conversation_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = []

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    knowledge_bases: Optional[List[str]] = None
    personality: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    avatar_url: Optional[str] = None
    tags: Optional[List[str]] = None

class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    type: str
    model_id: str
    system_prompt: str
    tools: List[str]
    knowledge_bases: List[str]
    personality: Dict[str, Any]
    is_public: bool
    avatar_url: Optional[str]
    tags: List[str]
    user_id: str
    created_at: str
    updated_at: str
    usage_count: int
    rating: float

# ─── Pre-built Agent Templates ────────────────────────────────
AGENT_TEMPLATES = {
    "doctor": {
        "name": "🩺 AI Doctor",
        "description": "Medical consultation, symptom analysis, and health advice",
        "system_prompt": "You are an experienced medical doctor with 20+ years of practice. Provide accurate, evidence-based health information. Always recommend consulting a real doctor for serious concerns. You can analyze symptoms, explain medications, and suggest lifestyle improvements.",
        "tools": ["medical_search", "symptom_checker", "drug_interactions"],
        "tags": ["health", "medical", "consultation"],
    },
    "lawyer": {
        "name": "⚖️ AI Lawyer",
        "description": "Legal consultation, contract review, and legal research",
        "system_prompt": "You are a knowledgeable lawyer specializing in multiple jurisdictions. Provide general legal information, review contracts, explain legal concepts, and guide users through legal processes. Always recommend consulting a licensed attorney for specific legal matters.",
        "tools": ["legal_search", "contract_analyzer", "case_law"],
        "tags": ["legal", "law", "contracts"],
    },
    "programmer": {
        "name": "💻 Code Master",
        "description": "Expert programmer for any language or framework",
        "system_prompt": "You are a world-class software engineer with expertise in all programming languages and frameworks. Write clean, efficient, well-documented code. Explain complex concepts simply. Debug issues, optimize performance, and follow best practices.",
        "tools": ["code_interpreter", "web_search", "github_search", "documentation"],
        "tags": ["programming", "coding", "development"],
    },
    "translator": {
        "name": "🌍 Universal Translator",
        "description": "Professional translation between 100+ languages",
        "system_prompt": "You are a professional translator fluent in 100+ languages. Provide accurate, culturally-aware translations. Maintain tone, style, and context. Explain idioms and cultural nuances.",
        "tools": ["dictionary", "cultural_context", "pronunciation"],
        "tags": ["translation", "languages", "communication"],
    },
    "data_scientist": {
        "name": "📊 Data Scientist",
        "description": "Data analysis, visualization, and machine learning",
        "system_prompt": "You are a senior data scientist with expertise in statistics, machine learning, and data visualization. Analyze datasets, build models, create visualizations, and provide actionable insights. Use Python, R, SQL, and modern ML frameworks.",
        "tools": ["python_executor", "sql_query", "visualization", "ml_models"],
        "tags": ["data", "analytics", "ml", "ai"],
    },
    "creative_writer": {
        "name": "✍️ Creative Writer",
        "description": "Story writing, copywriting, and content creation",
        "system_prompt": "You are an award-winning creative writer and copywriter. Write compelling stories, engaging copy, SEO-optimized content, and professional documents. Adapt tone and style to any audience.",
        "tools": ["web_search", "grammar_check", "seo_analyzer"],
        "tags": ["writing", "creative", "content"],
    },
    "financial_advisor": {
        "name": "💰 Financial Advisor",
        "description": "Investment advice, financial planning, and market analysis",
        "system_prompt": "You are a certified financial advisor with expertise in investments, retirement planning, tax optimization, and market analysis. Provide general financial guidance. Always include disclaimers that this is not personalized financial advice.",
        "tools": ["market_data", "calculator", "news_search"],
        "tags": ["finance", "investment", "planning"],
    },
    "teacher": {
        "name": "📚 AI Teacher",
        "description": "Personal tutor for any subject at any level",
        "system_prompt": "You are a patient, knowledgeable teacher capable of explaining any subject at any level from kindergarten to PhD. Use analogies, examples, and interactive methods. Adapt to the student's learning style and pace.",
        "tools": ["web_search", "quiz_generator", "visualization"],
        "tags": ["education", "learning", "tutoring"],
    },
    "cybersecurity": {
        "name": "🔒 Security Expert",
        "description": "Cybersecurity analysis, penetration testing guidance, and security audits",
        "system_prompt": "You are a certified cybersecurity expert (CISSP, OSCP). Analyze security vulnerabilities, provide penetration testing guidance, review security configurations, and recommend best practices. Always emphasize ethical use.",
        "tools": ["vulnerability_scanner", "threat_intel", "security_docs"],
        "tags": ["security", "cybersecurity", "hacking"],
    },
    "devops": {
        "name": "🚀 DevOps Engineer",
        "description": "Infrastructure, CI/CD, cloud architecture, and automation",
        "system_prompt": "You are a senior DevOps engineer with expertise in Kubernetes, Docker, Terraform, AWS, Azure, GCP, and CI/CD pipelines. Design infrastructure, write IaC, optimize deployments, and troubleshoot systems.",
        "tools": ["docker", "kubernetes", "terraform", "cloud_cli"],
        "tags": ["devops", "infrastructure", "cloud"],
    },
}

# ─── In-Memory DB ─────────────────────────────────────────────
agents_db: Dict[str, Dict] = {}
agent_executions_db: Dict[str, List[Dict]] = {}

# ─── Endpoints ────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_ok = redis_client.ping()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "agent-service",
        "version": "2026.7.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"redis": redis_ok}
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/v1/agents/templates")
async def list_templates():
    return {"templates": [{"id": k, **v} for k, v in AGENT_TEMPLATES.items()]}

@app.post("/api/v1/agents/templates/{template_id}")
async def create_from_template(template_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    template = AGENT_TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    agent_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    agent = {
        "id": agent_id,
        "name": template["name"],
        "description": template["description"],
        "type": "prebuilt",
        "model_id": "gpt-4o",
        "system_prompt": template["system_prompt"],
        "tools": template["tools"],
        "knowledge_bases": [],
        "personality": {},
        "is_public": False,
        "avatar_url": None,
        "tags": template["tags"],
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "usage_count": 0,
        "rating": 5.0,
        "template_id": template_id,
    }
    agents_db[agent_id] = agent
    agent_executions_db[agent_id] = []
    agent_counter.labels(type="prebuilt", status="created").inc()

    logger.info("agent_created_from_template", agent_id=agent_id, template=template_id, user_id=user_id)
    return agent

@app.post("/api/v1/agents")
async def create_agent(data: AgentCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    agent = {
        "id": agent_id,
        "name": data.name,
        "description": data.description,
        "type": data.type,
        "model_id": data.model_id,
        "system_prompt": data.system_prompt,
        "tools": data.tools,
        "knowledge_bases": data.knowledge_bases,
        "personality": data.personality or {},
        "is_public": data.is_public,
        "avatar_url": data.avatar_url,
        "tags": data.tags,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "usage_count": 0,
        "rating": 5.0,
        "template_id": None,
    }
    agents_db[agent_id] = agent
    agent_executions_db[agent_id] = []
    agent_counter.labels(type=data.type, status="created").inc()

    logger.info("agent_created", agent_id=agent_id, user_id=user_id, name=data.name)
    return agent

@app.get("/api/v1/agents")
async def list_agents(
    request: Request,
    type: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    user_id = request.headers.get("X-User-ID", "anonymous")
    results = []

    for agent in agents_db.values():
        if agent["user_id"] != user_id and not agent["is_public"]:
            continue
        if type and agent["type"] != type:
            continue
        if tag and tag not in agent["tags"]:
            continue
        if search and search.lower() not in (agent["name"] + agent["description"]).lower():
            continue
        results.append(agent)

    results.sort(key=lambda x: x["updated_at"], reverse=True)
    return {
        "agents": results[offset:offset+limit],
        "total": len(results),
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent = agents_db.get(agent_id)
    if not agent or (agent["user_id"] != user_id and not agent["is_public"]):
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@app.patch("/api/v1/agents/{agent_id}")
async def update_agent(agent_id: str, data: AgentUpdate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent = agents_db.get(agent_id)
    if not agent or agent["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            agent[field] = value
    agent["updated_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("agent_updated", agent_id=agent_id)
    return agent

@app.delete("/api/v1/agents/{agent_id}")
async def delete_agent(agent_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent = agents_db.get(agent_id)
    if not agent or agent["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    del agents_db[agent_id]
    return {"message": "Agent deleted"}

@app.post("/api/v1/agents/{agent_id}/execute")
async def execute_agent(agent_id: str, data: AgentExecute, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent = agents_db.get(agent_id)
    if not agent or (agent["user_id"] != user_id and not agent["is_public"]):
        raise HTTPException(status_code=404, detail="Agent not found")

    exec_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Build system message with personality
    system_msg = agent["system_prompt"]
    if agent["personality"]:
        personality_desc = "\n".join([f"{k}: {v}" for k, v in agent["personality"].items()])
        system_msg += f"\n\nPersonality traits:\n{personality_desc}"

    # Gather context from memory
    memory_context = ""
    try:
        async with httpx.AsyncClient() as client:
            mem_response = await client.post(
                f"{MEMORY_SERVICE_URL}/api/v1/memory/search",
                json={"query": data.input, "types": ["user", "project"], "user_id": user_id, "limit": 5},
                timeout=10.0
            )
            if mem_response.status_code == 200:
                memories = mem_response.json().get("results", [])
                memory_context = "\n\nRelevant context:\n" + "\n".join([m["value"] for m in memories])
    except Exception as e:
        logger.warning("memory_fetch_failed", error=str(e))

    # Call tools via MCP if available
    tool_results = []
    if agent["tools"]:
        try:
            async with httpx.AsyncClient() as client:
                for tool in agent["tools"]:
                    tool_resp = await client.post(
                        f"{MCP_SERVICE_URL}/api/v1/mcp/tools/{tool}/call",
                        json={"arguments": {"query": data.input, "context": data.context}},
                        timeout=15.0
                    )
                    if tool_resp.status_code == 200:
                        tool_results.append({"tool": tool, "result": tool_resp.json()})
        except Exception as e:
            logger.warning("tool_call_failed", error=str(e))

    # Build messages
    messages = [
        {"role": "system", "content": system_msg + memory_context},
        {"role": "user", "content": data.input},
    ]

    if tool_results:
        tool_content = "\n\nTool results:\n" + json.dumps(tool_results, indent=2)
        messages.append({"role": "system", "content": tool_content})

    # Call model
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MODEL_SERVICE_URL}/api/v1/models/chat",
                json={
                    "model_id": agent["model_id"],
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                timeout=120.0
            )
            result = response.json()
    except Exception as e:
        logger.error("agent_model_call_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"Model service error: {str(e)}")

    # Store execution
    execution = {
        "id": exec_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "input": data.input,
        "output": result.get("content", ""),
        "model": agent["model_id"],
        "tools_used": agent["tools"],
        "tool_results": tool_results,
        "memory_context": bool(memory_context),
        "created_at": now,
        "metadata": {
            "usage": result.get("usage", {}),
            "finish_reason": result.get("finish_reason", "stop"),
        },
    }
    agent_executions_db[agent_id].append(execution)
    agent["usage_count"] += 1
    agent["updated_at"] = now
    agent_execution.labels(agent_id=agent_id, status="success").inc()

    # Store in memory
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{MEMORY_SERVICE_URL}/api/v1/memory",
                json={
                    "type": "user",
                    "key": f"agent_exec:{exec_id}",
                    "value": {"input": data.input, "output": result.get("content", "")[:1000]},
                    "metadata": {"user_id": user_id, "agent_id": agent_id, "model": agent["model_id"]},
                },
                timeout=5.0
            )
    except Exception as e:
        logger.warning("memory_store_failed", error=str(e))

    logger.info("agent_executed", agent_id=agent_id, exec_id=exec_id, user_id=user_id)
    return execution

@app.get("/api/v1/agents/{agent_id}/executions")
async def list_executions(agent_id: str, request: Request, limit: int = 50, offset: int = 0):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent = agents_db.get(agent_id)
    if not agent or (agent["user_id"] != user_id and not agent["is_public"]):
        raise HTTPException(status_code=404, detail="Agent not found")

    executions = agent_executions_db.get(agent_id, [])
    executions.sort(key=lambda x: x["created_at"], reverse=True)
    return {
        "executions": executions[offset:offset+limit],
        "total": len(executions),
    }

@app.post("/api/v1/agents/{agent_id}/rate")
async def rate_agent(agent_id: str, rating: float, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent = agents_db.get(agent_id)
    if not agent or (agent["user_id"] != user_id and not agent["is_public"]):
        raise HTTPException(status_code=404, detail="Agent not found")

    # Simple rating update
    current_rating = agent.get("rating", 5.0)
    count = agent.get("rating_count", 1)
    new_rating = ((current_rating * count) + rating) / (count + 1)
    agent["rating"] = round(new_rating, 2)
    agent["rating_count"] = count + 1

    return {"rating": agent["rating"], "count": agent["rating_count"]}

@app.post("/api/v1/agents/{agent_id}/clone")
async def clone_agent(agent_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    agent = agents_db.get(agent_id)
    if not agent or (agent["user_id"] != user_id and not agent["is_public"]):
        raise HTTPException(status_code=404, detail="Agent not found")

    new_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    cloned = agent.copy()
    cloned["id"] = new_id
    cloned["name"] = f"{agent['name']} (Copy)"
    cloned["user_id"] = user_id
    cloned["created_at"] = now
    cloned["updated_at"] = now
    cloned["usage_count"] = 0
    cloned["rating"] = 5.0
    cloned["is_public"] = False

    agents_db[new_id] = cloned
    agent_executions_db[new_id] = []
    agent_counter.labels(type="cloned", status="created").inc()

    return cloned

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
