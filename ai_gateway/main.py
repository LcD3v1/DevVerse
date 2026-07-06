from __future__ import annotations

import os

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder")

app = FastAPI(
    title="DevVerse AI Gateway",
    description="Proxy seguro para conectar o bot hospedado ao Ollama que roda em uma maquina autorizada.",
    version="0.1.0",
)


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None
    stream: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ollama_host": OLLAMA_HOST}


@app.post("/api/generate")
def generate(payload: GenerateRequest) -> dict[str, str]:
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": payload.model or DEFAULT_MODEL,
                "prompt": payload.prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Ollama indisponivel no AI Gateway") from exc

    return {"response": data.get("response", "")}
