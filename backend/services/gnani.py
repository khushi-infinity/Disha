import httpx
from backend.config import settings

def configured(): return bool(settings.gnani_api_key)

async def synthesize(text: str, language: str = "hi-IN"):
    if not configured(): return None
    payload={"text": text, "voice": settings.gnani_tts_voice, "model": settings.gnani_tts_model, "language": language, "speed": 0.92,
             "audio_config":{"sample_rate":48000,"num_channels":1,"sample_width":2,"encoding":"linear_pcm","container":"wav"}}
    async with httpx.AsyncClient(timeout=40) as client:
        r=await client.post(f"{settings.gnani_api_base_url}/api/v1/tts/inference", json=payload, headers={"X-API-Key-ID":settings.gnani_api_key})
        r.raise_for_status(); return r.content, r.headers.get("content-type", "audio/wav")
