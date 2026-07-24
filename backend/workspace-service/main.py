import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

import redis
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8007"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/7")

logger = structlog.get_logger()
app = FastAPI(title="AetherAI Workspace Service", version="2026.7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class FileCreate(BaseModel):
    path: str
    content: str = ""
    language: str = None

class TerminalCommand(BaseModel):
    command: str
    cwd: str = "/workspace"

class GitOperation(BaseModel):
    operation: str
    args: List[str] = []

workspaces_db: Dict[str, Dict] = {}
files_db: Dict[str, Dict] = {}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "workspace-service", "version": "2026.7.0", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/workspace")
async def create_workspace(request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    ws = {"id": ws_id, "user_id": user_id, "name": f"Workspace {now[:10]}", "files": [], "created_at": now, "updated_at": now}
    workspaces_db[ws_id] = ws
    return ws

@app.get("/api/v1/workspace/{ws_id}")
async def get_workspace(ws_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws = workspaces_db.get(ws_id)
    if not ws or ws["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws

@app.post("/api/v1/workspace/{ws_id}/files")
async def create_file(ws_id: str, data: FileCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws = workspaces_db.get(ws_id)
    if not ws or ws["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    file_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    file = {"id": file_id, "ws_id": ws_id, "path": data.path, "content": data.content, "language": data.language or data.path.split(".")[-1], "created_at": now, "updated_at": now}
    files_db[file_id] = file
    ws["files"].append(file_id)
    ws["updated_at"] = now
    return file

@app.get("/api/v1/workspace/{ws_id}/files/{file_id}")
async def get_file(ws_id: str, file_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws = workspaces_db.get(ws_id)
    if not ws or ws["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    file = files_db.get(file_id)
    if not file or file["ws_id"] != ws_id:
        raise HTTPException(status_code=404, detail="File not found")
    return file

@app.put("/api/v1/workspace/{ws_id}/files/{file_id}")
async def update_file(ws_id: str, file_id: str, data: FileCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws = workspaces_db.get(ws_id)
    if not ws or ws["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    file = files_db.get(file_id)
    if not file or file["ws_id"] != ws_id:
        raise HTTPException(status_code=404, detail="File not found")
    file["content"] = data.content
    file["language"] = data.language or file["language"]
    file["updated_at"] = datetime.now(timezone.utc).isoformat()
    return file

@app.delete("/api/v1/workspace/{ws_id}/files/{file_id}")
async def delete_file(ws_id: str, file_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws = workspaces_db.get(ws_id)
    if not ws or ws["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if file_id in files_db:
        del files_db[file_id]
        ws["files"].remove(file_id)
    return {"message": "File deleted"}

@app.post("/api/v1/workspace/{ws_id}/terminal")
async def execute_terminal(ws_id: str, data: TerminalCommand, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws = workspaces_db.get(ws_id)
    if not ws or ws["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    allowed = ["ls", "cat", "echo", "pwd", "mkdir", "touch", "python", "node", "git", "pip", "npm"]
    cmd = data.command.split()[0]
    if cmd not in allowed:
        raise HTTPException(status_code=403, detail=f"Command '{cmd}' not allowed")
    return {"command": data.command, "output": f"Executed: {data.command}\nSandbox output...", "exit_code": 0, "cwd": data.cwd}

@app.post("/api/v1/workspace/{ws_id}/git")
async def git_operation(ws_id: str, data: GitOperation, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    ws = workspaces_db.get(ws_id)
    if not ws or ws["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"operation": data.operation, "args": data.args, "output": f"Git {data.operation} completed", "status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
