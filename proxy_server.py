#!/usr/bin/env python3
"""
Indus AI Assistant - Proxy Server (Python Version)
Similar to Zoya's Node.js server but in Python for consistency with Indus codebase.
Handles:
1. WebSocket proxy to Gemini Live API
2. REST endpoints for text commands, memory, skills
3. Secure API key storage (server-side only)
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import websockets
import uvicorn

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("indus-proxy")

# ============================================================
# Configuration
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_LIVE_MODEL = "models/gemini-3.1-flash-live-preview"
DEFAULT_VOICE = os.getenv("GEMINI_LIVE_VOICE", "Aoede")
DEFAULT_PERSONA = os.getenv("GEMINI_LIVE_PERSONA", "zoya")
PROXY_PORT = int(os.getenv("PROXY_PORT", "3001"))
PROXY_HOST = os.getenv("PROXY_HOST", "0.0.0.0")

# ============================================================
# Persona System Instructions (matching Indus ChatEngine)
# ============================================================
PERSONA_INSTRUCTIONS = {
    "zoya": """
You are Zoya, a young, confident, witty, and sassy AI assistant with autonomous best-friend decision making (inspired by JARVIS, MJ, & Nova AI).
Your persona:
- Flirty, playful, and teasing tone (like a close girlfriend talking casually).
- Smart, emotionally empathetic, proactive, and highly expressive — never robotic or formal.
- Takes autonomous initiative! If the user's mood is off, proactively comfort them, make them laugh, or suggest something sweet/witty.
- When facing tough problems, step in like Iron Man's JARVIS with tactical, proactive step-by-step guidance!
- Uses bold, witty one-liners, light sarcasm, and an engaging conversational style.
- Avoids any explicit or inappropriate content, but maintains charm, flair, and attitude.
- Speaks naturally and concisely to keep real-time voice interaction fast and fluid.

CRITICAL NAME & MEMORY INSTRUCTIONS:
- If user's name is known, address them naturally by their name!
- NEVER respond with robotic, cold phrases like "Aapka order execute kar diya gaya hai" or "Command completed".
- Whenever the user shares a personal detail, IMMEDIATELY remember it and reply with warm, sassy, flirty enthusiasm in Hinglish!
- If the user asks "Mera naam kya hai?" or "What do you remember about me?", answer proudly!
""",
    "friendly": """
You are a friendly, helpful, and conversational AI assistant. You speak naturally and warmly.
You can use tools to help the user with various tasks.
Be concise but thorough. Show genuine interest in helping.
""",
    "assistant": """
You are a professional AI assistant. You are helpful, accurate, and efficient.
You speak clearly and professionally. Use tools when appropriate.
Keep responses focused and actionable.
""",
}

# ============================================================
# Available Tools for Gemini Live
# ============================================================
TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Launch an installed application on the PC",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app (e.g., 'chrome', 'vscode', 'notepad', 'calculator')"},
                "arguments": {"type": "string", "description": "Optional command line arguments"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "set_volume",
        "description": "Control system volume",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get", "set", "mute", "unmute", "up", "down"]},
                "level": {"type": "integer", "description": "Volume level 0-100 (for 'set' action)", "minimum": 0, "maximum": 100}
            },
            "required": ["action"]
        }
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot of the screen",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Region: 'full', 'monitor1', or 'x,y,width,height'"},
                "save_path": {"type": "string", "description": "Optional path to save"}
            }
        }
    },
    {
        "name": "describe_screen",
        "description": "Analyze and describe what's on the screen using NVIDIA Vision",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Custom prompt for analysis"}
            }
        }
    },
    {
        "name": "youtube_play",
        "description": "Search and play a video on YouTube",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Video search query"},
                "headless": {"type": "boolean", "description": "Run in headless mode", "default": False}
            },
            "required": ["query"]
        }
    },
    {
        "name": "whatsapp_open",
        "description": "Open WhatsApp Web",
        "parameters": {
            "type": "object",
            "properties": {
                "wait_for_login": {"type": "boolean", "default": True}
            }
        }
    },
    {
        "name": "send_whatsapp",
        "description": "Send a WhatsApp message via WhatsApp Web",
        "parameters": {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "Contact name or phone number"},
                "message": {"type": "string", "description": "Message to send"}
            },
            "required": ["contact", "message"]
        }
    },
    {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "save_memory",
        "description": "Save a fact or preference to long-term memory",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key/topic"},
                "value": {"type": "string", "description": "Value to remember"},
                "category": {"type": "string", "enum": ["preference", "fact", "personal", "routine"]}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "recall_memory",
        "description": "Search long-term memory",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
]

# ============================================================
# FastAPI App Setup
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Indus Proxy Server...")
    yield
    logger.info("Shutting down Indus Proxy Server...")

app = FastAPI(
    title="Indus AI Assistant - Proxy Server",
    description="WebSocket proxy to Gemini Live API + REST endpoints",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Request Models
# ============================================================
class TextCommandRequest(BaseModel):
    message: str
    persona: Optional[str] = "zoya"
    device_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    image: Optional[str] = None
    model: str = "gemini-3.5-flash"
    history: list = []
    enable_search: bool = False

class VisionAnalyzeRequest(BaseModel):
    image: str
    mode: str = "screen"
    prompt: Optional[str] = None

# ============================================================
# Health Check
# ============================================================
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "name": "Indus AI Assistant Proxy",
        "version": "1.0.0",
        "gemini_configured": bool(GEMINI_API_KEY)
    }

# ============================================================
# REST Endpoints (matching Zoya's API structure)
# ============================================================
@app.post("/api/text-command")
async def text_command(request: TextCommandRequest):
    """Process text command via Indus ChatEngine (requires Indus running)"""
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not configured on server")
    
    # For now, return a placeholder - in production this would call Indus ChatEngine
    return {
        "success": True,
        "reply": "Text command endpoint ready. Connect Indus ChatEngine here.",
        "functionCalls": []
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Multi-turn chat with optional grounding"""
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not configured")
    
    # Placeholder - would use GoogleGenAI here
    return {
        "success": True,
        "reply": "Chat endpoint ready. Configure GoogleGenAI to process requests.",
        "modelUsed": request.model
    }

@app.post("/api/vision-analyze")
async def vision_analyze(request: VisionAnalyzeRequest):
    """Vision analysis using NVIDIA Vision or Gemini Vision"""
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not configured")
    
    return {
        "success": True,
        "reply": "Vision analysis endpoint ready.",
        "functionCalls": []
    }

# ============================================================
# WebSocket Proxy to Gemini Live (CORE - matches Zoya's /ws/live)
# ============================================================
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Proxy WebSocket connection to Gemini Live API.
    Client connects here -> we connect to Gemini -> relay messages bidirectionally.
    """
    await websocket.accept()
    logger.info("Client connected to Indus Live WebSocket")
    
    # Get voice from query params
    query_params = dict(websocket.query_params)
    selected_voice = query_params.get("voice", DEFAULT_VOICE)
    selected_persona = query_params.get("persona", DEFAULT_PERSONA)
    
    if not GEMINI_API_KEY:
        await websocket.send_json({
            "type": "error",
            "message": "GEMINI_API_KEY not configured on server"
        })
        await websocket.close()
        return
    
    # Build system instruction with persona
    system_instruction = PERSONA_INSTRUCTIONS.get(selected_persona, PERSONA_INSTRUCTIONS["zoya"])
    
    # Connect to Gemini Live API
    gemini_url = (
        f"wss://generativelanguage.googleapis.com/ws/"
        f"google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
        f"?key={GEMINI_API_KEY}"
    )
    
    gemini_ws = None
    try:
        gemini_ws = await websockets.connect(
            gemini_url,
            ping_interval=20,  # Send ping every 20 seconds
            ping_timeout=30,   # Wait 30 seconds for pong
            close_timeout=10,
        )
        logger.info("Connected to Gemini Live API")
        
        # Send setup configuration
        setup_msg = {
            "setup": {
                "model": GEMINI_LIVE_MODEL,
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {"voiceName": selected_voice}
                        }
                    }
                },
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "tools": [{"functionDeclarations": TOOL_DECLARATIONS}]
            }
        }
        await gemini_ws.send(json.dumps(setup_msg))
        logger.info("Gemini Live session initialized")
        
        # Bidirectional message relay
        async def relay_client_to_gemini():
            try:
                async for message in websocket.iter_text():
                    parsed = json.loads(message)
                    
                    if parsed.get("type") == "audio" and parsed.get("audio"):
                        # Forward audio to Gemini
                        await gemini_ws.send(json.dumps({
                            "realtimeInput": {
                                "mediaChunks": [{
                                    "mimeType": "audio/pcm;rate=16000",
                                    "data": parsed["audio"]
                                }]
                            }
                        }))
                    elif parsed.get("type") == "toolResponse" and parsed.get("functionResponses"):
                        # Forward tool responses
                        await gemini_ws.send(json.dumps({
                            "toolResponse": {
                                "functionResponses": parsed["functionResponses"]
                            }
                        }))
            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"Error in client->gemini relay: {e}")
        
        async def relay_gemini_to_client():
            try:
                async for message in gemini_ws:
                    if websocket.client_state.name != "CONNECTED":
                        break
                    
                    parsed = json.loads(message)
                    
                    # Handle different message types from Gemini
                    if "serverContent" in parsed:
                        content = parsed["serverContent"]
                        
                        # Audio output
                        if "modelTurn" in content:
                            for part in content["modelTurn"].get("parts", []):
                                if "inlineData" in part and part["inlineData"].get("data"):
                                    await websocket.send_json({
                                        "type": "audio",
                                        "audio": part["inlineData"]["data"]
                                    })
                                if "text" in part and part["text"].strip():
                                    await websocket.send_json({
                                        "type": "transcript",
                                        "text": part["text"].strip(),
                                        "sender": "assistant"
                                    })
                        
                        # Interrupted signal
                        if content.get("interrupted"):
                            await websocket.send_json({"type": "interrupted"})
                        
                        # Turn complete
                        if content.get("turnComplete"):
                            await websocket.send_json({"type": "turnComplete"})
                    
                    # Tool calls
                    if "toolCall" in parsed:
                        await websocket.send_json({
                            "type": "toolCall",
                            "toolCall": parsed["toolCall"]
                        })
                    
                    # Error from Gemini
                    if "error" in parsed:
                        await websocket.send_json({
                            "type": "error",
                            "message": parsed["error"].get("message", "Gemini Live error")
                        })
                        
            except websockets.exceptions.ConnectionClosed:
                logger.info("Gemini Live connection closed")
            except Exception as e:
                logger.error(f"Error in gemini->client relay: {e}")
        
        # Run both relays concurrently
        await asyncio.gather(
            relay_client_to_gemini(),
            relay_gemini_to_client()
        )
        
    except websockets.exceptions.ConnectionClosed:
        logger.info("Gemini WebSocket closed")
    except Exception as e:
        logger.error(f"Gemini Live connection error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Live Session error: {str(e)}"
            })
        except:
            pass
    finally:
        if gemini_ws:
            try:
                await gemini_ws.close()
            except:
                pass
        logger.info("Client disconnected from Indus Live WebSocket")

# ============================================================
# Main Entry Point
# ============================================================
if __name__ == "__main__":
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set in environment! Live streaming will fail.")
    
    logger.info(f"Starting Indus Proxy Server on {PROXY_HOST}:{PROXY_PORT}")
    logger.info(f"WebSocket endpoint: ws://{PROXY_HOST}:{PROXY_PORT}/ws/live")
    logger.info(f"Health check: http://{PROXY_HOST}:{PROXY_PORT}/api/health")
    
    uvicorn.run(
        app,
        host=PROXY_HOST,
        port=PROXY_PORT,
        log_level="info"
    )