"""
app.py
------
FastAPI backend for the SetuBot customer support chatbot demo.

Endpoints:
  POST /api/chat    -> {session_id, message} -> bot reply + quick replies + meta
  POST /api/reset    -> {session_id} -> clears that session's conversation state
  GET  /api/health   -> liveness check

Run with:
  uvicorn app:app --reload --port 8001
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import dialogue_manager

app = FastAPI(title="SetuBot — Customer Support Chatbot Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only — restrict to the bank's actual domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    result = dialogue_manager.handle_message(req.session_id, req.message)
    return result


@app.post("/api/reset")
def reset(req: ResetRequest):
    dialogue_manager.SESSIONS.pop(req.session_id, None)
    return {"status": "reset", "session_id": req.session_id}
