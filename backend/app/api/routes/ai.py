"""
AI-specific endpoints for CodeAtlas.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
import asyncio
import json

from app.services.ai.llm_client import llm_client
from app.services.ai.summarizer import summarize_codebase
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explain")
async def ai_explain(
    file_path: str,
    code: str,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Explain a code file using AI.
    """
    if not settings.ENABLE_AI_INSIGHTS:
        raise HTTPException(
            status_code=503,
            detail="AI insights are disabled"
        )
    
    try:
        explanation = summarize_codebase(file_path, code)
        
        return {
            "success": True,
            "file_path": file_path,
            "explanation": explanation,
            "model_used": llm_client.model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI explanation failed: {str(e)}"
        )


@router.post("/ask")
async def ai_ask(
    question: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ask a question about the codebase.
    """
    if not settings.ENABLE_AI_INSIGHTS:
        raise HTTPException(
            status_code=503,
            detail="AI insights are disabled"
        )
    
    try:
        prompt = f"Question: {question}\n\n"
        if context:
            prompt += f"Context:\n{context}\n\n"
        prompt += "Please answer based on the provided context."
        
        result = await llm_client.call_async(
            prompt,
            system_message="You are CodeAtlas AI, an expert code assistant.",
            temperature=0.3
        )
        
        if result["success"]:
            return {
                "success": True,
                "question": question,
                "answer": result["content"],
                "model_used": llm_client.model
            }
        else:
            return {
                "success": False,
                "question": question,
                "error": result.get("error", "Unknown error")
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI query failed: {str(e)}"
        )


@router.websocket("/chat")
async def ai_chat(websocket: WebSocket):
    """
    WebSocket for interactive AI chat with streaming.
    """
    await websocket.accept()
    
    if not settings.ENABLE_AI_INSIGHTS:
        await websocket.send_json({
            "error": "AI insights are disabled",
            "type": "error"
        })
        await websocket.close()
        return
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            question = message.get("question", "")
            context = message.get("context", "")
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "ack",
                "message": "Processing your question..."
            })
            
            # Build prompt
            prompt = f"Question: {question}\n\n"
            if context:
                prompt += f"Context:\n{context}\n\n"
            
            # Stream response
            async for chunk in llm_client.stream(
                prompt,
                system_message="You are CodeAtlas AI. Provide clear, helpful answers about code."
            ):
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk
                })
            
            # Send completion
            await websocket.send_json({
                "type": "complete",
                "message": "Response complete"
            })
            
    except WebSocketDisconnect:
        print("AI chat WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "error": str(e)
        })


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """
    List available Ollama models.
    """
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{llm_client.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    
                    return {
                        "success": True,
                        "models": models,
                        "current_model": llm_client.model,
                        "ollama_url": llm_client.base_url
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to fetch models: {response.status}",
                        "current_model": llm_client.model
                    }
                    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "current_model": llm_client.model
        }


@router.post("/models/switch")
async def switch_model(model_name: str) -> Dict[str, Any]:
    """
    Switch the active LLM model.
    """
    try:
        # Check if model exists
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{llm_client.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    
                    if model_name in models:
                        llm_client.model = model_name
                        return {
                            "success": True,
                            "message": f"Switched to model: {model_name}",
                            "current_model": llm_client.model
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Model {model_name} not found",
                            "available_models": models
                        }
                else:
                    return {
                        "success": False,
                        "error": "Failed to fetch models"
                    }
                    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/status")
async def ai_status() -> Dict[str, Any]:
    """
    Check AI service status.
    """
    try:
        # Test Ollama connection
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{llm_client.base_url}/api/tags", timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    
                    return {
                        "status": "healthy",
                        "ollama_connected": True,
                        "available_models": models,
                        "current_model": llm_client.model,
                        "features": {
                            "summaries": settings.ENABLE_AI_SUMMARIES,
                            "readme": settings.ENABLE_AI_README,
                            "insights": settings.ENABLE_AI_INSIGHTS
                        }
                    }
                else:
                    return {
                        "status": "degraded",
                        "ollama_connected": False,
                        "error": "Ollama not responding",
                        "features": {
                            "summaries": settings.ENABLE_AI_SUMMARIES,
                            "readme": settings.ENABLE_AI_README,
                            "insights": settings.ENABLE_AI_INSIGHTS
                        }
                    }
                    
    except Exception as e:
        return {
            "status": "unhealthy",
            "ollama_connected": False,
            "error": str(e),
            "features": {
                "summaries": settings.ENABLE_AI_SUMMARIES,
                "readme": settings.ENABLE_AI_README,
                "insights": settings.ENABLE_AI_INSIGHTS
            }
        }