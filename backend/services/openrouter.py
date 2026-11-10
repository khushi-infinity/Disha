import httpx
from backend.config import settings

SYSTEM = """You are gNani, a warm, patient voice companion for older adults in India. Reply in the user's language (Hindi, Kannada, or English), in 1-2 short sentences. Never invent directions, transit schedules, fares, distance, road names, locations, or safety facts. If navigation data is unavailable, say so plainly. Encourage users to stop safely when confused and never tell them to watch a phone while crossing."""

async def chat(messages):
    if not settings.openrouter_api_key: return None
    payload={"model":settings.openrouter_model,"messages":[{"role":"system","content":SYSTEM}, *messages],"temperature":0.3,"max_tokens":160}
    headers={"Authorization":f"Bearer {settings.openrouter_api_key}","HTTP-Referer":"http://localhost:5173","X-Title":"gNani AI"}
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(f"{settings.openrouter_base_url}/chat/completions",json=payload,headers=headers); r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()
