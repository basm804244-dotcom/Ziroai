import httpx
from typing import Optional, Dict, Any

class AetherAIClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.aether.ai", timeout: float = 60.0):
        self.api_key = api_key or self._get_api_key_from_env()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "X-Client-Version": "2026.7.0"},
        )

    def _get_api_key_from_env(self) -> str:
        import os
        key = os.getenv("AETHERAI_API_KEY")
        if not key:
            raise ValueError("AETHERAI_API_KEY not found")
        return key

    def chat(self, messages: list, model: str = "gpt-4o", stream: bool = False) -> Dict:
        return self._client.post("/models/chat", json={"model_id": model, "messages": messages, "stream": stream}).json()

    def list_models(self) -> Dict:
        return self._client.get("/models").json()

    def create_agent(self, name: str, description: str, system_prompt: str) -> Dict:
        return self._client.post("/agents", json={"name": name, "description": description, "system_prompt": system_prompt}).json()

    def execute_agent(self, agent_id: str, input_text: str) -> Dict:
        return self._client.post(f"/agents/{agent_id}/execute", json={"input": input_text}).json()
