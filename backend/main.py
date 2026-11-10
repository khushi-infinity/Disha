import asyncio, base64, json, re
import logging
from contextlib import suppress
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import websockets
import httpx
from backend.config import settings
from backend.models.schemas import ConversationInput
from backend.services.geocoding import search_destination
from backend.services.routing import pedestrian_route
from backend.services.gnani import synthesize, configured
from backend.services.openrouter import chat

app=FastAPI(title="gNani AI")
logger=logging.getLogger("gnani.voice")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def user_language(text: str):
    if any("\u0c80" <= ch <= "\u0cff" for ch in text): return "kn"
    if any("\u0900" <= ch <= "\u097f" for ch in text): return "hi"
    return "en"

def words(language: str):
    return {
        "hi": {"location":"बिलकुल। पहले अपनी जगह की अनुमति दे दीजिए, ताकि मैं सही रास्ता बता सकूँ।", "not_found":"मुझे यह जगह नहीं मिली। कृपया नाम फिर से बोलिए।", "confirm":"क्या आप इस जगह पर जाना चाहती हैं: "},
        "kn": {"location":"ಖಂಡಿತ. ಸರಿಯಾದ ದಾರಿ ಹೇಳಲು ಮೊದಲು ನಿಮ್ಮ ಸ್ಥಳದ ಅನುಮತಿ ನೀಡಿ.", "not_found":"ಈ ಸ್ಥಳ ಸಿಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಹೆಸರನ್ನು ಮತ್ತೆ ಹೇಳಿ.", "confirm":"ನೀವು ಈ ಜಾಗಕ್ಕೆ ಹೋಗಲು ಬಯಸುತ್ತೀರಾ: "},
        "en": {"location":"Of course. Please allow your location first, so I can guide you correctly.", "not_found":"I could not find that place. Please say its name again.", "confirm":"Do you want to go to: "},
    }[language]

def destination_from(text):
    patterns=[r"(?:jana|jaana|go|going|to)\s+(.+)",r"(.+?)\s+(?:jana hai|jaana hai)"]
    for p in patterns:
        m=re.search(p,text,re.I)
        if m: return m.group(1).strip(" ?!.,")
    return text.strip()

@app.get("/api/health")
async def health(): return {"ok":True,"speech_configured":configured(),"llm_configured":bool(settings.openrouter_api_key)}

@app.post("/api/conversation")
async def conversation(body: ConversationInput):
    text=body.text.strip(); lower=text.lower()
    language=user_language(text); text_words=words(language)
    # Navigation requests are fulfilled with verified map data before optional language assistance.
    navigation_request=any(x in lower for x in ["jana", "jaana", "jao", "go to", "route", "raasta", "majestic", "airport", "station", "directions", "take me"])
    if navigation_request and not body.location:
        return {"reply":text_words["location"],"kind":"need_location"}
    if navigation_request:
        query=destination_from(text)
        try:
            choices=await search_destination(query,body.location.lat,body.location.lon)
            if not choices: return {"reply":text_words["not_found"],"kind":"not_found"}
            if len(choices)>1:
                return {"reply":f"{text_words['confirm']}{choices[0]['name']}?","kind":"confirm_destination","choices":choices}
        except httpx.HTTPError: raise HTTPException(503,"Map search is temporarily unavailable. Please try again.")
    reply=await chat(body.history[-6:]+[{"role":"user","content":text}])
    return {"reply": reply or "Main aapki madad ke liye yahin hoon. Aap bataiye, aapko kahan jaana hai?", "kind":"chat"}

@app.post("/api/route")
async def route(body: dict):
    try:
        loc=body["location"]; dest=body["destination"]
        route=await pedestrian_route(loc["lat"],loc["lon"],dest["lat"],dest["lon"])
    except (KeyError, ValueError) as e: raise HTTPException(400,str(e))
    route["destination"]=dest["name"]
    mins=max(1,round(route["duration_s"]/60))
    route["summary"]=f"{dest['name']}: {(route['distance_m']/1000):.1f} km, about {mins} minutes walking. {route['steps'][0] if route['steps'] else ''}"
    return route

@app.post("/api/speak")
async def speak(body: dict):
    result=await synthesize(str(body.get("text",""))[:900],body.get("language","hi-IN"))
    if not result: raise HTTPException(503,"Gnani Timbre is not configured. Add GNANI_API_KEY on the server.")
    audio, content_type=result; return Response(audio,media_type=content_type)

@app.websocket("/ws/stt")
async def stt(ws: WebSocket):
    await ws.accept()
    if not configured():
        await ws.send_json({"type":"error","message":"Speech service is not configured on this server."}); await ws.close(); return
    headers={"x-api-key-id":settings.gnani_api_key,"model":settings.gnani_stt_model,"language_code":"indic-auto","x-sample-rate":"16000","x-vad-threshold":"0.5","x-min-silence-ms":"700","x-min-speech-ms":"100","x-min-segment-ms":"100","x-idle-timeout-sec":"900"}
    try:
        async with websockets.connect(f"{settings.gnani_api_base_url.replace('https://','wss://')}/stt/v3/stream",additional_headers=headers,max_size=2**20) as provider:
            async def receive_provider():
                async for raw in provider:
                    try:
                        event=json.loads(raw)
                        if event.get("type") in {"connected", "processing", "error"}:
                            logger.info("Gnani STT event: %s", event.get("type"))
                    except (json.JSONDecodeError, TypeError):
                        pass
                    await ws.send_text(raw)
            pump=asyncio.create_task(receive_provider())
            try:
                while True:
                    msg=await ws.receive_json()
                    if msg.get("type")=="audio": await provider.send(base64.b64decode(msg["data"]))
                    elif msg.get("type")=="commit": await provider.send(json.dumps({"type":"commit"}))
            finally: pump.cancel();
    except WebSocketDisconnect: pass
    except Exception as exc:
        logger.exception("Gnani STT relay failed: %s", type(exc).__name__)
        with suppress(Exception): await ws.send_json({"type":"error","message":"Speech connection failed. Please try again."})
