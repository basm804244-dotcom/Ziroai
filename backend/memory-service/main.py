"""
AetherAI Memory Service - Ultimate Edition 2026
Multi-layer memory: Vector (Qdrant) + Graph (Neo4j) + SQL (PostgreSQL) + Cache (Redis)
"""

import os
import uuid
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import httpx
import redis
import structlog
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from neo4j import GraphDatabase
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ─── Configuration ────────────────────────────────────────────
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8005"))
DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/5")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "aether_neo4j_2026")

# ─── Logging ──────────────────────────────────────────────────
logger = structlog.get_logger()

# ─── Metrics ──────────────────────────────────────────────────
memory_ops = Counter("memory_operations_total", "Memory operations", ["type", "operation"])
memory_search = Histogram("memory_search_duration_seconds", "Memory search duration")

# ─── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="AetherAI Memory Service",
    version="2026.7.0",
    description="Multi-Layer Memory Engine: Vector + Graph + SQL + Cache",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

provider = TracerProvider()
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

# ─── Clients ──────────────────────────────────────────────────
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Initialize Qdrant collections
try:
    qdrant.create_collection(
        collection_name="memory_vectors",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
except Exception:
    pass  # Already exists

# ─── Simple embedding function (production: use sentence-transformers) ───
def embed_text(text: str) -> List[float]:
    # Simple hash-based embedding for demo
    # In production, use: from sentence_transformers import SentenceTransformer; model.encode(text)
    h = hashlib.sha256(text.encode()).hexdigest()
    vec = [int(h[i:i+2], 16) / 255.0 for i in range(0, 768, 2)]
    return vec[:768]

# ─── Models ───────────────────────────────────────────────────
class MemoryEntryCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "long_term",
            "key": "user_preference_theme",
            "value": "dark_mode",
            "metadata": {"user_id": "user_123"},
        }
    })
    type: str = Field(..., pattern=r"^(long_term|short_term|episodic|semantic|user|project|team|conversation|knowledge)$")
    key: str = Field(..., min_length=1, max_length=500)
    value: Any
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = {}
    importance: float = Field(default=1.0, ge=0.0, le=10.0)
    expires_at: Optional[str] = None
    tags: List[str] = []

class MemoryQuery(BaseModel):
    query: str = Field(..., min_length=1)
    types: Optional[List[str]] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
    min_importance: float = Field(default=0.0, ge=0.0, le=10.0)

class MemoryUpdate(BaseModel):
    value: Optional[Any] = None
    importance: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    expires_at: Optional[str] = None

# ─── In-Memory DB ─────────────────────────────────────────────
memory_db: Dict[str, Dict] = {}

# ─── Endpoints ────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_ok = redis_client.ping()
    qdrant_ok = False
    neo4j_ok = False
    try:
        qdrant.get_collections()
        qdrant_ok = True
    except:
        pass
    try:
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        neo4j_ok = True
    except:
        pass

    return {
        "status": "healthy" if all([redis_ok, qdrant_ok, neo4j_ok]) else "degraded",
        "service": "memory-service",
        "version": "2026.7.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"redis": redis_ok, "qdrant": qdrant_ok, "neo4j": neo4j_ok}
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/v1/memory")
async def store_memory(data: MemoryEntryCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    memory_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Generate embedding if not provided
    embedding = data.embedding
    if not embedding and isinstance(data.value, str):
        embedding = embed_text(data.value)

    memory = {
        "id": memory_id,
        "type": data.type,
        "key": data.key,
        "value": data.value if isinstance(data.value, str) else json.dumps(data.value),
        "embedding": embedding,
        "metadata": {**(data.metadata or {}), "user_id": user_id},
        "importance": data.importance,
        "tags": data.tags,
        "created_at": now,
        "updated_at": now,
        "expires_at": data.expires_at,
        "access_count": 0,
        "last_accessed": now,
    }
    memory_db[memory_id] = memory

    # Store in Redis (short-term + cache)
    ttl = 86400  # 24 hours default
    if data.expires_at:
        try:
            expiry = datetime.fromisoformat(data.expires_at.replace("Z", "+00:00"))
            ttl = int((expiry - datetime.now(timezone.utc)).total_seconds())
        except:
            pass

    redis_key = f"memory:{data.type}:{user_id}:{data.key}"
    redis_client.setex(redis_key, max(ttl, 60), json.dumps(memory))

    # Store in Qdrant (vector search)
    if embedding:
        try:
            qdrant.upsert(
                collection_name="memory_vectors",
                points=[PointStruct(
                    id=memory_id,
                    vector=embedding,
                    payload={
                        "type": data.type,
                        "key": data.key,
                        "value": memory["value"][:1000] if len(memory["value"]) > 1000 else memory["value"],
                        "metadata": memory["metadata"],
                        "importance": data.importance,
                        "tags": data.tags,
                        "created_at": now,
                    }
                )]
            )
        except Exception as e:
            logger.warning("qdrant_store_failed", error=str(e))

    # Store in Neo4j (graph relationships)
    try:
        with neo4j_driver.session() as session:
            session.run("""
                MERGE (m:Memory {id: $id})
                SET m.type = $type, m.key = $key, m.value = $value,
                    m.importance = $importance, m.created_at = $created_at
                WITH m
                MATCH (u:User {id: $user_id})
                MERGE (u)-[:HAS_MEMORY]->(m)
            """, id=memory_id, type=data.type, key=data.key, value=memory["value"][:500],
                importance=data.importance, created_at=now, user_id=user_id)
    except Exception as e:
        logger.warning("neo4j_store_failed", error=str(e))

    memory_ops.labels(type=data.type, operation="store").inc()
    logger.info("memory_stored", memory_id=memory_id, type=data.type, user_id=user_id)
    return memory

@app.get("/api/v1/memory/{memory_id}")
async def get_memory(memory_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")

    # Try Redis first
    for key in redis_client.scan_iter(match=f"memory:*:{user_id}:*"):
        data = redis_client.get(key)
        if data:
            mem = json.loads(data)
            if mem["id"] == memory_id:
                mem["access_count"] = mem.get("access_count", 0) + 1
                mem["last_accessed"] = datetime.now(timezone.utc).isoformat()
                redis_client.setex(key, 86400, json.dumps(mem))
                memory_ops.labels(type=mem["type"], operation="retrieve").inc()
                return mem

    # Fallback to in-memory
    mem = memory_db.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    if mem["metadata"].get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    mem["access_count"] = mem.get("access_count", 0) + 1
    mem["last_accessed"] = datetime.now(timezone.utc).isoformat()
    memory_ops.labels(type=mem["type"], operation="retrieve").inc()
    return mem

@app.post("/api/v1/memory/search")
async def search_memory(data: MemoryQuery, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")

    results = []

    # 1. Vector search via Qdrant
    query_embedding = embed_text(data.query)
    try:
        search_results = qdrant.search(
            collection_name="memory_vectors",
            query_vector=query_embedding,
            limit=data.limit,
            with_payload=True,
        )
        for hit in search_results:
            payload = hit.payload
            if data.types and payload.get("type") not in data.types:
                continue
            if data.user_id and payload.get("metadata", {}).get("user_id") != data.user_id:
                continue
            if payload.get("importance", 0) < data.min_importance:
                continue
            results.append({
                "id": hit.id,
                "score": hit.score,
                "type": payload.get("type"),
                "key": payload.get("key"),
                "value": payload.get("value"),
                "metadata": payload.get("metadata"),
                "importance": payload.get("importance"),
                "tags": payload.get("tags", []),
                "created_at": payload.get("created_at"),
            })
    except Exception as e:
        logger.warning("vector_search_failed", error=str(e))

    # 2. Fallback: keyword search in Redis
    if len(results) < data.limit:
        for key in redis_client.scan_iter(match=f"memory:*:{user_id}:*"):
            data_str = redis_client.get(key)
            if data_str:
                mem = json.loads(data_str)
                if data.query.lower() in mem.get("value", "").lower() or data.query.lower() in mem.get("key", "").lower():
                    if data.types and mem["type"] not in data.types:
                        continue
                    if mem.get("importance", 0) < data.min_importance:
                        continue
                    if not any(r["id"] == mem["id"] for r in results):
                        results.append({
                            "id": mem["id"],
                            "score": 0.5,
                            "type": mem["type"],
                            "key": mem["key"],
                            "value": mem["value"],
                            "metadata": mem["metadata"],
                            "importance": mem.get("importance", 1.0),
                            "tags": mem.get("tags", []),
                            "created_at": mem["created_at"],
                        })

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    memory_ops.labels(type="all", operation="search").inc()

    return {
        "results": results[:data.limit],
        "total": len(results),
        "query": data.query,
    }

@app.patch("/api/v1/memory/{memory_id}")
async def update_memory(memory_id: str, data: MemoryUpdate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    mem = memory_db.get(memory_id)
    if not mem or mem["metadata"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")

    if data.value is not None:
        mem["value"] = data.value if isinstance(data.value, str) else json.dumps(data.value)
    if data.importance is not None:
        mem["importance"] = data.importance
    if data.metadata is not None:
        mem["metadata"].update(data.metadata)
    if data.tags is not None:
        mem["tags"] = data.tags
    if data.expires_at is not None:
        mem["expires_at"] = data.expires_at
    mem["updated_at"] = datetime.now(timezone.utc).isoformat()

    memory_ops.labels(type=mem["type"], operation="update").inc()
    return mem

@app.delete("/api/v1/memory/{memory_id}")
async def delete_memory(memory_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    mem = memory_db.get(memory_id)
    if not mem or mem["metadata"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")

    del memory_db[memory_id]

    # Remove from Qdrant
    try:
        qdrant.delete(collection_name="memory_vectors", points_selector=[memory_id])
    except:
        pass

    # Remove from Redis
    for key in redis_client.scan_iter(match=f"memory:*:{user_id}:*"):
        data = redis_client.get(key)
        if data and json.loads(data).get("id") == memory_id:
            redis_client.delete(key)

    memory_ops.labels(type=mem["type"], operation="delete").inc()
    return {"message": "Memory deleted"}

@app.get("/api/v1/memory")
async def list_memories(
    request: Request,
    type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    user_id = request.headers.get("X-User-ID", "anonymous")
    results = []
    for mem in memory_db.values():
        if mem["metadata"].get("user_id") == user_id:
            if type and mem["type"] != type:
                continue
            results.append(mem)
    results.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"memories": results[offset:offset+limit], "total": len(results)}

@app.post("/api/v1/memory/consolidate")
async def consolidate_memory(request: Request):
    """Consolidate short-term memories into long-term memory"""
    user_id = request.headers.get("X-User-ID", "anonymous")

    short_term = [m for m in memory_db.values() if m["type"] == "short_term" and m["metadata"].get("user_id") == user_id]

    # Simple consolidation: group by key patterns and create summaries
    consolidated = []
    for mem in short_term:
        if mem.get("access_count", 0) > 2 or mem.get("importance", 0) > 5:
            mem["type"] = "long_term"
            mem["updated_at"] = datetime.now(timezone.utc).isoformat()
            consolidated.append(mem["id"])

    memory_ops.labels(type="consolidation", operation="consolidate").inc()
    return {"consolidated": len(consolidated), "memory_ids": consolidated}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
