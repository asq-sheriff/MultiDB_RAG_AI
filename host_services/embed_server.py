#!/usr/bin/env python3
"""
BGE Large Embeddings Server - Host Service for GPU Acceleration
Runs on macOS host with Metal/MPS support for optimal M1 performance
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging
import time
import os
from typing import List
from contextlib import asynccontextmanager
import torch
import numpy as np

# Check MPS availability
print(f"🔧 PyTorch version: {torch.__version__}")
print(f"🔧 MPS available: {torch.backends.mps.is_available()}")
print(f"🔧 MPS built: {torch.backends.mps.is_built()}")

try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:
    print("❌ FlagEmbedding not installed. Install with: pip install FlagEmbedding")
    exit(1)

# Configuration
MODEL_ID = "BAAI/bge-large-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBEDDING_DIM = 1024

# Global model instance
model = None

class EmbeddingRequest(BaseModel):
    model: str
    input: List[str]

class SingleTextRequest(BaseModel):
    text: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print(f"🔄 Loading BGE model: {MODEL_ID}")
    start_time = time.time()
    
    try:
        # Use MPS if available, fallback to CPU
        device = ['mps'] if torch.backends.mps.is_available() else ['cpu']
        print(f"🎯 Using device: {device}")
        
        model = BGEM3FlagModel(
            MODEL_ID, 
            use_fp16=True if device == ['mps'] else False,
            devices=device
        )
        
        # Test the model
        test_result = model.encode(["Test embedding generation"])
        test_embedding = test_result["dense_vecs"][0]
        
        load_time = time.time() - start_time
        print(f"✅ BGE model loaded successfully in {load_time:.2f}s")
        print(f"✅ Model dimension: {len(test_embedding)}")
        print(f"✅ Ready to serve embeddings on all interfaces")
        
    except Exception as e:
        print(f"❌ Failed to load BGE model: {e}")
        raise
    
    yield
    
    # Cleanup on shutdown
    model = None
    print("🔄 BGE model unloaded")


# FastAPI app with lifespan
app = FastAPI(
    title="BGE Embeddings Server", 
    description="GPU-accelerated embeddings on M1 Metal",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "bge-embeddings-server",
        "model": MODEL_ID,
        "dimension": EMBEDDING_DIM,
        "device": "mps" if torch.backends.mps.is_available() else "cpu"
    }

@app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """OpenAI-compatible embeddings endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        start_time = time.time()
        
        # Add query prefix for search optimization
        prefixed_texts = [QUERY_PREFIX + text for text in request.input]
        
        # Generate embeddings
        embeddings_result = model.encode(prefixed_texts)
        vectors = embeddings_result["dense_vecs"]
        
        # Manually normalize embeddings (L2 normalization)
        normalized_vectors = []
        for vector in vectors:
            norm = np.linalg.norm(vector)
            if norm > 0:
                normalized_vectors.append(vector / norm)
            else:
                normalized_vectors.append(vector)
        vectors = normalized_vectors
        
        # Format response in OpenAI style
        data = []
        for i, vector in enumerate(vectors):
            data.append({
                "object": "embedding",
                "embedding": vector.tolist(),
                "index": i
            })
        
        processing_time = time.time() - start_time
        
        return {
            "object": "list",
            "data": data,
            "model": MODEL_ID,
            "usage": {
                "prompt_tokens": sum(len(text.split()) for text in request.input),
                "total_tokens": sum(len(text.split()) for text in request.input)
            },
            "processing_time": round(processing_time, 3)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.post("/embed")
async def embed_single_text(request: SingleTextRequest):
    """Single text embedding endpoint (compatible with existing API)"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        start_time = time.time()
        
        # Add query prefix
        prefixed_text = QUERY_PREFIX + request.text
        
        # Generate embedding
        embeddings_result = model.encode([prefixed_text])
        vector = embeddings_result["dense_vecs"][0]
        
        # Manually normalize embedding (L2 normalization)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        processing_time = time.time() - start_time
        
        return {
            "embedding": vector.tolist(),
            "dimension": len(vector),
            "model": MODEL_ID,
            "processing_time": round(processing_time, 3)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.get("/info")
async def model_info():
    """Model information endpoint"""
    return {
        "model_id": MODEL_ID,
        "dimension": EMBEDDING_DIM,
        "device": "mps" if torch.backends.mps.is_available() else "cpu",
        "query_prefix": QUERY_PREFIX,
        "normalization": "L2 normalized",
        "similarity_metric": "cosine"
    }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Starting BGE Embeddings Server...")
    print(f"📍 Model: {MODEL_ID}")
    print(f"📍 Dimension: {EMBEDDING_DIM}")
    print(f"📍 Device: MPS" if torch.backends.mps.is_available() else "CPU")
    print(f"📍 Endpoints: /v1/embeddings (OpenAI), /embed (single), /health, /info")
    
    # Get port from environment or default to 8005
    port = int(os.getenv("EMBEDDING_SERVICE_PORT", "8005"))
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )