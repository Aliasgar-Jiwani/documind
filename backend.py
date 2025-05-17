from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import logging
import re
import os
import json
import asyncio
from typing import Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="TinyLLaMA File Explainer API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request model
class ExplainRequest(BaseModel):
    file_content: str
    file_type: str
    max_chunk_length: int = 500  # Reduced from 1000 for better reliability

# Define response model
class ExplainResponse(BaseModel):
    explanation: str
    status: str
    error: Optional[str] = None

# Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_MODEL = "tinyllama"
FALLBACK_MODELS = ["llama2"]
CPU_ONLY = True
MAX_CONTENT_LENGTH = 5000  # Increased from 1500

async def get_available_models() -> list:
    """Get list of available models from Ollama"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OLLAMA_TAGS_URL)
            if response.status_code == 200:
                models_data = response.json().get("models", [])
                return [model["name"] for model in models_data]
            logger.error(f"Error fetching models, Ollama API status: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Unexpected error fetching models: {str(e)}")
        return []

async def test_model(model_name: str) -> bool:
    """Test if a model works with a simple prompt"""
    try:
        payload = {
            "model": model_name,
            "prompt": "Hello, respond with one word.",
            "stream": False,
            "options": {"num_gpu": 0} if CPU_ONLY else {}
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(OLLAMA_API_URL, json=payload)
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    return bool(response_data.get("response"))
                except json.JSONDecodeError:
                    return False
            return False
    except Exception:
        return False

async def find_working_model() -> Optional[str]:
    """Find a working model from available models"""
    available_models = await get_available_models()
    if not available_models:
        logger.warning("No models available from Ollama.")
        return None

    # Try primary model first
    if OLLAMA_MODEL in available_models:
        if await test_model(OLLAMA_MODEL):
            return OLLAMA_MODEL

    # Try fallback models
    for model in FALLBACK_MODELS:
        if model in available_models and await test_model(model):
            return model

    # Try other available models
    for model in available_models:
        if model not in FALLBACK_MODELS and model != OLLAMA_MODEL:
            if await test_model(model):
                return model

    return None

def split_text(text: str, max_length: int = 500) -> List[str]:
    """Split text into chunks without breaking lines"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_length
        if end >= len(text):
            chunks.append(text[start:])
            break
        # Use \n instead of literal newline
        last_newline = text.rfind('\n', start, end)
        if last_newline != -1:
            chunks.append(text[start:last_newline+1])
            start = last_newline + 1
        else:
            chunks.append(text[start:end])
            start = end
    return chunks

@app.post("/explain", response_model=ExplainResponse)
async def explain_file(request: ExplainRequest):
    # Truncate if necessary
    if len(request.file_content) > MAX_CONTENT_LENGTH:
        logger.warning(f"File content exceeds {MAX_CONTENT_LENGTH} characters, truncating")
        request.file_content = request.file_content[:MAX_CONTENT_LENGTH]

    # Determine working model
    model_to_use = await find_working_model()
    if not model_to_use:
        return ExplainResponse(
            explanation="",
            status="error",
            error="No working model found. Please check Ollama setup."
        )

    # Start with default chunk size
    chunk_size = request.max_chunk_length
    chunks = split_text(request.file_content, chunk_size)
    explanations = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, chunk in enumerate(chunks):
            chunk_prompt = f"""You are an expert technical assistant. Please read the following section of a file and explain it in clear, simple English. This is part of a larger file.
1. Summarize what this section does.
2. Explain important parts, logic, or commands.
3. Be concise and avoid technical jargon.
--- BEGIN SECTION ---
{chunk}
--- END SECTION ---
File type: {request.file_type}
Now provide your explanation for this section:"""

            payload = {
                "model": model_to_use,
                "prompt": chunk_prompt,
                "stream": False
            }
            if CPU_ONLY:
                payload["options"] = {"num_gpu": 0}

            # Retry logic with exponential backoff
            retry_count = 3
            delay = 5
            success = False

            while retry_count > 0 and not success:
                try:
                    logger.info(f"Processing chunk {i+1}/{len(chunks)} (attempt {4 - retry_count})")
                    response = await client.post(OLLAMA_API_URL, json=payload)
                    response_text = response.text  # raw response for debugging

                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            explanation = response_data.get("response", "").strip()
                            if explanation:
                                explanations.append(f"Section {i+1} Explanation:\n{explanation}")
                                success = True
                            else:
                                explanations.append(f"Section {i+1} returned empty explanation.\nRaw response:\n{response_text}")
                                success = True  # Still consider it handled
                        except json.JSONDecodeError as e:
                            explanations.append(f"Section {i+1} JSON decode error: {str(e)}\nRaw response:\n{response_text}")
                            retry_count -= 1
                            if retry_count > 0:
                                logger.warning(f"Retrying chunk {i+1} after JSON decode error. New chunk size: {chunk_size // 2}")
                                chunk_size = max(100, chunk_size // 2)
                                chunks = split_text(request.file_content, chunk_size)
                                break  # Restart loop with smaller chunks
                    else:
                        explanations.append(f"Section {i+1} failed with status {response.status_code}.\nRaw response:\n{response_text}")
                        retry_count -= 1
                        await asyncio.sleep(delay)
                        delay *= 2  # Exponential backoff

                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout) as e:
                    logger.warning(f"Timeout error on chunk {i+1}: {str(e)}. Retrying in {delay}s...")
                    retry_count -= 1
                    await asyncio.sleep(delay)
                    delay *= 2
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    explanations.append(f"Error processing section {i+1}: {str(e)}\nTraceback:\n{tb}")
                    retry_count = 0

            if not success:
                explanations.append(f"Section {i+1} failed after all retries.")

    # Combine explanations
    final_explanation = "\n\n".join(explanations)
    if not final_explanation.strip():
        final_explanation = "Could not generate explanation for any sections."
        return ExplainResponse(
            explanation=final_explanation,
            status="error",
            error="Model returned empty explanation."
        )

    return ExplainResponse(
        explanation=final_explanation,
        status="success",
        error=None
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running."}

@app.get("/ollama-status")
async def ollama_status_endpoint():
    """Check Ollama service status and available models."""
    ollama_running = False
    api_accessible = False
    models_list = []
    primary_model_available = False
    primary_model_working_status = "unknown"

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.get(OLLAMA_TAGS_URL.replace("/api/tags", ""))  # Check base URL
        ollama_running = True
    except httpx.RequestError:
        ollama_running = False

    if ollama_running:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(OLLAMA_TAGS_URL)
                if response.status_code == 200:
                    api_accessible = True
                    models_data = response.json().get("models", [])
                    models_list = [model["name"] for model in models_data]
                    if OLLAMA_MODEL in models_list:
                        primary_model_available = True
                        if await test_model(OLLAMA_MODEL):
                            primary_model_working_status = "working"
                        else:
                            primary_model_working_status = "not_working"
                    else:
                        primary_model_working_status = "not_available"
        except Exception as e:
            logger.error(f"Unexpected error checking Ollama API status: {str(e)}")

    system_info = {"cpu_only_mode_configured_in_backend": CPU_ONLY}
    return {
        "ollama_process_running_or_accessible": ollama_running,
        "ollama_api_accessible": api_accessible,
        "available_models": models_list,
        "primary_model_configured": OLLAMA_MODEL,
        "primary_model_available": primary_model_available,
        "primary_model_status": primary_model_working_status,
        "system_info": system_info,
    }

@app.post("/fix-model")
async def fix_model_endpoint():
    """Attempts to re-pull the primary Ollama model."""
    model_to_fix = OLLAMA_MODEL
    logger.info(f"Attempting to fix model: {model_to_fix} by re-pulling.")
    try:
        command = ["ollama", "pull", f"{model_to_fix}:latest"]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            logger.info(f"Successfully initiated pull for {model_to_fix}. Output: {stdout.decode()}")
            if await test_model(model_to_fix):
                return {"status": "success", "message": f"Successfully pulled and tested {model_to_fix} model."}
            else:
                return {"status": "warning", "message": f"Pulled {model_to_fix}, but it still failed the subsequent test."}
        else:
            error_message = stderr.decode() if stderr else stdout.decode()
            logger.error(f"Failed to pull model {model_to_fix}. Return code: {process.returncode}. Error: {error_message}")
            return {"status": "error", "message": f"Failed to pull model: {error_message}"}
    except FileNotFoundError:
        logger.error("Ollama CLI command not found. Ensure it's installed and in PATH.")
        return {"status": "error", "message": "Ollama CLI not found. Please install Ollama."}
    except Exception as e:
        logger.error(f"Error attempting to fix model {model_to_fix}: {str(e)}")
        return {"status": "error", "message": f"Error attempting to fix model: {str(e)}"}

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)