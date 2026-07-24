import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

import stripe
import redis
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8008"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/8")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

stripe.api_key = STRIPE_SECRET_KEY
logger = structlog.get_logger()
app = FastAPI(title="AetherAI Billing Service", version="2026.7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class SubscriptionCreate(BaseModel):
    price_id: str
    payment_method_id: str = None

class UsageRecord(BaseModel):
    user_id: str
    model_id: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0

subscriptions_db: Dict[str, Dict] = {}
usage_db: Dict[str, List[Dict]] = {}

PLANS = {
    "free": {"name": "Free", "price": 0, "limits": {"tokens_per_day": 10000, "agents": 3, "memory": 100}},
    "pro": {"name": "Pro", "price": 29, "limits": {"tokens_per_day": 1000000, "agents": 20, "memory": 10000}},
    "enterprise": {"name": "Enterprise", "price": 299, "limits": {"tokens_per_day": -1, "agents": -1, "memory": -1}},
}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "billing-service", "version": "2026.7.0", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/billing/plans")
async def list_plans():
    return {"plans": PLANS}

@app.post("/api/v1/billing/subscriptions")
async def create_subscription(data: SubscriptionCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    sub_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    sub = {"id": sub_id, "user_id": user_id, "price_id": data.price_id, "status": "active", "current_period_start": now, "current_period_end": (datetime.now(timezone.utc) + __import__("datetime").timedelta(days=30)).isoformat(), "cancel_at_period_end": False, "created_at": now}
    subscriptions_db[sub_id] = sub
    return sub

@app.get("/api/v1/billing/subscriptions")
async def get_subscription(request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    for sub in subscriptions_db.values():
        if sub["user_id"] == user_id:
            return sub
    return {"plan": "free", "status": "active"}

@app.post("/api/v1/billing/usage")
async def record_usage(data: UsageRecord):
    record = {"id": str(uuid.uuid4()), "user_id": data.user_id, "model_id": data.model_id, "tokens_input": data.tokens_input, "tokens_output": data.tokens_output, "cost": data.cost, "timestamp": datetime.now(timezone.utc).isoformat()}
    if data.user_id not in usage_db:
        usage_db[data.user_id] = []
    usage_db[data.user_id].append(record)
    return record

@app.get("/api/v1/billing/usage")
async def get_usage(request: Request, days: int = 30):
    user_id = request.headers.get("X-User-ID", "anonymous")
    records = usage_db.get(user_id, [])
    total_cost = sum(r["cost"] for r in records)
    total_tokens = sum(r["tokens_input"] + r["tokens_output"] for r in records)
    return {"usage": records[-100:], "total_cost": round(total_cost, 4), "total_tokens": total_tokens}

@app.post("/api/v1/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if event["type"] == "invoice.payment_succeeded":
        logger.info("payment_succeeded", invoice=event["data"]["object"]["id"])
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
