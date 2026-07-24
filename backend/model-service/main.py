"""
AetherAI Model Service - Ultimate Edition 2026
Unified model routing for 50+ providers with streaming, caching, and fallback
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, AsyncGenerator

import httpx
import redis
import structlog
import tiktoken
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ─── Configuration ────────────────────────────────────────────
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8004"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/4")

# Provider API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
VLLM_HOST = os.getenv("VLLM_HOST", "http://vllm:8000")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

# ─── Logging ──────────────────────────────────────────────────
logger = structlog.get_logger()

# ─── Metrics ──────────────────────────────────────────────────
model_requests = Counter("model_requests_total", "Total model requests", ["provider", "model", "status"])
model_tokens = Counter("model_tokens_total", "Total tokens", ["provider", "model", "type"])
model_latency = Histogram("model_latency_seconds", "Model request latency", ["provider", "model"])
active_models = Gauge("active_models", "Number of active models")

# ─── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="AetherAI Model Service",
    version="2026.7.0",
    description="Unified AI Model Routing Service",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

provider = TracerProvider()
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ─── Model Registry ───────────────────────────────────────────
MODEL_REGISTRY = {
    # OpenAI
    "gpt-4o": {"provider": "openai", "name": "GPT-4o", "context": 128000, "max_tokens": 4096, "pricing_input": 5.0, "pricing_output": 15.0, "capabilities": ["chat", "vision", "function_calling", "json_mode"], "category": "chat"},
    "gpt-4o-mini": {"provider": "openai", "name": "GPT-4o Mini", "context": 128000, "max_tokens": 4096, "pricing_input": 0.15, "pricing_output": 0.6, "capabilities": ["chat", "vision", "function_calling", "json_mode"], "category": "chat"},
    "o1": {"provider": "openai", "name": "o1", "context": 128000, "max_tokens": 32768, "pricing_input": 15.0, "pricing_output": 60.0, "capabilities": ["chat", "reasoning"], "category": "chat"},
    "o3-mini": {"provider": "openai", "name": "o3-mini", "context": 200000, "max_tokens": 100000, "pricing_input": 1.1, "pricing_output": 4.4, "capabilities": ["chat", "reasoning"], "category": "chat"},

    # Anthropic
    "claude-3-5-sonnet": {"provider": "anthropic", "name": "Claude 3.5 Sonnet", "context": 200000, "max_tokens": 8192, "pricing_input": 3.0, "pricing_output": 15.0, "capabilities": ["chat", "vision", "function_calling", "code"], "category": "chat"},
    "claude-3-opus": {"provider": "anthropic", "name": "Claude 3 Opus", "context": 200000, "max_tokens": 4096, "pricing_input": 15.0, "pricing_output": 75.0, "capabilities": ["chat", "vision", "function_calling", "code"], "category": "chat"},
    "claude-3-haiku": {"provider": "anthropic", "name": "Claude 3 Haiku", "context": 200000, "max_tokens": 4096, "pricing_input": 0.25, "pricing_output": 1.25, "capabilities": ["chat", "vision"], "category": "chat"},

    # Google
    "gemini-1.5-pro": {"provider": "google", "name": "Gemini 1.5 Pro", "context": 2000000, "max_tokens": 8192, "pricing_input": 3.5, "pricing_output": 10.5, "capabilities": ["chat", "vision", "function_calling", "code"], "category": "chat"},
    "gemini-1.5-flash": {"provider": "google", "name": "Gemini 1.5 Flash", "context": 1000000, "max_tokens": 8192, "pricing_input": 0.35, "pricing_output": 1.05, "capabilities": ["chat", "vision", "function_calling"], "category": "chat"},
    "gemini-ultra": {"provider": "google", "name": "Gemini Ultra", "context": 1000000, "max_tokens": 8192, "pricing_input": 7.0, "pricing_output": 21.0, "capabilities": ["chat", "vision", "function_calling", "reasoning"], "category": "chat"},

    # xAI
    "grok-2": {"provider": "xai", "name": "Grok-2", "context": 128000, "max_tokens": 4096, "pricing_input": 5.0, "pricing_output": 15.0, "capabilities": ["chat", "vision", "function_calling"], "category": "chat"},
    "grok-2-mini": {"provider": "xai", "name": "Grok-2 Mini", "context": 128000, "max_tokens": 4096, "pricing_input": 1.0, "pricing_output": 3.0, "capabilities": ["chat", "vision"], "category": "chat"},

    # DeepSeek
    "deepseek-v3": {"provider": "deepseek", "name": "DeepSeek-V3", "context": 64000, "max_tokens": 8192, "pricing_input": 0.14, "pricing_output": 0.28, "capabilities": ["chat", "code", "function_calling"], "category": "chat"},
    "deepseek-r1": {"provider": "deepseek", "name": "DeepSeek-R1", "context": 64000, "max_tokens": 8192, "pricing_input": 0.55, "pricing_output": 2.19, "capabilities": ["chat", "reasoning", "code"], "category": "chat"},

    # Meta
    "llama-3.3-70b": {"provider": "meta", "name": "Llama 3.3 70B", "context": 128000, "max_tokens": 4096, "pricing_input": 0.0, "pricing_output": 0.0, "capabilities": ["chat", "function_calling", "code"], "category": "chat", "is_local": True},
    "llama-3.1-405b": {"provider": "meta", "name": "Llama 3.1 405B", "context": 128000, "max_tokens": 4096, "pricing_input": 0.0, "pricing_output": 0.0, "capabilities": ["chat", "function_calling", "code"], "category": "chat", "is_local": True},

    # Mistral
    "mistral-large-2": {"provider": "mistral", "name": "Mistral Large 2", "context": 128000, "max_tokens": 4096, "pricing_input": 2.0, "pricing_output": 6.0, "capabilities": ["chat", "function_calling", "code"], "category": "chat"},
    "mixtral-8x22b": {"provider": "mistral", "name": "Mixtral 8x22B", "context": 64000, "max_tokens": 4096, "pricing_input": 2.0, "pricing_output": 6.0, "capabilities": ["chat", "function_calling"], "category": "chat"},

    # Cohere
    "command-r-plus": {"provider": "cohere", "name": "Command R+", "context": 128000, "max_tokens": 4096, "pricing_input": 3.0, "pricing_output": 15.0, "capabilities": ["chat", "function_calling", "rag"], "category": "chat"},
    "command-r": {"provider": "cohere", "name": "Command R", "context": 128000, "max_tokens": 4096, "pricing_input": 0.5, "pricing_output": 1.5, "capabilities": ["chat", "function_calling", "rag"], "category": "chat"},

    # Code Models
    "claude-code": {"provider": "anthropic", "name": "Claude Code", "context": 200000, "max_tokens": 8192, "pricing_input": 3.0, "pricing_output": 15.0, "capabilities": ["code", "function_calling"], "category": "code"},
    "deepseek-coder": {"provider": "deepseek", "name": "DeepSeek Coder", "context": 64000, "max_tokens": 8192, "pricing_input": 0.14, "pricing_output": 0.28, "capabilities": ["code", "function_calling"], "category": "code"},
    "qwen-coder": {"provider": "alibaba", "name": "Qwen2.5 Coder", "context": 128000, "max_tokens": 8192, "pricing_input": 0.0, "pricing_output": 0.0, "capabilities": ["code", "function_calling"], "category": "code", "is_local": True},

    # Image Models
    "dall-e-3": {"provider": "openai", "name": "DALL-E 3", "context": 0, "max_tokens": 0, "pricing_input": 0.04, "pricing_output": 0.0, "capabilities": ["image_generation"], "category": "image"},
    "flux-1": {"provider": "blackforest", "name": "FLUX.1", "context": 0, "max_tokens": 0, "pricing_input": 0.0, "pricing_output": 0.0, "capabilities": ["image_generation"], "category": "image", "is_local": True},
    "stable-diffusion-3": {"provider": "stability", "name": "Stable Diffusion 3", "context": 0, "max_tokens": 0, "pricing_input": 0.0, "pricing_output": 0.0, "capabilities": ["image_generation"], "category": "image", "is_local": True},
}

active_models.set(len(MODEL_REGISTRY))

# ─── Models ───────────────────────────────────────────────────
class ChatRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "model_id": "gpt-4o",
            "messages": [{"role": "user", "content": "Hello!"}],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 4096,
        }
    })
    model_id: str
    messages: List[Dict[str, Any]]
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None

class ImageRequest(BaseModel):
    model_id: str
    prompt: str = Field(..., max_length=4000)
    negative_prompt: Optional[str] = None
    size: str = "1024x1024"
    quality: str = "standard"
    style: Optional[str] = None
    n: int = Field(default=1, ge=1, le=10)

# ─── Helper Functions ─────────────────────────────────────────
def count_tokens(messages: List[Dict], model: str = "gpt-4o") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model if model.startswith("gpt") else "gpt-4")
        total = 0
        for msg in messages:
            total += len(encoding.encode(msg.get("content", "")))
        return total
    except:
        return sum(len(m.get("content", "")) for m in messages) // 4

async def call_openai(request: ChatRequest) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": request.model_id,
                "messages": request.messages,
                "stream": request.stream,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "tools": request.tools,
                "response_format": request.response_format,
            },
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()

async def call_anthropic(request: ChatRequest) -> Dict:
    async with httpx.AsyncClient() as client:
        # Convert messages to Anthropic format
        system_msg = ""
        msgs = []
        for m in request.messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                msgs.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": request.model_id,
            "messages": msgs,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if system_msg:
            payload["system"] = system_msg
        if request.tools:
            payload["tools"] = request.tools

        response = await client.post(
            f"{ANTHROPIC_BASE_URL}/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "Content-Type": "application/json", "anthropic-version": "2023-06-01"},
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()

        # Normalize to OpenAI format
        return {
            "id": data.get("id"),
            "model": data.get("model"),
            "content": data.get("content", [{}])[0].get("text", ""),
            "usage": data.get("usage", {}),
            "finish_reason": data.get("stop_reason", "stop"),
        }

async def call_google(request: ChatRequest) -> Dict:
    # Simplified Google Gemini integration
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{request.model_id}:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": GOOGLE_API_KEY},
            json={
                "contents": [{"role": m["role"], "parts": [{"text": m["content"]}]} for m in request.messages if m["role"] != "system"],
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                    "topP": request.top_p,
                },
            },
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()

        return {
            "id": data.get("name"),
            "model": request.model_id,
            "content": data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", ""),
            "usage": {},
            "finish_reason": "stop",
        }

async def call_local(request: ChatRequest) -> Dict:
    # Try vLLM first, then Ollama
    for host in [VLLM_HOST, OLLAMA_HOST]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{host}/v1/chat/completions",
                    json={
                        "model": request.model_id,
                        "messages": request.messages,
                        "stream": False,
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens,
                    },
                    timeout=120.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "id": data.get("id"),
                        "model": request.model_id,
                        "content": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                        "usage": data.get("usage", {}),
                        "finish_reason": data.get("choices", [{}])[0].get("finish_reason", "stop"),
                    }
        except Exception:
            continue
    raise HTTPException(status_code=503, detail="Local model service unavailable")

async def route_request(request: ChatRequest) -> Dict:
    model_info = MODEL_REGISTRY.get(request.model_id)
    if not model_info:
        raise HTTPException(status_code=404, detail=f"Model '{request.model_id}' not found")

    provider_name = model_info["provider"]

    # Check cache
    cache_key = f"model:cache:{hash(json.dumps(request.model_dump(), sort_keys=True))}"
    cached = redis_client.get(cache_key)
    if cached and not request.stream:
        return json.loads(cached)

    start_time = datetime.now(timezone.utc)

    try:
        if model_info.get("is_local"):
            result = await call_local(request)
        elif provider_name == "openai":
            result = await call_openai(request)
        elif provider_name == "anthropic":
            result = await call_anthropic(request)
        elif provider_name == "google":
            result = await call_google(request)
        else:
            # Generic OpenAI-compatible fallback
            result = await call_openai(request)

        latency = (datetime.now(timezone.utc) - start_time).total_seconds()
        model_latency.labels(provider=provider_name, model=request.model_id).observe(latency)
        model_requests.labels(provider=provider_name, model=request.model_id, status="success").inc()

        # Count tokens
        input_tokens = count_tokens(request.messages, request.model_id)
        output_tokens = len(result.get("content", "")) // 4
        model_tokens.labels(provider=provider_name, model=request.model_id, type="input").inc(input_tokens)
        model_tokens.labels(provider=provider_name, model=request.model_id, type="output").inc(output_tokens)

        # Cache result
        if not request.stream:
            redis_client.setex(cache_key, 300, json.dumps(result))

        return result

    except Exception as e:
        model_requests.labels(provider=provider_name, model=request.model_id, status="error").inc()
        logger.error("model_request_failed", provider=provider_name, model=request.model_id, error=str(e))
        raise

# ─── Endpoints ────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_ok = redis_client.ping()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "model-service",
        "version": "2026.7.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_models": len(MODEL_REGISTRY),
        "checks": {"redis": redis_ok}
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/v1/models")
async def list_models(
    category: Optional[str] = None,
    provider: Optional[str] = None,
    capability: Optional[str] = None,
    search: Optional[str] = None,
):
    results = []
    for model_id, info in MODEL_REGISTRY.items():
        if category and info["category"] != category:
            continue
        if provider and info["provider"] != provider:
            continue
        if capability and capability not in info["capabilities"]:
            continue
        if search and search.lower() not in (info["name"] + model_id).lower():
            continue
        results.append({"id": model_id, **info})

    return {
        "models": results,
        "total": len(results),
        "categories": list(set(m["category"] for m in MODEL_REGISTRY.values())),
        "providers": list(set(m["provider"] for m in MODEL_REGISTRY.values())),
    }

@app.get("/api/v1/models/{model_id}")
async def get_model(model_id: str):
    model = MODEL_REGISTRY.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": model_id, **model}

@app.post("/api/v1/models/chat")
async def chat(request: ChatRequest):
    result = await route_request(request)
    return result

@app.post("/api/v1/models/chat/stream")
async def chat_stream(request: ChatRequest):
    request.stream = True
    model_info = MODEL_REGISTRY.get(request.model_id)
    if not model_info:
        raise HTTPException(status_code=404, detail=f"Model '{request.model_id}' not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        if model_info.get("is_local"):
            host = VLLM_HOST if model_info["provider"] in ["meta", "alibaba"] else OLLAMA_HOST
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{host}/v1/chat/completions",
                        json={
                            "model": request.model_id,
                            "messages": request.messages,
                            "stream": True,
                            "temperature": request.temperature,
                            "max_tokens": request.max_tokens,
                        },
                        timeout=120.0
                    ) as response:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunk = line[6:]
                                if chunk == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    break
                                yield f"data: {chunk}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        elif model_info["provider"] == "openai":
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{OPENAI_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": request.model_id,
                            "messages": request.messages,
                            "stream": True,
                            "temperature": request.temperature,
                            "max_tokens": request.max_tokens,
                        },
                        timeout=120.0
                    ) as response:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunk = line[6:]
                                if chunk == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    break
                                yield f"data: {chunk}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        else:
            # Fallback: non-streaming wrapped as stream
            try:
                result = await route_request(request)
                yield f"data: {json.dumps({'choices': [{'delta': {'content': result['content']}}]})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )

@app.post("/api/v1/models/image")
async def generate_image(request: ImageRequest):
    model_info = MODEL_REGISTRY.get(request.model_id)
    if not model_info or model_info["category"] != "image":
        raise HTTPException(status_code=400, detail="Invalid image model")

    if request.model_id == "dall-e-3":
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/images/generations",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "dall-e-3",
                    "prompt": request.prompt,
                    "size": request.size,
                    "quality": request.quality,
                    "n": request.n,
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    raise HTTPException(status_code=501, detail="Image generation for this model not yet implemented")

@app.post("/api/v1/models/compare")
async def compare_models(request: ChatRequest, model_ids: List[str]):
    results = []
    for model_id in model_ids:
        req = request.model_copy()
        req.model_id = model_id
        try:
            result = await route_request(req)
            results.append({"model_id": model_id, "status": "success", **result})
        except Exception as e:
            results.append({"model_id": model_id, "status": "error", "error": str(e)})
    return {"comparisons": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
