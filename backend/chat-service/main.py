"""
AetherAI Chat Service - Ultimate Edition 2026
Real-time chat with WebSocket, streaming, multi-model support
"""

import os
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, AsyncGenerator

import httpx
import redis
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ─── Configuration ────────────────────────────────────────────
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8002"))
DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/2")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://model-service:8004")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory-service:8005")

# ─── Logging ──────────────────────────────────────────────────
logger = structlog.get_logger()

# ─── Metrics ──────────────────────────────────────────────────
message_counter = Counter("chat_messages_total", "Total messages", ["role", "model"])
conversation_counter = Counter("chat_conversations_total", "Total conversations created")
ws_connections = Counter("chat_websocket_connections_total", "WebSocket connections")

# ─── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="AetherAI Chat Service",
    version="2026.7.0",
    description="Real-time Chat Service with WebSocket and Streaming",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

provider = TracerProvider()
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

# ─── Redis ────────────────────────────────────────────────────
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ─── Models ───────────────────────────────────────────────────
class MessageCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"content": "Hello, AI!", "role": "user", "attachments": []}})
    content: str = Field(..., min_length=1, max_length=100000)
    role: str = Field(default="user", pattern=r"^(user|assistant|system|tool)$")
    attachments: Optional[List[Dict[str, Any]]] = []
    metadata: Optional[Dict[str, Any]] = {}

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    model_id: str = "gpt-4o"
    system_prompt: Optional[str] = None
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    model_id: str
    system_prompt: Optional[str]
    project_id: Optional[str]
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

class StreamingChunk(BaseModel):
    id: str
    conversation_id: str
    content: str
    role: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None

# ─── In-Memory DB ─────────────────────────────────────────────
conversations_db: Dict[str, Dict] = {}
messages_db: Dict[str, List[Dict]] = {}

# ─── Connection Manager ───────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_rooms: Dict[str, set] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        redis_client.sadd("chat:active_connections", client_id)
        ws_connections.inc()
        logger.info("websocket_connected", client_id=client_id)

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        redis_client.srem("chat:active_connections", client_id)
        for room, clients in self.user_rooms.items():
            clients.discard(client_id)
        logger.info("websocket_disconnected", client_id=client_id)

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast_to_room(self, message: dict, room_id: str):
        if room_id in self.user_rooms:
            for client_id in self.user_rooms[room_id]:
                await self.send_personal_message(message, client_id)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

# ─── Endpoints ────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_ok = redis_client.ping()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "chat-service",
        "version": "2026.7.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_connections": redis_client.scard("chat:active_connections"),
        "checks": {"redis": redis_ok}
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/v1/chat/conversations", response_model=ConversationResponse)
async def create_conversation(data: ConversationCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conversation = {
        "id": conv_id,
        "title": data.title or f"New Chat ({now[:10]})",
        "model_id": data.model_id,
        "system_prompt": data.system_prompt,
        "project_id": data.project_id,
        "user_id": user_id,
        "messages": [],
        "created_at": now,
        "updated_at": now,
        "metadata": data.metadata or {},
    }
    conversations_db[conv_id] = conversation
    messages_db[conv_id] = []
    conversation_counter.inc()

    if data.system_prompt:
        messages_db[conv_id].append({
            "id": str(uuid.uuid4()),
            "role": "system",
            "content": data.system_prompt,
            "created_at": now,
            "metadata": {}
        })

    logger.info("conversation_created", conv_id=conv_id, user_id=user_id, model=data.model_id)
    return ConversationResponse(**conversation)

@app.get("/api/v1/chat/conversations")
async def list_conversations(request: Request, limit: int = 50, offset: int = 0):
    user_id = request.headers.get("X-User-ID", "anonymous")
    user_convs = [
        c for c in conversations_db.values()
        if c["user_id"] == user_id
    ]
    user_convs.sort(key=lambda x: x["updated_at"], reverse=True)
    return {
        "conversations": user_convs[offset:offset+limit],
        "total": len(user_convs),
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/chat/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    conv = conversations_db.get(conv_id)
    if not conv or conv["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv["messages"] = messages_db.get(conv_id, [])
    return ConversationResponse(**conv)

@app.patch("/api/v1/chat/conversations/{conv_id}")
async def update_conversation(conv_id: str, data: ConversationUpdate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    conv = conversations_db.get(conv_id)
    if not conv or conv["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if data.title is not None:
        conv["title"] = data.title
    if data.model_id is not None:
        conv["model_id"] = data.model_id
    if data.system_prompt is not None:
        conv["system_prompt"] = data.system_prompt
    if data.metadata is not None:
        conv["metadata"].update(data.metadata)
    conv["updated_at"] = datetime.now(timezone.utc).isoformat()

    return conv

@app.delete("/api/v1/chat/conversations/{conv_id}")
async def delete_conversation(conv_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    conv = conversations_db.get(conv_id)
    if not conv or conv["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del conversations_db[conv_id]
    del messages_db[conv_id]
    return {"message": "Conversation deleted"}

@app.post("/api/v1/chat/conversations/{conv_id}/messages")
async def send_message(conv_id: str, data: MessageCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    conv = conversations_db.get(conv_id)
    if not conv or conv["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    message = {
        "id": msg_id,
        "role": data.role,
        "content": data.content,
        "attachments": data.attachments or [],
        "created_at": now,
        "metadata": data.metadata or {},
    }
    messages_db[conv_id].append(message)
    conv["updated_at"] = now
    message_counter.labels(role=data.role, model=conv["model_id"]).inc()

    # Store in memory service
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{MEMORY_SERVICE_URL}/api/v1/memory",
                json={
                    "type": "conversation",
                    "key": f"conv:{conv_id}:msg:{msg_id}",
                    "value": message,
                    "metadata": {"user_id": user_id, "conversation_id": conv_id, "model_id": conv["model_id"]},
                },
                timeout=5.0
            )
    except Exception as e:
        logger.warning("memory_store_failed", error=str(e))

    logger.info("message_sent", conv_id=conv_id, msg_id=msg_id, role=data.role)
    return message

@app.post("/api/v1/chat/conversations/{conv_id}/generate")
async def generate_response(conv_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    conv = conversations_db.get(conv_id)
    if not conv or conv["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = messages_db.get(conv_id, [])
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    # Call model service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MODEL_SERVICE_URL}/api/v1/models/chat",
                json={
                    "model_id": conv["model_id"],
                    "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                timeout=120.0
            )
            result = response.json()
    except Exception as e:
        logger.error("model_generation_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"Model service error: {str(e)}")

    assistant_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": result.get("content", ""),
        "model": conv["model_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "usage": result.get("usage", {}),
            "finish_reason": result.get("finish_reason", "stop"),
        },
    }
    messages_db[conv_id].append(assistant_msg)
    conv["updated_at"] = assistant_msg["created_at"]
    message_counter.labels(role="assistant", model=conv["model_id"]).inc()

    return assistant_msg

@app.post("/api/v1/chat/conversations/{conv_id}/generate/stream")
async def stream_response(conv_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    conv = conversations_db.get(conv_id)
    if not conv or conv["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = messages_db.get(conv_id, [])
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    async def event_generator() -> AsyncGenerator[str, None]:
        msg_id = str(uuid.uuid4())
        full_content = ""

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{MODEL_SERVICE_URL}/api/v1/models/chat/stream",
                    json={
                        "model_id": conv["model_id"],
                        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                        "stream": True,
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    },
                    timeout=120.0
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk == "[DONE]":
                                break
                            try:
                                data = json.loads(chunk)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_content += content
                                    yield f"data: {json.dumps({'id': msg_id, 'content': content, 'role': 'assistant', 'model': conv['model_id']})}\n\n"
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error("stream_generation_failed", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Store complete message
        assistant_msg = {
            "id": msg_id,
            "role": "assistant",
            "content": full_content,
            "model": conv["model_id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }
        messages_db[conv_id].append(assistant_msg)
        conv["updated_at"] = assistant_msg["created_at"]
        message_counter.labels(role="assistant", model=conv["model_id"]).inc()

        yield f"data: {json.dumps({'id': msg_id, 'content': '', 'role': 'assistant', 'model': conv['model_id'], 'finish_reason': 'stop'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

# ─── WebSocket ────────────────────────────────────────────────
@app.websocket("/ws/chat/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "join_conversation":
                conv_id = data.get("conversation_id")
                if conv_id not in manager.user_rooms:
                    manager.user_rooms[conv_id] = set()
                manager.user_rooms[conv_id].add(client_id)
                await manager.send_personal_message({"type": "joined", "conversation_id": conv_id}, client_id)

            elif action == "leave_conversation":
                conv_id = data.get("conversation_id")
                if conv_id in manager.user_rooms:
                    manager.user_rooms[conv_id].discard(client_id)

            elif action == "typing":
                conv_id = data.get("conversation_id")
                await manager.broadcast_to_room({
                    "type": "typing",
                    "conversation_id": conv_id,
                    "user_id": data.get("user_id"),
                }, conv_id)

            elif action == "message":
                conv_id = data.get("conversation_id")
                await manager.broadcast_to_room({
                    "type": "new_message",
                    "conversation_id": conv_id,
                    "message": data.get("message"),
                }, conv_id)

            elif action == "ping":
                await manager.send_personal_message({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}, client_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error("websocket_error", client_id=client_id, error=str(e))
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
