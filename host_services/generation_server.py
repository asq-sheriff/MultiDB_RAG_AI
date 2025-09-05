#!/usr/bin/env python3
"""
Generation Host Server
=====================

OpenAI-compatible generation API that connects to llama.cpp server.
Runs on host for GPU acceleration.
"""

import asyncio
import aiohttp
import logging
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import time
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Generation Host Server", version="1.0.0")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "qwen2-1.5b-instruct"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-123"
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]

class GenerationRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    search_results: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[ChatMessage]] = []
    model: str = "qwen2-1.5b-instruct"

class GenerationResponse(BaseModel):
    message: str
    message_id: str
    session_id: Optional[str] = None
    response_time_ms: float
    tokens_used: Optional[int] = None
    model: str
    citations: Optional[List[Dict[str, Any]]] = None

LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:8004")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LLAMA_SERVER_URL}/health", timeout=5) as resp:
                if resp.status == 200:
                    return {"status": "healthy", "llama_server": "connected"}
                else:
                    return {"status": "degraded", "llama_server": "disconnected"}
    except:
        return {"status": "degraded", "llama_server": "unreachable"}

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen2-1.5b-instruct",
                "object": "model",
                "owned_by": "host-service"
            }
        ]
    }

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{LLAMA_SERVER_URL}/v1/chat/completions",
                json=request.dict(),
                timeout=30
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=error_text)
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to llama server: {e}")
        raise HTTPException(status_code=503, detail="Generation service unavailable")

@app.post("/generate/response", response_model=GenerationResponse)
async def generate_response(request: GenerationRequest):
    """Generate response compatible with the expected API"""
    start_time = time.time()
    
    try:
        # Build conversation context
        messages = []
        
        # Add conversation history if provided
        if request.conversation_history:
            messages.extend([{"role": msg.role, "content": msg.content} for msg in request.conversation_history])
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Prepare llama.cpp request
        llama_request = {
            "model": request.model,
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.7,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{LLAMA_SERVER_URL}/v1/chat/completions",
                json=llama_request,
                timeout=30
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    # Extract the generated message
                    generated_message = result["choices"][0]["message"]["content"]
                    tokens_used = result.get("usage", {}).get("total_tokens", 0)
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    return GenerationResponse(
                        message=generated_message,
                        message_id=str(uuid4()),
                        session_id=request.session_id,
                        response_time_ms=response_time,
                        tokens_used=tokens_used,
                        model=request.model,
                        citations=None
                    )
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=error_text)
                    
    except aiohttp.ClientError as e:
        logger.warning(f"Llama server unavailable, using fallback response: {e}")
        # Fallback response for demo purposes when llama-server isn't running
        response_time = (time.time() - start_time) * 1000
        fallback_message = f"I understand you're asking about: '{request.message}'. This is a fallback response since the full generation service isn't available. For complete AI capabilities, please start the llama-server."
        
        return GenerationResponse(
            message=fallback_message,
            message_id=str(uuid4()),
            session_id=request.session_id,
            response_time_ms=response_time,
            tokens_used=len(fallback_message.split()),
            model="fallback-demo",
            citations=None
        )

if __name__ == "__main__":
    # Get port from environment or default to 8006
    port = int(os.getenv("GENERATION_SERVICE_PORT", "8006"))
    logger.info(f"🚀 Starting Generation Host Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")