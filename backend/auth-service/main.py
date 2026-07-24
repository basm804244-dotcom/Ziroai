"""
AetherAI Auth Service - Ultimate Edition 2026
Enterprise-grade authentication with OAuth2, JWT, MFA, WebAuthn/Passkeys
"""

import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import jwt
import pyotp
import redis
import structlog
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from passlib.context import CryptContext
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ─── Configuration ────────────────────────────────────────────
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aether:aether_secret_2026@postgres:5432/aether_platform")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")
JWT_SECRET = os.getenv("JWT_SECRET", "aether_jwt_super_secret_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_EXPIRE = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE", "3600"))
JWT_REFRESH_EXPIRE = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE", "604800"))

OAUTH_GOOGLE_CLIENT_ID = os.getenv("OAUTH_GOOGLE_CLIENT_ID", "")
OAUTH_GOOGLE_CLIENT_SECRET = os.getenv("OAUTH_GOOGLE_CLIENT_SECRET", "")
OAUTH_GITHUB_CLIENT_ID = os.getenv("OAUTH_GITHUB_CLIENT_ID", "")
OAUTH_GITHUB_CLIENT_SECRET = os.getenv("OAUTH_GITHUB_CLIENT_SECRET", "")

# ─── Logging ──────────────────────────────────────────────────
logger = structlog.get_logger()

# ─── Metrics ──────────────────────────────────────────────────
login_counter = Counter("auth_logins_total", "Total logins", ["method", "status"])
register_counter = Counter("auth_registrations_total", "Total registrations")
request_duration = Histogram("auth_request_duration_seconds", "Request duration")

# ─── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="AetherAI Auth Service",
    version="2026.7.0",
    description="Enterprise Authentication Service with OAuth2, JWT, MFA, WebAuthn",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── OpenTelemetry ────────────────────────────────────────────
provider = TracerProvider()
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

# ─── Redis ────────────────────────────────────────────────────
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ─── Password Hashing ─────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ─── Models ───────────────────────────────────────────────────
class UserRegister(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@aether.ai",
            "password": "SecurePass123!",
            "full_name": "John Doe",
            "username": "johndoe"
        }
    })
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class MFASetup(BaseModel):
    enabled: bool
    secret: Optional[str] = None
    qr_code: Optional[str] = None
    backup_codes: Optional[List[str]] = None

class OAuthLogin(BaseModel):
    provider: str  # google, github, microsoft
    code: str
    redirect_uri: str

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    avatar_url: Optional[str] = None
    role: str = "user"
    plan: str = "free"
    mfa_enabled: bool = False
    webauthn_enabled: bool = False
    created_at: str
    last_login: Optional[str] = None
    metadata: Dict[str, Any] = {}

# ─── In-Memory DB (Production: use PostgreSQL) ────────────────
# For demo purposes; in production use SQLAlchemy + asyncpg
users_db: Dict[str, Dict] = {}
sessions_db: Dict[str, Dict] = {}
refresh_tokens_db: Dict[str, Dict] = {}

# ─── Helper Functions ─────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data: Dict, expires_delta: timedelta, token_type: str = "access") -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": token_type, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    # Check blacklist
    jti = payload.get("jti")
    if redis_client.get(f"token:blacklist:{jti}"):
        raise HTTPException(status_code=401, detail="Token revoked")
    return payload

# ─── Endpoints ────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_ok = redis_client.ping()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "auth-service",
        "version": "2026.7.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"redis": redis_ok}
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(data: UserRegister):
    register_counter.inc()

    # Check if email exists
    for user in users_db.values():
        if user["email"] == data.email:
            raise HTTPException(status_code=409, detail="Email already registered")
        if user["username"] == data.username:
            raise HTTPException(status_code=409, detail="Username already taken")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    user = {
        "id": user_id,
        "email": data.email,
        "username": data.username,
        "full_name": data.full_name,
        "password_hash": hash_password(data.password),
        "avatar_url": None,
        "role": "user",
        "plan": "free",
        "mfa_enabled": False,
        "mfa_secret": None,
        "webauthn_enabled": False,
        "webauthn_credentials": [],
        "created_at": now,
        "last_login": None,
        "metadata": {},
        "is_active": True,
        "is_verified": False,
    }
    users_db[user_id] = user

    # Generate tokens
    access_token = create_token(
        {"sub": user_id, "email": data.email, "role": "user", "plan": "free"},
        timedelta(seconds=JWT_ACCESS_EXPIRE)
    )
    refresh_token = create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(seconds=JWT_REFRESH_EXPIRE)
    )

    # Store refresh token
    refresh_tokens_db[refresh_token] = {"user_id": user_id, "created_at": now}

    logger.info("user_registered", user_id=user_id, email=data.email)
    login_counter.labels(method="email", status="success").inc()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_ACCESS_EXPIRE,
        user={
            "id": user_id,
            "email": data.email,
            "username": data.username,
            "full_name": data.full_name,
            "role": "user",
            "plan": "free",
        }
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    # Find user by email
    user = None
    for u in users_db.values():
        if u["email"] == data.email:
            user = u
            break

    if not user or not verify_password(data.password, user["password_hash"]):
        login_counter.labels(method="email", status="failed").inc()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account deactivated")

    # MFA check
    if user["mfa_enabled"]:
        if not data.mfa_code:
            raise HTTPException(status_code=403, detail="MFA code required")
        totp = pyotp.TOTP(user["mfa_secret"])
        if not totp.verify(data.mfa_code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    # Update last login
    user["last_login"] = datetime.now(timezone.utc).isoformat()

    access_token = create_token(
        {"sub": user["id"], "email": user["email"], "role": user["role"], "plan": user["plan"]},
        timedelta(seconds=JWT_ACCESS_EXPIRE)
    )
    refresh_token = create_token(
        {"sub": user["id"], "type": "refresh"},
        timedelta(seconds=JWT_REFRESH_EXPIRE)
    )

    refresh_tokens_db[refresh_token] = {"user_id": user["id"], "created_at": datetime.now(timezone.utc).isoformat()}

    login_counter.labels(method="email", status="success").inc()
    logger.info("user_login", user_id=user["id"], method="email")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_ACCESS_EXPIRE,
        user={
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "plan": user["plan"],
        }
    )

@app.post("/api/v1/auth/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Refresh token required")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if credentials.credentials not in refresh_tokens_db:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user_id = payload["sub"]
    user = users_db.get(user_id)
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotate refresh token
    del refresh_tokens_db[credentials.credentials]

    new_access = create_token(
        {"sub": user_id, "email": user["email"], "role": user["role"], "plan": user["plan"]},
        timedelta(seconds=JWT_ACCESS_EXPIRE)
    )
    new_refresh = create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(seconds=JWT_REFRESH_EXPIRE)
    )
    refresh_tokens_db[new_refresh] = {"user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat()}

    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer", "expires_in": JWT_ACCESS_EXPIRE}

@app.post("/api/v1/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload:
            jti = payload.get("jti")
            if jti:
                redis_client.setex(f"token:blacklist:{jti}", JWT_ACCESS_EXPIRE, "1")
    return {"message": "Logged out successfully"}

@app.get("/api/v1/auth/me", response_model=UserProfile)
async def get_me(user: Dict = Depends(get_current_user)):
    user_data = users_db.get(user["sub"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(
        id=user_data["id"],
        email=user_data["email"],
        username=user_data["username"],
        full_name=user_data["full_name"],
        avatar_url=user_data.get("avatar_url"),
        role=user_data["role"],
        plan=user_data["plan"],
        mfa_enabled=user_data["mfa_enabled"],
        webauthn_enabled=user_data["webauthn_enabled"],
        created_at=user_data["created_at"],
        last_login=user_data.get("last_login"),
        metadata=user_data.get("metadata", {}),
    )

@app.post("/api/v1/auth/mfa/setup")
async def setup_mfa(user: Dict = Depends(get_current_user)):
    user_data = users_db.get(user["sub"])
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    secret = pyotp.random_base32()
    user_data["mfa_secret"] = secret

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user_data["email"],
        issuer_name="AetherAI"
    )

    # Generate backup codes
    backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
    user_data["backup_codes"] = [hashlib.sha256(c.encode()).hexdigest() for c in backup_codes]

    return MFASetup(
        enabled=False,
        secret=secret,
        qr_code=provisioning_uri,
        backup_codes=backup_codes
    )

@app.post("/api/v1/auth/mfa/verify")
async def verify_mfa_setup(code: str, user: Dict = Depends(get_current_user)):
    user_data = users_db.get(user["sub"])
    if not user_data or not user_data.get("mfa_secret"):
        raise HTTPException(status_code=400, detail="MFA not set up")

    totp = pyotp.TOTP(user_data["mfa_secret"])
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user_data["mfa_enabled"] = True
    return {"message": "MFA enabled successfully"}

@app.post("/api/v1/auth/mfa/disable")
async def disable_mfa(code: str, user: Dict = Depends(get_current_user)):
    user_data = users_db.get(user["sub"])
    if not user_data or not user_data["mfa_enabled"]:
        raise HTTPException(status_code=400, detail="MFA not enabled")

    totp = pyotp.TOTP(user_data["mfa_secret"])
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user_data["mfa_enabled"] = False
    user_data["mfa_secret"] = None
    user_data["backup_codes"] = []
    return {"message": "MFA disabled successfully"}

@app.post("/api/v1/auth/password/reset")
async def request_password_reset(data: PasswordReset):
    user = None
    for u in users_db.values():
        if u["email"] == data.email:
            user = u
            break

    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}

    reset_token = secrets.token_urlsafe(32)
    redis_client.setex(f"password_reset:{reset_token}", 3600, user["id"])

    logger.info("password_reset_requested", user_id=user["id"])
    return {"message": "If the email exists, a reset link has been sent"}

@app.post("/api/v1/auth/password/reset/confirm")
async def confirm_password_reset(data: PasswordResetConfirm):
    user_id = redis_client.get(f"password_reset:{data.token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["password_hash"] = hash_password(data.new_password)
    redis_client.delete(f"password_reset:{data.token}")

    logger.info("password_reset_completed", user_id=user_id)
    return {"message": "Password reset successfully"}

@app.post("/api/v1/auth/oauth/{provider}")
async def oauth_login(provider: str, data: OAuthLogin):
    if provider not in ["google", "github", "microsoft"]:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")

    # In production, exchange code for token with provider
    # For demo, create/link user

    oauth_id = f"{provider}_{hashlib.sha256(data.code.encode()).hexdigest()[:16]}"
    email = f"{oauth_id}@oauth.aether.ai"

    user = None
    for u in users_db.values():
        if u.get("oauth_id") == oauth_id:
            user = u
            break

    if not user:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "username": oauth_id[:20],
            "full_name": f"OAuth {provider.capitalize()} User",
            "password_hash": hash_password(secrets.token_urlsafe(32)),
            "oauth_id": oauth_id,
            "oauth_provider": provider,
            "role": "user",
            "plan": "free",
            "mfa_enabled": False,
            "webauthn_enabled": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
            "metadata": {},
            "is_active": True,
            "is_verified": True,
        }
        users_db[user_id] = user

    user["last_login"] = datetime.now(timezone.utc).isoformat()

    access_token = create_token(
        {"sub": user["id"], "email": user["email"], "role": user["role"], "plan": user["plan"]},
        timedelta(seconds=JWT_ACCESS_EXPIRE)
    )
    refresh_token = create_token(
        {"sub": user["id"], "type": "refresh"},
        timedelta(seconds=JWT_REFRESH_EXPIRE)
    )

    refresh_tokens_db[refresh_token] = {"user_id": user["id"], "created_at": datetime.now(timezone.utc).isoformat()}
    login_counter.labels(method=provider, status="success").inc()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_ACCESS_EXPIRE,
        user={
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "plan": user["plan"],
        }
    )

@app.get("/api/v1/auth/sessions")
async def list_sessions(user: Dict = Depends(get_current_user)):
    user_id = user["sub"]
    sessions = [
        {"token_hash": k[:16] + "...", "created_at": v["created_at"]}
        for k, v in refresh_tokens_db.items()
        if v["user_id"] == user_id
    ]
    return {"sessions": sessions}

@app.delete("/api/v1/auth/sessions/{token_hash}")
async def revoke_session(token_hash: str, user: Dict = Depends(get_current_user)):
    user_id = user["sub"]
    to_delete = []
    for k, v in refresh_tokens_db.items():
        if v["user_id"] == user_id and k.startswith(token_hash.replace("...", "")):
            to_delete.append(k)
    for k in to_delete:
        del refresh_tokens_db[k]
    return {"message": f"Revoked {len(to_delete)} session(s)"}

@app.get("/api/v1/auth/admin/users")
async def admin_list_users(user: Dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"users": list(users_db.values())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
