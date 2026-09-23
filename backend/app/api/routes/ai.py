"""
AI-specific endpoints for CodeAtlas.
"""
import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.services.ai.llm_client import llm_client
from app.services.ai.summarizer import explain_complex_file

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explain")
async def ai_explain(
    file_path: str,
    code: str,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    if not settings.ENABLE_AI_INSIGHTS:
        raise HTTPException(status_code=503, detail="AI insights are disabled")

    try:
        explanation = await asyncio.to_thread(explain_complex_file, file_path, code)
        return {
            "success": True,
            "file_path": file_path,
            "explanation": explanation,
            "model_used": llm_client.model,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"AI explanation failed: {str(e)}"
        )


@router.post("/ask")
async def ai_ask(
    question: str,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    if not settings.ENABLE_AI_INSIGHTS:
        raise HTTPException(status_code=503, detail="AI insights are disabled")

    try:
        prompt = f"Question: {question}\n\n"
        if context:
            prompt += f"Context:\n{context}\n\n"
        prompt += "Please answer based on the provided context."

        result = await llm_client.call_async(
            prompt,
            system_message="You are CodeAtlas AI, an expert code assistant.",
            temperature=0.3,
        )

        if result["success"]:
            return {
                "success": True,
                "question": question,
                "answer": result["content"],
                "model_used": llm_client.model,
            }
        return {
            "success": False,
            "question": question,
            "error": result.get("error", "Unknown error"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")


@router.websocket("/chat")
async def ai_chat(websocket: WebSocket):
    await websocket.accept()

    if not settings.ENABLE_AI_INSIGHTS:
        await websocket.send_json(
            {"error": "AI insights are disabled", "type": "error"}
        )
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            question = message.get("question", "")
            context = message.get("context", "")

            await websocket.send_json(
                {"type": "ack", "message": "Processing your question..."}
            )

            prompt = f"Question: {question}\n\n"
            if context:
                prompt += f"Context:\n{context}\n\n"

            async for chunk in llm_client.stream(
                prompt,
                system_message="You are CodeAtlas AI. Provide clear, helpful answers about code.",
            ):
                await websocket.send_json({"type": "chunk", "content": chunk})

            await websocket.send_json(
                {"type": "complete", "message": "Response complete"}
            )

    except WebSocketDisconnect:
        print("AI chat WebSocket disconnected")
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{llm_client.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {
                        "success": True,
                        "models": models,
                        "current_model": llm_client.model,
                        "ollama_url": llm_client.base_url,
                    }
                return {
                    "success": False,
                    "error": f"Failed to fetch models: {response.status}",
                    "current_model": llm_client.model,
                }
    except Exception as e:
        return {"success": False, "error": str(e), "current_model": llm_client.model}


@router.post("/models/switch")
async def switch_model(model_name: str) -> Dict[str, Any]:
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{llm_client.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if model_name in models:
                        llm_client.model = model_name
                        return {
                            "success": True,
                            "message": f"Switched to model: {model_name}",
                            "current_model": llm_client.model,
                        }
                    return {
                        "success": False,
                        "error": f"Model {model_name} not found",
                        "available_models": models,
                    }
                return {"success": False, "error": "Failed to fetch models"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/status")
async def ai_status() -> Dict[str, Any]:
    try:
        import aiohttp

        features = {
            "summaries": settings.ENABLE_AI_SUMMARIES,
            "readme": settings.ENABLE_AI_README,
            "insights": settings.ENABLE_AI_INSIGHTS,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{llm_client.base_url}/api/tags", timeout=2
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {
                        "status": "healthy",
                        "ollama_connected": True,
                        "available_models": models,
                        "current_model": llm_client.model,
                        "features": features,
                    }
                return {
                    "status": "degraded",
                    "ollama_connected": False,
                    "error": "Ollama not responding",
                    "features": features,
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "ollama_connected": False,
            "error": str(e),
            "features": {
                "summaries": settings.ENABLE_AI_SUMMARIES,
                "readme": settings.ENABLE_AI_README,
                "insights": settings.ENABLE_AI_INSIGHTS,
            },
        }